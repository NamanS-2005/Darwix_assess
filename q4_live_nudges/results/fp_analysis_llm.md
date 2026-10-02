# Q4 false-positive analysis

Labelled expectations per scenario (`scenarios/*.yaml`). A nudge matches a label if same type and triggered within the labelled turn +2 turns. Labels marked `duplicate_of_previous` must NOT produce a new nudge (repetition = FP).

**Precision 91% · Recall 100%** (TP 10, FP 1, FN 0).

| Call | Nudges | TP | FP | FN | optional | raw signals | below threshold | merged dups | cooldown | LLM-rejected rule hits | dropped ASR segments |
|---|---|---|---|---|---|---|---|---|---|---|---|
| s1_missed_cross_sell | 2 | 1 | 1 | 0 | 0 | 6 | 0 | 2 | 0 | 0 | 0 |
| s2_compliance_gap | 5 | 4 | 0 | 0 | 1 | 8 | 1 | 0 | 0 | 1 | 0 |
| s3_rising_frustration | 3 | 3 | 0 | 0 | 0 | 18 | 1 | 7 | 0 | 1 | 0 |
| s4_payment_difficulty | 3 | 2 | 0 | 0 | 1 | 7 | 1 | 0 | 0 | 1 | 0 |
| s5_noisy_ambiguous | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |

`raw signals` = every rule/state/LLM candidate before controls; the gap between raw signals and nudges is what thresholds, LLM corroboration, topic grouping, duplicate suppression and cooldowns removed.


### s1_missed_cross_sell – Missed cross-sell (education fees + second two-wheeler)

- ✅ TP `cross_sell` at turn 5 (rule+llm 1.0) – e2e 1638.8 ms – “My daughter just got admission in an engineering college and I have to arrange her fees next month.”
- ❌ FP `payment_difficulty` at turn 5 (llm 0.9) – “this month is a bit heavy for me”
- post-call: acted-on 0/2, missed opportunities 1, unresolved compliance 0

### s2_compliance_gap – Skipped disclosure + verification, risky statements

- ✅ TP `disclosure_missing` at turn 2 (state 0.9) – e2e 378.6 ms – “no recording disclosure before loan discussion”
- ✅ TP `verification_skipped` at turn 2 (state 0.9) – e2e 378.9 ms – “Your business loan EMI of 42,000 rupees is due on the 5th and you need”
- ✅ TP `risky_statement` at turn 4 (rule 0.85) – e2e 813.3 ms – “recovery team will come”
- ✅ TP `unauthorized_waiver` at turn 6 (rule 0.85) – e2e 728.4 ms – “I can waive”
- ➖ optional `payment_difficulty` at turn 3 (acceptable, not counted)
- post-call: acted-on 0/5, missed opportunities 0, unresolved compliance 4

### s3_rising_frustration – Rising frustration (already paid, repeated calls)

- ✅ TP `already_paid_dispute` at turn 5 (rule+llm 1.0) – e2e 1295.5 ms – “I already paid it two days ago through UPI”
- ✅ TP `frustration_rising` at turn 7 (llm 0.85) – e2e 1115.0 ms – “I told you I have already paid”
- ✅ TP `escalation_request` at turn 11 (rule+llm 1.0) – e2e 1120.4 ms – “I want to speak to your manager right now.”
- post-call: acted-on 0/3, missed opportunities 0, unresolved compliance 0

### s4_payment_difficulty – Payment difficulty + callback need

- ✅ TP `payment_difficulty` at turn 5 (rule+llm 1.0) – e2e 729.4 ms – “I lost my job last month and I really don't know how I will pay this EMI”
- ✅ TP `callback_needed` at turn 7 (rule+llm 1.0) – e2e 1901.3 ms – “I'm driving right now. Can you call me back in the evening?”
- ➖ optional `risky_statement` at turn 6 (acceptable, not counted)
- post-call: acted-on 0/3, missed opportunities 0, unresolved compliance 1

### s5_noisy_ambiguous – Noisy, ambiguous but compliant call (should stay quiet)

- post-call: acted-on 0/0, missed opportunities 0, unresolved compliance 0