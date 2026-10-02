# Q3 — Native-language voice bots (Philippines · Indonesia)

Both bots run on the same engine as Q1 (`q1_voice_agent/engine`), so they inherit KB grounding, tool-enforced rules, the
grounding guard and fixed compliance lines — but **everything customer-facing is re-authored per market**, not translated:
prompt, call script, business rules, KB content, fallback/escalation lines, greetings, honorifics, date and money formats,
ASR vocabulary and TTS voice.

| | Philippines | Indonesia |
|---|---|---|
| Company (fictional) | Bituin Life Assurance — life insurance / bancassurance via BancoBayan | Pundi Mitra Finance — motor & electronics multifinance |
| Flow | Premium reminder → payment intent → objections (lapse, APL, rider, "parang savings daw", cancel) → escalation | Angsuran reminder → janji bayar → keberatan (denda, keringanan, motor dioper, penipuan) → eskalasi |
| Languages | English, Filipino/Tagalog, natural Taglish (mirrors customer) | Formal + colloquial Bahasa Indonesia, finance loanwords, Javanese / Sundanese insertions |
| Config | [`markets/ph/`](markets/ph) | [`markets/id/`](markets/id) |
| KB (Q2, market-filtered) | `q2_knowledge_base/sources/ph_life/*` | `q2_knowledge_base/sources/id_multifinance/*` |
| Rules enforced in tools | 31-day grace period (coverage continues), no claim/reinstatement promises, no surrender on call, VUL ≠ savings/PDIC | No grace for denda (0,2 %/day), >7 days → Customer Care callback, never "tarik motor"/threats, never discuss with kontak darurat |
| Calling hours | 08:00–20:00 PHT, Mon–Sat | 08.00–20.00 local (WIB/WITA/WIT) |
| ASR | Groq Whisper large-v3, **auto language-ID** + Taglish vocabulary prompt | Groq Whisper large-v3, `language=id` + colloquial/finance vocabulary prompt |
| TTS | `fil-PH-BlessicaNeural` (native Filipino neural voice) | `id-ID-GadisNeural` (native Indonesian neural voice) |
| Vapi equivalent | Azure STT `fil-PH` + Azure `fil-PH-BlessicaNeural` | Deepgram nova-2 `id` + Azure `id-ID-GadisNeural` |

## Localization, not translation — examples

### Philippines
| Situation | Literal translation of the English bot | What the PH bot says / does | Why |
|---|---|---|---|
| Amount & date | "Ang inyong premium na apat na libo dalawang daan at limampung piso ay dapat bayaran sa ika-pito ng Oktubre." | Actual reply (`results/ph/ph_04`): *"Salamat po, Ma'am Maria. Ang premium para sa Bituin Life Protect ay ₱4,250, due date po ay October 7, 2026… may 31-day grace period hanggang November 7."* | Filipinos say money and dates in English even mid-Tagalog; deep-Tagalog numbers sound like a textbook and are hard to follow on a call. |
| Greeting / address | "Kumusta, ito ba si Maria Santos?" | "**Magandang hapon po!** … Si **Ma'am Maria** po ba ang kausap ko?" | Time-of-day greeting + *po* + *Sir/Ma'am + first name* is the expected service register; bare first name or full name is rude/cold. |
| Can't pay yet | "Ang huling bayad ay magdudulot ng multa." | "Naiintindihan ko po. May **31-day grace period** po at active pa rin ang coverage. Kailan po ang sweldo ninyo?" | Insurance (not lending) logic: the risk is *lapse of coverage*, not a late fee; *sweldo* timing (15th/30th) is the natural anchor. |
| "Sabi ng bangko parang savings daw" | Defensive denial | Honest clarification that it's insurance issued by Bituin Life, VUL fund value isn't guaranteed and not PDIC-insured, then offers advisor callback | Bancassurance mis-selling is the #1 sector complaint; the bot must not repeat the "savings" framing. |
| Fallback | "I don't have that information." (English) | "Pasensya na po, wala po akong impormasyon tungkol diyan ngayon…" (fixed line) | Fallbacks are pre-written in Taglish so the bot never flips to English when it's unsure. |

