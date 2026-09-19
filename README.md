# Roam — a conversational AI travel planner

A local hackathon application with email/password accounts, conversational trip planning,
Google Places retrieval, Open-Meteo forecasts, estimated budgets, packing checklists, and
saved conversations. The original downloaded `../ai-trip-planner` is untouched.

The final UI is our own **Roam React frontend**, not a dependency on the separate
Next.js TripAI project. TripAI inspired the preference fields. Click **Start with trip
details** to enter destination, inclusive dates, travelers, group budget, interests,
pace and requirements, or start directly in chat. Form-generated plans are saved in
your conversation and can be revised through chat. No mock results are served by the app.

Offline dummy files are in `examples/tripai/`. Run
`.\.venv\Scripts\python.exe -m backend.tripai.sample_data` to validate them without APIs;
see [dummy-data instructions](examples/tripai/README.md).

## Run on this computer

The dependencies and Python environment have been installed for this workspace.

```powershell
Set-Location 'C:\Users\Aditya Ram\Prodapt_Hackathon\trip-chat'
npm.cmd run dev
```

Open **http://localhost:5173**. Create an account in the app; it does not require a separate
authentication API key. FastAPI runs on port 8000 and Vite on 5173. Ctrl+C stops development.

For a production frontend build served locally by FastAPI:

```powershell
npm.cmd run build
npm.cmd start
```

Then open **http://localhost:8000**. Do not run two backend processes on the same port.
Interactive API schemas are at **http://localhost:8000/docs**.

Try:

> Plan a 2-day trip to Jaipur starting tomorrow for 2 adults. Our total budget is INR 20000,
> excluding travel to Jaipur. We like history and architecture. Keep it relaxed.

Then:

> Make day two less busy and reduce our local transport spending.

Incomplete requests cause the chatbot to ask for the missing preferences.

## Credentials

The backend reads `GEMINI_API_KEY` from the private, git-ignored `.env` file. The existing
Google Maps key is still read from `../API.txt`. Neither key is sent to the frontend.
Environment variables override file values; see `.env.example`. Restart the backend after changing keys.

- `GEMINI_API_KEY`: AI generation via the native Gemini REST API.
- `GOOGLE_MAPS_API_KEY`: Places Text Search.
- `GEMINI_MODEL`: defaults to `gemini-3.6-flash`; account access is checked by the probe.
- `API_KEYS_FILE`: optional alternate path.
- `DATA_DIR`: optional private SQLite location.

