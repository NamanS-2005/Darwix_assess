# ASR evaluation – Philippines & Indonesia

Audio: neural TTS voices (fil-PH, en-PH, id-ID, jv-ID, su-ID) + a telephone-band/noise copy; optional real recordings. WER/CER on normalised text (lower-case, punctuation removed). **TTS speech is cleaner than real callers, so absolute WER is optimistic; relative comparisons between configurations and accents are the useful signal.**


## id_multifinance

| Config | n | WER | WER (numbers normalised) | CER | Term recall | Translated→EN | p50 latency ms |
|---|---|---|---|---|---|---|---|
| whisper-v3 | lang hint + prompt | 58 | 20.2% | **13.0%** | 10.7% | 83% | 0 | 302.0 |
| whisper-v3 | auto-detect + prompt | 58 | 20.2% | **13.0%** | 10.7% | 83% | 0 | 304.5 |
| whisper-v3 | lang hint, no prompt | 58 | 22.3% | **15.2%** | 11.4% | 83% | 0 | 291.5 |
| whisper-v3-turbo | lang hint + prompt | 58 | 19.4% | **12.4%** | 10.3% | 87% | 0 | 251.5 |
| gemini-flash-lite | audio prompt | 58 | 18.1% | **10.9%** | 10.4% | 86% | 0 | 2187.0 |

**Breakdown for `whisper-v3 | lang hint + prompt`** (clean audio unless stated)


| cat | n | WER | WER (num-norm) | Term recall |
|---|---|---|---|---|
| colloquial | 8 | 14.6% | 14.6% | 75% |
| escalation | 4 | 4.2% | 4.2% | 100% |
| finance_terms | 8 | 30.9% | 12.8% | 92% |
| formal | 8 | 5.5% | 4.4% | 100% |
| javanese_insertions | 3 | 27.3% | 27.3% | 67% |
| mixed_english | 4 | 29.7% | 29.7% | 67% |
| numbers_dates | 4 | 57.8% | 12.5% | 67% |
| objection | 4 | 9.1% | 9.1% | 75% |
| sundanese_insertions | 3 | 27.8% | 27.8% | 67% |

| voice | n | WER | WER (num-norm) | Term recall |
|---|---|---|---|---|
| id-ID-ArdiNeural | 10 | 16.0% | 6.7% | 88% |
| id-ID-GadisNeural | 12 | 17.1% | 10.1% | 87% |
| jv-ID-DimasNeural | 11 | 29.5% | 22.3% | 79% |
| jv-ID-SitiNeural | 1 | 27.3% | 27.3% | 67% |
| su-ID-JajangNeural | 11 | 21.4% | 14.1% | 76% |
| su-ID-TutiNeural | 1 | 25.0% | 25.0% | 67% |

| condition (same utterances & voice) | n | WER (num-norm) | Term recall |
|---|---|---|---|
| clean | 12 | 9.4% | 87% |
| telephone 8 kHz + babble noise 15 dB | 12 | 9.4% | 87% |

Auto language-ID decisions (whisper auto-detect): {'Indonesian': 58}

**Largest errors (`whisper-v3 | lang hint + prompt`, number-normalised WER)**

- `id07` jv-ID-DimasNeural clean: WER 38% (num-norm 38%)  
  ref: Btw kalau saya bayar via virtual account BCA itu real-time kan, nggak pakai admin fee?  
  hyp: Rukalau soyo bayar via virtual account, co itu realtime kan, nggak pakai admin fee.
- `id07` su-ID-JajangNeural clean: WER 38% (num-norm 38%)  
  ref: Btw kalau saya bayar via virtual account BCA itu real-time kan, nggak pakai admin fee?  
  hyp: Tuh kalau saya bayar ya virtual account, cah itu realtime kan, nggak pakai admin eh.
- `id04` jv-ID-DimasNeural clean: WER 33% (num-norm 33%)  
  ref: Udah saya transfer kemarin sore lewat m-banking, kok belum masuk ya?  
  hyp: Udah soyo transfer kemarin sore lewat mbangking, kok belum masuk yo?
- `id12` id-ID-GadisNeural clean: WER 33% (num-norm 33%)  
  ref: Muhun Teh, teu acan gajian atuh, tapi pas jatuh tempo abdi bayar.  
  hyp: Mohon teh, tau acan gajian atuh, tapi pas jatuh tempo ab dibayar.
- `id05` su-ID-JajangNeural clean: WER 65% (num-norm 31%)  
  ref: Tenor saya dua puluh empat bulan, DP-nya dulu sepuluh persen, cicilannya satu koma dua lima juta.  
  hyp: Tenor saya 24 bulan, benya dulu 10%, cicilannya 1,25 juta.
