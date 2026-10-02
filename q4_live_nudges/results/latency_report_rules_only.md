# Q4 latency report

Mode: ASR **groq** (Groq whisper-large-v3-turbo, per-utterance requests) · LLM **off (rules + call-state only)** · replay speed 1.0× (real-time) · 7 nudges over 5 calls.

Stage definitions: **speech_end** = the last audio chunk of the evidence utterance was received → **endpoint** (VAD decides the turn ended, 500 ms hangover) → **asr_done** → **signal_done** (rules: sub-ms; LLM path: after LLM) → **nudge_created** → **delivered** (consumer output: WebSocket send / CLI print).

## End-to-end (speech end → nudge delivered)

| Metric | P50 ms | P95 ms | max ms |
|---|---|---|---|
| e2e | 834.3 | 2971.5 | 3817.7 |
| endpointing | 496.3 | 509.4 | 513.4 |
| asr | 549.1 | 2496.8 | 3320.5 |
| signal | 0.1 | 0.2 | 0.2 |
| llm | None | None | None |
| engine | 0.1 | 0.1 | 0.1 |
| delivery | 0.6 | 0.9 | 0.9 |

Rules fast-path nudges (compliance): n=7 P50 834.3 ms · P95 2971.5 ms  
LLM-confirmed nudges: n=0 P50 None ms · P95 None ms

## Component latency over all utterances

| Component | n | P50 | P95 |
|---|---|---|---|
| ASR request (ms) | 106 | 275.0 | 954.8 |
| Audio received → text (ms, incl. endpointing) | 106 | 770.5 | 1365.5 |
| Rule signal extraction (µs) | 106 | 44.1 | 102.9 |
| LLM signal extraction (ms) | 0 | None | None |

## Per-nudge timings

| Call | Nudge | Type | Path | endpointing | ASR | signal | engine | delivery | **e2e** |
|---|---|---|---|---|---|---|---|---|---|
| s2_compliance_gap | N1 | disclosure_missing | rules | 0.0 | 574.8 | 0.1 | 0.1 | 0.5 | **575.5** |
| s2_compliance_gap | N2 | verification_skipped | rules | 0.0 | 574.8 | 0.1 | 0.1 | 0.6 | **575.7** |
| s2_compliance_gap | N3 | risky_statement | rules | 513.4 | 269.4 | 0.2 | 0.1 | 0.6 | **783.6** |
| s2_compliance_gap | N4 | unauthorized_waiver | rules | 402.9 | 549.1 | 0.2 | 0.1 | 0.5 | **952.7** |
| s3_rising_frustration | N1 | already_paid_dispute | rules | 500.0 | 496.1 | 0.1 | 0.1 | 0.9 | **997.2** |
| s3_rising_frustration | N2 | escalation_request | rules | 499.4 | 334.4 | 0.1 | 0.1 | 0.4 | **834.3** |
| s4_payment_difficulty | N1 | risky_statement | rules | 496.3 | 3320.5 | 0.1 | 0.1 | 0.8 | **3817.7** |