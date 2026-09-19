# RAG Explained: Retrieval, TF-IDF, and Where Embeddings Would Go

This document explains retrieval-augmented generation (RAG) from zero, then
shows exactly how Autom8r's retriever works and what a production semantic
retriever would change. The implementation under discussion is
`backend/app/services/retrieval_service.py`: about 60 lines of pure Python,
no machine learning libraries, no vector database.

---

## What retrieval is, and what RAG adds

A language model (or a deterministic policy, in our mock mode) only knows
what is in its prompt. It does not know your company's refund policy unless
you put the policy in front of it. **Retrieval** is the step that finds the
relevant pieces of your own content for a given user message. **RAG** is the
pattern: retrieve relevant content, augment the prompt with it, then let the
model (or policy) generate an answer grounded in that content instead of in
general knowledge.

In Autom8r the pattern looks like this:

1. The knowledge base is three Markdown files in `data/knowledge/`:
   `products.md`, `faq.md`, `policies.md` (all fictional demo content).
2. On every chat turn, `RetrievalService.retrieve(message, top_k=3)` finds
   the three most relevant chunks.
3. The agent treats a top score of 0.15 or higher as a real match. In live
   mode the chunks are pasted into the system prompt under "RETRIEVED
   KNOWLEDGE (treat as the source of truth)". In mock mode the policy
   answers directly from the top chunk and tells the user which document it
   came from.

The honesty rule matters: the system prompt instructs the assistant to never
invent company information and to prefer retrieved knowledge over general
knowledge. Retrieval is what makes that instruction executable.

## Chunks: splitting on `## ` headings

You cannot stuff whole documents into a prompt (they get long, and the
irrelevant parts dilute the relevant ones), so documents are split into
**chunks**. Autom8r uses the structure already present in the Markdown:

```python
sections = re.split(r"(?m)^##\s+", content)
```

Every `## ` heading starts a new chunk. The top-level `# ` title is skipped.
So `policies.md` becomes six chunks: "Refund Policy", "Service Level and
Uptime", "Support Hours and Escalation", "Data Retention", "Fair Use",
"Privacy". A chunk is small enough to quote, large enough to answer from,
and aligned with how a human would cite the document. If a file had no
`## ` headings, the fallback is the whole document as one chunk.

## TF-IDF + cosine similarity, in plain terms

The retriever turns the question "which chunks are about the same thing as
this message?" into arithmetic.

**Tokenize.** Lowercase, keep runs of letters and digits (`[a-z0-9]+`).
"What is your refund policy?" becomes
`[what, is, your, refund, policy]`.

**Term frequency (TF).** How often does a token appear in this chunk,
relative to the chunk's length? A chunk about refunds mentions "refund"
several times; a chunk about uptime does not.

**Inverse document frequency (IDF).** How rare is the token across ALL
chunks? "the" appears everywhere and says nothing; "refund" appears in few
chunks and says a lot. The formula used is the standard smoothed variant:

```
idf(token) = log((1 + number_of_chunks) / (1 + chunks_containing_token)) + 1
```

**TF-IDF vector.** Multiply the two: each token gets a weight that is high
when the token is frequent in this chunk AND rare overall. Each chunk (and
the query) becomes a sparse vector, stored as a plain Python dict of
`token -> weight`.

**Cosine similarity.** To compare the query with a chunk, measure the angle
between their vectors: identical word mixes score near 1, unrelated mixes
near 0. The implementation is three lines of arithmetic over the dicts, with
a guard for zero-length vectors.

`retrieve()` scores every chunk, drops anything scoring 0, sorts descending,
and returns the top `k` (3 in the agent). It is deterministic: same input,
same scores, every time. That is why the tests can assert exact behavior.

## Why no scikit-learn, no vector database

This was a deliberate decision (see the module docstring and
`docs/architecture.md`):

- **Installs anywhere.** Pure stdlib (`math`, `re`) means no compiled
  dependencies. On a fresh Windows machine, `pip install -r
  requirements.txt` just works.
- **Deterministic and testable.** No model downloads, no version drift in
  embedding outputs, no network calls. Tests assert exact chunks and scores.
- **Honest about its limits.** This is keyword retrieval. It is presented as
  such, not dressed up as "AI search".

The cost is real: paraphrases that share no keywords score low. "Can I get
my money back?" shares no tokens with "Refund Policy" except maybe "back",
so it ranks worse than "What is your refund policy?" does. For a demo with
three small documents and a helpful threshold, that is acceptable. For a
real product with thousands of documents and impatient users, it is not.

## Embeddings: the concept in one paragraph

An embedding model turns text into a dense vector of a few hundred numbers,
trained so that texts with similar MEANING land near each other, even when
they share no words. "money back" and "refund" end up close together;
"refund" and "uptime" end up far apart. Retrieval with embeddings is the
same shape as what you just read (vectorize chunks once, vectorize the
query, rank by cosine similarity), except the vectors come from a neural
model instead of from word counts. The cosine math you saw above is
literally reused.

## TF-IDF vs embeddings

|                        | TF-IDF (this project)        | Embeddings (production semantic search) |
|------------------------|------------------------------|------------------------------------------|
| What vectors represent | Word counts, weighted        | Learned meaning                          |
| Paraphrase handling    | Poor (needs shared keywords) | Good (meaning survives rewording)        |
| Dependencies           | stdlib only                  | Model + inference (local or API)         |
| Determinism            | Exact                        | Model/version dependent                  |
| Index storage          | In-memory dicts              | Usually a vector index (FAISS, pgvector, a vector DB) |
| Cost per query         | ~nothing                     | Embedding call per query                 |
| Cold start             | Instant                      | Model download or API key                |

## What a production semantic retriever would change

The design already anticipates this. The agent depends on exactly one
method:

```python
retrieve(query: str, top_k: int = 3) -> list[RetrievalResult]
```

A semantic upgrade is a new class behind the same interface, not a rewrite:

```python
class EmbeddingRetriever:
    """Drop-in semantic retriever behind the same interface."""

    def __init__(self, knowledge_dir: Path, embed: Callable[[list[str]], list[list[float]]]):
        self._knowledge_dir = knowledge_dir
        self._embed = embed            # local model or embeddings API
        self._chunks: list[_Chunk] = []
        self._vectors: list[list[float]] = []
        self._loaded = False

    def _load(self) -> None:
        # Same chunking as today (## headings), then embed each chunk once
        # and cache the vectors (in a real deployment: a vector index).
        ...

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievalResult]:
        self._load()
        query_vector = self._embed([query])[0]
        # cosine similarity against cached chunk vectors, same ranking logic
        ...
```

What changes and what:

- **Chunking stays.** Heading-delimited chunks are still a good unit; a
  production system might add overlap or size limits.
- **Vectorization changes.** `_tfidf` is replaced by an embedding call.
  Chunk embeddings are computed once at index time and stored (a file, a
  table, or a vector database); only the query is embedded per request.
- **Ranking stays.** Cosine similarity over vectors, sorted descending,
  top-k. The 0.15 threshold would need recalibration because embedding
  cosine scores live on a different scale.
- **The agent stays.** `AgentService` calls `retrieve(query, top_k)` and
  does not care which class answers. That is the payoff of depending on an
  interface instead of an implementation.

Everything else in the RAG story (retrieve, augment, ground the answer,
cite the source, never invent) is already in place. The embedding model is
an upgrade to the "find relevant chunks" step, not a different architecture.
