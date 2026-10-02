# Q4 latency report

Mode: ASR **groq** (Groq whisper-large-v3-turbo, per-utterance requests) · LLM **signal tier: qwen/qwen3.8-27b,openai/gpt-oss-20b → gemini-flash-lite-latest,gemini-3.1-flash-lite** · replay speed 1.0× (real-time) · 13 nudges over 5 calls.

Stage definitions: **speech_end** = the last audio chunk of the evidence utterance was received → **endpoint** (VAD decides the turn ended, 500 ms hangover) → **asr_done** → **signal_done** (rules: sub-ms; LLM path: after LLM) → **nudge_created** → **delivered** (consumer output: WebSocket send / CLI print).

## End-to-end (speech end → nudge delivered)

| Metric | P50 ms | P95 ms | max ms |
|---|---|---|---|
| e2e | 1115.0 | 1935.5 | 1986.7 |
| endpointing | 497.6 | 505.9 | 513.5 |
| asr | 309.7 | 438.2 | 533.3 |
| signal | 370.7 | 926.4 | 953.0 |
| llm | 493.0 | 937.3 | 952.8 |
| engine | 0.1 | 289.1 | 722.4 |
| delivery | 0.5 | 3.8 | 3.9 |

Rules fast-path nudges (compliance): n=5 P50 724.4 ms · P95 796.3 ms  
LLM-confirmed nudges: n=8 P50 1342.2 ms · P95 1956.8 ms

## Component latency over all utterances

| Component | n | P50 | P95 |
|---|---|---|---|
| ASR request (ms) | 106 | 240.0 | 387.2 |
| Audio received → text (ms, incl. endpointing) | 106 | 739.0 | 887.0 |
| Rule signal extraction (µs) | 106 | 45.2 | 94.5 |
| LLM signal extraction (ms) | 70 | 589.5 | 919.5 |

## Per-nudge timings

| Call | Nudge | Type | Path | endpointing | ASR | signal | engine | delivery | **e2e** |
|---|---|---|---|---|---|---|---|---|---|
| s1_missed_cross_sell | N1 | payment_difficulty | llm | 497.6 | 254.0 | 636.9 | 0.2 | 0.4 | **1389.0** |
| s1_missed_cross_sell | N2 | cross_sell | llm | 389.8 | 339.8 | 908.6 | 0.1 | 0.4 | **1638.8** |
| s2_compliance_gap | N1 | disclosure_missing | rules | 0.0 | 374.8 | 0.1 | 0.1 | 3.6 | **378.6** |
| s2_compliance_gap | N2 | verification_skipped | rules | 0.0 | 374.8 | 0.1 | 0.1 | 3.9 | **378.9** |
| s2_compliance_gap | N3 | payment_difficulty | llm | 499.8 | 533.3 | 953.0 | 0.1 | 0.5 | **1986.7** |
| s2_compliance_gap | N4 | risky_statement | rules | 499.7 | 309.7 | 0.1 | 0.1 | 3.7 | **813.3** |
| s2_compliance_gap | N5 | unauthorized_waiver | rules | 405.7 | 319.1 | 0.2 | 0.1 | 3.4 | **728.4** |
| s3_rising_frustration | N1 | already_paid_dispute | llm | 494.1 | 232.1 | 568.8 | 0.1 | 0.5 | **1295.5** |
| s3_rising_frustration | N2 | frustration_rising | llm | 500.8 | 243.1 | 370.7 | 0.1 | 0.3 | **1115.0** |
| s3_rising_frustration | N3 | escalation_request | llm | 513.5 | 280.7 | 325.7 | 0.1 | 0.4 | **1120.4** |
| s4_payment_difficulty | N1 | payment_difficulty | llm | 0.0 | 343.6 | 385.3 | 0.1 | 0.4 | **729.4** |
| s4_payment_difficulty | N2 | risky_statement | rules | 497.9 | 223.2 | 0.1 | 0.1 | 3.2 | **724.4** |
| s4_payment_difficulty | N3 | callback_needed | llm | 500.5 | 260.3 | 417.5 | 722.4 | 0.7 | **1901.3** |