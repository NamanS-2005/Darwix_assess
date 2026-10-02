# Q3 findings — ASR, code-switching, accents, localization

All numbers come from `asr_eval/results/asr_report.md` (raw rows in `asr_results.json`) and the simulated calls in `results/ph`, `results/id`.

## 1. Language-specific ASR (configured and tested per market)

**Test set.** 10 PH utterances × 3 voices and 12 ID utterances × 4–5 voices, plus a telephone-band + babble-noise copy. That gives 40 PH and 58 ID audio cases per configuration, over 5 configurations: 490 transcriptions in total.

**Normalisation.** WER is on lower-cased, punctuation-free text. The **number-normalised WER** additionally maps spoken numbers to digits on both sides, so "satu juta dua ratus lima puluh ribu" and "Rp1.250.000" count as equal. Without this, number-heavy utterances look 4× worse than they are.

| Market | Config | WER | **WER (num-norm)** | Finance-term recall | p50 latency |
|---|---|---|---|---|---|
| PH (EN/Filipino/Taglish) | whisper-large-v3, auto-LID + vocab prompt | 17.1% | **13.4%** | 82% | 312 ms |
| | whisper-large-v3, `language=tl` + prompt | 17.1% | 13.4% | 82% | 309 ms |
| | whisper-large-v3, no prompt | 21.6% | 18.7% | 79% | 301 ms |
| | whisper-large-v3-turbo + prompt | 22.1% | 18.2% | 79% | 256 ms |
| | Gemini Flash-Lite (audio in chat) | 19.3% | 16.5% | 82% | 2 078 ms |
| ID (formal/colloquial Bahasa) | whisper-large-v3 + prompt | 20.2% | 13.0% | 83% | 302 ms |
| | whisper-large-v3, no prompt | 22.3% | 15.2% | 83% | 292 ms |
| | **whisper-large-v3-turbo + prompt** | 19.4% | **12.4%** | 87% | 252 ms |
| | Gemini Flash-Lite (audio in chat) | 18.1% | 10.9% | 86% | 2 187 ms |

**Chosen configuration** (in `markets/*/market.yaml`):
- **PH:** `whisper-large-v3`, auto language-ID, Taglish vocabulary prompt. The prompt is worth about 5 WER points, and turbo loses about 5 points on Taglish.
- **ID:** `whisper-large-v3-turbo`, `language=id`, colloquial/finance vocabulary prompt. Gemini is about 1.5 points better but about 9× slower per turn, which is too slow for live turn-taking. It's a good option for post-call QA.

**Code-switching behaviour.**
- Auto language-ID labelled 36 of 40 PH clips Tagalog and 4 English: the English-heavy Taglish lines.
- Whisper never *translated* code-switched speech into English (0 translate-to-English failures across all 490 transcriptions).
- English insurance terms inside Tagalog sentences survive well: premium, policy, beneficiary, coverage and grace period all have 100% term recall in the `finance_terms`/`english_heavy` categories.
- Indonesian with English loanwords ("btw", "real-time", "admin fee") has the highest error of the standard-accent categories (`mixed_english` ≈ 30% WER).

**Observed errors.**
- Whisper writes Filipino numbers as Tagalog words ("isang libo siyam na daan at walumpu't pito" = 1987), which the LLM then mis-converted (1997). This was found in the simulated calls. **Fix:** deterministic number-word → digit normalisation before the LLM (`engine/numwords.py`), plus a verification guard that only accepts identifiers actually present in the customer's words.
- Indonesian "DP-nya" was transcribed as "benya"/"nya" with accented voices, and "VA" and "m-banking" are fragile. The vocabulary prompt helps but doesn't fully fix these.
- Short PH objections ("Scam ba 'to?") were often mis-heard (`objection` term recall 50%), so the agent must confirm before acting on them.

**Telephone/noise robustness** (same utterances and voice, 8 kHz narrow-band + babble at 15 dB SNR):
- PH: WER 6.5% → 9.2%.
- ID: 9.4% → 9.4%.

## 2. Indonesian regional accent

Javanese (`jv-ID`) and Sundanese (`su-ID`) neural voices reading Indonesian text were used as an **accent proxy**: native phonetics speaking Indonesian. The test set also has utterances with Javanese/Sundanese insertions.

| Voice (whisper-large-v3 + prompt, clean) | WER (num-norm) | Term recall |
|---|---|---|
| id-ID standard (Ardi / Gadis) | 6.7% / 10.1% | 88% / 87% |
| **su-ID Sundanese-accented** | 14.1% | 76% |
| **jv-ID Javanese-accented** | 22.3% | 79% |

- **Javanese-accented speech roughly doubles the error rate** against standard Jakarta voices. Typical errors are vowel shifts ("saya" → "soyo") and loanword fragments.
- Javanese/Sundanese *insertions* ("nggih", "sampun", "teu acan", "muhun") are transcribed at about 27% WER regardless of voice.
- The agent still understood intent in the regional-accent simulated calls (see section 3), because it relies on intent, not exact words.
- **Gap:** a TTS accent proxy is not real regional speech. Medan (Batak), Makassar, Madurese and Ambon speakers are untested.

