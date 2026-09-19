# The AI Agent Flow: One Chat Turn, End to End

This document traces exactly what happens when a user sends one message to
`POST /api/v1/chat`, first as a pipeline, then as a verified four-turn
conversation, then in live (real LLM) mode. All behavior described here is
pinned by the test suites (`backend/tests/test_chat.py`,
`mcp_server/tests/test_server.py`).

The orchestrator is `AgentService.handle_chat`
(`backend/app/services/agent_service.py`).

---

## The pipeline

```
USER MESSAGE (message + client-kept history)
  |
  v
1. RETRIEVAL        RetrievalService.retrieve(message, top_k=3)
                    TF-IDF cosine over data/knowledge/*.md chunks.
                    Top score >= 0.15 (RETRIEVAL_THRESHOLD) = strong match.
  |
  v
2. EXTRACTION       accumulate_extraction(message, history)
                    Re-derives all lead fields from EVERY user turn
                    (the server is stateless), resolving short answers
                    against the last question the assistant asked.
  |
  v
3. DECISION         mock policy (MockLLMService.decide)
                    OR live model (OpenAILLMService tool-calling loop)
                    Output: reply to user, or a tool call.
  |
  v
4. TOOL EXECUTION   MCPClientService.call_tool(name, arguments)
                    Per-call Streamable HTTP session to :8001/mcp.
                    Failures become typed errors, not crashes.
  |
  v
5. REPLY            Compose the final text + ChatResponse:
                    reply, lead, tool_activity, retrieval_used, llm_mode
```

Two design facts explain most of what follows:

- **The server is stateless.** There is no conversation table. The client
  sends the whole history each turn, and `accumulate_extraction` re-runs the
  rule-based extractors over every user message in order, merging results
  (newer non-empty values win). That is cheap at demo scale and it is what
  lets "About 500." make sense: `_apply_question_context` looks at the last
  assistant message, sees it asked "how many", and interprets the bare
  number as `monthly_queries`.
- **The mock is a policy, not a puppet.** `MockLLMService.decide` inspects
  the accumulated fields and the message, then CHOOSES to reply or to call a
  real MCP tool. The tool call is a genuine round trip to the MCP server;
  only the decision-maker is deterministic.

### The mock policy, in order

`MockLLMService.decide` checks, in this exact order:

1. **Business-info intent** ("who are you", "about the company", ...) ->
   call `get_business_info`.
2. **Update intent** ("update", "change", "correct") -> build an
   `update_lead` call from the phone plus whatever fields the message
   contains; ask a clarifying question if the phone or the fields are
   missing.
3. **Search intent** ("search", "find my", "look up", "check if", ...) ->
   call `search_lead` with the phone found in the message, or with the
   message minus stopwords.
4. **Knowledge question** (interrogative phrasing or a trailing `?`) AND a
   retrieval hit -> answer from the top chunk and mark `used_knowledge`.
5. **Lead complete** (name, phone, and requirement-or-business-type all
   known) -> call `create_lead` with the accumulated fields.
6. **Nothing known at all** (opening turn) -> greet and invite.
7. **Otherwise** -> ask the next question in a fixed natural order:
   business type, then monthly enquiry volume, then name and phone.

At most one tool call happens per turn in mock mode.

---

## The verified four-turn conversation ("Rahul")

This is the demo script, and it is also a passing test
(`test_full_qualification_conversation_creates_lead`). Watch what the
pipeline does at each step.

### Turn 1

**User:** `I am interested in automating WhatsApp customer support.`

- Retrieval runs (mock mode always passes the results to the policy, but
  this message is not a question, so they go unused).
- Extraction: the trigger "interested in" yields
  `requirement = "WhatsApp customer support automation"` (the extractor
  normalizes "automating X" to "X automation"). No name, phone, or business
  type yet.
- Policy: not an intent, not a question, lead incomplete, but something is
  known, so step 7 fires. Business type is the first missing piece.

**Assistant:** `Absolutely, I can help with that. What type of business do you operate?`

`tool_activity: []`, `lead: null`, `retrieval_used: false`.

### Turn 2

**User:** `Real estate.`

