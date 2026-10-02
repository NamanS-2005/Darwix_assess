# Retrieval evaluation

KB version `2026.10.01-89661c9` · retrieval mode: **hybrid** · 18 queries · correct 17 · partially correct 1 · incorrect 0

| # | Type | Question | Retrieved record (top-1) | Source reference | Relevance explanation | Verdict |
|---|---|---|---|---|---|---|
| Q01 | product | What is the interest rate on a two-wheeler loan? | `kb_in_product_52467a` – Two-Wheeler Loan | `in_lender/web/home.html` § Two-Wheeler Loan (v1.0) | matched terms: interest, loan, two, wheeler; category=product, topics=- | **correct** |
| Q02 | policy | How much is the bounce charge if my auto-debit fails? | `kb_in_process_6101d0` – Auto-debit (NACH / e-mandate) | `in_lender/web/pay-emi.html` § 1. Auto-debit (NACH / e-mandate) (v1.0) | matched terms: auto, bounce, charge, debit, fail; category=process, topics=payments/late_fees, payments/channels | **partially correct** |
| Q03 | policy | How many days of grace period do I get after the due date? | `kb_in_process_a3a749` – Grace period | `in_lender/web/pay-emi.html` § Grace period (v1.0) | matched terms: after, date, days, due, grace, period; category=process, topics=payments/late_fees, payments/grace_period | **correct** |
| Q04 | qualification | What is the minimum monthly income to qualify for a personal loan? | `kb_in_qualification_5c5c7c` – Personal Loan eligibility criteria | `in_lender/tables/product_eligibility.csv` § Personal Loan eligibility criteria (v1.0) | matched terms: income, loan, minimum, monthly, personal; category=qualification, topics=credit_bureau, eligibility | **correct** |
| Q05 | qualification | Who is eligible for a top-up loan? | `kb_in_qualification_a499d1` – Top-up Loan eligibility criteria | `in_lender/tables/product_eligibility.csv` § Top-up Loan eligibility criteria (v1.0) | matched terms: loan, top, up; category=qualification, topics=eligibility | **correct** |
| Q06 | faq | Will paying late affect my CIBIL score? | `kb_in_faq_3f3266` – Will a late payment affect my CIBIL score? | `in_lender/web/faq.html` § Will a late payment affect my CIBIL score? (v2026-03-12) | matched terms: affect, cibil, late, pay, score; category=faq, topics=payments/late_fees, payments/grace_period, credit_bureau | **correct** |
| Q07 | faq | How can I change my EMI date? | `kb_in_faq_279e0d` – Can I change my EMI due date? | `in_lender/web/faq.html` § Can I change my EMI due date? (v2026-03-12) | matched terms: change, date, emi; category=faq, topics=account/emi_date_change | **correct** |
| Q08 | objection | I already paid yesterday through UPI, why are you still calling me? | `kb_in_faq_1848f4` – I have already paid but still received a reminder. What should I do? | `in_lender/web/faq.html` § I have already paid but still received a reminder. What should I do? (v2026-03-12) | matched terms: already, paid, still, through, upi; category=faq, topics=payments/late_fees, payments/channels, payments/already_paid | **correct** |
| Q09 | objection | My salary is late this month and I don't have money right now | `kb_in_objection_02a0c6` – Objection: "I don't have money right now / salary is late" | `in_lender/docs/objection_playbook.md` § Objection: "I don't have money right now / salary is late" (v2026-08-20) | matched terms: don, late, money, now, right, salary, t; category=objection, topics=payments/late_fees, payments/grace_period, payments/promise_to_pay | **correct** |
| Q10 | objection | Can you waive the bounce charge from last month? | `kb_in_objection_227ba7` – Objection: "Waive my late fee / bounce charge" | `in_lender/docs/objection_playbook.md` § Objection: "Waive my late fee / bounce charge" (v2026-08-20) | matched terms: bounce, charge, waive; category=objection, topics=payments/late_fees, waiver | **correct** |
| Q11 | objection | How do I know this call is not a fraud? | `kb_in_objection_e5f359` – Objection: "Is this call a fraud? How do I know you are from Udaan?" | `in_lender/docs/objection_playbook.md` § Objection: "Is this call a fraud? How do I know you are from Udaan?" (v2026-08-20) | matched terms: call, fraud; category=objection, topics=compliance/verification, compliance/fraud | **correct** |
| Q12 | product | What support do branch partners get? | `kb_in_partnership_a7b67a` – Branch Partnership Benefits | `in_lender/web/partners.html` § Branch Partnership Benefits (v1.0) | matched terms: branch, partner, support; category=partnership, topics=payments/channels | **correct** |
| Q13 | out_of_scope | What is your gold loan interest rate? | — (abstained) | — | retrieval abstained (no confident match) | **correct** |
| Q14 | out_of_scope | Can you book a train ticket to Delhi for me? | — (abstained) | — | retrieval abstained (no confident match) | **correct** |
| Q15 | faq | Ano po mangyayari kapag na-lapse yung policy ko? | `kb_ph_faq_e5bd9f` – Ano ang mangyayari kapag nag-lapse ang policy? | `ph_life/premium_faq_taglish.md` § Ano ang mangyayari kapag nag-lapse ang policy? (v2026-02-01) | matched terms: ano, kapag, lapse, mangyayari, policy; category=faq, topics=policy/lapse, policy/riders | **correct** |
| Q16 | objection | Wala pa po akong pambayad, sa sweldo pa po sa 30 | `kb_ph_objection_e3b149` – Objection: "Wala pa akong pambayad / sa sweldo pa po" | `ph_life/objections_and_rules.md` § Objection: "Wala pa akong pambayad / sa sweldo pa po" (v2026-05-15) | matched terms: akong, pa, pambayad, sweldo, wala; category=objection, topics=payments/grace_period, hardship, compliance/escalation | **correct** |
| Q17 | faq | Berapa dendanya kalau saya telat bayar cicilan? | `kb_id_faq_74136f` – Berapa denda keterlambatan? | `id_multifinance/faq_angsuran.md` § Berapa denda keterlambatan? (v2026-03-01) | matched terms: berapa, denda; category=faq, topics=payments/late_fees, payments/grace_period, credit_bureau | **correct** |
| Q18 | faq | Bayar angsuran bisa lewat Indomaret nggak? | `kb_id_faq_3f8cee` – Bagaimana cara membayar angsuran? | `id_multifinance/faq_angsuran.md` § Bagaimana cara membayar angsuran? (v2026-03-01) | matched terms: angsuran, bayar, indomaret; category=faq, topics=payments/channels, payments/already_paid, policy/apl | **correct** |

