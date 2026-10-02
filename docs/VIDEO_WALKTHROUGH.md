# Video walkthrough script (~12 minutes)

Record the screen with the two servers running:
- `uvicorn q1_voice_agent.server:app --port 8000`
- `uvicorn q4_live_nudges.server:app --port 8001`

| Time | Show | Say (key points) |
|---|---|---|
| 0:00–1:00 | README table | Four connected prototypes on one engine; fictional lender, insurer and multifinance company; everything measured and reproducible. |
| 1:00–2:30 | `docs/ARCHITECTURE.md` diagram | KB build → hybrid retrieval → voice engine (LLM tool loop, rules in tools, grounding guard) → Q4 streaming pipeline. Key decisions: rules in code not prompt; KB via tool with citations; fixed compliance lines; approved nudge playbook. |
| 2:30–4:00 | `q2_knowledge_base/sources/` then `output/build_report.md` | Messy inputs: nav/footer boilerplate, an archived FAQ, a scanned PDF, a JS-only page, a ₹5900 typo, a 5-day vs 3-day grace conflict, PII in call notes. Show what the pipeline removed, superseded, corrected (authority ranking) and redacted. Show one record in `records.jsonl` (schema, version, source, PII flag). |
| 4:00–5:00 | http://localhost:8000/kb | Ask "Will late payment affect my CIBIL?" (answer + citation), then "What's your gold loan rate?" (abstains → safe fallback). Mention eval: `eval/results.md`. |
| 5:00–7:30 | http://localhost:8000 — live call, Udaan C002 | Speak: confirm last 4 digits 7730 → hear reminder → "why are you calling before the due date" → "salary is late, I'll pay on <date>" → ask to waive fee → ask for a human. Point at the side panel: tools called, KB citations, disposition, latency per turn. End call → open transcript + recording. |
| 7:30–8:00 | `q1_voice_agent/results/simulated/summary.md` | Automated suite: cooperative, objection, conflicting details, out-of-scope, human request, wrong party, failed verification — with TTS→Whisper in the loop. Show one guard intervention if present. |
| 8:00–9:30 | Market dropdown → Bituin Life (PH) and Pundi Mitra (ID) | Play a PH Taglish call and an ID colloquial call (or play recordings from `q3_multilingual/results`). Show `q3_multilingual/README.md` localization tables, then `asr_eval/results/asr_report.md`: auto-LID vs forced language for Taglish, Javanese/Sundanese accent WER, the telephone/noise drop. |
| 9:30–11:00 | http://localhost:8001 | Run "Skipped disclosure" — compliance nudges appear within ~1 s of the agent's sentence (rules fast path). Run "Rising frustration" — duplicates merge instead of spamming. Run "Noisy call" — stays quiet. Show latency panel; then `results/latency_report.md` P50/P95 and `fp_analysis.md`. |
| 11:00–12:00 | `docs/LIMITATIONS_AND_PRODUCTION_PLAN.md` | Half-duplex web UI, free-tier quotas, synthetic test audio, small eval sets; 10× plan (streaming ASR, classifier for signals, vector DB, Redis sessions); noisy-audio plan (neural VAD, denoise, confidence gating). |