## 3. Simulated calls

The customer's speech goes through TTS and then Whisper before the agent hears it, so ASR errors are part of every call. A language/register judge checks each call for unexpected English switching.

**Philippines 4/5, Indonesia 6/7** ([PH summary](results/ph/summary.md), [ID summary](results/id/summary.md)).

**Language consistency:** every one of the 12 calls passed the language/register judge, including both failures.

| Coverage required | PH | ID |
|---|---|---|
| Cooperative customer | ✅ ph_01 Taglish, PTP_ON_TIME | ✅ id_01 formal, PTP_ON_TIME |
| Sector objection | ✅ ph_02 "parang savings daw" / cancel → honest VUL explanation from KB (not a deposit, not PDIC, returns not guaranteed) → ESCALATED | ✅ id_02 asks to waive denda + motorbike transferred → no waiver promise, no threats → HARDSHIP_REFERRED |
| Mixed English / finance terms | ✅ ph_03 lapse + rider questions answered from KB (31-day grace) → PTP_WITHIN_GRACE | ✅ id_03 pelunasan penalty (3%) + VA real-time from KB → PTP_ON_TIME |
| Colloquial speech | ⚠️ ph_04 casual Tagalog → PTP_WITHIN_GRACE, stayed in Taglish; the check failed only because the simulated customer never asked its KB question | ✅ id_04 "belum gajian, telat dikit" → denda + SLIK disclosure → PTP_BEYOND_GRACE |
| Human escalation | ✅ ph_05 claim concern → ESCALATED, no claim promise | ✅ id_05 PHK / wants staff → ESCALATED |
| Regional accent (ID) | – | ✅ id_06 Javanese-accented voice (41.5% WER) → PTP_ON_TIME · ❌ id_07 Sundanese-accented voice (93% WER on numbers) → INCOMPLETE, nothing disclosed |

### Defects the multilingual suites found, and the deterministic fixes
| Found in | Problem | Fix |
|---|---|---|
| ph_01 | Whisper writes Filipino numbers as Tagalog words ("isang libo siyam na daan at walumpu't pito"); the LLM decoded 1997 instead of 1987 | Number-word → digit normalisation before the LLM, for English, Tagalog, Indonesian, Sundanese and Javanese (`engine/numwords.py`) |
| ph_01/02 | One mis-heard digit ("June 10", "1779") locked the customer out | Read-back of the heard identifier after a failed attempt; impossible ages (<18 or >100) are treated as ASR errors and don't consume an attempt |
| ph_02 | "Sir Jose" heard as "Sergio" → agent declared wrong party and hung up | `mark_wrong_party` requires an explicit third-party cue or a second confirmation |
| ph_02 | The LLM rewrote the Taglish objection into an English KB query → retrieval abstained | Multi-query fallback: if the rewritten query abstains, search with the customer's own words (found the "parang savings daw" playbook entry) |
| ph_04 | Closing turned into a full English sentence for a Tagalog-speaking customer | Language-consistency guard: native-language customer + reply with no native markers and several English function words → regenerate in the customer's language |
| id_04 | Agent said "saya catat rencana pembayaran" without recording it, so no denda disclosure | Action-claim guard (EN/ID/TL): claiming "recorded" without a recorded promise → must call the tool |
| id_04 | My own relative-date check treated "nanti" (later) as "today" | Explicit dates win over relative words; ambiguous words removed |
| id_06 | Javanese "sampun" (= already) misread as "already paid" → same question asked 9× | Javanese/Sundanese glossary in the ID prompt + loop breaker (localised closed question, then escalation) |
| id_07 | Sundanese-accented TTS reads numbers in Sundanese ("sarebu salapan ratus…"); Whisper garbles them ("Sarbu 880 Tilu") | Sundanese/Javanese number words parsed; mixed forms ("sarbu 178" = 1178) handled. **Not fully solved:** "880" for "990" is unrecoverable ASR damage. The production answer is DTMF keypad entry for identifiers, or a human callback |

**Observed ASR risk to keep:** "GCash" was heard as "cash", and the agent recorded the channel as branch. Payment channels should be read back for confirmation.

**Model note:** free-tier quotas forced a mix of Qwen3.8-27B, gpt-oss-120b/20b and Gemini Flash-Lite across calls (listed per call in the summaries).

## 4. Comparison PH vs ID

| | Philippines | Indonesia |
|---|---|---|
| Main ASR risk | Numbers spoken/written in Tagalog; short objections | Regional accents; English loanwords |
| Code-switching | Constant (Taglish is the default register) | Loanwords plus regional insertions; full-English sentences are rare |
| Register | po/opo, Sir/Ma'am + first name, English numbers & dates | Bapak/Ibu, time-of-day greeting, Indonesian number format |
| Sector risk | Lapse of coverage, bancassurance mis-selling ("savings daw") | Late fees (denda), collection conduct (no threats, no emergency-contact disclosure) |
| Best ASR | whisper-large-v3 + prompt | whisper-large-v3-turbo + prompt |
| TTS | fil-PH-BlessicaNeural reads English terms naturally inside Tagalog | id-ID-GadisNeural reads "Rp1.250.000" and "0,2%" correctly |