## Grounded answers (what the voice agent would say)

**Q01. What is the interest rate on a two-wheeler loan?**  
The interest rate on a two-wheeler loan starts from 11.99% per annum. [1][2]  
Citations: [kb_in_product_52467a | in_lender/web/home.html §Two-Wheeler Loan | v1.0] [kb_in_qualification_4de409 | in_lender/tables/product_eligibility.csv row 4 | v1.0]

**Q02. How much is the bounce charge if my auto-debit fails?**  
The bounce charge for a failed auto-debit is ₹590, inclusive of GST. [2][3]  
Citations: [kb_in_faq_c00b42 | in_lender/web/faq.html §What happens if I miss my EMI due date? | v2026-03-12] [kb_in_charges_7fc660 | in_lender/tables/charges_matrix.csv row 2 | v2026-04-01]

**Q03. How many days of grace period do I get after the due date?**  
You get a grace period of 3 days after the due date before late payment charges are levied. [1][2]  
Citations: [kb_in_process_a3a749 | in_lender/web/pay-emi.html §Grace period | v1.0] [kb_in_policy_728268 | in_lender/pdf/Schedule_of_Charges_and_Policies_2026.pdf p.1 | v3.0]

**Q04. What is the minimum monthly income to qualify for a personal loan?**  
The minimum monthly income required to qualify for a personal loan is ₹25,000. [1]  
Citations: [kb_in_qualification_5c5c7c | in_lender/tables/product_eligibility.csv row 2 | v1.0]

**Q05. Who is eligible for a top-up loan?**  
To be eligible for a top-up loan, you must be an existing customer with 12 on-time EMIs and no current overdue. Additionally, you need to be between 21 and 58 years old with a minimum monthly income of ₹25,000. [1]  
Citations: [kb_in_qualification_a499d1 | in_lender/tables/product_eligibility.csv row 5 | v1.0]

**Q06. Will paying late affect my CIBIL score?**  
Yes, a payment delayed beyond the due date can be reported as overdue and may reduce your CIBIL score. [1]  
Citations: [kb_in_faq_3f3266 | in_lender/web/faq.html §Will a late payment affect my CIBIL score? | v2026-03-12]

