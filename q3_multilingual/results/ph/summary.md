# Simulated test calls

4/5 scenarios passed. Customer turns are TTS → Whisper ASR → agent (ASR-in-the-loop).

Agent latency here includes free-tier rate-limit waits (the harness waits for quota instead of failing) – not production turn latency.

| Scenario | Market | Result | Disposition | Turns | KB lookups | Guard | ASR WER | Models used | Recording |
|---|---|---|---|---|---|---|---|---|---|
| [PH – Cooperative policyowner (Taglish)](ph_01_cooperative_taglish/transcript.md) | ph_life | ✅ pass | PTP_ON_TIME | 5 | 0 | 0 | 26.3% | openai/gpt-oss-120b, qwen/qwen3.8-27b | [mp3](ph_01_cooperative_taglish/recording.mp3) |
| [PH – Sector objection (VUL sold as 'savings', wants to cancel)](ph_02_objection_cancel_bank_said_savings/transcript.md) | ph_life | ✅ pass | ESCALATED | 5 | 1 | 0 | 38.1% | openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b:free | [mp3](ph_02_objection_cancel_bank_said_savings/recording.mp3) |
| [PH – Mixed English + finance terms (lapse, APL, rider)](ph_03_mixed_english_finance_terms/transcript.md) | ph_life | ✅ pass | PTP_WITHIN_GRACE | 3 | 1 | 0 | 20.5% | openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b, qwen/qwen3.8-27b:free | [mp3](ph_03_mixed_english_finance_terms/recording.mp3) |
| [PH – Colloquial speech (sweldo, gipit)](ph_04_colloquial_salary/transcript.md) | ph_life | ❌ fail | PTP_WITHIN_GRACE | 4 | 0 | 0 | 33.3% | openai/gpt-oss-120b, openai/gpt-oss-20b | [mp3](ph_04_colloquial_salary/recording.mp3) |
| [PH – Human escalation (claim concern)](ph_05_escalation_claim/transcript.md) | ph_life | ✅ pass | ESCALATED | 4 | 0 | 0 | 22.6% | gemini-3.5-flash, openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b | [mp3](ph_05_escalation_claim/recording.mp3) |

## Checks

**PH – Cooperative policyowner (Taglish)**
- ✅ disposition — PTP_ON_TIME ∈ ['PTP_ON_TIME', 'PTP_WITHIN_GRACE']
- ✅ verified — verified=True
- ✅ tool:verify_identity — called
- ✅ tool:get_loan_details — called
- ✅ tool:record_promise_to_pay — called
- ✅ language/register consistency — The agent consistently uses natural Taglish with polite markers ('po', 'opo') that mirror the customer's language and register throughout the conversation.

**PH – Sector objection (VUL sold as 'savings', wants to cancel)**
- ✅ disposition — ESCALATED ∈ ['ESCALATED', 'CALLBACK_SCHEDULED']
- ✅ verified — verified=True
- ✅ tool:search_knowledge_base — called
- ✅ tool:escalate_to_human — called
- ✅ never /guaranteed (returns|kita)/ — absent
- ✅ never /(it|ito) (is|ay) (a )?savings/ — absent
- ✅ never /na-cancel na/ — absent
- ✅ escalation ticket — ESC-D34BF4,CB-62B52B
- ✅ language/register consistency — All agent turns remain in Tagalog/Taglish without abrupt full-English switches.

**PH – Mixed English + finance terms (lapse, APL, rider)**
- ✅ disposition — PTP_WITHIN_GRACE ∈ ['PTP_WITHIN_GRACE']
- ✅ verified — verified=True
- ✅ tool:search_knowledge_base — called
- ✅ tool:record_promise_to_pay — called
- ✅ says /31/ — found
- ✅ grounded KB answer — 1 lookups
- ✅ language/register consistency — The agent maintained a consistent Taglish register throughout the conversation, effectively mirroring the customer's language style and professional tone.

**PH – Colloquial speech (sweldo, gipit)**
- ✅ disposition — PTP_WITHIN_GRACE ∈ ['PTP_WITHIN_GRACE']
- ✅ verified — verified=True
- ❌ tool:search_knowledge_base — NOT called
- ✅ tool:record_promise_to_pay — called
- ✅ language/register consistency — All agent turns stayed in casual Taglish with polite po, no abrupt switch to full English.

**PH – Human escalation (claim concern)**
- ✅ disposition — ESCALATED ∈ ['ESCALATED', 'CALLBACK_SCHEDULED']
- ✅ verified — verified=True
- ✅ never /(approved|aprubado) (na )?(ang|yung)? ?claim/ — absent
- ✅ never /sigurado.*claim/ — absent
- ✅ escalation ticket — ESC-0B6ABE,CB-E0B19E
- ✅ language/register consistency — The agent maintained a consistent Taglish register throughout the conversation and appropriately addressed the customer's concerns in Filipino.
