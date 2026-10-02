# Call ph-20261001-235819-7df3
- Market: ph_life · Channel: simulated · Customer: P001 (mock CRM)
- Disposition: **PTP_WITHIN_GRACE** · Verified: True · Tickets: -
- KB lookups: 0 · Guard interventions: 0

**Agent**: Magandang gabi po! Ako po si Bea, virtual assistant ng Bituin Life Assurance. Paalala lang po, naka-record ang tawag na ito para sa quality at compliance. Si Ma'am Maria po ba ang kausap ko?
  - source: fixed_script
**Customer**: Ay, ako to, ate, gipit pa ako ngayon eh, sa katapusan pa sweldo ko.
  - ASR: {'intended': "Ay oo, ako 'to. Ate, gipit pa ako ngayon eh, sa katapusan pa sweldo ko.", 'ms': 325}
**Agent**: Naiintindihan ko po, Ma'am. Para po sa security, puwede ko po bang makuha ang birthday ninyo o ang huling apat na digits ng policy number?
**Customer**: June 9, 1987, at ang huling apat na digits ng policy ko ay 4417.
  - ASR: {'intended': 'June nine, nineteen eighty-seven, at ang huling apat na digits ng policy ko ay four four one seven.', 'ms': 418}
**Agent**: Salamat po, Ma'am Maria. Ang premium para sa Bituin Life Protect ay ₱4,250, due date po ay October 7, 2026. Maaari po ninyong bayaran sa GCash, Maya, auto‑debit, o sa mga Bayad Center at BancoBayan branch. Kung hindi po makabayad sa due date, may 31‑day grace period hanggang November 7. May plano na ba kayo kung kailan at paano magbabayad?
  - tools: verify_identity({"account_last4": "4417", "date_of_birth": "1987-06-09"}); get_loan_details({})
**Customer**: Pwede po ako magbayad via cash sa Oktubre 27, 2000 at 26.
  - ASR: {'intended': 'Pwede po ako magbayad via GCash sa Oktubre 27, 2026.', 'ms': 380}
**Agent**: Ma'am, kung cash po kayo, pwede po ninyong dalhin sa pinakamalapit na Bayad Center o BancoBayan branch. Ano po ang eksaktong petsa kung kailan ninyo balak magbayad?
**Customer**: Pwede po ako magbayad via cash sa Oktubre 27, 2000 at 26.
  - ASR: {'intended': 'Pwede po ako magbayad via GCash sa Oktubre 27, 2026.', 'ms': 1070}
**Agent**: Nai-record ko po ang payment sa cash sa branch para sa October 27, 2026. Salamat po, Ma'am Maria. Kung may tanong pa po kayo, sabihin niyo lang. Otherwise, magandang araw po!
  - tools: record_promise_to_pay({"date": "2026-10-27", "mode": "branch"})

## ASR in the loop (customer voice `fil-PH-AngeloNeural`) – WER 33.3%
- said: “Ay oo, ako 'to. Ate, gipit pa ako ngayon eh, sa katapusan pa sweldo ko.”  
  heard: “Ay, ako to, ate, gipit pa ako ngayon eh, sa katapusan pa sweldo ko.”
- said: “June nine, nineteen eighty-seven, at ang huling apat na digits ng policy ko ay four four one seven.”  
  heard: “June 9, 1987, at ang huling apat na digits ng policy ko ay 4417.”
- said: “Pwede po ako magbayad via GCash sa Oktubre 27, 2026.”  
  heard: “Pwede po ako magbayad via cash sa Oktubre 27, 2000 at 26.”
- said: “Pwede po ako magbayad via GCash sa Oktubre 27, 2026.”  
  heard: “Pwede po ako magbayad via cash sa Oktubre 27, 2000 at 26.”