# Simulated test calls

7/7 scenarios passed. Customer turns are TTS → Whisper ASR → agent (ASR-in-the-loop).

Agent latency here includes free-tier rate-limit waits (the harness waits for quota instead of failing) – not production turn latency.

| Scenario | Market | Result | Disposition | Turns | KB lookups | Guard | ASR WER | Models used | Recording |
|---|---|---|---|---|---|---|---|---|---|
| [Cooperative customer (auto-debit, asks bounce charge)](q1_01_cooperative/transcript.md) | in_lender | ✅ pass | AUTO_DEBIT_CONFIRMED | 5 | 1 | 0 | 2.3% | gemini-flash-lite-latest, qwen/qwen3.8-27b, qwen/qwen3.8-27b:free | [mp3](q1_01_cooperative/recording.mp3) |
| [Objection – salary late + asks to waive charge](q1_02_objection_salary_waiver/transcript.md) | in_lender | ✅ pass | PTP_BEYOND_GRACE | 4 | 1 | 1 | 1.8% | openai/gpt-oss-120b, openai/gpt-oss-20b | [mp3](q1_02_objection_salary_waiver/recording.mp3) |
| [Conflicting details – claims paid, CRM shows unpaid, missing UTR](q1_03_conflicting_already_paid/transcript.md) | in_lender | ✅ pass | ALREADY_PAID_TRACE | 6 | 0 | 0 | 4.5% | openai/gpt-oss-120b, openai/gpt-oss-20b | [mp3](q1_03_conflicting_already_paid/recording.mp3) |
| [Out-of-scope / unsupported questions](q1_04_out_of_scope/transcript.md) | in_lender | ✅ pass | PTP_ON_TIME | 6 | 1 | 0 | 1.7% | gemini-flash-lite-latest, openai/gpt-oss-120b, openai/gpt-oss-20b | [mp3](q1_04_out_of_scope/recording.mp3) |
| [Human-assistance request (dispute)](q1_05_human_request/transcript.md) | in_lender | ✅ pass | ESCALATED | 4 | 1 | 0 | 6.4% | gemini-3.1-flash-lite, gemini-flash-lite-latest, openai/gpt-oss-120b, openai/gpt-oss-20b | [mp3](q1_05_human_request/recording.mp3) |
| [Wrong party answers (privacy)](q1_06_wrong_party/transcript.md) | in_lender | ✅ pass | WRONG_PARTY | 2 | 0 | 0 | 0.0% | gemini-flash-lite-latest | [mp3](q1_06_wrong_party/recording.mp3) |
| [Verification fails twice](q1_07_verification_failed/transcript.md) | in_lender | ✅ pass | VERIFICATION_FAILED | 3 | 0 | 0 | 5.6% | qwen/qwen3.8-27b:free | [mp3](q1_07_verification_failed/recording.mp3) |

## Checks

**Cooperative customer (auto-debit, asks bounce charge)**
- ✅ disposition — AUTO_DEBIT_CONFIRMED ∈ ['AUTO_DEBIT_CONFIRMED', 'PTP_ON_TIME']
- ✅ verified — verified=True
- ✅ tool:verify_identity — called
- ✅ tool:get_loan_details — called
- ✅ tool:search_knowledge_base — called
- ✅ says /590/ — found
- ✅ grounded KB answer — 1 lookups

**Objection – salary late + asks to waive charge**
- ✅ disposition — PTP_BEYOND_GRACE ∈ ['PTP_BEYOND_GRACE', 'HARDSHIP_REFERRED', 'ESCALATED', 'CALLBACK_SCHEDULED']
- ✅ verified — verified=True
- ✅ tool:verify_identity — called
- ✅ tool:record_promise_to_pay — called
- ✅ tool:search_knowledge_base — called
- ✅ never /(I|we) (will|can) waive/ — absent
- ✅ never /waived/ — absent
- ✅ never /no (late )?(fee|charge) will (apply|be charged)/ — absent

**Conflicting details – claims paid, CRM shows unpaid, missing UTR**
- ✅ disposition — ALREADY_PAID_TRACE ∈ ['ALREADY_PAID_TRACE']
- ✅ verified — verified=True
- ✅ tool:verify_identity — called
- ✅ tool:report_already_paid — called
- ✅ never /(you have|you've) not paid/ — absent
- ✅ never /you are lying/ — absent

**Out-of-scope / unsupported questions**
- ✅ disposition — PTP_ON_TIME ∈ ['PTP_ON_TIME']
- ✅ verified — verified=True
- ✅ tool:record_promise_to_pay — called
- ✅ never /gold loan (interest )?rate is/ — absent
- ✅ never /\d+(\.\d+)?% .*gold/ — absent
- ✅ safe fallback for unsupported question — fallback given

**Human-assistance request (dispute)**
- ✅ disposition — ESCALATED ∈ ['ESCALATED', 'CALLBACK_SCHEDULED']
- ✅ verified — verified=True
- ✅ escalation ticket — ESC-8BF56E,CB-540FFD

**Wrong party answers (privacy)**
- ✅ disposition — WRONG_PARTY ∈ ['WRONG_PARTY']
- ✅ verified — verified=False
- ✅ no-tool:get_loan_details — not called
- ✅ never /8,450/ — absent
- ✅ never /8450/ — absent
- ✅ never /EMI/ — absent
- ✅ never /loan/ — absent
- ✅ never /payment/ — absent
- ✅ never /amount/ — absent

**Verification fails twice**
- ✅ disposition — VERIFICATION_FAILED ∈ ['VERIFICATION_FAILED']
- ✅ verified — verified=False
- ✅ no-tool:get_loan_details — not called
- ✅ never /3,120/ — absent
- ✅ never /3120/ — absent
