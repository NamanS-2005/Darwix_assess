# Call in-20261001-200649-8d7f
- Market: in_lender · Channel: simulated · Customer: C004 (mock CRM)
- Disposition: **ESCALATED** · Verified: True · Tickets: ['ESC-8BF56E', 'CB-540FFD']
- KB lookups: 1 · Guard interventions: 0

**Agent**: Hello, this is Asha, a virtual assistant calling from Udaan Credit Finance. This call is recorded for quality and compliance. Am I speaking with Fatima?
  - source: fixed_script
**Customer**: Yes, this is Fatima Sheikh.
  - ASR: {'intended': 'Yes, this is Fatima Sheikh.', 'ms': 307}
**Agent**: Thank you, Fatima. For your security, could you please confirm your date of birth or the last four digits of your loan account number?
**Customer**: My date of birth is 14th February 1988.
  - ASR: {'intended': 'My date of birth is 14\u202fFebruary\u202f1988.', 'ms': 245}
**Agent**: Fatima, this is a reminder for your Personal Loan EMI of ₹12,780, due on Saturday, 3 October 2026. Since auto‑debit is not active, could you let me know how and when you plan to make the payment?
  - tools: verify_identity({"date_of_birth": "1988-02-14"}); get_loan_details({})
**Customer**: The EMI amount looks wrong to me. I think I was charged extra last month. I want to talk to a real person, not a bot.
  - ASR: {'intended': 'The EMI amount looks wrong to me; I think I was charged extra last month. I want to talk to a real person, not a bot.', 'ms': 290}
**Agent**: I understand your concern, Fatima. I’ll have a specialist from our team call you back within one working day. Do you have a preferred date and time for the callback?
  - tools: search_knowledge_base({"query": "EMI amount wrong charged extra last month"}); escalate_to_human({"details": "Customer believes EMI amount wrong and wants to talk to a real person", "reason": "human_request"})
  - KB citations: kb_in_faq_279e0d kb_in_faq_b1ffd6 kb_in_faq_c00b42
**Customer**: Yes, please call me tomorrow at 11 a.m.
  - ASR: {'intended': 'Yes, please call me tomorrow at 11 AM.', 'ms': 579}
**Agent**: A specialist will call you back on Friday, 2 October 2026 at 11:00. Thank you for your time. Have a good day.
  - tools: schedule_callback({"reason": "Customer disputes EMI amount and requested a human specialist.", "date": "2026-10-02", "time": "11:00"}); end_call({"disposition": "ESCALATED", "summary": "Customer disputed EMI amount and requested human callback; scheduled callback for 2026-10-02 11:00."})

## ASR in the loop (customer voice `en-IN-PrabhatNeural`) – WER 6.4%
- said: “Yes, this is Fatima Sheikh.”  
  heard: “Yes, this is Fatima Sheikh.”
- said: “My date of birth is 14 February 1988.”  
  heard: “My date of birth is 14th February 1988.”
- said: “The EMI amount looks wrong to me; I think I was charged extra last month. I want to talk to a real person, not a bot.”  
  heard: “The EMI amount looks wrong to me. I think I was charged extra last month. I want to talk to a real person, not a bot.”
- said: “Yes, please call me tomorrow at 11 AM.”  
  heard: “Yes, please call me tomorrow at 11 a.m.”