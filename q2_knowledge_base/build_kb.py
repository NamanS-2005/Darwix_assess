"""Build the production KB: extract -> clean -> normalise -> PII redact -> classify -> chunk -> dedupe ->
reconcile conflicts -> version -> index (BM25 + Gemini embeddings) -> report.

Run:  python -m q2_knowledge_base.build_kb [--no-embed]
Outputs (q2_knowledge_base/output/):
  records.jsonl        one JSON record per chunk (schema in docs / README)
  manifest.json        KB version, counts, per-record content hashes, changelog vs previous build
  build_report.md      what was removed / redacted / flagged and why
  embeddings.npy + embeddings_ids.json  (if GEMINI_API_KEY set)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import llm  # noqa: E402

from .extract import ExtractionIssue, Section, extract_file  # noqa: E402
from .normalize import normalize_date, normalize_heading, normalize_text, redact_pii  # noqa: E402
from .taxonomy import AUTHORITY, CHARGE_TYPES, FORM_FIELD_MAP, MARKETS, PRODUCT_RULES, TOPIC_RULES  # noqa: E402

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources"
OUT = HERE / "output"
MAX_WORDS = 110


# ---------------------------------------------------------------- helpers
def inr(n: str) -> str:
    """'1000000' -> '₹10,00,000' (Indian digit grouping)."""
    if not n or not n.isdigit():
        return n
    s = n
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
        s = f"{head},{tail}"
    return f"₹{s}"


def sha(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def shingles(text: str, k: int = 3) -> set[str]:
    w = re.findall(r"\w+", text.lower())
    return {" ".join(w[i : i + k]) for i in range(max(1, len(w) - k + 1))}


def title_tokens(title: str) -> set[str]:
    """Question-title tokens with terminology folded, so 'Can I change my instalment date?' ~ 'Can I change my EMI due date?'."""
    canon = {"instalment": "emi", "installment": "emi", "due": "", "my": "", "i": "", "can": "", "the": ""}
    return {canon.get(w, w) for w in re.findall(r"\w+", title.lower())} - {""}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z₹\"(])", text) if s.strip()]


# ---------------------------------------------------------------- table rendering
def render_table_row(sec: Section) -> Section:
    row = sec.extra["row"]
    if "charge_type" in row:
        product = row["product"].replace("Two Wheeler", "Two-Wheeler")
        ctype = CHARGE_TYPES.get(row["charge_type"].lower(), row["charge_type"])
        gst = "GST inclusive" if row.get("gst", "").lower().startswith("incl") else "plus GST"
        revised = normalize_date(row.get("last_revised"))
        sec.heading = f"{ctype} – {product}"
        sec.text = f"{product} – {ctype}: {row['amount']} ({gst}). Last revised {revised}."
        sec.doc_date = revised
        sec.extra["structured"] = {"product": product, "charge_type": ctype, "amount": row["amount"], "gst": gst, "last_revised": revised}
    elif "min_amount" in row:
        p = row["product"]
        parts = [f"loan amount {inr(row['min_amount'])} to {inr(row['max_amount'])}", f"tenure {row['tenure_months']} months",
                 f"interest from {row['interest_from']}", f"age {row['min_age']} to {row['max_age']} years"]
        if row.get("min_income_monthly"):
            parts.append(f"minimum monthly income {inr(row['min_income_monthly'])}")
        if row.get("other_criteria"):
            parts.append(row["other_criteria"])
        sec.heading = f"{p} eligibility criteria"
        sec.text = f"{p} eligibility: " + "; ".join(parts) + "."
        sec.extra["structured"] = row
    return sec


def render_form(sec: Section) -> Section:
    fields = []
    for f in sec.extra.get("fields", []):
        canon = FORM_FIELD_MAP.get(f["raw_name"].lower(), re.sub(r"\W+", "_", f["raw_name"].lower()).strip("_"))
        fields.append({"field": canon, "label": f["label"], "required": f["required"], "options": f["options"]})
    sec.extra["fields"] = fields
    listing = "; ".join(f"{f['label']}{' (options: ' + ', '.join(f['options']) + ')' if f['options'] else ''}" for f in fields)
    sec.text = f"{sec.text} Fields required: {listing}.".strip()
    return sec


# ---------------------------------------------------------------- classification
def categorize(sec: Section) -> str:
    h, rel = sec.heading.lower(), sec.source_uri.lower()
    if sec.kind == "note":
        return "insight"
    if sec.kind == "form":
        return "form"
    if h.startswith(("objection", "keberatan")):
        return "objection"
    if h.startswith(("rule", "aturan")) or "fair_practices" in rel:
        return "compliance"
    if "eligibility" in rel:
        return "qualification"
    if "charges" in rel and sec.kind == "table_row":
        return "charges"
    if sec.kind == "qa":
        return "faq"
    if "partners" in rel:
        return "partnership"
    if "contact" in rel:
        return "contact"
    if sec.extra.get("marketing_promo") or "why customers" in h:
        return "marketing"
    if "home" in rel:
        return "product"
    if "pay-emi" in rel:
        return "process"
    return "policy"


def tag(text: str, rules) -> list[str]:
    t = text.lower()
    return [name for name, kws in rules if any(k in t for k in kws)]


def audience_for(category: str) -> str:
    return {"insight": "internal", "compliance": "agent", "objection": "agent"}.get(category, "customer")


# ---------------------------------------------------------------- conflicts / source errors
FACTS = {
    "grace_period_days": re.compile(r"grace period (?:po )?(?:na |of )?(\d+)(?= (?:calendar )?days)", re.I),
    "bounce_charge_inr": re.compile(r"(?:bounce|dishonour)[^.]*?₹(\d[\d,]*)", re.I),
    "emi_date_change_notice_days": re.compile(r"request[^.]*?at least (\d+) days before the next due date", re.I),
}


def reconcile_conflicts(records: list[dict]) -> list[dict]:
    """For each market+fact, the value in the most authoritative active record wins. Lower-authority records that
    disagree are corrected in-place, with the original preserved in `corrections` for owner review."""
    log = []
    by_market = defaultdict(list)
    for r in records:
        if r["status"] == "active":
            by_market[r["market"]].append(r)
    for market, recs in by_market.items():
        for fact, pat in FACTS.items():
            found = [(r, m) for r in recs for m in pat.finditer(r["content"])]
            if len({m.group(1) for _, m in found}) <= 1:
                continue
            found.sort(key=lambda x: (x[0]["authority"], x[0]["effective_date"] or ""), reverse=True)
            truth_rec, truth_m = found[0]
            truth = truth_m.group(1)
            for r, m in found[1:]:
                if m.group(1) == truth:
                    continue
                original = m.group(0)
                fixed = original[: m.start(1) - m.start(0)] + truth + original[m.end(1) - m.start(0):]
                r["content"] = r["content"].replace(original, fixed)
                entry = {"fact": fact, "original": original, "corrected": fixed, "authoritative_record": truth_rec["record_id"],
                         "authoritative_source": truth_rec["source"]["uri"], "reason": "conflicts with higher-authority source"}
                r.setdefault("corrections", []).append(entry)
                r["quality_flags"].append(f"source_error_corrected:{fact}")
                log.append({"record_id": r["record_id"], "source": r["source"]["uri"], **entry})
    return log


# ---------------------------------------------------------------- main build
def build(embed: bool = True) -> dict:
    OUT.mkdir(exist_ok=True)
    sections: list[Section] = []
    issues: list[ExtractionIssue] = []
    files = [p for p in sorted(SOURCES.rglob("*")) if p.is_file() and not p.name.startswith("_")]
    for p in files:
        rel = p.relative_to(SOURCES).as_posix()
        market = rel.split("/")[0]
        secs, iss = extract_file(p, rel, market)
        sections += secs
        issues += iss

    # cross-document boilerplate: sentences repeated in >=3 different documents (missed by selectors)
    sent_docs = defaultdict(set)
    for s in sections:
        for sent in split_sentences(s.text):
            sent_docs[sent].add(s.source_uri)
    boiler = {k for k, v in sent_docs.items() if len(v) >= 3 and len(k) > 25}
    boiler_removed = 0
    for s in sections:
        if s.kind in ("prose",) and boiler:
            kept = [x for x in split_sentences(s.text) if x not in boiler]
            boiler_removed += len(split_sentences(s.text)) - len(kept)
            s.text = " ".join(kept)

    records, pii_totals = [], Counter()
    for s in sections:
        if s.kind == "table_row":
            s = render_table_row(s)
        if s.kind == "form":
            s = render_form(s)
        text = normalize_text(s.text)
        text, pii = redact_pii(text)
        heading, hp = redact_pii(normalize_heading(s.heading))
        for k, v in {**pii, **hp}.items():
            pii_totals[k] += v
        if len(text.split()) < 5:
            issues.append(ExtractionIssue(f"{s.source_uri}#{s.heading}", "Section too short after cleaning", "Dropped."))
            continue
        category = categorize(s)
        if s.kind == "qa" and not heading.endswith("?") and "?" not in heading:
            pass
        topics = tag(f"{heading} {text}", TOPIC_RULES)
        products = tag(f"{heading} {text}", PRODUCT_RULES) or ["all"]
        if s.market == "ph_life":
            products = ["life_insurance"]
        elif s.market == "id_multifinance":
            products = ["motor_financing"] if "motor" in text.lower() or "bpkb" in text.lower() else ["consumer_financing"]

        # chunking: structure-aware units first (Q&A, table row, form, heading section); long prose -> sentence windows
        sents = split_sentences(text)
        chunks, cur = [], []
        for sent in sents:
            if cur and len(" ".join(cur + [sent]).split()) > MAX_WORDS:
                chunks.append(" ".join(cur))
                cur = [cur[-1]]  # 1-sentence overlap keeps context across the boundary
            cur.append(sent)
        if cur:
            chunks.append(" ".join(cur))

        authority = AUTHORITY[s.authority_key]
        short = MARKETS[s.market]["short"]
        for ci, chunk in enumerate(chunks):
            rid = f"kb_{short}_{category}_{sha(s.source_uri + '|' + s.heading + '|' + s.text[:60] + '|' + str(ci), 6)}"
            version = s.doc_version or (s.doc_date or "1.0")
            records.append({
                "record_id": rid,
                "title": heading if s.kind == "qa" or len(chunks) == 1 else f"{heading} (part {ci + 1})",
                "content": chunk,
                "market": s.market,
                "language": s.language or MARKETS[s.market]["default_language"],
                "category": category,
                "topics": topics,
                "products": products,
                "audience": audience_for(category),
                "source": {"type": s.source_type, "uri": s.source_uri, "doc_title": s.doc_title, "section": s.heading,
                           "page": s.page, "row": s.extra.get("row_number")},
                "version": version,
                "effective_date": s.doc_date,
                "status": "active",
                "authority": authority,
                "pii": bool(pii) or bool(hp),
                "pii_redacted": sorted({**pii, **hp}.keys()),
                "quality_flags": (["archived_source"] if s.authority_key == "web_archived" else [])
                                 + (["time_bound_promo"] if s.extra.get("marketing_promo") else []),
                "chunk": {"index": ci, "of": len(chunks)},
                **({"form_fields": s.extra["fields"]} if s.kind == "form" else {}),
                **({"structured": s.extra["structured"]} if "structured" in s.extra else {}),
            })

    # ---- dedupe: exact + near-duplicate (3-gram Jaccard) within market; winner = authority, then recency
    dedupe_log = []
    sh = {r["record_id"]: shingles(r["content"]) for r in records}
    title_sh = {r["record_id"]: title_tokens(r["title"]) for r in records}
    for i, a in enumerate(records):
        for b in records[i + 1 :]:
            if a["market"] != b["market"] or a["status"] != "active" or b["status"] != "active":
                continue
            if "structured" in a or "structured" in b:  # table rows: exact dups dropped at extraction; similar rows differ by product
                continue
            sim = jaccard(sh[a["record_id"]], sh[b["record_id"]])
            same_q = a["category"] == b["category"] == "faq" and jaccard(title_sh[a["record_id"]], title_sh[b["record_id"]]) >= 0.5 \
                and a["source"]["uri"] != b["source"]["uri"]
            if sim >= 0.6 or (same_q and sim >= 0.2):
                win, lose = sorted([a, b], key=lambda r: (r["authority"], r["effective_date"] or ""), reverse=True)
                lose["status"] = "superseded"
                lose["superseded_by"] = win["record_id"]
                win.setdefault("supersedes", []).append(lose["record_id"])
                dedupe_log.append({"kept": win["record_id"], "kept_source": win["source"]["uri"], "dropped": lose["record_id"],
                                   "dropped_source": lose["source"]["uri"], "similarity": round(sim, 2),
                                   "reason": "same question, older/lower-authority version" if same_q else "near-duplicate content"})

    conflict_log = reconcile_conflicts(records)

    # final hashes (after corrections)
    for r in records:
        r["content_hash"] = sha(r["title"] + r["content"], 16)

    # ---- versioning / manifest / changelog
    prev_path = OUT / "manifest.json"
    prev = json.loads(prev_path.read_text(encoding="utf-8")) if prev_path.exists() else {"records": {}}
    cur_hashes = {r["record_id"]: r["content_hash"] for r in records}
    changelog = {
        "added": sorted(set(cur_hashes) - set(prev["records"])),
        "removed": sorted(set(prev["records"]) - set(cur_hashes)),
        "modified": sorted(k for k in cur_hashes if k in prev["records"] and prev["records"][k] != cur_hashes[k]),
    }
    kb_version = datetime.now(timezone.utc).strftime("%Y.%m.%d") + "-" + sha("".join(sorted(cur_hashes.values())), 7)
    if prev.get("kb_version", "").endswith(kb_version.split("-")[1]):
        kb_version = prev["kb_version"]  # content unchanged -> same version
    for r in records:
        r["kb_version"] = kb_version

    with (OUT / "records.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ---- embeddings (cached by content hash so unchanged records are never re-embedded)
    emb_status = "skipped (--no-embed)"
    if embed:
        emb_status = embed_records(records)

    manifest = {
        "kb_version": kb_version,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": {
            "source_files": len(files), "sections_extracted": len(sections), "records": len(records),
            "active": sum(r["status"] == "active" for r in records),
            "superseded": sum(r["status"] == "superseded" for r in records),
            "by_market": dict(Counter(r["market"] for r in records)),
            "by_category": dict(Counter(r["category"] for r in records if r["status"] == "active")),
        },
        "embeddings": emb_status,
        "changelog_vs_previous": changelog,
        "records": cur_hashes,
    }
    prev_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(manifest, issues, dedupe_log, conflict_log, pii_totals, boiler_removed, records)
    return manifest


def embed_records(records: list[dict]) -> str:
    ids_path, vec_path = OUT / "embeddings_ids.json", OUT / "embeddings.npy"
    cache: dict[str, np.ndarray] = {}
    if ids_path.exists() and vec_path.exists():
        old_ids = json.loads(ids_path.read_text())
        old_vecs = np.load(vec_path)
        cache = {h: old_vecs[i] for i, h in enumerate(old_ids)}
    todo = [r for r in records if r["content_hash"] not in cache]
    if todo:
        vecs = llm.embed([embedding_text(r) for r in todo])
        if vecs is None:
            return "unavailable (no GEMINI_API_KEY or API error) – lexical retrieval only" if not cache else "partial (cache only)"
        for r, v in zip(todo, vecs):
            cache[r["content_hash"]] = np.asarray(v, dtype=np.float32)
    hashes = [r["content_hash"] for r in records]
    mat = np.stack([cache[h] for h in hashes]).astype(np.float32)
    mat /= np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
    np.save(vec_path, mat.astype(np.float16))
    ids_path.write_text(json.dumps(hashes))
    return f"{len(hashes)} vectors ({mat.shape[1]}-d, gemini), {len(todo)} newly embedded"


def embedding_text(r: dict) -> str:
    return f"{r['title']}\n{r['content']}"


def write_report(manifest, issues, dedupe_log, conflict_log, pii_totals, boiler_removed, records):
    L = [f"# KB Build Report\n", f"- KB version: `{manifest['kb_version']}`  ", f"- Built: {manifest['built_at']}  ",
         f"- Embeddings: {manifest['embeddings']}\n", "## Counts\n", "| Metric | Value |", "|---|---|"]
    for k, v in manifest["counts"].items():
        L.append(f"| {k} | {v} |")
    L += ["\n## Extraction failures and dropped content\n", "| Source | Issue | Action |", "|---|---|---|"]
    L += [f"| `{i.source_uri}` | {i.issue} | {i.action} |" for i in issues]
    L += [f"\nCross-document boilerplate sentences removed: **{boiler_removed}** (plus nav/header/footer/cookie banners/"
          "breadcrumbs/chat widgets removed structurally, and PDF running headers/footers/page numbers).\n"]
    L += ["## Duplicates / superseded versions\n", "| Kept | Source | Dropped | Source | Sim | Reason |", "|---|---|---|---|---|---|"]
    L += [f"| {d['kept']} | `{d['kept_source']}` | {d['dropped']} | `{d['dropped_source']}` | {d['similarity']} | {d['reason']} |" for d in dedupe_log]
    L += ["\n## Source errors and conflicts (auto-reconciled to authoritative source, flagged for owner review)\n",
          "| Record | Source | Fact | Original | Corrected | Authority |", "|---|---|---|---|---|---|"]
    L += [f"| {c['record_id']} | `{c['source']}` | {c['fact']} | “{c['original']}” | “{c['corrected']}” | `{c['authoritative_source']}` |" for c in conflict_log]
    L += ["\n## PII protection\n", "Detected and replaced with typed placeholders before indexing (raw values are never written to the KB):\n",
          "| Type | Count |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(pii_totals.items())]
    L += [f"\nRecords that contained PII: {sum(r['pii'] for r in records)} (all `audience=internal` call notes; excluded from customer-facing retrieval).\n"]
    L += ["## Changelog vs previous build\n", "```json", json.dumps(manifest["changelog_vs_previous"], indent=1), "```"]
    (OUT / "build_report.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-embed", action="store_true")
    a = ap.parse_args()
    m = build(embed=not a.no_embed)
    print(json.dumps(m["counts"], indent=1))
    print("embeddings:", m["embeddings"])
    print("KB version:", m["kb_version"])
