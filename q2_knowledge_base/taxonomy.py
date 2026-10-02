"""Taxonomy, terminology normalisation, source authority and synonym tables.

Everything that encodes a business decision about the KB lives here so it can be reviewed in one place.
"""

MARKETS = {
    "in_lender": {"short": "in", "default_language": "en", "org": "Udaan Credit Finance (fictional)"},
    "ph_life": {"short": "ph", "default_language": "tl-en", "org": "Bituin Life Assurance (fictional)"},
    "id_multifinance": {"short": "id", "default_language": "id", "org": "Pundi Mitra Finance (fictional)"},
}

# Authority decides who wins on duplicates and fact conflicts (higher = more authoritative).
AUTHORITY = {
    "pdf_policy": 100,   # versioned, approved policy documents
    "web_current": 80,   # live customer-facing website
    "table": 70,         # internal master tables (error-prone, typos)
    "form": 60,
    "playbook": 50,      # training material written by ops teams
    "web_archived": 10,  # archived / superseded pages
    "call_notes": 5,     # free-text notes: insight only, never customer-facing facts
}

CATEGORIES = [
    "product", "policy", "charges", "faq", "objection", "qualification", "compliance",
    "form", "partnership", "contact", "marketing", "insight",
]

# Topic tagging: ordered keyword rules (lower-cased substring match). A record can carry several topics.
TOPIC_RULES = [
    ("payments/late_fees", ["late payment", "late fee", "late charge", "bounce", "dishonour", "denda", "penalti"]),
    ("payments/grace_period", ["grace period", "masa tenggang"]),
    ("payments/channels", ["upi", "nach", "auto-debit", "net banking", "branch", "gcash", "maya", "virtual account", "indomaret", "alfamart", "bayad center", "cara membayar", "paano magbayad"]),
    ("payments/already_paid", ["already paid", "utr", "payment trace", "reference number", "bukti pembayaran"]),
    ("payments/promise_to_pay", ["promise to pay", "ptp", "janji bayar"]),
    ("account/emi_date_change", ["date change", "change my emi", "change my instalment", "emi date"]),
    ("account/foreclosure", ["foreclos", "prepay", "pelunasan", "close my loan"]),
    ("account/statements", ["statement", "interest certificate", "noc"]),
    ("credit_bureau", ["cibil", "credit bureau", "credit score", "slik"]),
    ("hardship", ["hardship", "difficulty", "job loss", "lost job", "restructur", "kesulitan", "wala pa akong pambayad", "belum gajian", "salary is late"]),
    ("compliance/calling_hours", ["calling hours", "8:00 am", "8:00 a.m", "08.00", "contacted only between"]),
    ("compliance/verification", ["verif", "date of birth", "last 4 digits", "4 digit", "huling 4"]),
    ("compliance/disclosure", ["recorded", "direkam", "naka-record", "disclosure"]),
    ("compliance/fraud", ["fraud", "otp", "scam", "penipuan", "pin"]),
    ("compliance/escalation", ["escalat", "transfer", "callback", "eskalasi", "telepon balik"]),
    ("waiver", ["waive", "waiver", "keringanan", "hapus denda"]),
    ("policy/lapse", ["lapse", "reinstat"]),
    ("policy/beneficiary", ["beneficiary"]),
    ("policy/riders", ["rider"]),
    ("policy/apl", ["automatic premium loan", "apl"]),
    ("bancassurance", ["bancassurance", "bank referral", "pdic"]),
    ("collateral", ["bpkb", "jaminan"]),
    ("down_payment", ["uang muka", "dp minimal", "(dp)"]),
    ("grievance", ["grievance", "ombudsman", "complaint"]),
    ("eligibility", ["eligib", "minimum", "vintage", "cibil 700", "min_age"]),
]

