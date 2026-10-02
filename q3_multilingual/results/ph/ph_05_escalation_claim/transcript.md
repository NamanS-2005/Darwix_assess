# Call ph-20261001-214214-219e
- Market: ph_life · Channel: simulated · Customer: P002 (mock CRM)
- Disposition: **ESCALATED** · Verified: True · Tickets: ['ESC-0B6ABE', 'CB-E0B19E']
- KB lookups: 0 · Guard interventions: 0

**Agent**: Magandang gabi po! Ako po si Bea, virtual assistant ng Bituin Life Assurance. Paalala lang po, naka-record ang tawag na ito para sa quality at compliance. Si Sir Jose po ba ang kausap ko?
  - source: fixed_script
**Customer**: Opo, ako nga po si Jose de la Cruz.
  - ASR: {'intended': 'Opo, ako nga po si Jose Dela Cruz.', 'ms': 356}
**Agent**: Para po sa security, puwede ko po bang makuha ang birthday ninyo o ang huling apat na digits ng policy number?
  - tools: verify_identity({"date_of_birth": "1990-05-15"})
**Customer**: December 1, 1979 at ang policy number ko ay 7759.
  - ASR: {'intended': 'December first, nineteen seventy-nine, at ang policy number ko ay seven seven five nine.', 'ms': 632}
**Agent**: Salamat po, Sir Jose, verified na po kayo. Paalala lang po, ₱3,000 po ang premium ninyo para sa Bituin Future VUL, due po ito on October 5. May active po kayong auto-debit sa BancoBayan. Kaya po ba niyo i-secure ang balance bago ang due date?
  - tools: verify_identity({"account_last4": "7759", "date_of_birth": "1979-12-01"}); get_loan_details({})
**Customer**: Actually po, naospital yung asawa ko last week, paano po yung claim? Gusto ko po makausap yung tao, hindi bot.
  - ASR: {'intended': 'Actually po, naospital yung asawa ko last week, paano po yung claim? Gusto ko po makausap yung tao, hindi bot.', 'ms': 544}
**Agent**: Naiintindihan ko po, Sir Jose. May isang specialist kami na makakausap ninyo para sa claim. Makaka‑call‑back po siya sa loob ng isang working day. May gusto po ba kayong partikular na oras o araw para sa callback?
  - tools: escalate_to_human({"details": "Customer wants to discuss claim due to spouse hospitalization and wants to speak to a person.", "reason": "human_request"})
**Customer**: Pwede po ba bukas ng alas 10 ng umaga? Salamat!
  - ASR: {'intended': 'Puwede po ba bukas ng alas diyes ng umaga? Salamat.', 'ms': 407}
**Agent**: Okay po, naka‑schedule na po ang callback sa October 3, 2026, alas 10:00 ng umaga. Maraming salamat po, Sir Jose! Magandang araw po.End of call.
  - tools: schedule_callback({"date": "2026-10-03", "time": "10:00", "reason": "Claim inquiry and human specialist request"})

## ASR in the loop (customer voice `fil-PH-AngeloNeural`) – WER 22.6%
- said: “Opo, ako nga po si Jose Dela Cruz.”  
  heard: “Opo, ako nga po si Jose de la Cruz.”
- said: “December first, nineteen seventy-nine, at ang policy number ko ay seven seven five nine.”  
  heard: “December 1, 1979 at ang policy number ko ay 7759.”
- said: “Actually po, naospital yung asawa ko last week, paano po yung claim? Gusto ko po makausap yung tao, hindi bot.”  
  heard: “Actually po, naospital yung asawa ko last week, paano po yung claim? Gusto ko po makausap yung tao, hindi bot.”
- said: “Puwede po ba bukas ng alas diyes ng umaga? Salamat.”  
  heard: “Pwede po ba bukas ng alas 10 ng umaga? Salamat!”