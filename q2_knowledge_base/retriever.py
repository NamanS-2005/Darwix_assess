"""Hybrid retriever over the built KB.

Pipeline:  metadata filter (market, audience, status=active)
        -> lexical BM25 (with synonym expansion)  +  dense cosine (Gemini embeddings, if available)
        -> Reciprocal Rank Fusion
        -> small, explainable boosts (authority, category hint)
        -> abstention gate (no confident match -> return nothing, the agent must say "I don't have that information")
Every hit carries a citation string the agent can speak/log:  [record_id | source#section | v<version>]
"""
from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import llm  # noqa: E402

from .taxonomy import STOPWORDS, SYNONYMS  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[\w₹%]+", text.lower()) if t not in STOPWORDS]


def light_stem(tok: str) -> str:
    """Tiny, language-agnostic stemmer: English plural/verb endings + Indonesian enclitics (-nya, -lah, -kah)."""
    if len(tok) > 5 and tok.endswith(("nya", "lah", "kah")):
        return tok[:-3]
    if len(tok) > 4:
        if tok.endswith("ing"):
            return tok[:-3]
        if tok.endswith(("ses", "xes", "ches", "shes")):
            return tok[:-2]
        if tok.endswith("ed"):
            return tok[:-2]
        if tok.endswith("s") and not tok.endswith("ss"):
            return tok[:-1]
    return tok


def analyze(text: str) -> list[str]:
    return [light_stem(t) for t in tokenize(text)]


def expand_query(q: str) -> str:
    extra = []
    ql = q.lower()
    for k, syns in SYNONYMS.items():
        if re.search(rf"\b{re.escape(k)}\b", ql):
            extra += syns
    return q + " " + " ".join(extra)


@dataclass
class Hit:
    record: dict
    score: float
    bm25: float
    dense: float | None
    coverage: float
    rank_lex: int | None
    rank_dense: int | None

    @property
    def citation(self) -> str:
        r = self.record
        sec = r["source"]["section"]
        loc = f"p.{r['source']['page']}" if r["source"].get("page") else (f"row {r['source']['row']}" if r["source"].get("row") else f"§{sec}")
        return f"[{r['record_id']} | {r['source']['uri']} {loc} | v{r['version']}]"

    def to_dict(self) -> dict:
        r = self.record
        return {"record_id": r["record_id"], "title": r["title"], "content": r["content"], "category": r["category"],
                "source": r["source"]["uri"], "section": r["source"]["section"], "version": r["version"],
                "citation": self.citation, "score": round(self.score, 4), "bm25": round(self.bm25, 3),
                "dense": None if self.dense is None else round(self.dense, 3), "coverage": round(self.coverage, 2)}