**Q07. How can I change my EMI date?**  
You can change your EMI date once during the loan tenure by submitting the EMI Date Change Request form at least 10 days before your next due date. The available dates are the 2nd, 5th, 10th, and 15th, and any broken-period interest will be added to your next EMI. [1][2]  
Citations: [kb_in_faq_279e0d | in_lender/web/faq.html §Can I change my EMI due date? | v2026-03-12] [kb_in_form_1a3782 | in_lender/forms/emi_date_change_form.html §EMI Date Change Request Form | v1.0]

**Q08. I already paid yesterday through UPI, why are you still calling me?**  
Thank you for your patience. Since UPI payments are credited the same day, please share your UTR or receipt number so we can trace the payment and update your account. [1][2][3]  
Citations: [kb_in_faq_1848f4 | in_lender/web/faq.html §I have already paid but still received a reminder. What should I do? | v2026-03-12] [kb_in_objection_9e323d | in_lender/docs/objection_playbook.md §Objection: "I already paid" | v2026-08-20] [kb_in_process_e158c4 | in_lender/web/pay-emi.html §2. UPI | v1.0]

**Q09. My salary is late this month and I don't have money right now**  
I understand your situation. Please let us know when you expect to receive your salary. If it is within 3 days after the due date, we can record a promise to pay; otherwise, late charges and credit bureau reporting may apply, and we can offer a callback from our Customer Assistance team. [1]  
Citations: [kb_in_objection_02a0c6 | in_lender/docs/objection_playbook.md §Objection: "I don't have money right now / salary is late" | v2026-08-20]

**Q10. Can you waive the bounce charge from last month?**  
I am unable to waive or reduce the bounce charge. Your request can be reviewed by the Customer Assistance team within 5 working days, but I cannot promise a specific outcome. [1]  
Citations: [kb_in_objection_227ba7 | in_lender/docs/objection_playbook.md §Objection: "Waive my late fee / bounce charge" | v2026-08-20]

**Q11. How do I know this call is not a fraud?**  
You can verify the call by checking your loan details in the Udaan app or by calling our toll-free number 1800-000-1234. Please remember that we never ask for your OTP, PIN, or card details over the phone. [1][2]  
Citations: [kb_in_objection_e5f359 | in_lender/docs/objection_playbook.md §Objection: "Is this call a fraud? How do I know you are from Udaan?" | v2026-08-20] [kb_in_contact_c8be2e | in_lender/web/contact.html §Report fraud | v1.0]

**Q12. What support do branch partners get?**  
Branch partners receive operational, marketing, and technology support, along with a co-branded outlet kit, access to the Udaan partner CRM, a dedicated relationship manager, and monthly payouts on disbursed volumes. [1]  
Citations: [kb_in_partnership_a7b67a | in_lender/web/partners.html §Branch Partnership Benefits | v1.0]

**Q15. Ano po mangyayari kapag na-lapse yung policy ko?**  
Kapag na-lapse ang policy, wala nang coverage at hindi na mababayaran ang death o rider benefits. Puwedeng i-reinstate ito within 3 years mula sa lapse date kung babayaran ang lahat ng unpaid premiums with interest at magsusumite ng evidence of insurability. [1]  
Citations: [kb_ph_faq_e5bd9f | ph_life/premium_faq_taglish.md §Ano ang mangyayari kapag nag-lapse ang policy? | v2026-02-01]

**Q16. Wala pa po akong pambayad, sa sweldo pa po sa 30**  
Alam ko po ang concern niyo. May 31-day grace period po at active pa rin ang coverage habang nasa loob nito. Kailan po ang exact date ng sweldo niyo para ma-assess natin kung lalampas ba ito sa grace period? [1][2]  
Citations: [kb_ph_objection_e3b149 | ph_life/objections_and_rules.md §Objection: "Wala pa akong pambayad / sa sweldo pa po" | v2026-05-15] [kb_ph_faq_d1e4ff | ph_life/premium_faq_taglish.md §Ano ang grace period? | v2026-02-01]

**Q17. Berapa dendanya kalau saya telat bayar cicilan?**  
Denda keterlambatan sebesar 0,2% per hari dari angsuran yang tertunggak. Denda ini berlaku tanpa masa tenggang sejak tanggal jatuh tempo. [1]  
Citations: [kb_id_faq_74136f | id_multifinance/faq_angsuran.md §Berapa denda keterlambatan? | v2026-03-01]

**Q18. Bayar angsuran bisa lewat Indomaret nggak?**  
Bisa, Anda dapat membayar angsuran di gerai Indomaret dengan menyebutkan "bayar angsuran Pundi Mitra" dan nomor kontrak. Perhatikan bahwa akan dikenakan biaya admin sebesar Rp2.500 hingga Rp5.000. [1]  
Citations: [kb_id_faq_3f8cee | id_multifinance/faq_angsuran.md §Bagaimana cara membayar angsuran? | v2026-03-01]


