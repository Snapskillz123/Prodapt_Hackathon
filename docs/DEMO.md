# Five-minute demo walkthrough

## Before presenting

Start `npm.cmd run dev`, open localhost:5173, and run `npm.cmd run probe` once. Check quotas.
Use a dedicated demonstration account. Never show API.txt, .env or browser network requests
that might contain personal messages. No secret keys are sent to the browser by this app.

## 0:00–0:40 — user problem and accounts

Explain the coordination problem: destinations, schedules, costs and packing scattered
across tools. Register or sign in. Point out the saved-journey sidebar and guest-free private
workspace. Authentication runs locally without another API key.

## 0:40–1:20 — conversational clarification

Send: “I want a relaxed weekend in Jaipur.”

Show that missing dates, traveler count and budget are requested instead of invented.
Reply with a date within the next week, two days, two travelers and INR 20000 total.

## 1:20–2:30 — generated plan and its boundaries

Show day cards, real place names and Google Maps links. Open Budget to explain group totals,
estimates, excluded travel-to-destination and any shortfall. Open Packing and tick an item.
Point out available forecast dates and uncertainty messages. Download the plan JSON.

## 2:30–3:10 — revisions and persistence

Ask: “Make the second day less busy and reduce transport spending.”

After a successful result, reload and reopen the saved conversation. Explain that older
versions are retained in SQLite and a failed generation leaves the last good plan intact.
Only the latest version is currently exposed in the UI.

## 3:10–4:20 — code walkthrough

1. `schemas.py`: show Profile, PlanDraft, TravelPlan and tool-input schemas.
2. `tools.py`: show Google retrieval, schema-based AI calls and deterministic validation.
3. `nodes.py`: each node invokes one useful named tool.
4. `graph.py`: show the missing-data branch and bounded repair edge.
5. `db.py`: five entities, ownership relationships, transaction and version constraints.
6. `/docs`: show generated request contracts.

Explain API grounding: fetch actual places before generation, pass records as context,
and reject unknown place IDs. This project has no document/vector-search RAG pipeline.

## 4:20–5:00 — evidence and business value

Show the test results and validation boundaries. Discuss proposed outcomes: less repetitive
planning, clearer budget tradeoffs, fewer fabricated locations. Explain future priorities:
verified pricing/opening hours, route calculations and multi-city support. Do not claim
measured business ROI, guaranteed feasibility or production readiness.

## Likely questions

- Why LangGraph? Explicit branching, meaningful tools, controlled retries and inspectable execution.
- Why Pydantic? One source for schemas, runtime constraints and generated API documentation.
- Why SQLite? Simple local persistence; migration to PostgreSQL for multi-worker deployment.
- Why no travel-time guarantee? Only place identities/coordinates are retrieved; buffers are estimates.
- What happens if weather fails? Generate with a warning; no invented forecast.
- What happens if Places fails? Stop safely; do not substitute fabricated attractions.
- Can another user read my trip? Ownership is enforced in SQL for read/write/delete and tested.
- Can prompt injection call arbitrary tools? No: graph-defined nodes call fixed tools/endpoints.
- What does deletion do? Cascades through local account data; it is not forensic disk erasure.
