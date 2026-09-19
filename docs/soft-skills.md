# Soft Skills and Answer Frameworks

Interviewers score how you think, not just what you know. These four
frameworks give every answer a shape. Practice them until the shape is
automatic, then fill it with Autom8r stories.

---

## Framework 1: TECHNICAL (for "how would you build X?")

**Understand -> Approach -> Implement -> Test**

1. **Understand.** Repeat the requirement back and ask one clarifying
   question. "So the goal is X, and the constraint that matters is Y. Should
   it handle Z as well?"
2. **Approach.** Sketch the design in two or three boxes before code. Name
   the tradeoff you are choosing. "I'd put the tool boundary here, which
   costs an extra hop but keeps the model away from the database."
3. **Implement.** Talk through the build in small pieces, interfaces first.
   "I'd define the response shape first, then the route, then the service."
4. **Test.** Say how you would prove it works before you are asked. "Then I'd
   write the test: this input, this expected status, this expected body."

Example, "how would you add a search endpoint?":
"Understand: search leads by phone or name fragment, read-only. Approach:
one query parameter, a LIKE query with a parameterized pattern, newest first,
capped at 20 rows. Implement: a `search_leads` service function and a thin
route, same envelope as the other list endpoints. Test: seed two leads,
search a fragment, assert count and order; also search garbage and assert an
empty list, not an error. That's exactly how `search_lead` works in Autom8r,
so I've done this one for real."

## Framework 2: DEBUGGING (for "tell me about a bug you fixed")

**Reproduce -> Isolate -> Diagnose -> Fix -> Verify**

1. **Reproduce.** Make it happen on demand. "I got 'database is locked' every
   time the MCP server wrote while the backend was reading."
2. **Isolate.** Shrink the failing case. "I reproduced it with two raw
   connections in a script, no FastAPI involved, so it was SQLite, not my
   routes."
3. **Diagnose.** Find the mechanism, not the symptom. "Default journal mode
   serializes readers and writers. Two processes made that visible."
4. **Fix.** The smallest change that addresses the mechanism. "WAL mode plus
   a busy timeout, set on every connection in both processes."
5. **Verify.** Prove it and lock it in. "A test now writes from both sides;
   and the fix lives in `backend/app/db/database.py` and `mcp_server/db.py`."

Saying the five steps out loud, even quickly, is what separates "I fixed a
bug" from "I debug systems".

## Framework 3: BEHAVIORAL (for "tell me about a time when...")

**Situation -> Action -> Result -> Learning**

Keep Situation to one sentence. Spend your time on Action (what YOU did, not
"we") and Learning (what changed in how you work).

Example, "a time you learned something fast":
"Situation: I decided to build Autom8r's tool layer on MCP, which I had never
used, and half the tutorials described a transport the spec had already
replaced. Action: I ignored the tutorials, read the current spec and the
Python SDK source, built the smallest possible server, and tested it
in-process before wiring it into the backend. Result: a tested four-tool MCP
server over Streamable HTTP, and a backend that talks to it through one small
client module. Learning: for fast-moving technology, primary sources beat
tutorials; and the smallest working version is the fastest teacher."

## Framework 4: UNKNOWN QUESTION (for when you don't know)

**What I know -> What I don't -> How I'd investigate**

Never bluff. Never just say "I don't know" either. Show the shape of your
ignorance and the path out.

Example, "how does Kubernetes autoscaling work?":
"What I know: it schedules containers across machines and can add or remove
replicas based on metrics like CPU. What I don't: the exact algorithms and
knobs, I haven't run it. How I'd investigate: read the official docs'
autoscaling section, then run the smallest local experiment with kind or
minikube and watch replicas react to load. That's the same way I came up to
speed on MCP for this project."

---

## Anti-bluffing coaching

The fastest way to fail a technical interview is to claim depth you don't
have. Interviewers probe. One follow-up question collapses a bluff, and the
whole interview's credibility goes with it. The rule: claim exactly what you
built, say "I don't know, but here's how I'd find out" for the rest. Compare
these pairs.

**MCP**

Bad: "I have extensive experience with the Model Context Protocol and its
various enterprise implementations."
(One probe, "which SDK version and transport?", and this collapses.)

Better: "I implemented MCP using the current Python SDK v2: MCPServer exposes
the lead tools, and the backend connects via an MCP client over Streamable
HTTP. I can show you the four tools, the resource, and the prompt, and the
in-process tests that cover them."

**LLM integration**

Bad: "I integrated advanced AI with RAG and agents, fully production-grade."

Better: "The chat runs in two modes: a live OpenAI-compatible tool-calling
loop capped at three rounds, and a deterministic mock policy that runs the
same pipeline. If the provider throws, the turn falls back to mock and the
response says so. Retrieval is TF-IDF over Markdown chunks; I chose it over
embeddings deliberately, and I can tell you the tradeoff."

**Databases**

Bad: "I'm an expert in SQL and NoSQL at scale."

Better: "Autom8r uses SQLite in WAL mode, shared by two processes; the
backend uses SQLAlchemy 2.0 and the MCP server uses raw parameterized SQL, on
purpose, to show both. I know where SQLite stops fitting and I'd move to
Postgres through the existing DATABASE_URL setting."

**Testing**

Bad: "Everything is fully tested, 100% coverage."

Better: "67 automated tests: 58 backend, 9 for the MCP server. They cover
CRUD status codes, auth failures, webhook dedupe, the full chat-to-lead flow
through the real MCP server, scoring, and retrieval. I haven't measured
coverage as a percentage; the tests target behavior, not lines."

**Security**

Bad: "The app is fully secure."

Better: "Admin routes need a Bearer token, webhooks need a shared secret,
both compared in constant time with hmac.compare_digest. It's demo auth and I
say so in the docs; the production answer is OAuth2 for users and HMAC body
signatures for webhooks, and I can explain both."

**Scale**

Bad: "It scales to millions of users."

Better: "It's a local prototype, and I know the scaling order: Postgres
first, then horizontal scaling of the stateless backend, pooled MCP sessions,
then retrieval and LLM cost work. Nothing in the design blocks that path;
the stateless chat and the per-call MCP client were chosen with it in mind."

**The pattern:** Bad answers inflate and invite a probe. Better answers state
the real scope, name the file or the number, and offer the next level as a
plan, not a claim. "I built X, here's the proof, and here's what I'd do at
the next level" is the strongest sentence a fresher can say.