## Retrieved chunks (top-3) per query

<details><summary>Q01 – What is the interest rate on a two-wheeler loan?</summary>

- [kb_in_product_52467a | in_lender/web/home.html §Two-Wheeler Loan | v1.0] score=0.0334 bm25=14.779 dense=0.805 coverage=0.75  
  > Up to 95% on-road funding for two-wheelers, tenure 12 to 36 months, interest from 11.99% per annum
- [kb_in_qualification_4de409 | in_lender/tables/product_eligibility.csv row 4 | v1.0] score=0.0326 bm25=13.201 dense=0.777 coverage=0.75  
  > Two-Wheeler Loan eligibility: loan amount ₹30,000 to ₹3,00,000; tenure 12-36 months; interest from 11.99% per annum; age 18 to 65 years; minimum monthly income ₹15,000; Valid driving licence; address proof.
- [kb_in_charges_91659e | in_lender/tables/charges_matrix.csv row 10 | v2026-04-01] score=0.0323 bm25=13.988 dense=0.731 coverage=0.8  
  > Two-Wheeler Loan – Foreclosure charge (fixed rate): 3% of principal outstanding (plus GST). Last revised 2026-04-01.

</details>

<details><summary>Q02 – How much is the bounce charge if my auto-debit fails?</summary>

- [kb_in_process_6101d0 | in_lender/web/pay-emi.html §1. Auto-debit (NACH / e-mandate) | v1.0] score=0.0334 bm25=12.878 dense=0.76 coverage=0.72  
  > If you registered a NACH mandate, your EMI is debited automatically from your bank account on the due date. Please keep sufficient balance in the account one day before the due date. If the debit fails, a bounce charge applies and the amount must be paid through any other mode.
- [kb_in_faq_c00b42 | in_lender/web/faq.html §What happens if I miss my EMI due date? | v2026-03-12] score=0.0321 bm25=9.962 dense=0.714 coverage=0.72  
  > If the EMI is not received within the grace period, a late payment charge of 2% per month on the overdue EMI amount is levied, along with a bounce charge of ₹590 (inclusive of GST) if an auto-debit or cheque fails. Missed payments are reported to credit bureaus such as CIBIL and may lower your credi
- [kb_in_charges_7fc660 | in_lender/tables/charges_matrix.csv row 2 | v2026-04-01] score=0.0321 bm25=5.317 dense=0.734 coverage=0.2  
  > Personal Loan – Bounce charge: ₹590 (GST inclusive). Last revised 2026-04-01.

</details>

<details><summary>Q03 – How many days of grace period do I get after the due date?</summary>

- [kb_in_process_a3a749 | in_lender/web/pay-emi.html §Grace period | v1.0] score=0.0334 bm25=17.028 dense=0.852 coverage=0.7  
  > A grace period of 3 days after the due date is available before late payment charges are levied.
- [kb_in_policy_728268 | in_lender/pdf/Schedule_of_Charges_and_Policies_2026.pdf p.1 | v3.0] score=0.0329 bm25=16.977 dense=0.721 coverage=0.7  
  > EMIs are payable monthly on the due date recorded in the loan agreement. A grace period of 3 calendar days after the due date is allowed before late payment charges. If the due date falls on a bank holiday, NACH presentation happens on the next working day and no late charge is levied for that delay
- [kb_in_faq_c00b42 | in_lender/web/faq.html §What happens if I miss my EMI due date? | v2026-03-12] score=0.0318 bm25=13.192 dense=0.672 coverage=0.42  
  > If the EMI is not received within the grace period, a late payment charge of 2% per month on the overdue EMI amount is levied, along with a bounce charge of ₹590 (inclusive of GST) if an auto-debit or cheque fails. Missed payments are reported to credit bureaus such as CIBIL and may lower your credi

</details>

<details><summary>Q04 – What is the minimum monthly income to qualify for a personal loan?</summary>

- [kb_in_qualification_5c5c7c | in_lender/tables/product_eligibility.csv row 2 | v1.0] score=0.0334 bm25=12.991 dense=0.759 coverage=0.73  
  > Personal Loan eligibility: loan amount ₹50,000 to ₹10,00,000; tenure 12-60 months; interest from 13.5% per annum; age 21 to 58 years; minimum monthly income ₹25,000; Salaried with 1 year total work experience; CIBIL 700+.
