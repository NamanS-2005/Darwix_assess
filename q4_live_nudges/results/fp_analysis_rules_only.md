# Q4 false-positive analysis

Labelled expectations per scenario (`scenarios/*.yaml`). A nudge matches a label if same type and triggered within the labelled turn +2 turns. Labels marked `duplicate_of_previous` must NOT produce a new nudge (repetition = FP).

**Precision 100% · Recall 60%** (TP 6, FP 0, FN 4).

| Call | Nudges | TP | FP | FN | optional | raw signals | below threshold | merged dups | cooldown | LLM-rejected rule hits | dropped ASR segments |
|---|---|---|---|---|---|---|---|---|---|---|---|
| s1_missed_cross_sell | 0 | 0 | 0 | 1 | 0 | 2 | 2 | 0 | 0 | 0 | 0 |
| s2_compliance_gap | 4 | 4 | 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 |
| s3_rising_frustration | 2 | 2 | 0 | 1 | 0 | 8 | 5 | 1 | 0 | 0 | 0 |
| s4_payment_difficulty | 1 | 0 | 0 | 2 | 1 | 4 | 3 | 0 | 0 | 0 | 0 |
| s5_noisy_ambiguous | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |

`raw signals` = every rule/state/LLM candidate before controls; the gap between raw signals and nudges is what thresholds, LLM corroboration, topic grouping, duplicate suppression and cooldowns removed.


### s1_missed_cross_sell – Missed cross-sell (education fees + second two-wheeler)

- ⚠️ FN expected `cross_sell` at turn 5 – not delivered
- post-call: acted-on 0/0, missed opportunities 0, unresolved compliance 0

### s2_compliance_gap – Skipped disclosure + verification, risky statements

- ✅ TP `disclosure_missing` at turn 2 (state 0.9) – e2e 575.5 ms – “no recording disclosure before loan discussion”
- ✅ TP `verification_skipped` at turn 2 (state 0.9) – e2e 575.7 ms – “Your business loan EMI of 42,000 rupees is due on the 5th and you need”
- ✅ TP `risky_statement` at turn 4 (rule 0.85) – e2e 783.6 ms – “recovery team will come”
- ✅ TP `unauthorized_waiver` at turn 6 (rule 0.85) – e2e 952.7 ms – “I can waive”
- post-call: acted-on 0/4, missed opportunities 0, unresolved compliance 4

### s3_rising_frustration – Rising frustration (already paid, repeated calls)

- ✅ TP `already_paid_dispute` at turn 5 (rule-only 0.75) – e2e 997.2 ms – “already paid”
- ✅ TP `escalation_request` at turn 11 (rule-only 0.8) – e2e 834.3 ms – “your manager”
- ⚠️ FN expected `frustration_rising` at turn 7 – not delivered
- post-call: acted-on 0/2, missed opportunities 0, unresolved compliance 0

### s4_payment_difficulty – Payment difficulty + callback need

- ➖ optional `risky_statement` at turn 6 (acceptable, not counted)
- ⚠️ FN expected `payment_difficulty` at turn 5 – not delivered
- ⚠️ FN expected `callback_needed` at turn 7 – not delivered
- post-call: acted-on 0/1, missed opportunities 0, unresolved compliance 1

### s5_noisy_ambiguous – Noisy, ambiguous but compliant call (should stay quiet)

- post-call: acted-on 0/0, missed opportunities 0, unresolved compliance 0