PRODUCT_RULES = [
    ("personal_loan", ["personal loan"]),
    ("business_loan", ["business loan", "msme", "proprietor"]),
    ("two_wheeler_loan", ["two-wheeler", "two wheeler"]),
    ("top_up_loan", ["top-up loan", "top-up"]),
    ("life_insurance", ["policy", "premium"]),
    ("motor_financing", ["motor", "bpkb"]),
]

# Content normalisation (applied to text). Keep conservative: only unambiguous rewrites.
TEXT_REWRITES = [
    (r"\bRs\.?\s?(\d)", r"₹\1"),
    (r"\bINR\s?(\d)", r"₹\1"),
    (r"(\d)\s?% p\.m\.", r"\1% per month"),
    (r"(\d)\s?% p\.a\.", r"\1% per annum"),
    (r"\bof POS\b", "of principal outstanding"),
    (r"\binstalment amt\b", "instalment amount"),
    (r"\bInstallment\b", "Instalment"),
    (r"\binstallment\b", "instalment"),
]

# Canonical charge names for the charges table
CHARGE_TYPES = {
    "bounce charge": "Bounce charge",
    "cheque/nach dishonour": "Bounce charge",
    "late payment charges": "Late payment charge",
    "late payment charge": "Late payment charge",
    "foreclosure (fixed)": "Foreclosure charge (fixed rate)",
}

# Canonical form field names (forms come with inconsistent field labels)
FORM_FIELD_MAP = {
    "loan_acct_no": "loan_account_number", "loan account no.": "loan_account_number",
    "borrower_name": "customer_name", "name of account holder": "account_holder_name",
    "mobile": "registered_mobile", "mobile no.": "registered_mobile",
    "current_emi_dt": "current_emi_date", "requested_emi_dt": "requested_emi_date",
    "reason": "reason", "consent_bpi": "broken_period_interest_consent",
    "bank name": "bank_name", "account no.": "bank_account_number", "ifsc": "ifsc_code",
    "account type": "account_type", "max debit amount (rs.)": "max_debit_amount",
    "frequency": "frequency", "start date (dd/mm/yyyy)": "start_date", "end date": "end_date",
    "signature of account holder(s)": "signature",
}

# Query-time synonym expansion (lexical channel). Dense embeddings cover the rest.
SYNONYMS = {
    "emi": ["instalment", "installment"],
    "instalment": ["emi"],
    "installment": ["emi", "instalment"],
    "late": ["late payment charge", "overdue"],
    "fee": ["charge"],
    "fine": ["late payment charge", "charge"],
    "penalty": ["late payment charge", "charge"],
    "bounce": ["dishonour"],
    "rate": ["interest"],
    "cibil": ["credit bureau", "credit score"],
    "score": ["credit bureau", "cibil"],
    "close": ["foreclosure", "foreclose"],
    "foreclose": ["foreclosure"],
    "skip": ["financial difficulty", "hardship"],
    "money": ["financial difficulty", "pay"],
    "salary": ["financial difficulty", "funds"],
    "paid": ["already paid", "utr", "payment"],
    "waive": ["waiver", "waive charges"],
    "fraud": ["otp", "verify", "scam"],
    "scam": ["fraud", "otp"],
    "date": ["due date", "emi date"],
    "cicilan": ["angsuran"],
    "angsuran": ["cicilan"],
    "telat": ["denda", "keterlambatan"],
    "denda": ["keterlambatan"],
    "lunas": ["pelunasan"],
    "bayar": ["pembayaran", "membayar"],
    "sweldo": ["pambayad", "grace period"],
    "lapse": ["lapsed", "reinstate"],
    "bayad": ["magbayad", "payment"],
}

STOPWORDS = set(
    """a an the is are am be to of for in on at by with and or not no do does did can could will would should
    my me i you your we our it this that what when how which who why if as from about there their they
    have has had was were please tell know want need get any some ba ang ng sa na po ko mo ako ka ito iyan
    yang dan di ke dari ini itu saya apa kalau bisa ada untuk dengan""".split()
)
