# AI Engineer Assessment — Voice agents, KB, multilingual bots, live nudges

Four connected, working prototypes on one codebase. All companies, customers and policies are **fictional**; no real customer data is used.

| # | What | Where | Evidence |
|---|---|---|---|
| Q1 | Loan **pre-due EMI reminder** voice agent (India, English), KB-grounded, with verification, promise-to-pay rules, objection handling, safe fallback, human escalation, mock-CRM + escalation webhook | `q1_voice_agent/` | `q1_voice_agent/results/` (transcripts, recordings, checks) |
| Q2 | Production KB from messy sources (HTML, PDF, CSV, forms, PII-laden notes, duplicates, conflicts) with hybrid retrieval + citations | `q2_knowledge_base/` | `output/build_report.md`, `eval/results.md` |
| Q3 | Native-language bots: **Philippines** life-insurance premium reminder (English/Filipino/Taglish) and **Indonesia** multifinance angsuran reminder (formal + colloquial Bahasa, Javanese/Sundanese accents) | `q3_multilingual/` | `q3_multilingual/README.md`, `asr_eval/results/`, `results/` |
| Q4 | **Real-time** call insights & nudges: streaming ASR, rule+LLM signals, nudge controls, WebSocket dashboard, measured latency | `q4_live_nudges/` | `results/latency_report.md`, `results/fp_analysis.md` |

## Results at a glance

| | Result | Evidence |
|---|---|---|
| **Q2 KB build** | 20 messy source files → 101 traceable records (97 active, 4 superseded). Scanned PDF and JS-only page flagged, not ingested. 2 source errors auto-corrected against the authoritative policy PDF (5-day vs 3-day grace, ₹5900 typo). 24 PII items redacted | [`build_report.md`](q2_knowledge_base/output/build_report.md) |
| **Q2 retrieval** | 18 queries (product, policy, qualification, FAQ, objection, Taglish, Bahasa, 2 out-of-scope): **17 correct, 1 partially correct, 0 incorrect**. Both out-of-scope queries refused at retrieval; every answer cited | [`eval/results.md`](q2_knowledge_base/eval/results.md) |
| **Q1 voice agent** | **7/7** scenarios pass (cooperative, objection, conflicting details, out-of-scope, human request, wrong party, failed verification), with TTS→Whisper ASR in the loop. 8 defects found by the suite and fixed deterministically | [`q1_voice_agent/results/README.md`](q1_voice_agent/results/README.md) |
| **Q3 ASR** | 490 transcriptions, 5 configurations. PH best: whisper-large-v3 + vocab prompt, **13.4% WER** (numbers normalised). ID best for live calls: whisper-turbo + prompt, **12.4%** at 250 ms. Javanese-accented voice ≈ 2× WER of standard Jakarta voices. 0 translate-to-English failures | [`asr_report.md`](q3_multilingual/asr_eval/results/asr_report.md), [`FINDINGS.md`](q3_multilingual/FINDINGS.md) |
| **Q3 bots** | Simulated calls with ASR in the loop and a language/register judge: **PH 4/5, ID 6/7**. All 12 stay in the customer's language and register. The Javanese-accented call passes; the Sundanese-accented number reading is the documented failure. 10 multilingual defects found and fixed in code | [`results/ph`](q3_multilingual/results/ph/summary.md), [`results/id`](q3_multilingual/results/id/summary.md), [`FINDINGS.md`](q3_multilingual/FINDINGS.md) |
| **Q4 live nudges** | Real Whisper streaming at real-time speed, rules + LLM signals: **precision 91%, recall 100%**. End of speech → nudge on screen **P50 1.12 s, P95 1.94 s**; compliance fast path P50 0.72 s. The noisy/ambiguous call stays silent, and repeated frustration merges into one card | [`q4_live_nudges/README.md`](q4_live_nudges/README.md), [`latency_report.md`](q4_live_nudges/results/latency_report.md), [`fp_analysis.md`](q4_live_nudges/results/fp_analysis.md) |

Architecture and design decisions: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Limitations & production plan: [docs/LIMITATIONS_AND_PRODUCTION_PLAN.md](docs/LIMITATIONS_AND_PRODUCTION_PLAN.md) · Video script: [docs/VIDEO_WALKTHROUGH.md](docs/VIDEO_WALKTHROUGH.md)

