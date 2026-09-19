# Evaluation evidence map

| Judging category | Evidence in this project | What to explain honestly |
|---|---|---|
| 1. Problem, approach, innovation | Conversational preferences, revisions, weather-aware packing and grounded places | Scope is short leisure trips; no booking engine |
| 2. Prompt engineering and LLM use | Separate extraction/generation prompts in tools.py, schema prompt, bounded repairs | Schema-valid output does not prove factual accuracy |
| 3. Data modeling | Five SQLite entities, ownership FKs, indexes, versioned JSON plans | JSON snapshots are convenient; analytics would need normalized stops |
| 4. Architecture and code flow | schemas.py → tools.py → nodes.py → graph.py; provider adapters separate | Graph is deliberately controlled, not autonomous browsing |
| 5. Stack reasoning | React/FastAPI/Pydantic/LangGraph/SQLite and available APIs | SQLite/process-local throttles fit a demo, not a multi-worker cloud deployment |
| 6. BRD/HLD | BRD-HLD.md, actual workflow.mmd, FastAPI /docs | Requirements trace to acceptance criteria and implementation |
| 7. Testing and reliability | pytest schema/graph/security tests, Playwright, real provider probes | Browser plan provider is mocked; full live graph is separately tested |
| 8. Security and PII | Argon2id, session digests, owner filters, origin checks, deletion, no frontend secrets | No email verification/reset, MFA or database encryption yet |
| 9. Demo and walkthrough | DEMO.md, illustrative screenshots, named tool trace | Do not present estimates as live pricing or buffers as road routing |
| 10. Business value | Clear planning workflow, reuse/revisions, proposed outcome metrics | ROI and adoption remain hypotheses until evaluated with users |

## Suggested follow-up experiments

1. Compare unguided generation against retrieved-place generation on fabricated-place rate.
2. Measure planning completion time for five users with and without Roam.
3. Test a fixed prompt set: missing dates, contradictory budgets, tight budgets, rainy weather,
   unavailable providers, out-of-window dates and requests to ignore system rules.
4. Record successful-plan latency and provider usage without logging personal conversations.
5. Evaluate how well interests and relaxed/busy pacing actually influence generated plans.

## Limits of current validation

Automated checks validate IDs, types, arithmetic and time overlap. They do not verify actual
opening hours, prices, traffic, walking distances, accessibility or whether a landmark is
appropriate for a particular traveler. Explain these boundaries proactively in the demo.
