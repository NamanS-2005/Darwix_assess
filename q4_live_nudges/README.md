# Q4 — Live insights and nudges from call audio

The call is analysed **while it plays**. Audio is replayed at real-time speed (1.0×) in 100 ms chunks, the same way a live media stream arrives. Nothing is analysed after the call ends.

```
stereo call audio (agent L / customer R)
  └─ 100 ms chunks, real-time ──► per-channel VAD endpointing (adaptive noise floor, 500 ms hangover, 6 s force-cut)
                                   └─► streaming ASR: Groq Whisper per utterance (client-side rate limiter over 2 orgs × 2 models)
                                        ├─► Tier 1: regex lexicons + call-state checks (≈45 µs) ──► compliance fast path
                                        └─► Tier 2: LLM JSON signals on a rolling 6-utterance window (Qwen3.8-27B on Groq; fallbacks)
                                             └─► nudge engine: thresholds · corroboration · topic grouping · duplicate merge ·
                                                  cooldown · spacing · priority · TTL · auto-resolve when the agent acts
                                                  └─► WebSocket dashboard / CLI   (+ post-call summary: missed opportunities)
```

## Run it
```bash
python -m q4_live_nudges.make_audio
```
```bash
uvicorn q4_live_nudges.server:app --port 8001
```
Then open http://localhost:8001, pick a scenario and press **Start live replay**. The audio plays in the browser in sync while transcript, nudges and latency appear. CLI alternatives:
- One call: `python -m q4_live_nudges.pipeline --scenario s2_compliance_gap`
- Full evaluation: `python -m q4_live_nudges.evaluate`
- A Q1/Q3 recording: `python -m q4_live_nudges.pipeline --wav q1_voice_agent/results/simulated/q1_02_objection_salary_waiver/recording_stereo.wav`

## Results (real Whisper ASR, real-time replay)

| Configuration | Precision | Recall | E2E P50 | E2E P95 | Report |
|---|---|---|---|---|---|
| **Rules + LLM signals** | **91%** | **100%** | **1.12 s** | **1.94 s** | [latency](results/latency_report_llm.md) · [FP analysis](results/fp_analysis_llm.md) |
| Rules + call-state only (ablation) | 100% | 60% | 0.83 s | 2.97 s* | [latency](results/latency_report_rules_only.md) · [FP analysis](results/fp_analysis_rules_only.md) |

\* The rules-only run started straight after the LLM run, so the free-tier Whisper rate limiter (20 requests/min per org per model) queued requests: its ASR P95 was 2.5 s, against 0.39 s in the uncontended LLM run.

The ablation shows the division of labour:
- **Rules alone** are perfectly precise and fast for compliance.
- **Fuzzy signals** (cross-sell, frustration, hardship, callback) need the LLM. The LLM tier lifts recall from 60% to 100% at a cost of one false positive.

Component latency with the LLM (P50 / P95):

| Stage | P50 / P95 |
|---|---|
| VAD endpointing | 498 / 506 ms |
| ASR request | 240 / 387 ms |
| Audio received → text | 739 / 887 ms |
| Rule extraction | 45 / 95 µs |
| LLM signal call | 590 / 920 ms |
| Nudge engine | 0.1 ms |
| Delivery | 0.5 / 3.8 ms |

By path:
- **Compliance nudges** (rules fast path): P50 0.72 s.
- **LLM-confirmed nudges**: P50 1.34 s.

### Required test coverage
| Requirement | Scenario | Outcome |
|---|---|---|
| Missed cross-sell | `s1` education fees + second two-wheeler | Opportunity nudge 1.6 s after the mention. The second need *merged* into the same card. Post-call summary lists 1 missed opportunity, because the agent never acted on it |
| Skipped disclosure / risky statement | `s2` no recording disclosure, loan details before verification, threat, waiver promise | All 4 compliance nudges, 0.38–0.81 s after the sentence |
| Rising frustration | `s3` already paid, third call this week, "stop calling", "manager" | Payment-dispute → frustration → escalation nudges. **7 repeated frustration signals merged**, not re-shown |
| Noisy / ambiguous | `s5` street noise at 8 dB SNR, decoys ("traffic is killing me", brother's old bike loan, "maybe later") | **0 nudges**. Two noise-only segments were dropped by the Whisper hallucination filter |
| Extra: payment difficulty + callback | `s4` job loss, driving | Hardship nudge 0.73 s, callback nudge 1.9 s |

**False positive:** "This month is a bit heavy for me" was flagged as payment difficulty while the customer confirmed auto-debit. It's borderline: a soft empathy nudge is arguably fine. It is counted as an FP.

## Nudge controls (`nudges.py`)
- **Approved playbook text.** Nudges are compliance-safe templates; the LLM only detects the signal and quotes the evidence.
- **Corroboration policy.** Compliance types (missing disclosure, skipped verification, threats, waiver promises) fire on rules alone, for speed. Fuzzy types (cross-sell, frustration, payment difficulty, already-paid dispute, callback, escalation) need LLM confirmation, and the LLM can veto a rule hit.
- **Thresholds per type,** raised by 0.15 when ASR confidence is low (Whisper `avg_logprob` and `no_speech_prob`). On noisy audio, rule and LLM must agree.
- **Topic grouping and duplicate merge.** A repeat signal updates the open card (evidence appended, ×N) instead of creating a new one.
- **Cooldowns** per type after a card closes, **5 s spacing** between non-critical cards (held, not dropped), **max 3 cards on screen**, **priorities** P1 compliance → P3 opportunity, and **TTL** expiry.
- **Auto-resolve.** A card closes when the agent does the recommended thing (says the disclosure, asks for the UTR, apologises, mentions the top-up…). Acted-on vs missed is reported post-call.
- **Cost control.** Agent utterances go to the LLM only when they touch money or consequences; customer utterances always do.

## Limitations at 10× scale and with noisy audio
See [docs/LIMITATIONS_AND_PRODUCTION_PLAN.md](../docs/LIMITATIONS_AND_PRODUCTION_PLAN.md).

In short:
- Per-utterance Whisper HTTP plus 500 ms endpointing sets the latency floor. At 10× concurrency, move to self-hosted streaming ASR (faster-whisper / Riva) and replace most LLM calls with a fine-tuned classifier.
- Noisy audio needs a neural VAD and denoising. The confidence gating here already keeps the noisy test call silent.
- The 5 labelled test calls are synthetic (TTS); precision and recall are indicative, not statistically strong.
