# Call ph-20261002-005902-1cd7
- Market: ph_life · Channel: simulated · Customer: P002 (mock CRM)
- Disposition: **ESCALATED** · Verified: True · Tickets: ['ESC-D34BF4', 'CB-62B52B']
- KB lookups: 1 · Guard interventions: 0

**Agent**: Magandang gabi po! Ako po si Bea, virtual assistant ng Bituin Life Assurance. Paalala lang po, naka-record ang tawag na ito para sa quality at compliance. Si Sir Jose po ba ang kausap ko?
  - source: fixed_script
**Customer**: Po. Si Jose de la Cruz, 46, December 1, 1979. Policy number ends in 7759.
  - ASR: {'intended': 'Oo, po. Si Jose Dela Cruz, 46, December 1, nineteen seventy‑nine. Policy number ends in seven seven five nine.', 'ms': 1308}
**Agent**: Salamat po, Sir Jose. Ang premium para sa Bituin Future VUL ay ₱3,000, due date po ay October 5, 2026. May auto‑debit na kayo sa BancoBayan. Kung hindi kayo makabayad sa due date, may 31‑day grace period hanggang November 5. May gusto po ba kayong malaman kung paano magbayad?
  - tools: verify_identity({"account_last4": "7759", "date_of_birth": "1979-12-01"}); get_loan_details({"": ""}); get_loan_details({"": ""}); get_loan_details({"": ""}); get_loan_details({})
**Customer**: Hindi po, gusto ko lang po malaman bakit bumaba yung fund value. Sabi ng taga-bank ko parang savings lang daw to. Ipacancel ko na lang.
  - ASR: {'intended': "Hindi po, gusto ko lang po malaman bakit bumaba yung fund value—sabi ng taga‑bangko parang savings lang daw 'to. Ipa‑cancel ko na lang.", 'ms': 455}
**Agent**: Sir Jose, ang Bituin Future VUL ay insurance na may investment component. Hindi ito bank deposit at hindi PDIC insured, kaya ang returns ay hindi guaranteed. Kung may reklamo kayo sa kung paano ito ibinenta, maari po naming i‑schedule ang callback ng licensed financial advisor.
  - tools: search_knowledge_base({"query": "why fund value decreased VUL savings claim"})
  - KB citations: kb_ph_objection_5a3ea9 kb_ph_faq_6e5c4c kb_ph_compliance_54e513
**Customer**: Pakistchedule po ng call.
  - ASR: {'intended': 'Oo, paki‑schedule po ng call.', 'ms': 329}
**Agent**: Pasensya po, Sir Jose. Ang callback ay available mula 8:00–20:00, Lunes hanggang Sabado. Puwede po bang mag‑schedule tayo ng 2:00 PM o 4:00 PM sa araw na ito?
  - tools: schedule_callback({"date": "2026-10-04", "reason": "policy inquiry", "time": "15:00"})
**Customer**: Pwede po, dalawa oras yes ngayon.
  - ASR: {'intended': 'Pwede po, 2:00\u202fPM ngayon.', 'ms': 293}
**Agent**: May isang specialist mula sa aming team ang tatawagan sa loob ng isang working day. May gusto po ba kayong partikular na oras para sa callback?
  - tools: escalate_to_human({"details": "Customer wants to cancel policy and requests callback", "reason": "human_request"})
**Customer**: Pwede po, dalawa oras yan.
  - ASR: {'intended': 'Pwede po, 2:00\u202fPM.', 'ms': 280}
**Agent**: Sige po, Sir Jose. Ang callback ay nakatakda sa October 2, 2026 (Friday) sa 2:42 PM. Maraming salamat po at ingat. Goodbye!
  - tools: schedule_callback({"date": "2026-10-02", "reason": "policy cancellation inquiry", "time": "14:42"})

## ASR in the loop (customer voice `fil-PH-AngeloNeural`) – WER 38.1%
- said: “Oo, po. Si Jose Dela Cruz, 46, December 1, nineteen seventy‑nine. Policy number ends in seven seven five nine.”  
  heard: “Po. Si Jose de la Cruz, 46, December 1, 1979. Policy number ends in 7759.”
- said: “Hindi po, gusto ko lang po malaman bakit bumaba yung fund value—sabi ng taga‑bangko parang savings lang daw 'to. Ipa‑cancel ko na lang.”  
  heard: “Hindi po, gusto ko lang po malaman bakit bumaba yung fund value. Sabi ng taga-bank ko parang savings lang daw to. Ipacancel ko na lang.”
- said: “Oo, paki‑schedule po ng call.”  
  heard: “Pakistchedule po ng call.”
- said: “Pwede po, 2:00 PM ngayon.”  
  heard: “Pwede po, dalawa oras yes ngayon.”
- said: “Pwede po, 2:00 PM.”  
  heard: “Pwede po, dalawa oras yan.”