### Indonesia
| Situation | Literal translation | What the ID bot says / does | Why |
|---|---|---|---|
| Opening | "Halo, ini Dewi dari Pundi Mitra. Panggilan ini direkam." | "**Selamat sore**, saya Dewi, asisten virtual dari Pundi Mitra Finance. Percakapan ini direkam untuk menjaga kualitas layanan. Apakah saya berbicara dengan **Pak Budi**?" | *Selamat pagi/siang/sore/malam* by local time; *Bapak/Ibu* + first name; softer "untuk menjaga kualitas layanan". |
| Terminology | "cicilan bulanan yang setara", "biaya keterlambatan", "tanggal jatuh tempo pembayaran" | **angsuran/cicilan, jatuh tempo, denda, tenor, DP, BPKB** | These are the words customers and collectors actually use; English terms (due date, installment) are avoided except loanwords customers themselves use. |
| Amount | "satu koma dua lima juta rupiah" / "1,250,000" | **Rp1.250.000** (dot thousands separator) — the TTS reads it naturally | Indonesian number formatting; comma is the decimal separator (denda **0,2 %**). |
| "Belum gajian, telat dikit gapapa kan?" | Formal refusal | Actual reply (`results/id`, first id_04 run): *"Boleh, Bu, tapi perlu saya sampaikan kalau lewat jatuh tempo akan ada denda 0,2% per hari dan keterlambatan dilaporkan ke SLIK OJK… Apakah Ibu mau saya jadwalkan telepon balik dari Customer Care?"* | Accommodating register ("Boleh, Bu"), consequence stated factually from the KB, never threatening; >7 days late → Customer Care callback per the call guide. |
| "Motornya udah saya oper" | Argue / threaten repossession | Calm explanation that transfer without written consent isn't allowed and the obligation stays; escalates to supervisor | OJK conduct rules; "tarik motor" talk is explicitly banned in the rules and tested. |
| Javanese/Sundanese insertions ("nggih", "sampun", "teu acan", "muhun") | Not understood | Understood (prompted + ASR vocab), answered in polite standard Indonesian | Regional speakers mix languages; replying in Javanese/Sundanese would be presumptuous, staying in Indonesian is the safe register. |

## Terminology (KB taxonomy synonyms + ASR vocabulary prompts)
- **PH:** premium, policy, policyowner, beneficiary (revocable/irrevocable), rider (Critical Illness, Accidental Death, Waiver of Premium), lapse, reinstatement, grace period, coverage, APL (Automatic Premium Loan), VUL / fund value, bank referral, bancassurance, PDIC, GCash, Maya, Bayad Center, auto-debit · conversational: *po/opo, sige po, sweldo, katapusan, gipit, hulog, bayad*.
- **ID:** angsuran / cicilan, tenor, jatuh tempo, denda keterlambatan, DP (uang muka), BPKB, pembiayaan, pelunasan dipercepat, restrukturisasi, keringanan, SLIK OJK, virtual account (VA), Indomaret/Alfamart · colloquial: *udah, nggak/gak, gajian, telat, dikit, oper* · Javanese: *nggih, mboten, sampun, kulo, matur nuwun* · Sundanese: *muhun, teu acan, abdi, hatur nuhun, atuh*.

## Evidence
- Simulated calls with ASR in the loop: [`results/ph/summary.md`](results/ph/summary.md), [`results/id/summary.md`](results/id/summary.md) (transcripts + MP3 per call). Each run has an LLM-judge check for **language/register consistency** (no unexpected English switches).
- ASR benchmark: [`asr_eval/results/asr_report.md`](asr_eval/results/asr_report.md).
- Findings, comparison and gaps: see [FINDINGS.md](FINDINGS.md).

## Known native-speaker and compliance gaps (honest list)
- **No native-speaker review yet.** Scripts were written to the conventions above but should be reviewed by Filipino and Indonesian collections/insurance agents before production.
- **Synthetic speech.** ASR accuracy was measured on neural TTS voices (incl. jv-ID / su-ID voices as an accent proxy) plus a telephone/noise degradation. Real callers (hesitations, overlaps, cheap handsets, strong Visayan/Batak/Madurese accents) will be worse. `asr_eval/audio/real/<market>/` accepts real recordings and they are scored automatically.
- **Regional accent ≠ regional language.** jv-ID/su-ID voices speak with Javanese/Sundanese phonetics; that is a proxy, not a substitute for real Surabaya/Medan/Makassar speakers.
- **Regulatory text is simplified.** Insurance Commission (PH) and OJK/POJK (ID) rules on contact hours, disclosures and collection conduct are encoded as summarised in the fictional KB; legal review would be required.
- **TTS prosody.** `fil-PH` voices read English insurance terms with Filipino prosody (good), but long Taglish sentences sometimes sound flat; `id-ID` voices read "Rp1.250.000" correctly but may mis-stress English loanwords (e.g. "real-time").
