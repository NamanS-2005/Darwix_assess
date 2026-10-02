# Call in-20261001-200216-9f52
- Market: in_lender · Channel: simulated · Customer: C002 (mock CRM)
- Disposition: **PTP_BEYOND_GRACE** · Verified: True · Tickets: -
- KB lookups: 1 · Guard interventions: 1

**Agent**: Hello, this is Asha, a virtual assistant calling from Udaan Credit Finance. This call is recorded for quality and compliance. Am I speaking with Sneha?
  - source: fixed_script
**Customer**: Yes, this is Sneha. Why are you calling before the due date?
  - ASR: {'intended': 'Yes, this is Sneha. Why are you calling before the due date?', 'ms': 844}
**Agent**: We’re calling as a friendly reminder that your upcoming EMI is due soon, so you have time to plan the payment. May I verify your identity by confirming your date of birth or the last four digits of your loan account number?
**Customer**: The last four digits are 7730 and my date of birth digits are 1205.
  - ASR: {'intended': 'The last 4 digits are 7730, and my date of birth digits are 1205.', 'ms': 362}
**Agent**: Thank you, Sneha. This is a reminder for your Two‑Wheeler Loan EMI of ₹3,120, due on Sunday, 4 October 2026. How do you plan to make the payment?
  - tools: verify_identity({"account_last4": "7730", "date_of_birth": "1205"}); get_loan_details({})
**Customer**: My salary is delayed, so I can only pay 6 days after the due date by UPI.
  - ASR: {'intended': 'My salary is delayed, so I can only pay 6 days after the due date, by UPI.', 'ms': 351}
**Agent**: Please note, paying after the grace period may attract late payment charges and can be reported to credit bureaus. I have noted this for our Customer Assistance team. I understand. Would it be possible to pay a bit earlier than Saturday, 10 October, or is that the earliest you can manage?
  - tools: record_promise_to_pay({"date": "2026-10-10", "mode": "upi"})
**Customer**: That's the earliest I can manage. Can you waive any late fee for this?
  - ASR: {'intended': "That's the earliest I can manage. Can you waive any late fee for this?", 'ms': 327}
**Agent**: You have committed to pay ₹3,120 via UPI on 10 October 2026; the request for a fee waiver will be reviewed by our Customer Assistance team. Thank you for your time. Have a good day.
  - tools: search_knowledge_base({"query": "late fee waiver"}); end_call({"disposition": "PTP_BEYOND_GRACE", "summary": "Customer Sneha promised to pay ₹3,120 via UPI on 2026-10-10, beyond grace period. Requested late fee waiver; informed it will be reviewed by Customer Assistance team. Call concluded."})
  - KB citations: kb_in_objection_227ba7 kb_in_charges_25adf7 kb_in_policy_6e4887

## Grounding guard interventions
- beyond-grace disclosure missing:  → inserted_fixed_line  (draft: “Please note, paying after the grace period may attract late payment charges and can be reported to credit bureaus. I have noted this for our Customer Assistance”)

## ASR in the loop (customer voice `en-IN-PrabhatNeural`) – WER 1.8%
- said: “Yes, this is Sneha. Why are you calling before the due date?”  
  heard: “Yes, this is Sneha. Why are you calling before the due date?”
- said: “The last 4 digits are 7730, and my date of birth digits are 1205.”  
  heard: “The last four digits are 7730 and my date of birth digits are 1205.”
- said: “My salary is delayed, so I can only pay 6 days after the due date, by UPI.”  
  heard: “My salary is delayed, so I can only pay 6 days after the due date by UPI.”
- said: “That's the earliest I can manage. Can you waive any late fee for this?”  
  heard: “That's the earliest I can manage. Can you waive any late fee for this?”