# Verification report

Verified on 2026-09-19 in the Windows development workspace.

## Gemini provider migration

The active provider is now Gemini (`gemini-2.5-flash` by default), using native
`generateContent` with JSON output and local Pydantic validation/one repair attempt.
All **64 backend tests passed**, including ten adapter cases for request conversion,
JSON repair, truncated/blocked responses, credential errors, quota errors and model validation.
Live Google Places and Open-Meteo probes passed. Gemini explicitly rejected the supplied
key with `API_KEY_INVALID`; no successful live Gemini generation is claimed.
Replace `GEMINI_API_KEY` in the private `.env` file and restart the backend before retrying.
Earlier Groq results below are historical and do not verify Gemini.

## Final Roam frontend and guided form

- **54 backend tests passed**, including exact form-preference preservation, persisted
  plans, unauthenticated/unknown-conversation access, past dates and provider failures.
- **2 Chrome tests passed**, covering the existing chatbot and new guided form, mobile
  overflow, failure recovery, keyboard tab navigation, packing and authentication.
- **Production Vite build passed.** Desktop/mobile form screenshots were reviewed.
- Dummy JSON validation passed offline, including expected invalid-input rejection and
  the calculated INR 5,400 example total. Browser fixtures now use committed dummy data,
  not a live-plan artifact. No provider calls were made for this frontend verification.
- The final product is the custom Roam React UI. The separate Next.js app is no longer
  an integration dependency. The latest new form workflow has not been live-API tested.

## TripAI extension

The subsequent form/dashboard backend extension passes **51 tests total** (the original
33 plus 18 new TripAI cases). The new authenticated endpoint supports generation and
revision; request/result JSON schemas and the compiled graph were exported successfully.
These new workflow tests use fake providers. The new TripAI workflow has not been live
end-to-end tested, and the unseen Next.js frontend has not been connected or browser-tested.
See `TRIPAI.md` for the provisional frontend contract and remaining integration boundary.

## Original chatbot verification

| Check | Result | Scope |
|---|---|---|
| Python backend suite | 33 passed | Pydantic validation, graph branching and bounded repair, budget/schedule checks, authentication, isolation, persistence and deletion |
| Production frontend build | Passed | Vite build after React component extraction |
| Chrome browser test | 1 passed | Real local registration and account deletion; fixture-backed itinerary rendering, budget, packing, download, desktop/mobile checks |
| Compiled graph export | Passed | `docs/workflow.mmd` generated from the actual graph |
| Earlier live provider probe and itinerary | Passed | Groq, Google Places and Open-Meteo; a complete two-day itinerary traversed all six planning tools |
| Final live itinerary recheck | Provider-limited | Groq returned a usage-limit response during generation; final full live recheck did not complete |

The browser test substitutes the message response with a previously generated sample;
it is not evidence that live provider calls will always succeed. The final code passed
the deterministic backend tests, including final-plan validation and packaging.

Sandbox-only temporary-directory and network access failures were rerun with permission.
The Groq limit occurred with network access permitted, so it is a provider limitation,
not a passing live result. Retry the smoke check once quota is available:

```powershell
.\.venv\Scripts\python.exe -m backend.smoke
```

No performance/load test or independent security audit has been performed. Costs are
unverified estimates, and the application is a local hackathon prototype rather than
a production booking service.
