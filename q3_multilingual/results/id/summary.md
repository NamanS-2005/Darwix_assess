# Simulated test calls

6/7 scenarios passed. Customer turns are TTS → Whisper ASR → agent (ASR-in-the-loop).

Agent latency here includes free-tier rate-limit waits (the harness waits for quota instead of failing) – not production turn latency.

| Scenario | Market | Result | Disposition | Turns | KB lookups | Guard | ASR WER | Models used | Recording |
|---|---|---|---|---|---|---|---|---|---|
| [ID – Cooperative customer (formal Bahasa)](id_01_cooperative_formal/transcript.md) | id_multifinance | ✅ pass | PTP_ON_TIME | 4 | 1 | 0 | 2.9% | openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b | [mp3](id_01_cooperative_formal/recording.mp3) |
| [ID – Sector objection (minta hapus denda, motor dioper)](id_02_objection_keringanan_dioper/transcript.md) | id_multifinance | ✅ pass | HARDSHIP_REFERRED | 6 | 1 | 0 | 3.6% | openai/gpt-oss-120b, qwen/qwen3.8-27b | [mp3](id_02_objection_keringanan_dioper/recording.mp3) |
| [ID – Mixed English loanwords (DP, tenor, transfer, cashback)](id_03_mixed_english_terms/transcript.md) | id_multifinance | ✅ pass | PTP_ON_TIME | 3 | 2 | 0 | 9.5% | openai/gpt-oss-120b, qwen/qwen3.8-27b | [mp3](id_03_mixed_english_terms/recording.mp3) |
| [ID – Colloquial speech (belum gajian, telat dikit)](id_04_colloquial_belum_gajian/transcript.md) | id_multifinance | ✅ pass | PTP_BEYOND_GRACE | 5 | 1 | 1 | 8.6% | openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b | [mp3](id_04_colloquial_belum_gajian/recording.mp3) |
| [ID – Human escalation (minta bicara dengan petugas)](id_05_escalation_petugas/transcript.md) | id_multifinance | ✅ pass | ESCALATED | 4 | 0 | 1 | 6.8% | openai/gpt-oss-120b, qwen/qwen3.8-27b | [mp3](id_05_escalation_petugas/recording.mp3) |
| [ID – Javanese-accented speaker (jv-ID voice, ASR in the loop)](id_06_regional_accent_javanese/transcript.md) | id_multifinance | ✅ pass | PTP_ON_TIME | 5 | 0 | 0 | 41.5% | openai/gpt-oss-120b, openai/gpt-oss-20b | [mp3](id_06_regional_accent_javanese/recording.mp3) |
| [ID – Sundanese-accented speaker (su-ID voice, ASR in the loop)](id_07_regional_accent_sundanese/transcript.md) | id_multifinance | ❌ fail | INCOMPLETE | 4 | 0 | 2 | 93.3% | openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b | [mp3](id_07_regional_accent_sundanese/recording.mp3) |

## Checks

**ID – Cooperative customer (formal Bahasa)**
- ✅ disposition — PTP_ON_TIME ∈ ['PTP_ON_TIME']
- ✅ verified — verified=True
- ✅ tool:verify_identity — called
- ✅ tool:get_loan_details — called
- ✅ tool:record_promise_to_pay — called
- ✅ tool:search_knowledge_base — called
- ✅ language/register consistency — Agent tetap menggunakan Bahasa Indonesia yang sopan sepanjang percakapan

**ID – Sector objection (minta hapus denda, motor dioper)**
- ✅ verified — verified=True
- ✅ tool:search_knowledge_base — called
- ✅ tool:escalate_to_human — called
- ✅ never /(denda|biaya) (akan |sudah )?(kami )?(hapus|dihapus|dihapuskan)/ — absent
- ✅ never /tarik motor/ — absent
- ✅ never /menarik motor/ — absent
- ✅ escalation ticket — ESC-FE28F4
- ✅ language/register consistency — Agent consistently used polite Bahasa Indonesia throughout the conversation.

**ID – Mixed English loanwords (DP, tenor, transfer, cashback)**
- ✅ disposition — PTP_ON_TIME ∈ ['PTP_ON_TIME']
- ✅ verified — verified=True
- ✅ tool:search_knowledge_base — called
- ✅ tool:record_promise_to_pay — called
- ✅ says /3\s?%/ — found
- ✅ grounded KB answer — 2 lookups
- ✅ language/register consistency — Agent tetap menggunakan Bahasa Indonesia sepanjang percakapan

**ID – Colloquial speech (belum gajian, telat dikit)**
- ✅ disposition — PTP_BEYOND_GRACE ∈ ['PTP_BEYOND_GRACE', 'HARDSHIP_REFERRED', 'ESCALATED', 'CALLBACK_SCHEDULED']
- ✅ verified — verified=True
- ✅ tool:search_knowledge_base — called
- ✅ says /denda/ — found
- ✅ language/register consistency — Agent consistently used Indonesian with acceptable loanwords, no abrupt English switch.

**ID – Human escalation (minta bicara dengan petugas)**
- ✅ disposition — ESCALATED ∈ ['HARDSHIP_REFERRED', 'ESCALATED', 'CALLBACK_SCHEDULED']
- ✅ verified — verified=True
- ✅ escalation ticket — ESC-DC0DA5,CB-B434D6
- ✅ language/register consistency — Agent consistently used empathetic Bahasa Indonesia throughout the conversation.

**ID – Javanese-accented speaker (jv-ID voice, ASR in the loop)**
- ✅ disposition — PTP_ON_TIME ∈ ['PTP_ON_TIME']
- ✅ verified — verified=True
- ✅ tool:verify_identity — called
- ✅ tool:record_promise_to_pay — called
- ✅ language/register consistency — Agent maintains polite Bahasa Indonesia with appropriate code‑switching, no abrupt language changes.

**ID – Sundanese-accented speaker (su-ID voice, ASR in the loop)**
- ❌ disposition — INCOMPLETE ∈ ['PTP_ON_TIME']
- ❌ verified — verified=False
- ✅ tool:verify_identity — called
- ❌ tool:record_promise_to_pay — NOT called
- ✅ language/register consistency — Semua balasan agen tetap dalam bahasa Indonesia yang sopan tanpa ada pergantian ke bahasa Inggris.