class KnowledgeBase:
    # Abstention thresholds (calibrated on q2_knowledge_base/eval/queries.yaml, incl. out-of-scope queries)
    MIN_COVERAGE = 0.34       # share of (expanded) query terms found in the record, lexical-only mode
    MIN_DENSE = 0.70          # cosine floor when embeddings are available (in-scope min 0.737, out-of-scope max 0.662 on eval set)
    MIN_DENSE_STRONG = 0.74   # dense alone is enough above this

    def __init__(self, records_path: Path = OUT / "records.jsonl"):
        self.records = [json.loads(l) for l in records_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.kb_version = self.records[0]["kb_version"] if self.records else "empty"
        self.docs_tokens = [analyze(self._index_text(r)) for r in self.records]
        self.bm25 = BM25Okapi(self.docs_tokens, k1=1.3, b=0.6)
        self.vectors = None
        ids_p, vec_p = OUT / "embeddings_ids.json", OUT / "embeddings.npy"
        if ids_p.exists() and vec_p.exists():
            hashes = json.loads(ids_p.read_text())
            vecs = np.load(vec_p).astype(np.float32)
            pos = {h: i for i, h in enumerate(hashes)}
            if all(r["content_hash"] in pos for r in self.records):
                self.vectors = np.stack([vecs[pos[r["content_hash"]]] for r in self.records])
        self.dense_enabled = self.vectors is not None and bool(llm.config.GEMINI_API_KEY)

    def _weighted_coverage(self, q_terms: set[str], doc_terms: set[str]) -> float:
        """IDF-weighted share of query terms present in the doc. Terms unseen in the whole KB get the highest weight,
        so 'gold loan interest rate' does NOT look covered by a two-wheeler interest-rate record."""
        if not q_terms:
            return 0.0
        max_idf = max(self.bm25.idf.values()) if self.bm25.idf else 1.0
        w = {t: max(self.bm25.idf.get(t, max_idf), 0.1) for t in q_terms}
        return sum(w[t] for t in q_terms if t in doc_terms) / sum(w.values())

    @staticmethod
    def _index_text(r: dict) -> str:
        return " ".join([r["title"], r["title"], r["content"], " ".join(r["topics"]).replace("/", " ").replace("_", " "),
                         " ".join(r["products"]).replace("_", " "), r["category"]])

    def search(self, query: str, market: str = "in_lender", k: int = 3, audiences=("customer", "agent"),
               category: str | None = None, include_superseded: bool = False) -> tuple[list[Hit], dict]:
        t0 = time.perf_counter()
        allowed = [i for i, r in enumerate(self.records)
                   if r["market"] == market and r["audience"] in audiences and (include_superseded or r["status"] == "active")]
        if not allowed:
            return [], {"latency_ms": 0, "abstained": True, "reason": "no records for filter"}
        q_exp = expand_query(query)
        q_tok = analyze(q_exp)
        q_core = {t for t in analyze(query) if not t.isdigit()}
        lex_all = self.bm25.get_scores(q_tok)
        lex = {i: lex_all[i] for i in allowed}
        lex_rank = {i: n for n, i in enumerate(sorted(allowed, key=lambda i: -lex[i]))}

        dense, dense_rank = {}, {}
        if self.dense_enabled:
            qv = llm.embed([query], task="RETRIEVAL_QUERY")
            if qv:
                v = np.asarray(qv[0], dtype=np.float32)
                v /= np.linalg.norm(v) + 1e-9
                sims = self.vectors @ v
                dense = {i: float(sims[i]) for i in allowed}
                dense_rank = {i: n for n, i in enumerate(sorted(allowed, key=lambda i: -dense[i]))}

        hits = []
        for i in allowed:
            r = self.records[i]
            rrf = 1 / (60 + lex_rank[i]) + (1 / (60 + dense_rank[i]) if dense_rank else 0)
            boost = 1 + (r["authority"] - 50) / 20000  # tie-break only: never outweighs one rank of relevance
            if category and r["category"] == category:
                boost += 0.05
            coverage = self._weighted_coverage(q_core, set(self.docs_tokens[i]))
            hits.append(Hit(r, rrf * boost, float(lex[i]), dense.get(i), coverage, lex_rank[i], dense_rank.get(i)))
        hits.sort(key=lambda h: -h.score)

        top = hits[0]
        head = hits[:k]
        best_cov = max(h.coverage for h in head)
        if dense:
            best_dense = max(h.dense or 0 for h in head)
            confident = best_dense >= self.MIN_DENSE_STRONG or (best_dense >= self.MIN_DENSE and best_cov >= 0.3)
        else:
            confident = any(h.coverage >= self.MIN_COVERAGE and h.bm25 > 1.0 for h in head)
        meta = {"latency_ms": round((time.perf_counter() - t0) * 1000, 1), "mode": "hybrid" if dense else "lexical",
                "abstained": not confident, "kb_version": self.kb_version,
                "top_dense": top.dense, "top_coverage": round(top.coverage, 2), "top_bm25": round(top.bm25, 2)}
        if not confident:
            return [], meta
        return hits[:k], meta


_kb: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Query the KB from the command line")
    ap.add_argument("query")
    ap.add_argument("--market", default="in_lender")
    ap.add_argument("-k", type=int, default=3)
    a = ap.parse_args()
    hits, meta = get_kb().search(a.query, a.market, a.k)
    print(json.dumps(meta, indent=1))
    for h in hits:
        print(f"\n{h.citation}  score={h.score:.4f} bm25={h.bm25:.2f} dense={h.dense} cov={h.coverage:.2f}\n  {h.record['title']}: {h.record['content'][:250]}")