## Stack
- **LLM**: Groq `llama-3.3-70b-versatile` (agent, tool calling), `llama-3.1-8b-instant` (Q4 signals); automatic fallback to Gemini `gemini-2.5-flash` via the OpenAI-compatible endpoint (`common/llm.py`).
- **ASR**: Groq Whisper `whisper-large-v3` (agent turns, Q3) / `whisper-large-v3-turbo` (Q4 streaming); market-specific language + vocabulary prompts. Gemini 2.5 Flash audio benchmarked in Q3.
- **TTS**: Microsoft neural voices via `edge-tts` (no key): `en-IN-NeerjaNeural`, `fil-PH-BlessicaNeural`, `id-ID-GadisNeural` (+ `jv-ID`, `su-ID` voices for accent tests).
- **Embeddings**: Gemini `gemini-embedding-001`; lexical BM25 always on (works with no key).
- **Voice platform**: built-in browser calling UI (FastAPI) **and** Vapi via a custom-LLM endpoint (`q1_voice_agent/vapi/`).

## Setup
```bash
python -m venv .venv
```
```bash
.venv\Scripts\pip install -r requirements.txt
```
Copy `.env.example` to `.env` and set `GROQ_API_KEY` and `GEMINI_API_KEY` (both have free tiers). Optional: `VAPI_API_KEY` + `PUBLIC_BASE_URL`, `ESCALATION_WEBHOOK_URL`.

## Run the portal (everything in one website)
```bash
.venv\Scripts\python -m uvicorn portal.server:app --port 8080
```
Open **http://localhost:8080**. The portal has one section per question:

| Section | What's there |
|---|---|
| **Q1** | Live browser call with the agent (mic or typing, test identities shown), automated test calls with recordings and transcripts, script and rules, defects found and fixed |
| **Q2** | Ask the KB (grounded answers with citations), record browser (PII, corrections, versions), retrieval evaluation, build report |
| **Q3** | Live Philippines and Indonesia calls, test calls, ASR benchmark charts, localization examples, findings |
| **Q4** | Live replay with nudges streaming in as the call plays, results (precision, recall, latency by stage, per-nudge verdicts), reports |
| **Docs** | README, architecture diagram, limitations and production plan, video script |

The individual servers below still work on their own.

## Run individual pieces
| Task | Command |
|---|---|
| Build KB (extract → clean → dedupe → PII → chunk → version → embed) | `python -m q2_knowledge_base.build_kb` |
| Retrieval evaluation (18 queries, verdicts, grounded answers) | `python -m q2_knowledge_base.eval.run_eval` |
| Ask the KB from the CLI | `python -m q2_knowledge_base.retriever "will late payment affect my CIBIL"` |
| **Voice agent web call UI** (Q1 + Q3 markets) + KB search page | `uvicorn q1_voice_agent.server:app --port 8000` → http://localhost:8000 and /kb |
| Automated test calls Q1 (LLM customer, TTS→ASR in the loop, recordings) | `python -m q1_voice_agent.simulate_calls` |
| Automated test calls Q3 | `python -m q1_voice_agent.simulate_calls --scenarios q3_multilingual/markets/ph/scenarios.yaml --out q3_multilingual/results/ph` (same for `id`) |
| Q3 ASR benchmark | `python -m q3_multilingual.asr_eval.run_asr_eval` |
| Vapi assistants (phone/web) using this engine | `python -m q1_voice_agent.vapi.create_assistants` |
| Q4 render test calls (stereo) | `python -m q4_live_nudges.make_audio` |
| Q4 live CLI run of one call | `python -m q4_live_nudges.pipeline --scenario s2_compliance_gap` |
| **Q4 live dashboard** | `uvicorn q4_live_nudges.server:app --port 8001` → http://localhost:8001 |
| Q4 evaluation (latency P50/P95, FP analysis) | `python -m q4_live_nudges.evaluate` |
| Q4 on a Q1/Q3 recording | `python -m q4_live_nudges.pipeline --wav q1_voice_agent/results/simulated/<call>/recording_stereo.wav` |

## Repository map
```
portal/                 the website: server.py (merges Q1+Q4 live APIs, adds results APIs) · static/ (index.html, app.js, styles.css)
common/                 LLM/ASR/embedding client with provider fallback, TTS + audio utils
q2_knowledge_base/      sources/ (raw inputs) · extract.py · normalize.py · taxonomy.py · build_kb.py · retriever.py · answer.py · eval/
q1_voice_agent/         engine/ (agent.py, tools.py, markets.py) · market/ (script, rules, prompt) · crm/ (mock CRM)
                        server.py · static/ (call UI, KB UI) · simulate_calls.py · tests/scenarios.yaml · vapi/ · results/
q3_multilingual/        markets/ph · markets/id (prompt, script, rules, scenarios) · asr_eval/ · results/ · README.md
q4_live_nudges/         scenarios/ · make_audio.py · streaming.py · signals.py · nudges.py · pipeline.py · server.py · evaluate.py · results/
docs/                   architecture, limitations / production plan, video walkthrough script
```

No credentials, keys or real customer data are committed (`.env` is git-ignored; mock CRM and call notes are synthetic, and PII in the notes is redacted by the pipeline before indexing).
