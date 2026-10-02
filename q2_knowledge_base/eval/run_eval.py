"""Retrieval + grounded-answer evaluation. Writes eval/results.md and eval/results.json.

python -m q2_knowledge_base.eval.run_eval [--no-answer]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from ..answer import grounded_answer
from ..retriever import analyze, get_kb

HERE = Path(__file__).resolve().parent


def is_gold(hit_record: dict, gold: list[list[str]]) -> bool:
    for uri, sec in gold:
        if hit_record["source"]["uri"] == uri and sec.lower() in (hit_record["source"]["section"] + " " + hit_record["title"]).lower():
            return True
    return False


def explain(q: str, rec: dict) -> str:
    q_terms = set(analyze(q))
    d_terms = set(analyze(rec["title"] + " " + rec["content"]))
    overlap = sorted(q_terms & d_terms)
    return f"matched terms: {', '.join(overlap) or '(none – semantic match only)'}; category={rec['category']}, topics={', '.join(rec['topics'][:3]) or '-'}"


def main(with_answer: bool):
    from common import llm

    kb = get_kb()
    cases = yaml.safe_load((HERE / "queries.yaml").read_text(encoding="utf-8"))
    rows, tally = [], {"correct": 0, "partially correct": 0, "incorrect": 0}
    for c in cases:
        market = c.get("market", "in_lender")
        hits, meta = kb.search(c["question"], market=market, k=3)
        if c.get("expect_abstain"):
            ans = grounded_answer(c["question"], market) if (with_answer and llm.has_llm() and hits) else None
            refused = not hits or (ans and ans["status"] == "not_in_kb")
            verdict = "correct" if refused else "incorrect"
            why = ("retrieval abstained (no confident match)" if not hits else
                   "retrieval returned near-misses; generator returned NOT_IN_KB" if refused else "system answered an out-of-scope question")
        else:
            ranks = [n for n, h in enumerate(hits) if is_gold(h.record, c["gold"])]
            verdict = "correct" if ranks and ranks[0] == 0 else ("partially correct" if ranks else "incorrect")
            why = explain(c["question"], hits[0].record) if hits else "retrieval abstained"
            ans = grounded_answer(c["question"], market) if (with_answer and llm.has_llm()) else None
        tally[verdict] += 1
        rows.append({
            "id": c["id"], "type": c["type"], "market": market, "question": c["question"],
            "top_hits": [h.to_dict() for h in hits], "retrieval_meta": meta, "verdict": verdict, "relevance": why,
            "answer": ans,
        })
        print(f"{c['id']} {verdict:18s} {c['question'][:60]:60s} -> {hits[0].citation if hits else 'ABSTAIN'}")

    (HERE / "results.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    md = [f"# Retrieval evaluation\n", f"KB version `{kb.kb_version}` · retrieval mode: **{rows[0]['retrieval_meta'].get('mode', 'lexical')}** · "
          f"{len(rows)} queries · correct {tally['correct']} · partially correct {tally['partially correct']} · incorrect {tally['incorrect']}\n",
          "| # | Type | Question | Retrieved record (top-1) | Source reference | Relevance explanation | Verdict |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        h = r["top_hits"][0] if r["top_hits"] else None
        rec = f"`{h['record_id']}` – {h['title']}" if h else "— (abstained)"
        src = f"`{h['source']}` § {h['section']} (v{h['version']})" if h else "—"
        md.append(f"| {r['id']} | {r['type']} | {r['question']} | {rec} | {src} | {r['relevance']} | **{r['verdict']}** |")
    if any(r["answer"] for r in rows):
        md += ["\n## Grounded answers (what the voice agent would say)\n"]
        for r in rows:
            a = r["answer"]
            if not a:
                continue
            body = a["answer"] if a["status"] == "answered" else f"_NOT_IN_KB → fallback: “I don’t have that information; I can arrange a callback.”_ ({a['reason']})"
            md.append(f"**{r['id']}. {r['question']}**  \n{body}  \nCitations: {' '.join(a['citations']) or '—'}\n")
    md += ["\n## Retrieved chunks (top-3) per query\n"]
    for r in rows:
        md.append(f"<details><summary>{r['id']} – {r['question']}</summary>\n")
        for h in r["top_hits"]:
            md.append(f"- {h['citation']} score={h['score']} bm25={h['bm25']} dense={h['dense']} coverage={h['coverage']}  \n  > {h['content'][:300]}")
        md.append("\n</details>\n")
    (HERE / "results.md").write_text("\n".join(md), encoding="utf-8")
    print(tally)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-answer", action="store_true")
    main(not ap.parse_args().no_answer)