- [kb_in_qualification_4de409 | in_lender/tables/product_eligibility.csv row 4 | v1.0] score=0.0323 bm25=9.007 dense=0.655 coverage=0.58  
  > Two-Wheeler Loan eligibility: loan amount ₹30,000 to ₹3,00,000; tenure 12-36 months; interest from 11.99% per annum; age 18 to 65 years; minimum monthly income ₹15,000; Valid driving licence; address proof.
- [kb_in_qualification_a499d1 | in_lender/tables/product_eligibility.csv row 5 | v1.0] score=0.0323 bm25=8.943 dense=0.658 coverage=0.58  
  > Top-up Loan eligibility: loan amount ₹50,000 to ₹5,00,000; tenure 12-48 months; interest from 14% per annum; age 21 to 58 years; minimum monthly income ₹25,000; Existing customer with 12 on-time EMIs and no current overdue.

</details>

<details><summary>Q05 – Who is eligible for a top-up loan?</summary>

- [kb_in_qualification_a499d1 | in_lender/tables/product_eligibility.csv row 5 | v1.0] score=0.0334 bm25=11.312 dense=0.813 coverage=0.61  
  > Top-up Loan eligibility: loan amount ₹50,000 to ₹5,00,000; tenure 12-48 months; interest from 14% per annum; age 21 to 58 years; minimum monthly income ₹25,000; Existing customer with 12 on-time EMIs and no current overdue.
- [kb_in_faq_75cb20 | in_lender/web/faq.html §Can I foreclose or prepay my loan? | v2026-03-12] score=0.0306 bm25=2.899 dense=0.58 coverage=0.23  
  > Personal loans can be foreclosed after 6 EMIs are paid. The foreclosure charge is 4% of principal outstanding plus GST. There is no foreclosure charge for individual borrowers on floating-rate loans. Part-prepayment of up to 25% of principal outstanding is allowed once a year.
- [kb_in_product_ab3f69 | in_lender/web/home.html §Personal Loan | v1.0] score=0.0303 bm25=3.018 dense=0.567 coverage=0.23  
  > Unsecured personal loans from ₹50,000 to ₹10 lakh for tenures of 12 to 60 months. Interest rates from 13.5% per annum (reducing balance). Processing fee up to 2.5% of the loan amount plus GST.

</details>

<details><summary>Q06 – Will paying late affect my CIBIL score?</summary>

- [kb_in_faq_3f3266 | in_lender/web/faq.html §Will a late payment affect my CIBIL score? | v2026-03-12] score=0.0334 bm25=43.895 dense=0.857 coverage=1.0  
  > Yes. Udaan reports repayment status to all four credit bureaus every month. A payment delayed beyond the due date can be reported as overdue (DPD) and may reduce your credit score. Paying within the grace period avoids late charges, but the bureau status depends on whether the EMI was paid before th
- [kb_in_faq_c00b42 | in_lender/web/faq.html §What happens if I miss my EMI due date? | v2026-03-12] score=0.0328 bm25=30.717 dense=0.808 coverage=0.56  
  > If the EMI is not received within the grace period, a late payment charge of 2% per month on the overdue EMI amount is levied, along with a bounce charge of ₹590 (inclusive of GST) if an auto-debit or cheque fails. Missed payments are reported to credit bureaus such as CIBIL and may lower your credi
- [kb_in_faq_4dd9d7 | in_lender/web/faq.html §Can I pay part of my EMI? | v2026-03-12] score=0.0316 bm25=10.432 dense=0.73 coverage=0.21  
  > Part payment of an EMI is accepted but the unpaid balance remains overdue and attracts late payment charges. We recommend paying the full EMI before the due date.

</details>

<details><summary>Q07 – How can I change my EMI date?</summary>

- [kb_in_faq_279e0d | in_lender/web/faq.html §Can I change my EMI due date? | v2026-03-12] score=0.0334 bm25=14.729 dense=0.89 coverage=1.0  
  > Yes, once during the loan tenure. Submit the EMI Date Change Request form at least 10 days before the next due date. Available dates are the 2nd, 5th, 10th and 15th. Broken-period interest for the extra days is added to the next EMI.
