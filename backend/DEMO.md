# George shop-demo runbook

Keep this path green before building a frontend.

## Demo corpus to ingest

| PDF | document_ref | year | make | model |
| --- | --- | --- | --- | --- |
| `subaru_wrx_2022_service_manual.pdf` | `subaru_wrx_2022_service_manual` | 2022 | subaru | wrx |

The demo vehicle is a 2022 Subaru WRX. The PDF is a local-only input and is not tracked in Git. Confirm that the file exists and that the Qdrant `george_specs` collection contains points before starting the API. If the database still holds the earlier Silverado/VR30 demo manuals, run `purge_db.py` first (it empties the whole `george_specs` collection), then ingest the WRX manual, so old manuals can't answer WRX questions.

Parse Markdown is cached in `.george_parse_cache/` (gitignored). Re-ingest does **not** call LlamaParse unless you pass `--force-parse`.

## Start for a Call test (3 terminals)

```bash
cd /Users/raghav.s18/Documents/Projects/HackUTD26/backend

# Terminal 1 — API (only one process; holds local Qdrant lock)
../.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 — tunnel
ngrok http 8000
```

Vapi → George assistant → tool `lookup_spec` → Server URL:

```text
# Local demo
https://YOUR-NGROK-HOST/vapi-tool

# Production (Render)
https://YOUR-SERVICE.onrender.com/vapi-tool
```

## Vapi webhook secret (`x-vapi-secret`)

`backend/.env` must have matching `VAPI_WEBHOOK_SECRET=...` (restart uvicorn after changes).
This is **not** on the **API Keys** page (Private/Public keys are for calling Vapi).
This is **not** **Encryption Settings**.

### Preferred: HTTP header on `lookup_spec`

1. **Build → Tools → `lookup_spec`**
2. Keep Request URL: `https://YOUR-NGROK-HOST/vapi-tool`
3. Find **Headers** (often near Auth / Request / Advanced — not Encryption)
4. Add header:
   - Name: `X-Vapi-Secret`
   - Value: same string as `VAPI_WEBHOOK_SECRET` in `backend/.env`
5. Save

### Alternate: Custom Credential

1. Dashboard → **Custom Credentials** (org settings; not API Keys)
2. Create **Bearer Token**:
   - Header Name: `X-Vapi-Secret`
   - Include Bearer Prefix: **off**
   - Token: same as `VAPI_WEBHOOK_SECRET`
3. On `lookup_spec`, attach that credential under **Authentication** / `credentialId`

## Vapi setup (stops “what year?” loops)

### Tool `lookup_spec` parameters

| Param | Required? | Notes |
| --- | --- | --- |
| `query` | **Yes** | What they’re asking |
| `make` | No | e.g. subaru |
| `model` | No | e.g. wrx |
| `year` | **No** | Uncheck required in Vapi |

If the tech says “WRX” (or speech-to-text hears “W R X”), the API infers `subaru` / `wrx` / `2022` from the uploaded catalog. “Subie” is read as `subaru`.

### Paste into Assistant **System Prompt**

```text
You are George, a hands-free shop-floor automotive voice assistant for technicians wearing headphones.

MISSION
Answer torque, fastener, gasket, and install-spec questions ONLY from the lookup_spec tool. You do not invent specs. The tool result is the source of truth.

WHEN TO CALL lookup_spec
- Call lookup_spec on EVERY question about torque, bolts, nuts, fasteners, gaskets, torque sequences, install notes, or service-manual specs.
- Call it again for EVERY new question in the same call, even if the vehicle is the same.
- Never answer a numbers/specs question from memory, prior turns, or general car knowledge.

HOW TO CALL lookup_spec
- query: the mechanic's request in their words (required).
- make / model / year: only if the mechanic clearly stated them. All are optional.
- Do NOT interrogate for year if they already named the platform (WRX, Subaru WRX, Subie, etc.).
- If speech-to-text looks like W R X / W.R.X., treat it as WRX and still call the tool. Otherwise read the tool result as-is.
- Never skip the tool because a similar question was asked earlier.

AFTER THE TOOL RETURNS (CRITICAL — VERBATIM MODE)
- If result is present: speak the result string EXACTLY. Character-for-character intent. No paraphrase. No rewrite. No synonym swap.
- Forbidden rewrites include: "ft", "ft.", "ft-lb", "ft-lbs", "lb-ft", "lb.ft", "in-lb", "N·m", "Nm", "N.m", or any abbreviation of foot-pounds / inch-pounds / newton-meters.
- Keep every unit word exactly as returned: "foot-pounds", "inch-pounds", "newton-meters".
- Do not add greetings, emojis, "sure", "absolutely", or extra shop chatter.
- Do not merge this answer with a previous answer.
- Do not reuse numbers, cautions, or sentences from earlier tool results.
- Do not substitute the answer for one fastener or component for another.
- If the tool returns an error string: say that you do not have that spec in the manuals, briefly. Only then ask for year/make/model if the vehicle is still unknown.

CONVERSATION STYLE
- Voice-first: 1–2 short sentences max, matching the tool string.
- Confirm the working vehicle only if it helps; do not block the lookup.
- If the mechanic is clearly chatting (not asking a spec), reply briefly without calling the tool.
- Never invent part numbers, torque values, sequences, or warnings.

FAILURE MODES YOU MUST AVOID
- Saying "15-18 ft" instead of "15-18 foot-pounds".
- Saying "15 N·m or 11 ft" instead of "15 newton-meters or 11 foot-pounds".
- Answering one fastener question with the reply for a different fastener.
- Using an earlier result after a new lookup_spec completed.
```

### Tool description (paste on the tool)

```text
Looks up torque and fastener specs from shop manuals. ALWAYS call for every new torque/spec question in a call. Pass query always. make, model, and year are optional — omit year when the platform is clear (WRX / W R X mishears → Subaru WRX; Subie → Subaru). The API returns a ready-to-speak result string. The assistant MUST speak that result EXACTLY with no paraphrasing, no unit abbreviations, and no reuse of prior-turn answers. Never invent values.
```

## Re-seed (credit-safe)

```bash
cd /Users/raghav.s18/Documents/Projects/HackUTD26/backend

../.venv/bin/python ingest.py "subaru_wrx_2022_service_manual.pdf" \
  --year 2022 --make subaru --model wrx
```

After ingest, restart uvicorn.

## Smoke questions

Swap these for questions the ingested WRX manual actually covers; anything it doesn't cover should be refused.

1. “Oil drain plug torque for a 2022 WRX?”
2. “Spark plug torque on the 2022 Subaru WRX?”
3. “Wheel lug nut torque on the WRX?”
4. “Ford F-150 head bolt torque?” (should be refused — no matching manual)

## Curl

```bash
# Without secret → 401 if VAPI_WEBHOOK_SECRET is set
curl -s -X POST "http://127.0.0.1:8000/vapi-tool" \
  -H "Content-Type: application/json" \
  -H "x-vapi-secret: YOUR_SECRET_HERE" \
  -d '{"query":"oil drain plug torque 2022 Subaru WRX"}'
```

Run the API from `backend/` so `.env` and local paths resolve correctly.

## Credit rules

- Default LlamaParse tier is `cost_effective`; `premium_mode` only with `--premium`.
- Local cache short-circuits all remote parse calls.
- Do not use `--force-parse` unless the PDF bytes changed.
