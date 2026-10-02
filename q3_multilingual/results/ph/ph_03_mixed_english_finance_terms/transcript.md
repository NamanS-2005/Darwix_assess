# Call ph-20261001-214008-3549
- Market: ph_life · Channel: simulated · Customer: P001 (mock CRM)
- Disposition: **PTP_WITHIN_GRACE** · Verified: True · Tickets: -
- KB lookups: 1 · Guard interventions: 0

**Agent**: Magandang gabi po! Ako po si Bea, virtual assistant ng Bituin Life Assurance. Paalala lang po, naka-record ang tawag na ito para sa quality at compliance. Si Ma'am Maria po ba ang kausap ko?
  - source: fixed_script
**Customer**: Hi, yes this is Maria. Para ma-verify, Ninoy birthday is June 9, 1987 and Ninoy policy ends in 4417.
  - ASR: {'intended': 'Hi, yes this is Maria. Para ma-verify, my birthday is June ninth, nineteen eighty-seven, and my policy ends in four four one seven.', 'ms': 434}
**Agent**: Salamat po, Ma'am Maria, verified na po kayo. Paalala lang po, ang premium ninyo na ₱4,250 due na po on October 7. Kailan at paano po kayo magbabayad?
  - tools: verify_identity({"account_last4": "4417", "date_of_birth": "1987-06-09"}); get_loan_details({"": ""}); get_loan_details({})
**Customer**: Hi, yes this is Maria. Quick question lang, if I miss the due date, will Enway policy lapse agad? And what happens to Enway critical illness rider?
  - ASR: {'intended': 'Hi, yes this is Maria. Quick question lang — if I miss the due date, will my policy lapse agad? And what happens to my critical illness rider?', 'ms': 449}
**Agent**: Hindi agad po, Ma'am. May 31-day grace period po kayo, kaya active pa rin ang coverage hanggang November 7. Pero kung lapsed na ang base policy, lapsed din po ang Critical Illness rider. Kailan po kayo magbabayad?
  - tools: search_knowledge_base({"query": "grace period lapse critical illness rider if premium missed"})
  - KB citations: kb_ph_faq_4d8f47 kb_ph_faq_d1e4ff kb_ph_faq_e5bd9f
**Customer**: Okay, gets ko. I'll pay naman within the grace period via Maya, probably mga 10 days after the due date.
  - ASR: {'intended': 'Okay, gets ko. I’ll pay naman within the grace period via Maya, probably mga ten days after the due date.', 'ms': 422}
**Agent**: Naiintindihan ko po, Ma'am Maria. Nakarecord po ang payment sa Maya on October 17, Saturday. Salamat po, at kung may tanong pa po kayo, sabihin niyo lang. Good luck!
  - tools: record_promise_to_pay({"date": "2026-10-17", "mode": "app"})

## ASR in the loop (customer voice `fil-PH-AngeloNeural`) – WER 20.5%
- said: “Hi, yes this is Maria. Para ma-verify, my birthday is June ninth, nineteen eighty-seven, and my policy ends in four four one seven.”  
  heard: “Hi, yes this is Maria. Para ma-verify, Ninoy birthday is June 9, 1987 and Ninoy policy ends in 4417.”
- said: “Hi, yes this is Maria. Quick question lang — if I miss the due date, will my policy lapse agad? And what happens to my critical illness rider?”  
  heard: “Hi, yes this is Maria. Quick question lang, if I miss the due date, will Enway policy lapse agad? And what happens to Enway critical illness rider?”
- said: “Okay, gets ko. I’ll pay naman within the grace period via Maya, probably mga ten days after the due date.”  
  heard: “Okay, gets ko. I'll pay naman within the grace period via Maya, probably mga 10 days after the due date.”