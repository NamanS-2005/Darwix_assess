# Call in-20261002-014328-eafe
- Market: in_lender · Channel: simulated · Customer: C002 (mock CRM)
- Disposition: **VERIFICATION_FAILED** · Verified: False · Tickets: -
- KB lookups: 0 · Guard interventions: 0

**Agent**: Hello, this is Asha, a virtual assistant calling from Udaan Credit Finance. This call is recorded for quality and compliance. Am I speaking with Sneha?
  - source: fixed_script
**Customer**: Yes, this is Sneha.
  - ASR: {'intended': 'Yes, this is Sneha.', 'ms': 331}
**Agent**: Thank you, Sneha ji. For your security, could you please confirm your date of birth, or the last four digits of your loan account number?
**Customer**: My date of birth is 1st January 1990.
  - ASR: {'intended': 'My date of birth is 1 January 1990.', 'ms': 314}
**Agent**: I heard 1st January 1990. Could you please confirm or correct that, or share the last four digits of your loan account number instead?
  - tools: verify_identity({"date_of_birth": "1990-01-01"})
**Customer**: The last four digits are 1234.
  - ASR: {'intended': 'The last four digits are 1234.', 'ms': 302}
**Agent**: You can reach us anytime via the Udaan app or our helpline. Thank you for your time, have a good day.
  - tools: verify_identity({"account_last4": "1234"}); end_call({"disposition": "VERIFICATION_FAILED", "summary": "Customer Sneha failed identity verification twice (DOB and last 4 digits did not match). No account details shared; directed to app/helpline."})

## ASR in the loop (customer voice `en-IN-PrabhatNeural`) – WER 5.6%
- said: “Yes, this is Sneha.”  
  heard: “Yes, this is Sneha.”
- said: “My date of birth is 1 January 1990.”  
  heard: “My date of birth is 1st January 1990.”
- said: “The last four digits are 1234.”  
  heard: “The last four digits are 1234.”