- Extraction: `business_type = "real estate"` (keyword match; the question
  context would also have caught it because the assistant asked about "type
  of business"). Requirement carries over from turn 1 via accumulation.
- Policy: lead still incomplete (no name, no phone). Next missing piece in
  the order is enquiry volume.

**Assistant:** `Thanks! Approximately how many customer enquiries do you receive per month?`

### Turn 3

**User:** `About 500.`

- Extraction: no volume pattern matches ("500" has no unit word), but the
  bare-number extractor finds `500`, and the question context ("how many"
  in the last assistant message) assigns it to `monthly_queries = 500`.
- Policy: name and phone are the last missing pieces.

**Assistant:** `Understood. Could you share your name and phone number so I can record your requirement?`

### Turn 4

**User:** `Rahul, 9876543210.`

- Extraction: `extract_name_phone_pair` parses the compact answer shape into
  `name = "Rahul"`, `phone = "9876543210"`.
- Policy: `missing_for_creation()` is now empty, so the decision is a tool
  call: `create_lead(name="Rahul", phone="9876543210", source="chat",
  business_type="real estate", requirement="WhatsApp customer support
  automation", monthly_queries=500)`.
- Execution: `MCPClientService` opens a session to `http://127.0.0.1:8001/mcp`
  and calls `create_lead`. The MCP server scores the lead with the shared
  formula and inserts the row into the shared SQLite file.
- Reply composition: the confirmation template fills in name, requirement,
  and phone from the tool result.

**Assistant:** `Thanks Rahul! I've recorded your requirement for WhatsApp customer support automation. Our team will reach out to you shortly at 9876543210.`

```json
{
  "lead": {
    "name": "Rahul", "phone": "9876543210",
    "business_type": "real estate",
    "requirement": "WhatsApp customer support automation",
    "monthly_queries": 500,
    "lead_score": 65, "priority": "medium",
    "status": "new", "source": "chat"
  },
  "tool_activity": [
    { "tool": "create_lead", "source": "mcp", "status": "success", "summary": "Lead #12 created" }
  ],
  "retrieval_used": false,
  "llm_mode": "mock"
}
```

### Why the score is exactly 65 (medium)

The deterministic formula (`backend/app/services/scoring.py`):

| Signal                              | Points | Rahul |
|-------------------------------------|--------|-------|
| phone present                       | +20    | yes   |
| email present                       | +10    | no    |
| requirement clear                   | +15    | yes   |
| business type present               | +15    | yes   |
| city present                        | +10    | no    |
| timeline within 3 months            | +15    | no    |
| monthly_queries >= 300              | +15    | yes (500) |
| **Total (clamped 0-100)**           |        | **65** |

Bands: 0-39 low, 40-69 medium, 70-100 high. So 65 is **medium**.

A note on honesty: an early marketing-style brief quoted a score of 85 for
this conversation. That number assumed Rahul also gave an email (+10) and a
city (+10), which he never does in the four turns. The formula above is the
truth, and both test suites pin 65/medium
(`test_chat.py` on the backend side, `test_create_lead_returns_structured_scored_lead`
on the MCP side). Document the formula, not the wish.

### A knowledge-question turn, for contrast

**User:** `What is your refund policy?`

The message is interrogative, retrieval finds the "Refund Policy" chunk in
`data/knowledge/policies.md` above the 0.15 threshold, and the policy
answers from that chunk (heading stripped, body capped at 600 characters):

`Based on our documentation (policies.md): We offer a 14-day money-back guarantee ... Is there anything else you'd like to know?`

Here `retrieval_used` is `true` and `tool_activity[0]` is
`{ "tool": "knowledge_search", "source": "retrieval", "status": "success",
"summary": "Found N relevant knowledge chunk(s)" }`. The UI only reports
retrieval when the answer was actually grounded in it.

### When MCP is down mid-conversation

The turn still returns HTTP 200. The failed `create_lead` becomes an
`error` item in `tool_activity`, `lead` is `null`, and the reply says the
lead-recording service is temporarily unavailable and asks the user to try
again in a moment. Verified by `test_degraded_mode_when_mcp_down`.

---

## Live mode: the OpenAI tool-calling loop

Set `LLM_ENABLED=true` and `LLM_API_KEY=...` (optionally `LLM_BASE_URL` for
OpenRouter, Ollama, vLLM, or any OpenAI-compatible endpoint; `LLM_MODEL`
defaults to `gpt-4o-mini`) and the same endpoint runs a real model instead.

Differences from mock mode:

1. **Knowledge gating.** In live mode the retrieved chunks are only added to
   the system prompt when the top score clears 0.15 (a "strong match"), and
   `retrieval_used` reports exactly that. The system prompt, qualification
   prompt, and knowledge are combined into one system message, followed by
   the history and the current user message (`_build_messages`).
2. **Tool discovery is live.** `_openai_tools` calls `list_tools` on the
   MCP server and converts each tool to an OpenAI function schema. This
   works because an MCP `inputSchema` IS JSON Schema, which is exactly what
   OpenAI function calling expects for `parameters`. If discovery fails (MCP
   down), the model simply gets no tools that turn.
3. **The loop.** Up to `MAX_TOOL_ROUNDS = 3` times: send messages + tools
   with `tool_choice="auto"`; if the model replies with no tool calls, its
   content is the answer; otherwise each requested tool is executed via the
   MCP client, the assistant message and one `tool` message per result are
   appended, and the loop continues. Tool failures are fed back to the model
   as `{"success": false, "error": ...}` payloads so it can react. If all
   three rounds are exhausted without a final answer, the user gets
   "I wasn't able to complete that action just now. Could you rephrase or
   try again?" The cap exists as runaway protection: a model that keeps
   asking for tools forever cannot spin the request.
4. **Fallback to mock.** ANY exception from the live path (network, auth,
   rate limit, malformed response) is caught, logged, and the turn is
   re-served by the mock policy. The response then reports
   `llm_mode: "mock"`, because that is what actually served it. The chat
   endpoint never fails because the LLM provider did.

Mock and live are the same shape on purpose: the `LLMService` protocol
(`mode` + `decide`) plus the `MCPClientLike` protocol mean the agent code
above them does not care which brain or which tool transport is attached.