Create a Gemini key through [Google AI Studio](https://aistudio.google.com/apikey), put it in
the private `.env` file, restart the backend, then run `npm.cmd run probe`. Do not paste keys
into chat or source files. No Groq fallback is enabled.

Implementation references: [Gemini REST API](https://ai.google.dev/api/generate-content)
and [available models](https://ai.google.dev/gemini-api/docs/models).

Open-Meteo does not need a key for the supported noncommercial usage. Google Maps demo
access does not include user photos/reviews, so this app uses original CSS illustrations
and external Maps links rather than unsupported photo calls. Keys are never stored in a
`VITE_` variable. Gemini quota and billing are independent of ChatGPT Plus. Groq is no longer called.

## Project flow

The application has a React/Vite frontend and a FastAPI backend. Vite serves the UI on port
5173 and proxies `/api` requests to FastAPI on port 8000. Users register or sign in, then
submit either a free-text request or the guided trip form. Conversations and successful
plans are stored in the local SQLite database.

### Planning request

1. `src/main.jsx` sends a chat message to `POST /api/chats/{id}/messages` or form preferences
  to `POST /api/chats/{id}/preferences`.
2. `backend/app.py` authenticates the user, applies rate limits and invokes the LangGraph
  planning workflow.
3. The graph validates preferences, asks follow-up questions when information is missing,
  retrieves destination places from Google Places, and retrieves weather from Open-Meteo.
4. `backend/services.py` sends the grounded request to Gemini using structured JSON output.
  Pydantic schemas validate the model response, and one bounded schema repair is allowed.
5. Local validation checks place IDs, day counts, chronological times, visit gaps and budget
  arithmetic. Invalid drafts receive one bounded business-validation repair.
6. The final plan is packaged with itinerary, budget, weather, warnings, notes and a workflow
  trace, then saved to SQLite only after successful completion.
7. `src/components/Plan.jsx` renders the saved plan with itinerary, budget and packing tabs.

### Monitoring and testing

Run `npm.cmd run dev` and watch the backend terminal for API timing, workflow steps, Gemini
attempts and schema-validation events. Use `http://localhost:8000/docs` to inspect the API.
Run `npm.cmd run probe` to check Gemini, Google Places and Open-Meteo independently. Run
`npm.cmd test` for backend tests and `npm.cmd run test:browser` for the offline browser suite.

### Secret handling

`.env`, local SQLite data, virtual environments, build output, logs, test results and generated
artifacts are ignored by Git. Commit `.env.example` only; copy it to `.env` locally and add
your private keys there. Never commit `GEMINI_API_KEY`, `GOOGLE_MAPS_API_KEY`, or `API.txt`.

## Architecture and requested LangGraph files

For the newer **TripAI Next.js form/dashboard contract**, use the separate
`backend/tripai/schemas.py`, `backend/tripai/nodes.py`, `backend/tripai/graph.py`, and
`backend/tripai/tools.py`. These expose authenticated `POST /api/tripai/plan` for
generation and modification. See [TripAI setup and integration](docs/TRIPAI.md).
This separate adapter remains available for experiments; exact compatibility with the
unseen Next.js types is not claimed. The final Roam UI instead uses
`POST /api/chats/{id}/preferences` and the existing saved-chat workflow below. Form inputs
are Pydantic-validated and are not reinterpreted by an LLM before planning.

| File | Responsibility |
|---|---|
| `backend/schemas.py` | Pydantic request, profile, tool-input, place, forecast, draft and final-plan schemas; graph transport state |
| `backend/nodes.py` | Node functions; each invokes a named tool |
| `backend/graph.py` | StateGraph topology, branches, bounded repair edge |
| `backend/tools.py` | Eight LangChain tools, including local validation of complete form preferences |
| `backend/services.py` | Gemini, Google Places and Open-Meteo adapters, timeouts, retries, weather cache |
| `backend/validation.py` | Deterministic schedule, place-ID and budget checks |
| `backend/app.py` | FastAPI routes, sessions, ownership checks and throttling |
| `backend/db.py` | SQLite schema, transaction boundaries and plan versions |
| `src/main.jsx` | Conversation UI and app state |
| `src/components/` | Authentication and travel-plan views |
| `src/components/TripForm.jsx` | Our own responsive preference form and client-side validation |

Each node uses an actual tool. Some tools use APIs; others perform useful local validation
without spending tokens. This is a deterministic tool workflow, not an LLM with arbitrary
tool execution. No LangSmith account/key is required, and the app does not enable tracing.
There is no document/vector-search RAG pipeline, embedding model, or vector database.

## Fresh setup on another computer

Requires Node 22+ and Python 3.12+. On Windows:

```powershell
npm.cmd ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
npm.cmd run dev
```

On this machine the project-local `.tools/uv/uv.exe` was used to install Python 3.12 because
the normal `python` command resolved to a Windows Store alias. The runtime is managed by uv;
the project's packages are isolated in `.venv`. It does not require changing PowerShell's
execution policy or activating a shell script.

On macOS/Linux use `.venv/bin/python`; the development launcher detects that location.
The `start`, `test`, and `probe` npm shortcuts target Windows; their portable equivalents are
`python -m uvicorn backend.app:app`, `python -m pytest tests -q`, and `python -m backend.probe`.

## Verification

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run probe
.\.venv\Scripts\python.exe -m backend.smoke
npm.cmd run test:browser
```

- Backend tests use deterministic fake external services and isolated databases.
- `probe` and `backend.smoke` use the real keys and consume provider quota.
- The live smoke test writes a nonpersonal sample plan to ignored `artifacts/live-plan.json`.
- The two browser tests use Chrome, real local authentication, and committed offline dummy
  fixtures to isolate AI nondeterminism. They do not require the live smoke test or quota.
  They check chat, form validation/submission/failure recovery, mobile layouts, cards,
  budget, packing, keyboard tabs, download and account deletion.
- Screenshots are saved under ignored `artifacts/`.
- Export the actual graph with `python -m backend.export_graph`.

## Scope and limitations

Plans cover one destination for 1–7 days and 1–20 travelers. Budgets support INR/USD/EUR/GBP.
The guided form uses the narrower TripAI-inspired limits: 2–7 inclusive days, 1–12
travelers, and INR 1,000–10,000,000 in increments of 100. Free-text chat retains its
existing wider supported inputs. Pace and special requirements are saved with the plan.
Place identities are retrieved; ratings, live prices, opening hours and bookings are not.
Entry costs, accommodation and transport are AI estimates, clearly labeled. Totals are
calculated in code; over-budget plans are flagged, not silently forced to fit. Visit buffers
are not road travel-time calculations. Forecasts outside Open-Meteo coverage are not invented.

The latest plan stays visible until a replacement is successfully generated. During a
clarification it may represent previous preferences; the plan header shows its own dates
and destination. Prior versions remain in SQLite for audit, but only the latest is shown.
Packing ticks are temporary UI state; the packing list itself is saved.

Accounts are local: no email verification, password recovery or cross-device cloud sync.
Sessions last seven days. Conversation and account deletion remove their database records,
including plan versions. Database files/backups are not encrypted by this application.
Do not claim forensic erasure or removal from external provider systems.

See `docs/BRD-HLD.md`, `docs/EVALUATION.md`, and `docs/DEMO.md` for the submission materials.
