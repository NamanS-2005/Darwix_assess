"""Stage 1 – Extraction. Turns heterogeneous raw files into `Section`s (one logical unit of text with provenance).

Every extractor is defensive: a failure produces an `ExtractionIssue` instead of crashing the build, so a bad
source never silently disappears and never blocks the rest of the KB.
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from .normalize import normalize_date


@dataclass
class Section:
    market: str
    source_type: str          # web | pdf | table | form | doc | notes
    source_uri: str           # path relative to sources/
    doc_title: str
    heading: str
    text: str
    kind: str = "prose"       # prose | qa | table_row | form | note
    page: int | None = None
    doc_date: str | None = None
    doc_version: str | None = None
    authority_key: str = "web_current"
    language: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class ExtractionIssue:
    source_uri: str
    issue: str
    action: str


BOILERPLATE_SELECTORS = ["nav", "header", "footer", "script", "style", "noscript", "aside",
                         ".cookie-banner", ".breadcrumb", ".chat-widget"]


# ---------------------------------------------------------------- HTML
def extract_html(path: Path, rel: str, market: str) -> tuple[list[Section], list[ExtractionIssue]]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    title = (soup.title.get_text(strip=True) if soup.title else path.stem).split("|")[0].strip()
    meta = soup.find("meta", attrs={"name": "last-updated"})
    doc_date = normalize_date(meta["content"]) if meta else None
    archived = "archive" in path.stem.lower() or "(archived)" in title.lower()
    for sel in BOILERPLATE_SELECTORS:
        for el in soup.select(sel):
            el.decompose()
    main = soup.find("main") or soup.body
    text_len = len(main.get_text(" ", strip=True)) if main else 0
    if text_len < 40:
        return [], [ExtractionIssue(rel, "No readable text after boilerplate removal (JS-rendered single-page app)",
                                    "Skipped. Re-fetch with headless browser (Playwright) rendering before ingest.")]

    authority = "web_archived" if archived else ("form" if main.find("form") else "web_current")
    sections: list[Section] = []
    h1 = main.find("h1")
    h1_text = h1.get_text(strip=True) if h1 else title

    # Forms -> one structured form section
    for form in main.find_all("form"):
        fields = []
        for inp in form.find_all(["input", "select", "textarea"]):
            name = inp.get("name")
            if not name:
                continue
            label = form.find("label", attrs={"for": inp.get("id")}) if inp.get("id") else inp.find_parent("label")
            options = [o.get_text(strip=True) for o in inp.find_all("option")] if inp.name == "select" else []
            fields.append({"raw_name": name, "label": label.get_text(" ", strip=True) if label else name,
                           "required": inp.has_attr("required"), "options": options})
        intro = " ".join(p.get_text(" ", strip=True) for p in main.find_all("p", recursive=False))
        sections.append(Section(market, "form", rel, title, h1_text, intro, kind="form", doc_date=doc_date,
                                authority_key="form", extra={"fields": fields}))
        form.decompose()
    if sections:
        return sections, []

    # FAQ blocks: question heading + answer
    for faq in main.select(".faq"):
        q = faq.find(["h2", "h3", "h4"])
        a = " ".join(p.get_text(" ", strip=True) for p in faq.find_all("p"))
        if q and a:
            sections.append(Section(market, "web", rel, title, q.get_text(strip=True), a, kind="qa",
                                    doc_date=doc_date, authority_key=authority))
        faq.decompose()

    # Heading-delimited prose
    current_heading, buf, section_class = h1_text, [], None
    for el in main.find_all(["h1", "h2", "h3", "p", "li"]):
        if el.name in ("h1", "h2", "h3"):
            if buf:
                sections.append(_prose(market, rel, title, current_heading, buf, doc_date, authority, section_class))
            current_heading, buf = el.get_text(strip=True), []
            parent_section = el.find_parent("section")
            section_class = " ".join(parent_section.get("class", [])) if parent_section else None
        else:
            t = el.get_text(" ", strip=True)
            if t and not (el.get("class") and "updated" in el.get("class")):
                buf.append(t)
    if buf:
        sections.append(_prose(market, rel, title, current_heading, buf, doc_date, authority, section_class))
    return sections, []


def _prose(market, rel, title, heading, buf, doc_date, authority, section_class) -> Section:
    s = Section(market, "web", rel, title, heading, " ".join(buf), doc_date=doc_date, authority_key=authority)
    if section_class and "promo" in section_class:
        s.extra["marketing_promo"] = True
    return s


# ---------------------------------------------------------------- PDF
HEADER_FOOTER_RE = [re.compile(p, re.I) for p in [r"^page \d+ of \d+$", r"page \d+ of \d+\s*$", r"^version [\d.]+ \|"]]
PDF_HEADING_RE = re.compile(r"^(\d+)\.\s+([A-Z].{2,80})$")


def extract_pdf(path: Path, rel: str, market: str) -> tuple[list[Section], list[ExtractionIssue]]:
    try:
        reader = PdfReader(str(path))
        pages = [(p.extract_text() or "") for p in reader.pages]
    except Exception as e:  # corrupt / encrypted
        return [], [ExtractionIssue(rel, f"PDF parse error: {e}", "Skipped. Request a clean copy from the owner.")]
    if not any(p.strip() for p in pages):
        return [], [ExtractionIssue(rel, "PDF has no text layer (scanned image)",
                                    "Skipped and queued for OCR (e.g. Tesseract / Document AI) + human check.")]

    lines_per_page = [[l.strip() for l in p.splitlines() if l.strip()] for p in pages]
    # version / effective date live in the running header – capture before stripping it
    joined = "\n".join(pages)
    ver = re.search(r"Version ([\d.]+)", joined)
    eff = re.search(r"Effective ([0-9A-Za-z-]+)", joined)
    # running headers/footers = lines repeated on every page (or matching page-number patterns)
    counts = Counter(l for lines in lines_per_page for l in set(lines))
    repeated = {l for l, c in counts.items() if len(pages) > 1 and c == len(pages)}

    title = None
    sections: list[Section] = []
    heading, buf, page_of_heading = None, [], 1
    for pno, lines in enumerate(lines_per_page, 1):
        for line in lines:
            if line in repeated or any(r.search(line) for r in HEADER_FOOTER_RE) or line.startswith("Udaan Credit Finance Ltd. -") \
                    or line.startswith("Udaan Credit Finance Ltd. | Regd."):
                continue
            m = PDF_HEADING_RE.match(line)
            if title is None and not m:
                title = line
                continue
            if m:
                if heading and buf:
                    sections.append(Section(market, "pdf", rel, title, heading, " ".join(buf), page=page_of_heading,
                                            authority_key="pdf_policy"))
                heading, buf, page_of_heading = m.group(2).strip(), [], pno
            else:
                buf.append(line)
    if heading and buf:
        sections.append(Section(market, "pdf", rel, title, heading, " ".join(buf), page=page_of_heading, authority_key="pdf_policy"))
    for s in sections:
        s.doc_version = ver.group(1) if ver else None
        s.doc_date = normalize_date(eff.group(1)) if eff else None
    return sections, []


# ---------------------------------------------------------------- CSV tables
def extract_csv(path: Path, rel: str, market: str) -> tuple[list[Section], list[ExtractionIssue]]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    issues, seen, sections = [], set(), []
    for i, row in enumerate(rows, 2):
        key = tuple(v.strip() for v in row.values())
        if key in seen:
            issues.append(ExtractionIssue(f"{rel}#row{i}", "Exact duplicate table row", "Dropped duplicate row."))
            continue
        seen.add(key)
        clean = {k.strip().lower().replace(" ", "_"): (v or "").strip() for k, v in row.items()}
        sections.append(Section(market, "table", rel, path.stem.replace("_", " ").title(), f"row {i}", "",
                                kind="table_row", authority_key="table", extra={"row": clean, "row_number": i}))
    return sections, issues


# ---------------------------------------------------------------- Markdown docs (frontmatter optional)
def extract_markdown(path: Path, rel: str, market: str) -> tuple[list[Section], list[ExtractionIssue]]:
    raw = path.read_text(encoding="utf-8")
    meta = {}
    if raw.startswith("---"):
        _, fm, raw = raw.split("---", 2)
        for line in fm.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    lines = raw.strip().splitlines()
    title = meta.get("source_title") or next((l[2:].strip() for l in lines if l.startswith("# ")), path.stem)
    doc_date = meta.get("effective_date")
    owner_line = next((l for l in lines if "Last reviewed:" in l), None)
    if owner_line and not doc_date:
        doc_date = normalize_date(owner_line.split("Last reviewed:")[1].strip())
    sections, heading, buf = [], None, []
    for line in lines:
        if line.startswith("## "):
            if heading and buf:
                sections.append(_md(market, rel, title, heading, buf, doc_date, meta))
            heading, buf = line[3:].strip(), []
        elif line.startswith("# ") or "Last reviewed:" in line:
            continue
        elif line.strip():
            buf.append(line.strip().lstrip("- ").strip())
    if heading and buf:
        sections.append(_md(market, rel, title, heading, buf, doc_date, meta))
    return sections, []


def _md(market, rel, title, heading, buf, doc_date, meta) -> Section:
    is_faq = "faq" in rel.lower()
    return Section(market, "doc", rel, title, heading, " ".join(buf), kind="qa" if is_faq else "prose",
                   doc_date=doc_date, authority_key="web_current" if is_faq else "playbook", language=meta.get("language"))


# ---------------------------------------------------------------- Plain-text form (label : ____ lines)
def extract_text_form(path: Path, rel: str, market: str) -> tuple[list[Section], list[ExtractionIssue]]:
    lines = [l.rstrip() for l in path.read_text(encoding="utf-8").splitlines()]
    title = next((l.strip() for l in lines if "FORM" in l.upper() and len(l.strip()) > 10), path.stem)
    title = re.split(r"\s{3,}", title)[0].title()
    form_no = re.search(r"Form No\. ([\w-]+)", "\n".join(lines))
    fields, prose = [], []
    for l in lines:
        m = re.match(r"^([A-Za-z][\w .()/]+?)\s*:\s*(.*)$", l.strip())
        if m and ("___" in m.group(2) or "[" in m.group(2)):
            options = re.findall(r"\[[ x]\]\s*([A-Za-z][A-Za-z ]+?)(?=\s*\[|$)", m.group(2))
            fields.append({"raw_name": m.group(1).strip(), "label": m.group(1).strip(), "required": True, "options": [o.strip() for o in options]})
        elif l.strip() and not re.search(r"page \d+ of \d+", l, re.I) and l.strip().upper() != l.strip() and "Signature" not in l:
            prose.append(l.strip())
    return [Section(market, "form", rel, title, title, " ".join(prose), kind="form", authority_key="form",
                    extra={"fields": fields, "form_number": form_no.group(1) if form_no else None})], []


# ---------------------------------------------------------------- Call notes (insight only, PII heavy)
def extract_notes(path: Path, rel: str, market: str) -> tuple[list[Section], list[ExtractionIssue]]:
    text = path.read_text(encoding="utf-8")
    entries = re.split(r"\n(?=\[\d{4}-\d{2}-\d{2} )", text)
    sections = []
    for e in entries:
        m = re.match(r"\[(\d{4}-\d{2}-\d{2}) [\d:]+\]\s*(.*)", e.strip(), re.S)
        if not m:
            continue
        sections.append(Section(market, "notes", rel, "Agent call notes export", f"Call note {m.group(1)}",
                                " ".join(m.group(2).split()), kind="note", doc_date=m.group(1), authority_key="call_notes"))
    return sections, []


def extract_file(path: Path, rel: str, market: str):
    suffix, name = path.suffix.lower(), path.name.lower()
    if suffix == ".html":
        return extract_html(path, rel, market)
    if suffix == ".pdf":
        return extract_pdf(path, rel, market)
    if suffix == ".csv":
        return extract_csv(path, rel, market)
    if suffix == ".md":
        return extract_markdown(path, rel, market)
    if suffix == ".txt" and "notes" in rel:
        return extract_notes(path, rel, market)
    if suffix == ".txt":
        return extract_text_form(path, rel, market)
    return [], [ExtractionIssue(rel, f"Unsupported file type {suffix}", "Skipped.")]
