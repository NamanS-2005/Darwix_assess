# Call in-20261002-014314-f909
- Market: in_lender · Channel: simulated · Customer: C001 (mock CRM)
- Disposition: **WRONG_PARTY** · Verified: False · Tickets: -
- KB lookups: 0 · Guard interventions: 0

**Agent**: Hello, this is Asha, a virtual assistant calling from Udaan Credit Finance. This call is recorded for quality and compliance. Am I speaking with Rahul?
  - source: fixed_script
**Customer**: No, I am his colleague Amit, I just picked up his phone.
  - ASR: {'intended': 'No, I am his colleague Amit, I just picked up his phone.', 'ms': 310}
**Agent**: Sorry, I'm having a technical issue. I'll arrange for our team to call you back. Thank you for your patience.
  - source: fixed_fallback
**Customer**: What is this about? Is it his loan? How much does he owe?
  - ASR: {'intended': 'What is this about? Is it his loan? How much does he owe?', 'ms': 313}
**Agent**: Sorry, I'm having a technical issue. I'll arrange for our team to call you back. Thank you for your patience. Thank you for your time. Have a good day.
  - source: fixed_fallback

## ASR in the loop (customer voice `en-IN-PrabhatNeural`) – WER 0.0%
- said: “No, I am his colleague Amit, I just picked up his phone.”  
  heard: “No, I am his colleague Amit, I just picked up his phone.”
- said: “What is this about? Is it his loan? How much does he owe?”  
  heard: “What is this about? Is it his loan? How much does he owe?”