- `id11` jv-ID-DimasNeural clean: WER 27% (num-norm 27%)  
  ref: Nggih leres, angsuranipun sampun kulo siapke, mangke tak bayar lewat Alfamart.  
  hyp: Gihleres, angsurani pun sampun kulo siapke, mangke tak bayar lewat Alfamart.

## ph_life

| Config | n | WER | WER (numbers normalised) | CER | Term recall | Translated→EN | p50 latency ms |
|---|---|---|---|---|---|---|---|
| whisper-v3 | lang hint + prompt | 40 | 17.1% | **13.4%** | 8.4% | 82% | 0 | 308.5 |
| whisper-v3 | auto-detect + prompt | 40 | 17.1% | **13.4%** | 8.4% | 82% | 0 | 312.0 |
| whisper-v3 | lang hint, no prompt | 40 | 21.6% | **18.7%** | 9.1% | 79% | 0 | 300.5 |
| whisper-v3-turbo | lang hint + prompt | 40 | 22.1% | **18.2%** | 9.1% | 79% | 0 | 255.5 |
| gemini-flash-lite | audio prompt | 40 | 19.3% | **16.5%** | 9.9% | 82% | 0 | 2078.0 |

**Breakdown for `whisper-v3 | lang hint + prompt`** (clean audio unless stated)


| cat | n | WER | WER (num-norm) | Term recall |
|---|---|---|---|---|
| bancassurance | 3 | 14.3% | 14.3% | 100% |
| colloquial | 3 | 20.5% | 20.5% | 78% |
| english_heavy | 3 | 7.4% | 7.4% | 100% |
| escalation | 3 | 15.7% | 15.7% | 78% |
| finance_terms | 3 | 11.1% | 11.1% | 100% |
| formal_tagalog | 3 | 15.6% | 15.6% | 100% |
| numbers_dates | 3 | 48.9% | 12.1% | 56% |
| objection | 3 | 27.8% | 27.8% | 50% |
| taglish | 6 | 11.5% | 11.5% | 78% |

| voice | n | WER | WER (num-norm) | Term recall |
|---|---|---|---|---|
| en-PH-RosaNeural | 10 | 35.2% | 32.2% | 75% |
| fil-PH-AngeloNeural | 10 | 9.6% | 5.6% | 85% |
| fil-PH-BlessicaNeural | 10 | 10.5% | 6.5% | 85% |

| condition (same utterances & voice) | n | WER (num-norm) | Term recall |
|---|---|---|---|
| clean | 10 | 6.5% | 85% |
| telephone 8 kHz + babble noise 15 dB | 10 | 9.2% | 85% |

Auto language-ID decisions (whisper auto-detect): {'Tagalog': 36, 'English': 4}

**Largest errors (`whisper-v3 | lang hint + prompt`, number-normalised WER)**

- `ph05` en-PH-RosaNeural clean: WER 62% (num-norm 62%)  
  ref: Ay naku, gipit pa ako ngayon, sa katapusan pa yung sweldo ko eh.  
  hyp: Ay naku, jipit pa e kayo nayon, es e katapusin pa yung sweldo kayo eh.
- `ph01` en-PH-RosaNeural clean: WER 47% (num-norm 47%)  
  ref: Magandang umaga po. Gusto ko pong malaman kung kailan ang due date ng premium ko.  
  hyp: Magandang umaga pa! Gusto kayo pang malamon kang kailin ang due date ng premium kayo.
- `ph10` en-PH-RosaNeural clean: WER 42% (num-norm 42%)  
  ref: Scam ba 'to? Paano ko malalaman na taga-Bituin Life talaga kayo?  
  hyp: Scambiae 2? Paano kayo malalaman na taga between life talaga kayo?
- `ph09` en-PH-RosaNeural clean: WER 41% (num-norm 41%)  
  ref: Gusto ko pong makausap yung tao, hindi po bot. Pakitawagan na lang po ako bukas ng umaga.  
  hyp: Gusto kayo pong makasap yung tao, hindi pa ba't? Pakitawagan na lang pa ekayo bukas ing umaga.
- `ph07` en-PH-RosaNeural clean: WER 67% (num-norm 36%)  
  ref: Babayaran ko po yung four thousand two hundred fifty sa October fifteen, sa BancoBayan branch.  
  hyp: Babayaran kayo payang 4,250 sa Oct. 15 sa Bancobayan branch.
- `ph02` en-PH-RosaNeural clean: WER 33% (num-norm 33%)  
  ref: Hi po, nag-check ako sa app pero hindi pa nag-reflect yung bayad ko sa GCash kahapon.  
  hyp: Hi pa! Nag-check eh KOSA app pero hindi pa nag-reflect yung bayad KOSAG cash kahapon.