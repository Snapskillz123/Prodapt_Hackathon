# Offline dummy validation data

These are fictional examples, not real recommendations or API responses. They are
not used by the running application and do not replace its live providers.

From `C:\Users\Aditya Ram\Prodapt_Hackathon\trip-chat`:

```powershell
# Check built-in valid/invalid examples and deterministic budget calculations, offline:
.\.venv\Scripts\python.exe -m backend.tripai.sample_data

# Regenerate the six sample files, refreshing dates to next week:
.\.venv\Scripts\python.exe -m backend.tripai.sample_data --export

# Validate a request file after making your own edits:
.\.venv\Scripts\python.exe -m backend.tripai.sample_data --file examples/tripai/valid-generation.json

# Validate a complete response:
.\.venv\Scripts\python.exe -m backend.tripai.sample_data --file examples/tripai/valid-result.json --schema result

# See expected field errors; this command deliberately exits with code 1:
.\.venv\Scripts\python.exe -m backend.tripai.sample_data --file examples/tripai/invalid-generation.json
```

| File | Schema | Expected result |
|---|---|---|
| `valid-generation.json` | request | Valid preference form |
| `valid-modification.json` | request | Valid modification with full existing trip |
| `valid-trip.json` | trip | Valid dashboard object |
| `valid-draft.json` | draft | Valid illustrative LLM draft with fictional place IDs |
| `valid-result.json` | result | Valid complete response, INR 5,400 spend and INR 4,600 remaining |
| `invalid-generation.json` | request | Reject 99 travellers and negative budget |

Copy a sample before editing if you want to keep your changes: `--export` overwrites
these six generated files. Regenerate when their start dates have passed.

Try setting `style` to `Fast`, emptying `interests`, using the same start/end date,
or adding an unknown field. Each should fail validation. A modification also requires
a nonblank `modification` and complete `existingTrip` rather than `preferences`.

`--file` checks Pydantic structure and schema validators only. It does not prove that
places exist, schedules are feasible, or supplied budget totals are correct. The default
sample run additionally exercises local draft materialization and calculated totals;
the full graph/business test suite is `python -m pytest tests -q` in the project venv.

**No keys, running server or API calls are needed for these commands.** In contrast,
posting a valid example to `/api/tripai/plan` in Swagger triggers real API calls and
requires authentication/quota. Do not confuse offline validation with live generation.
