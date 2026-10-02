# Known limitations and production-improvement plan

## Limitations (as built)

**Voice agent (Q1/Q3)**
- The built-in web UI is half-duplex: no barge-in, and the agent's turn is synthesised in full before playback (time-to-first-audio = LLM + full TTS). Vapi provides barge-in and streaming TTS; the web UI is the fallback channel.
- Turn latency is dominated by LLM tool loops (verification → loan details = 2–3 LLM calls on the first substantive turn). Measured per turn in each `call.json` (`metrics.llm_ms`, `turn_ms`).
- Free-tier quotas (Groq 8k tokens/min per model, 1k requests/day) cap concurrency at about one live call per model. Fallback to Gemini keeps calls alive but mixes models; the provider used per call is logged.
- The grounding guard checks **numbers** (fees, dates, %, amounts). Non-numeric fabrications ("you can pay at the post office") are mitigated by tool-only facts + NOT_IN_KB, not verified by the guard.
- Dates spoken relatively ("next Friday") are resolved by the LLM with a calendar in the prompt; tools validate the result, but a wrong resolution is possible.
- Test calls are LLM-simulated customers with TTS→Whisper in the loop; real human calls should be added via the web UI (they are recorded automatically).

**Knowledge base (Q2)**
- Abstention thresholds were calibrated on an 18-query set — small; they need re-calibration on real query logs.
- Conflict detection covers a curated list of facts (grace period, bounce charge, notice days); unknown conflicts surface only via near-duplicate review.
- PII detection is regex + checksum based (Indian/PH/ID formats). Free-text names without an honorific/label can be missed; production should add an NER model (e.g. Presidio) and a human sample audit.
- JS-rendered pages and scanned PDFs are flagged, not processed (Playwright / OCR are the documented next step).

**Live nudges (Q4)**
- ASR is per-utterance (VAD endpoint → Whisper), not token-streaming; 500 ms endpointing hangover + one HTTP round-trip per utterance is the floor. Long turns are force-cut at 6 s.
- Speaker separation relies on dual-channel audio; a mono recording would need diarization.
- Test calls are synthetic (TTS); the noisy scenario uses synthetic street noise at 8 dB SNR.
- False-positive analysis uses 5 labelled calls — indicative, not statistically strong.

## At 10× scale
| Pressure | What breaks | Mitigation |
|---|---|---|
| 10× concurrent calls | Groq/Gemini TPM limits; one Whisper request per utterance per call | Paid tiers / provisioned throughput; self-hosted streaming ASR (faster-whisper / Riva / Deepgram streaming) with GPU batching; a small fine-tuned classifier replaces most LLM signal calls; LLM only on rule hits + every Nth customer turn |
| KB size 10× | Python BM25 in-process, numpy brute-force cosine | OpenSearch/Elastic hybrid or pgvector + HNSW; incremental embedding by content hash (already implemented) |
| Many tenants/markets | YAML configs per market | Config service + versioned prompts/rules, CI regression suite (the simulated-call scenarios) gating every change |
| Call state | In-memory sessions | Redis session store; stateless workers behind the telephony gateway |
| Observability | JSON logs per call | OpenTelemetry traces per turn (ASR/LLM/TTS spans), dashboards for P95, guard interventions, abstention rate, escalation rate |
| Nudge noise at scale | Same thresholds for all agents | Per-agent feedback (thumbs up/down on nudges), per-type precision tracking, auto-tuned thresholds |

## With noisy audio
- Whisper hallucinates on noise ("Thank you.") → filtered using `no_speech_prob` + avg log-prob; low-confidence utterances raise nudge thresholds (+0.15) and require rule **and** LLM agreement.
- VAD floor is adaptive (min-tracking); production should use a neural VAD (Silero) and noise suppression (RNNoise / DeepFilterNet) before ASR.
- Agent headset channel is usually clean; most noise is on the customer leg — channel-specific thresholds help.

## Production-improvement plan (prioritised)
1. Native-speaker review of PH/ID scripts + 50 real recorded calls per market → re-run ASR benchmark and simulated suite.
2. Streaming everywhere: streaming ASR, token-streamed LLM, chunked TTS → time-to-first-audio < 1 s; barge-in in the web channel.
3. Replace prompt-only date resolution with a deterministic date parser (dateparser + locale) feeding tools.
4. NER-based PII + DLP on transcripts and recordings; retention policy; encryption at rest.
5. KB ops: owner workflow for flagged conflicts/corrections, scheduled re-crawl, changelog review before publish, retrieval regression tests in CI.
6. Human-in-the-loop: live transfer to agents (SIP), supervisor whisper for Q4 nudges, feedback loop into thresholds.
7. Compliance: consent capture, DNC lists, calling-window enforcement at the dialer, audit log of every disclosure and tool action.
