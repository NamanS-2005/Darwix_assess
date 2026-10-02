"""Generates the PDF inputs of the source corpus (run once; the PDFs are committed as 'raw' inputs).

- Schedule_of_Charges_and_Policies_2026.pdf : multi-page policy doc with repeated header/footer + page numbers
- Fair_Practices_Code_Collections.pdf        : compliance rules for reminder / recovery calls
- scanned_kyc_update_form.pdf                : image-only page (no text layer) -> must be flagged 'needs_ocr'
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "in_lender" / "pdf"
OUT.mkdir(parents=True, exist_ok=True)
W, H = A4


def doc(path: Path, title: str, pages: list[list[str]]):
    c = canvas.Canvas(str(path), pagesize=A4)
    for i, lines in enumerate(pages, 1):
        c.setFont("Helvetica", 8)
        c.drawString(40, H - 30, "Udaan Credit Finance Ltd. - Customer Policy Document")
        c.drawRightString(W - 40, H - 30, "Version 3.0 | Effective 01-Apr-2026")
        y = H - 70
        if i == 1:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(40, y, title)
            y -= 30
        for line in lines:
            if line.startswith("## "):
                c.setFont("Helvetica-Bold", 11)
                y -= 6
                c.drawString(40, y, line[3:])
                y -= 18
            else:
                c.setFont("Helvetica", 10)
                c.drawString(40, y, line)
                y -= 15
        c.setFont("Helvetica", 8)
        c.drawString(40, 30, "Udaan Credit Finance Ltd. | Regd. Office: Andheri East, Mumbai | www.udaancredit.example")
        c.drawRightString(W - 40, 30, f"Page {i} of {len(pages)}")
        c.showPage()
    c.save()


doc(
    OUT / "Schedule_of_Charges_and_Policies_2026.pdf",
    "Schedule of Charges and Repayment Policy",
    [
        [
            "## 1. Scope",
            "This schedule applies to all Personal Loans, Business Loans and Two-Wheeler Loans",
            "disbursed or serviced by Udaan Credit Finance Ltd. from 01-Apr-2026. It supersedes",
            "Version 2.1 dated 15-Jan-2025.",
            "## 2. Repayment and due date",
            "EMIs are payable monthly on the due date recorded in the loan agreement. A grace",
            "period of 3 calendar days after the due date is allowed before late payment charges.",
            "If the due date falls on a bank holiday, NACH presentation happens on the next working day",
            "and no late charge is levied for that delay.",
            "## 3. Charges",
            "Late payment charge: 2% per month on the overdue EMI, calculated daily.",
            "Bounce / dishonour charge (NACH, cheque, e-mandate): Rs. 590 per instance, GST inclusive.",
            "Duplicate statement: Rs. 200 + GST. Duplicate NOC: Rs. 500 + GST.",
            "EMI date change: Rs. 0 (first request); not permitted more than once per tenure.",
            "Foreclosure (fixed rate, after 6 EMIs): 4% of principal outstanding + GST.",
            "Foreclosure (floating rate, individual borrowers): Nil.",
        ],
        [
            "## 4. Promise to pay (PTP) rules for reminder calls",
            "A customer may commit to pay on any date up to the end of the grace period without",
            "approval. A commitment beyond the grace period must be recorded as 'PTP - beyond grace',",
            "the customer must be informed that late payment charges and bureau reporting may apply,",
            "and the case is flagged for the Customer Assistance team.",
            "Reminder agents must not waive, reduce or promise reversal of any charge. Waiver requests",
            "are reviewed only by the Customer Assistance team within 5 working days.",
            "## 5. Hardship and restructuring",
            "Customers reporting job loss, medical emergency, business disruption or natural calamity",
            "may be offered a review by the Customer Assistance team. Options include a one-time",
            "EMI date shift, a payment plan for overdue amounts of up to 3 instalments, or tenure",
            "restructuring. No option is guaranteed until approved.",
            "## 6. Payment in cash",
            "Cash is accepted only at branches or by authorised collection staff carrying an Udaan ID",
            "card and issuing an instant e-receipt. Customers must not pay cash to anyone else.",
        ],
    ],
)

doc(
    OUT / "Fair_Practices_Code_Collections.pdf",
    "Fair Practices Code - Reminder and Collection Calls",
    [
        [
            "## 1. Calling hours",
            "Customers may be contacted only between 8:00 AM and 7:00 PM local time, unless the",
            "customer has explicitly requested a call outside these hours.",
            "## 2. Identification and disclosure",
            "Every call must start with the caller's name, the company name (Udaan Credit Finance),",
            "the purpose of the call, and a disclosure that the call is recorded for quality and",
            "compliance purposes.",
            "## 3. Identity verification and privacy",
            "Loan details (EMI amount, due date, outstanding) may be shared only after verifying the",
            "customer with at least one identifier: date of birth or last 4 digits of the loan account.",
            "Loan details must never be disclosed to a third party, family member or colleague.",
            "If the person answering is not the customer, end the call politely without details.",
            "## 4. Conduct",
            "Agents must not use threatening, abusive or misleading language, must not threaten legal",
            "action that is not initiated, and must not contact the customer's references or employer",
            "about the loan. Agents must not ask for OTP, PIN, CVV or passwords.",
            "## 5. Escalation",
            "If the customer requests a human, disputes the loan, raises a complaint, or reports",
            "hardship, the call must be transferred or a callback created within 1 working day.",
        ]
    ],
)

# image-only "scan": shapes but no text layer -> text extraction returns nothing
c = canvas.Canvas(str(OUT / "scanned_kyc_update_form.pdf"), pagesize=A4)
for y in range(700, 200, -40):
    c.rect(60, y, 470, 25)
c.showPage()
c.save()
print("PDFs written to", OUT)
