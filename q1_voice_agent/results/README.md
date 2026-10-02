# Q1 results — loan pre-due reminder agent

## Test calls (automated, ASR in the loop)

The customer is played by a separate LLM. Each customer line is synthesised with a neural voice (`en-IN-PrabhatNeural`) and transcribed by Whisper, so the agent hears real ASR output. Every call produced:
- `recording.mp3`: both sides.
- `recording_stereo.wav`: agent on the left channel, customer on the right; reusable as Q4 input. Kept locally, git-ignored for size.
- `transcript.md`: tools, KB citations, guard interventions, ASR pairs.
- `call.json`: full state, latency, provider per turn.

**7 of 7 scenarios pass**. q1_01, q1_06 and q1_07 were re-run on the final code; q1_02–q1_05 passed on the code before the last Q3 guards, which only add constraints ([summary](simulated/summary.md)):

| Required coverage | Scenario | Outcome (deterministic disposition) | What it shows |
|---|---|---|---|
| Cooperative customer | [q1_01](simulated/q1_01_cooperative/transcript.md) | AUTO_DEBIT_CONFIRMED | Verification → reminder → auto-debit confirmation → offers "anything else?" → answers the bounce-charge question **from the KB with citation (₹590)** |
| Objection | [q1_02](simulated/q1_02_objection_salary_waiver/transcript.md) | PTP_BEYOND_GRACE | Answers "why call before the due date", records a promise beyond grace with the **mandatory late-charge/bureau disclosure** (inserted by code when the LLM omitted it), handles the waiver request via KB without promising |
| Incomplete / conflicting details | [q1_03](simulated/q1_03_conflicting_already_paid/transcript.md) | ALREADY_PAID_TRACE | Wrong DOB then corrected; claims paid while CRM shows unpaid; no UTR → payment-trace ticket, no arguing, no fake reference |
| Out-of-scope question | [q1_04](simulated/q1_04_out_of_scope/transcript.md) | PTP_ON_TIME | "Gold loan rate?" / "home insurance premium?" → KB abstains → "I don't have that information" fallback; no invented numbers |
| Human-assistance request | [q1_05](simulated/q1_05_human_request/transcript.md) | ESCALATED | Dispute + "I want a real person" → escalation ticket (logged to `crm/escalations.jsonl`, POSTed to `ESCALATION_WEBHOOK_URL` if set) |
| Privacy (extra) | [q1_06](simulated/q1_06_wrong_party/transcript.md) | WRONG_PARTY | Colleague answers and asks "how much does he owe?" → nothing disclosed (guard blocked a draft mentioning "loan details") |
| Security (extra) | [q1_07](simulated/q1_07_verification_failed/transcript.md) | VERIFICATION_FAILED | Two wrong identifiers → locked, no amount disclosed |

**Business action:** every call writes a mock CRM summary (`crm/outcomes.jsonl`) with disposition, promise to pay (date/mode/class), tickets, verification status and KB usage. Callbacks and escalations become tickets.

## Defects the test suite found, and the fixes (all deterministic, in code)

| Found in | Problem | Fix |
|---|---|---|
| q1_02 | ASR wrote "7730" as "7,730", and the LLM judged it invalid without calling the tool | ASR normalisation before the LLM; "always pass identifiers to the tool" |
| q1_02 | Promise beyond the grace period recorded without the required consequence disclosure | Code inserts the fixed, approved disclosure line if the reply lacks it (logged as a guard intervention) |
| q1_03 | LLM invented a date of birth and a payment reference the customer never said | Tool-argument guard: identifiers and references must appear in the customer's actual words (digits or spoken number words), otherwise they are ignored without consuming an attempt |
| q1_03 | "Paid two days ago" resolved to a future date; the agent then recorded a *promise* to pay | Calendar now includes the past week; the promise-to-pay tool refuses when the customer's latest words claim payment |
| q1_04 (quota outage) | LLM labelled a call VERIFICATION_FAILED that never attempted verification | Dispositions need tool evidence (e.g. a payment-trace ticket for ALREADY_PAID_TRACE); otherwise INCOMPLETE |
| q1_06 | Agent told a colleague "I'm calling regarding Rahul's **loan**" | Third-party guard: once the speaker may not be the customer, replies mentioning loan/payment/amount are blocked and regenerated, with a fixed neutral line as fallback |
| q1_01 | Agent hung up before the customer could ask a question; duplicate closing line | `end_call` requires an "anything else?" offer or a customer goodbye; closing detection by per-market regex |
| q1_01 (final regression) | Mid-call fallback from Groq to Gemini failed: Gemini 3 rejects replayed tool calls from another provider ("missing thought signature") | Earlier tool calls/results are converted into context notes for Gemini; leaked tool syntax is stripped. q1_01 then passed while switching across Groq → Gemini → OpenRouter |
| several | Model leaked "(Conversation ends)", JSON blobs, invented helpline numbers | Stage directions and JSON stripped; the grounding guard blocked the unsupported "1800-123-456" and fell back to the safe line |

## Honest caveats
- **Models used.** The Groq free tier caps each model at 200k tokens/day. These calls were served by `gpt-oss-120b`/`gpt-oss-20b`, with Gemini Flash-Lite as fallback (the provider per turn is in `summary.json`). The intended primary agent model (Qwen3.8-27B) ran out of quota during development.
- **Latency.** The "Agent p50 ms" column in `summary.md` includes free-tier rate-limit waits; the harness waits for quota instead of failing. It is not production turn latency. Measured component latencies without contention:
- single LLM call with a tool: 0.26–0.45 s (Qwen on Groq); a turn makes 1–3 calls
- Whisper: 0.25–0.35 s
- full-sentence neural TTS: about 1.7 s

So time to first audio is roughly 1.5–3 s in the half-duplex web UI. Streaming TTS (Vapi) removes most of the TTS share.
- **Simulated customers.** Live human test calls should be recorded with the web UI (`uvicorn q1_voice_agent.server:app` → http://localhost:8000). They are saved automatically to `recordings/<call_id>/`.
