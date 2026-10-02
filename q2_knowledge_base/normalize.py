"""Stage 2 – Normalisation (dates, currency, terminology, headings) and PII protection."""
from __future__ import annotations

import re
from datetime import datetime

from .taxonomy import TEXT_REWRITES

_DATE_FORMATS = ["%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%d.%m.%Y"]


def normalize_date(value: str | None) -> str | None:
    """Mixed formats ('12 March 2026', '02/08/2024', '01-Apr-2026') -> ISO 8601. Day-first (Indian/PH/ID convention)."""
    if not value:
        return None
    v = value.strip().rstrip(".")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_text(text: str) -> str:
    t = " ".join(text.split())
    for pat, rep in TEXT_REWRITES:
        t = re.sub(pat, rep, t)
    t = re.sub(r"₹\s+", "₹", t)
    return t


def normalize_heading(h: str) -> str:
    h = re.sub(r"^\s*(\d+[.)]|[-*])\s*", "", h).strip().rstrip(":")
    if h.isupper():
        h = h.title()
    return h[0].upper() + h[1:] if h else h


# ---------------------------------------------------------------- PII
# Order matters: specific identifiers before generic digit runs.
PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@(?!udaancredit\.example)[\w-]+\.[\w.]+\b")),
    ("UTR", re.compile(r"\bUTR[:\s]*[\d ]{10,16}\d\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("AADHAAR", re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b")),
    ("ID_NIK", re.compile(r"\b\d{16}\b")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("PHONE", re.compile(r"(?:\+91[\s-]?|\+63[\s-]?|\+62[\s-]?|\b0)?\b[6-9]\d{4}[\s-]?\d{5}\b|\+91-\d{5}-\d{5}|\+?\b(?:62|63)\d{9,11}\b")),
    ("ACCOUNT_NO", re.compile(r"\b(?:LAN|Loan A/c|Acct)[:\s#]*\d{8,14}\b|\b\d{12}\b")),
    ("PERSON", re.compile(r"\b(?:Mr|Mrs|Ms|Dr)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-zA-Z']+)?")),
    ("PERSON", re.compile(r"(?<=Agent: )[A-Z][a-z]+(?: [A-Z]\.?)?")),
]


def _luhn_ok(digits: str) -> bool:
    d = [int(c) for c in digits if c.isdigit()]
    if not 13 <= len(d) <= 19:
        return False
    s = 0
    for i, n in enumerate(reversed(d)):
        if i % 2:
            n *= 2
            n = n - 9 if n > 9 else n
        s += n
    return s % 10 == 0


def redact_pii(text: str) -> tuple[str, dict[str, int]]:
    """Replace PII with typed placeholders. Returns (redacted_text, counts_by_type). Raw values are never stored."""
    counts: dict[str, int] = {}

    def sub(kind: str, pattern: re.Pattern, t: str) -> str:
        def repl(m: re.Match) -> str:
            if kind == "CARD" and not _luhn_ok(m.group(0)):
                return m.group(0)
            counts[kind] = counts.get(kind, 0) + 1
            return f"[{kind}]"
        return pattern.sub(repl, t)

    for kind, pat in PII_PATTERNS:
        text = sub(kind, pat, text)
    return text, counts
