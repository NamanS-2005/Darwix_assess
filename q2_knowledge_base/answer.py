"""Grounded answering on top of the retriever (the 'simple retrieval interface' + what the voice agent relies on).

The generator may ONLY use retrieved chunks. If they do not contain the answer it must return NOT_IN_KB, which callers
turn into a safe fallback ("I don't have that information, I can arrange a callback").
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import llm  # noqa: E402

from .retriever import get_kb  # noqa: E402

SYSTEM = """You answer customer-service questions using ONLY the numbered knowledge-base excerpts provided.
Rules:
- If the excerpts do not contain the information needed, reply exactly: NOT_IN_KB
- Never add numbers, fees, dates, products or promises that are not in the excerpts.
- Answer in 1-3 short sentences suitable to be spoken on a phone call, in the same language as the question.
- End with the excerpt numbers you used, like [1] or [1][2]."""


def grounded_answer(question: str, market: str = "in_lender", k: int = 3) -> dict:
    hits, meta = get_kb().search(question, market=market, k=k)
    if not hits:
        return {"answer": None, "status": "not_in_kb", "reason": "retrieval abstained", "citations": [], "retrieval": meta}
    ctx = "\n\n".join(f"[{n}] {h.record['title']}: {h.record['content']}" for n, h in enumerate(hits, 1))
    res = llm.chat([{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"Excerpts:\n{ctx}\n\nQuestion: {question}"}], tier="agent", max_tokens=200)
    text = res.content.strip()
    if "NOT_IN_KB" in text:
        return {"answer": None, "status": "not_in_kb", "reason": "generator: excerpts do not answer", "citations": [h.citation for h in hits],
                "retrieval": meta, "llm_ms": round(res.latency_ms)}
    used = [h.citation for n, h in enumerate(hits, 1) if f"[{n}]" in text] or [hits[0].citation]
    return {"answer": text, "status": "answered", "citations": used, "retrieval": meta, "llm_ms": round(res.latency_ms),
            "model": f"{res.provider}/{res.model}"}


if __name__ == "__main__":
    import json

    q = " ".join(sys.argv[1:]) or "Will a late payment affect my CIBIL score?"
    print(json.dumps(grounded_answer(q), indent=1, ensure_ascii=False))