- [kb_in_form_1a3782 | in_lender/forms/emi_date_change_form.html §EMI Date Change Request Form | v1.0] score=0.0328 bm25=14.1 dense=0.826 coverage=1.0  
  > Use this form to request a change of your monthly EMI due date. Requests must reach us at least 10 days before the next due date. Only one change is allowed during the loan tenure. Fields required: Loan Account No.; Name of Borrower (as per records); Registered Mobile No.; Current EMI Date (options:
- [kb_in_process_4f9b9b | in_lender/web/pay-emi.html §Ways to pay your EMI | v1.0] score=0.0321 bm25=12.467 dense=0.753 coverage=0.52  
  > Your Equated Monthly Instalment (EMI) is due on the due date shown in your loan agreement and the Udaan app. Most customers have EMIs due on the 5th of every month.

</details>

<details><summary>Q08 – I already paid yesterday through UPI, why are you still calling me?</summary>

- [kb_in_faq_1848f4 | in_lender/web/faq.html §I have already paid but still received a reminder. What should I do? | v2026-03-12] score=0.0334 bm25=28.466 dense=0.751 coverage=0.71  
  > Payments can take up to 2 working days to reflect. If you paid through UPI, net banking or branch, keep your UTR or receipt number ready and share it with us. We will trace the payment and update your account. You will not be charged a late fee for a payment that was made on or before the due date.
- [kb_in_objection_9e323d | in_lender/docs/objection_playbook.md §Objection: "I already paid" | v2026-08-20] score=0.0325 bm25=19.886 dense=0.706 coverage=0.24  
  > Thank the customer. Ask for the payment date, mode and UTR / receipt number. Explain that payments can take up to 2 working days to reflect and raise a payment trace request. Never argue with the customer.
- [kb_in_process_e158c4 | in_lender/web/pay-emi.html §2. UPI | v1.0] score=0.0318 bm25=9.319 dense=0.703 coverage=0.27  
  > Pay through the Udaan app or any UPI app using the UPI ID udaanemi@exampleupi. Enter your 12-digit loan account number in the remarks. UPI payments are credited the same day.

</details>

<details><summary>Q09 – My salary is late this month and I don't have money right now</summary>

- [kb_in_objection_02a0c6 | in_lender/docs/objection_playbook.md §Objection: "I don't have money right now / salary is late" | v2026-08-20] score=0.0333 bm25=40.109 dense=0.759 coverage=0.95  
  > Acknowledge the situation. Ask when the customer expects funds. If the expected date is within the grace period of 3 days after the due date, record a promise to pay. If later, explain that late payment charges and credit bureau reporting may apply and offer a callback from the Customer Assistance t
- [kb_in_faq_65da7b | in_lender/web/faq.html §I am facing financial difficulty. What are my options? | v2026-03-12] score=0.0328 bm25=24.157 dense=0.656 coverage=0.0  
  > Please tell us early. Depending on eligibility, our Customer Assistance team can offer a one-time EMI date shift, a short payment plan for the overdue amount, or tenure restructuring as per our board-approved policy. These are reviewed case by case by a specialist and are not guaranteed.
- [kb_in_faq_4dd9d7 | in_lender/web/faq.html §Can I pay part of my EMI? | v2026-03-12] score=0.0321 bm25=10.432 dense=0.601 coverage=0.03  
  > Part payment of an EMI is accepted but the unpaid balance remains overdue and attracts late payment charges. We recommend paying the full EMI before the due date.

</details>

<details><summary>Q10 – Can you waive the bounce charge from last month?</summary>

- [kb_in_objection_227ba7 | in_lender/docs/objection_playbook.md §Objection: "Waive my late fee / bounce charge" | v2026-08-20] score=0.0333 bm25=20.182 dense=0.797 coverage=0.66  
  > Explain politely that reminder agents cannot waive or reduce charges. The request can be reviewed by the Customer Assistance team within 5 working days. Do not promise an outcome.
- [kb_in_charges_7fc660 | in_lender/tables/charges_matrix.csv row 2 | v2026-04-01] score=0.0326 bm25=9.4 dense=0.713 coverage=0.51  
  > Personal Loan – Bounce charge: ₹590 (GST inclusive). Last revised 2026-04-01.
- [kb_in_charges_5fd523 | in_lender/tables/charges_matrix.csv row 5 | v2026-04-01] score=0.032 bm25=9.4 dense=0.71 coverage=0.51  
  > Business Loan – Bounce charge: ₹590 (GST inclusive). Last revised 2026-04-01.

</details>

<details><summary>Q11 – How do I know this call is not a fraud?</summary>

- [kb_in_objection_e5f359 | in_lender/docs/objection_playbook.md §Objection: "Is this call a fraud? How do I know you are from Udaan?" | v2026-08-20] score=0.0333 bm25=12.642 dense=0.737 coverage=1.0  
  > Never ask for OTP, PIN or card details. Tell the customer they can verify by calling the toll-free number 1800-000-1234 or by checking the loan details in the Udaan app. Offer to end the call and let them pay through the app.
- [kb_in_contact_c8be2e | in_lender/web/contact.html §Report fraud | v1.0] score=0.0328 bm25=9.688 dense=0.658 coverage=1.0  
  > Udaan never asks for your OTP, UPI PIN, CVV or passwords over phone, SMS or email. Report suspicious calls to fraud@udaancredit.example.
- [kb_in_compliance_ab4c9b | in_lender/pdf/Fair_Practices_Code_Collections.pdf p.1 | v3.0] score=0.0321 bm25=4.151 dense=0.64 coverage=0.34  
  > Loan details (EMI amount, due date, outstanding) may be shared only after verifying the customer with at least one identifier: date of birth or last 4 digits of the loan account. Loan details must never be disclosed to a third party, family member or colleague. If the person answering is not the cus

</details>

<details><summary>Q12 – What support do branch partners get?</summary>

- [kb_in_partnership_a7b67a | in_lender/web/partners.html §Branch Partnership Benefits | v1.0] score=0.0334 bm25=15.26 dense=0.793 coverage=1.0  
  > Operational, marketing, and technology support is provided to branch partners. Partners receive a co-branded outlet kit, access to the Udaan partner CRM, a dedicated relationship manager and monthly payout on disbursed volumes.
- [kb_in_process_732bca | in_lender/web/pay-emi.html §4. Branch cash or cheque | v1.0] score=0.0323 bm25=3.667 dense=0.561 coverage=0.21  
  > Visit any Udaan branch between 10 AM and 4 PM on working days. Cash payments above ₹49,999 require a PAN card. Always collect a computer-generated receipt. Udaan does not authorise field staff to collect cash without issuing a receipt.
- [kb_in_policy_aa0a46 | in_lender/pdf/Schedule_of_Charges_and_Policies_2026.pdf p.2 | v3.0] score=0.0316 bm25=2.541 dense=0.543 coverage=0.21  
  > Cash is accepted only at branches or by authorised collection staff carrying an Udaan ID card and issuing an instant e-receipt. Customers must not pay cash to anyone else.

</details>

<details><summary>Q13 – What is your gold loan interest rate?</summary>


</details>

<details><summary>Q14 – Can you book a train ticket to Delhi for me?</summary>


</details>

<details><summary>Q15 – Ano po mangyayari kapag na-lapse yung policy ko?</summary>

- [kb_ph_faq_e5bd9f | ph_life/premium_faq_taglish.md §Ano ang mangyayari kapag nag-lapse ang policy? | v2026-02-01] score=0.0334 bm25=28.025 dense=0.901 coverage=0.77  
  > Kapag lapsed na, wala nang coverage — hindi na mababayaran ang death o rider benefits. Puwedeng i-reinstate ang policy within 3 years mula sa lapse date kung babayaran ang lahat ng unpaid premiums with interest at magsusumite ng evidence of insurability (health declaration, minsan medical exam).
- [kb_ph_faq_d1e4ff | ph_life/premium_faq_taglish.md §Ano ang grace period? | v2026-02-01] score=0.0326 bm25=12.174 dense=0.789 coverage=0.54  
  > May grace period po na 31 days mula sa due date. Habang nasa grace period, active pa rin ang coverage ng policy. Kapag hindi nabayaran ang premium pagkatapos ng 31 days, puwedeng mag-lapse ang policy maliban kung may sapat na cash value para sa Automatic Premium Loan (APL).
- [kb_ph_faq_4d8f47 | ph_life/premium_faq_taglish.md §Ano ang riders? | v2026-02-01] score=0.0321 bm25=17.222 dense=0.726 coverage=0.54  
  > Ang riders ay dagdag na benefits na naka-attach sa base policy, gaya ng Critical Illness rider, Accidental Death rider at Waiver of Premium rider. Kapag nag-lapse ang base policy, lapsed din ang riders.

</details>

<details><summary>Q16 – Wala pa po akong pambayad, sa sweldo pa po sa 30</summary>

- [kb_ph_objection_e3b149 | ph_life/objections_and_rules.md §Objection: "Wala pa akong pambayad / sa sweldo pa po" | v2026-05-15] score=0.0333 bm25=44.501 dense=0.787 coverage=1.0  
  > I-acknowledge ang concern. Ipaalala na may 31-day grace period at active pa ang coverage. Itanong kung kailan ang sweldo. Kung lalampas sa grace period, ipaliwanag ang risk ng lapse at i-offer ang callback mula sa Policy Services para pag-usapan ang options (change of payment mode, APL kung qualifie
- [kb_ph_faq_d1e4ff | ph_life/premium_faq_taglish.md §Ano ang grace period? | v2026-02-01] score=0.0328 bm25=13.281 dense=0.67 coverage=0.18  
  > May grace period po na 31 days mula sa due date. Habang nasa grace period, active pa rin ang coverage ng policy. Kapag hindi nabayaran ang premium pagkatapos ng 31 days, puwedeng mag-lapse ang policy maliban kung may sapat na cash value para sa Automatic Premium Loan (APL).
- [kb_ph_faq_6e5c4c | ph_life/premium_faq_taglish.md §Ano ang Automatic Premium Loan (APL)? | v2026-02-01] score=0.0316 bm25=4.863 dense=0.604 coverage=0.0  
  > Para sa traditional policies na may cash value, kung hindi nabayaran ang premium pagkatapos ng grace period, automatic na kukunin ang premium sa cash value bilang loan para hindi mag-lapse ang policy. May interest ang APL na 8% per year at ibabawas ito sa benefits kung hindi mabayaran.

</details>

<details><summary>Q17 – Berapa dendanya kalau saya telat bayar cicilan?</summary>

- [kb_id_faq_74136f | id_multifinance/faq_angsuran.md §Berapa denda keterlambatan? | v2026-03-01] score=0.0334 bm25=26.889 dense=0.869 coverage=0.38  
  > Jika angsuran belum dibayar setelah tanggal jatuh tempo, dikenakan denda keterlambatan sebesar 0,2% per hari dari angsuran yang tertunggak. Tidak ada masa tenggang untuk denda. Keterlambatan juga dilaporkan ke SLIK OJK dan dapat memengaruhi riwayat kredit.
- [kb_id_faq_50ba7e | id_multifinance/faq_angsuran.md §Apakah saya bisa membayar sebagian angsuran? | v2026-03-01] score=0.0328 bm25=16.772 dense=0.77 coverage=0.16  
  > Bisa, tetapi sisa angsuran tetap dianggap tertunggak dan dikenakan denda. Disarankan membayar penuh sebelum jatuh tempo.
- [kb_id_objection_2af971 | id_multifinance/panduan_keberatan.md §Keberatan: "Belum gajian, Pak/Bu" | v2026-06-01] score=0.032 bm25=10.879 dense=0.749 coverage=0.35  
  > Tunjukkan empati. Tanyakan kapan konsumen bisa membayar. Ingatkan bahwa denda 0,2% per hari berlaku sejak lewat jatuh tempo. Jika konsumen menyanggupi tanggal tertentu, catat janji bayar. Jika lebih dari 7 hari setelah jatuh tempo, tawarkan telepon balik dari tim Customer Care untuk membahas opsi.

</details>

<details><summary>Q18 – Bayar angsuran bisa lewat Indomaret nggak?</summary>

- [kb_id_faq_3f8cee | id_multifinance/faq_angsuran.md §Bagaimana cara membayar angsuran? | v2026-03-01] score=0.0334 bm25=19.653 dense=0.821 coverage=0.56  
  > Virtual account BCA, BRI, Mandiri atau BNI (nomor VA = kode perusahaan + nomor kontrak) Gerai Indomaret dan Alfamart (sebutkan "bayar angsuran Pundi Mitra" dan nomor kontrak), biaya admin Rp2.500–Rp5.000 Aplikasi Pundi Mitra, Tokopedia atau DANA Pembayaran melalui virtual account masuk secara real-t
- [kb_id_faq_50ba7e | id_multifinance/faq_angsuran.md §Apakah saya bisa membayar sebagian angsuran? | v2026-03-01] score=0.0328 bm25=9.84 dense=0.745 coverage=0.14  
  > Bisa, tetapi sisa angsuran tetap dianggap tertunggak dan dikenakan denda. Disarankan membayar penuh sebelum jatuh tempo.
- [kb_id_faq_220845 | id_multifinance/faq_angsuran.md §Kapan tanggal jatuh tempo angsuran saya? | v2026-03-01] score=0.0321 bm25=8.673 dense=0.717 coverage=0.14  
  > Tanggal jatuh tempo tercantum di kontrak pembiayaan dan di aplikasi Pundi Mitra. Angsuran (cicilan) dibayar setiap bulan sesuai tenor yang dipilih, misalnya tenor 12, 24 atau 36 bulan.

</details>
