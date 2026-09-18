"""Lightweight knowledge retrieval ("local RAG") over Markdown documents.

WHY pure-Python TF-IDF and not embeddings/vector DB?
  WHAT: chunks of the three knowledge files, scored by TF-IDF cosine
        similarity against the query.
  WHY: zero native dependencies (installs anywhere, including fresh Windows
       machines), fully deterministic (testable), and honest about what it
       is: keyword retrieval, not semantic search.
  TRADEOFF: paraphrases the keywords miss ("money back" vs "refund") score
       lower than they would with embeddings. docs/rag-explanation.md shows
       how an EmbeddingRetriever could replace this class behind the same
       ``retrieve(query, top_k)`` interface.
"""
import math
import re
from dataclasses import dataclass
from pathlib import Path

from app.config import REPO_ROOT
from app.logging_config import get_logger

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
DEFAULT_KNOWLEDGE_DIR = REPO_ROOT / "data" / "knowledge"


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """One scored chunk: which document, what text, how strong the match."""

    document: str
    chunk: str
    score: float


@dataclass(frozen=True, slots=True)
class _Chunk:
    """A heading-delimited section of a knowledge document."""

    document: str
    text: str
    tokens: tuple[str, ...]


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens."""
    return _TOKEN_RE.findall(text.lower())


def _split_chunks(document: str, content: str) -> list[_Chunk]:
    """Split Markdown into one chunk per '## section' (fallback: whole doc)."""
    sections = re.split(r"(?m)^##\s+", content)
    chunks: list[_Chunk] = []
    for section in sections:
        text = section.strip()
        if not text or text.startswith("# "):  # skip the top-level title
            continue
        chunks.append(_Chunk(document=document, text=text, tokens=tuple(_tokenize(text))))
    return chunks


class RetrievalService:
    """TF-IDF retriever over the local knowledge base."""

    def __init__(self, knowledge_dir: Path = DEFAULT_KNOWLEDGE_DIR) -> None:
        self._knowledge_dir = knowledge_dir
        self._chunks: list[_Chunk] = []
        self._idf: dict[str, float] = {}
        self._loaded = False

    def _load(self) -> None:
        """Load and index all .md files once (lazy, so tests control timing)."""
        if self._loaded:
            return
        self._loaded = True
        if not self._knowledge_dir.is_dir():
            logger.warning("knowledge dir missing: %s (retrieval disabled)", self._knowledge_dir)
            return
        for path in sorted(self._knowledge_dir.glob("*.md")):
            self._chunks.extend(_split_chunks(path.name, path.read_text(encoding="utf-8")))
        # Inverse document frequency with standard smoothing.
        doc_count = len(self._chunks)
        document_frequency: dict[str, int] = {}
        for chunk in self._chunks:
            for token in set(chunk.tokens):
                document_frequency[token] = document_frequency.get(token, 0) + 1
        self._idf = {
            token: math.log((1 + doc_count) / (1 + df)) + 1.0
            for token, df in document_frequency.items()
        }
        logger.info("knowledge indexed: %d chunks from %s", doc_count, self._knowledge_dir)

    def _tfidf(self, tokens: tuple[str, ...] | list[str]) -> dict[str, float]:
        """Term-frequency * idf vector for a token sequence."""
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        total = max(1, len(tokens))
        return {t: (c / total) * self._idf.get(t, 0.0) for t, c in counts.items()}

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        """Cosine similarity between two sparse vectors."""
        dot = sum(value * b.get(term, 0.0) for term, value in a.items())
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievalResult]:
        """Return the top_k chunks most similar to the query (score > 0)."""
        self._load()
        if not self._chunks:
            return []
        query_vector = self._tfidf(_tokenize(query))
        scored = [
            RetrievalResult(
                document=chunk.document,
                chunk=chunk.text,
                score=self._cosine(query_vector, self._tfidf(chunk.tokens)),
            )
            for chunk in self._chunks
        ]
        scored = [result for result in scored if result.score > 0.0]
        scored.sort(key=lambda result: result.score, reverse=True)
        return scored[:top_k]
