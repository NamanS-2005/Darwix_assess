"""Darwix assessment portal: one website for Q1–Q4.

Combines the live APIs of the voice-agent server (Q1/Q3 web calls, KB search) and the live-nudge server (Q4 WebSocket
replay) with read-only APIs over every saved result (test calls, retrieval eval, ASR benchmark, latency reports).

Run:  uvicorn portal.server:app --port 8000   ->  http://localhost:8000
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import llm  # noqa: E402
from q1_voice_agent import server as q1  # noqa: E402
from q4_live_nudges import server as q4  # noqa: E402

HERE = Path(__file__).resolve().parent
app = FastAPI(title="Darwix AI assessment portal")

# Re-use the live endpoints of both existing apps (everything except their own HTML pages).
for src in (q1.app, q4.app):
    for route in src.router.routes:
        if getattr(route, "path", "") in ("/", "/kb", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"):
            continue
        app.router.routes.append(route)

app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

SIM_DIRS = {"q1": ROOT / "q1_voice_agent" / "results" / "simulated",
            "ph": ROOT / "q3_multilingual" / "results" / "ph",
            "id": ROOT / "q3_multilingual" / "results" / "id"}
DOCS = {  # whitelisted markdown documents shown in the portal
    "readme": "README.md", "architecture": "docs/ARCHITECTURE.md", "limitations": "docs/LIMITATIONS_AND_PRODUCTION_PLAN.md",
    "video": "docs/VIDEO_WALKTHROUGH.md", "q1-results": "q1_voice_agent/results/README.md",
    "q1-script": "q1_voice_agent/market/call_script.md", "q1-rules": "q1_voice_agent/market/business_rules.yaml",
    "kb-build": "q2_knowledge_base/output/build_report.md", "kb-eval": "q2_knowledge_base/eval/results.md",
    "q3-readme": "q3_multilingual/README.md", "q3-findings": "q3_multilingual/FINDINGS.md",
    "asr-report": "q3_multilingual/asr_eval/results/asr_report.md", "q4-readme": "q4_live_nudges/README.md",
    "q4-latency": "q4_live_nudges/results/latency_report.md", "q4-fp": "q4_live_nudges/results/fp_analysis.md",
    "q4-latency-rules": "q4_live_nudges/results/latency_report_rules_only.md", "q4-fp-rules": "q4_live_nudges/results/fp_analysis_rules_only.md",
}


def _json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _pct(xs, q):
    xs = [x for x in xs if x is not None]
    return round(float(np.percentile(xs, q)), 1) if xs else None


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(HERE / "static" / "index.html")


@app.get("/api/doc/{key}", response_class=PlainTextResponse)
def doc(key: str):
    if key not in DOCS:
        raise HTTPException(404)
    p = ROOT / DOCS[key]
    if not p.exists():
        raise HTTPException(404, "not generated yet")
    text = p.read_text(encoding="utf-8")
    return f"```yaml\n{text}\n```" if p.suffix == ".yaml" else text


@app.get("/api/status")
def status():
    from common import config
    kb = q1.get_kb()
    return {"providers": llm.available_providers(), "asr": bool(config.GROQ_API_KEY), "kb_version": kb.kb_version,
            "retrieval": "hybrid" if kb.dense_enabled else "lexical", "vapi": bool(config.VAPI_API_KEY)}


@app.get("/api/overview")
def overview():
    out = {}
    for k, d in SIM_DIRS.items():
        rs = _json(d / "summary.json", []) or []
        out[f"sims_{k}"] = {"passed": sum(r["passed"] for r in rs), "total": len(rs)}
    man = _json(ROOT / "q2_knowledge_base" / "output" / "manifest.json", {}) or {}
    out["kb"] = man.get("counts", {})
    ev = _json(ROOT / "q2_knowledge_base" / "eval" / "results.json", []) or []
    out["kb_eval"] = {v: sum(r["verdict"] == v for r in ev) for v in ("correct", "partially correct", "incorrect")}
    q4r = q4_results("llm")
    out["q4"] = {k: q4r[k] for k in ("precision", "recall", "e2e_p50", "e2e_p95", "nudges")}
    asr = asr_summary()
    out["asr"] = {m: min(v["configs"], key=lambda c: c["wer_norm"]) for m, v in asr.items()} if asr else {}
    return out


@app.get("/api/test-customers")
def test_customers():
    """Fictional mock-CRM identities, shown in the portal so testers know what to say for verification."""
    data = _json(ROOT / "q1_voice_agent" / "crm" / "customers.json", {}) or {}
    return {m: [{"id": c["customer_id"], "name": c["name"], "dob": c["dob"], "last4": c["loan_account"][-4:],
                 "product": c["product"], "hint": c.get("scenario_hint", "")} for c in v]
            for m, v in data.items() if not m.startswith("_")}


# ---------------------------------------------------------------- Q2
@app.get("/api/kb/records")
def kb_records(market: str = "", category: str = "", status: str = "", q: str = "", limit: int = 300):
    kb = q1.get_kb()
    ql = q.lower()
    rows = []
    for r in kb.records:
        if market and r["market"] != market or category and r["category"] != category or status and r["status"] != status:
            continue
        if ql and ql not in (r["title"] + " " + r["content"] + " " + r["record_id"]).lower():
            continue
        rows.append(r)
    return {"total": len(rows), "records": rows[:limit],
            "facets": {"market": sorted({r["market"] for r in kb.records}), "category": sorted({r["category"] for r in kb.records})}}


@app.get("/api/kb/eval")
def kb_eval():
    ev = _json(ROOT / "q2_knowledge_base" / "eval" / "results.json", []) or []
    return [{"id": r["id"], "type": r["type"], "market": r["market"], "question": r["question"], "verdict": r["verdict"],
             "relevance": r["relevance"], "top": (r["top_hits"] or [None])[0], "answer": r.get("answer"), "meta": r["retrieval_meta"]} for r in ev]


@app.get("/api/kb/manifest")
def kb_manifest():
    m = _json(ROOT / "q2_knowledge_base" / "output" / "manifest.json", {}) or {}
    m.pop("records", None)
    return m


# ---------------------------------------------------------------- simulated calls (Q1, Q3)
@app.get("/api/sims/{suite}")
def sims(suite: str):
    if suite not in SIM_DIRS:
        raise HTTPException(404)
    rows = _json(SIM_DIRS[suite] / "summary.json", []) or []
    for r in rows:
        d = SIM_DIRS[suite] / r["id"]
        r["has_audio"] = (d / "recording.mp3").exists()
    return sorted(rows, key=lambda r: r["id"])


@app.get("/files/sims/{suite}/{sid}/{name}")
def sim_file(suite: str, sid: str, name: str):
    if suite not in SIM_DIRS or name not in ("transcript.md", "recording.mp3", "call.json"):
        raise HTTPException(404)
    p = (SIM_DIRS[suite] / sid / name).resolve()
    if SIM_DIRS[suite].resolve() not in p.parents or not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="text/plain; charset=utf-8" if name.endswith(".md") else None)


# ---------------------------------------------------------------- Q3 ASR benchmark
@app.get("/api/asr")
def asr_summary():
    rows = _json(ROOT / "q3_multilingual" / "asr_eval" / "results" / "asr_results.json", []) or []
    out: dict = {}
    by = defaultdict(list)
    for r in rows:
        by[(r["market"], r["config"])].append(r)
    for (market, cfg), rs in by.items():
        m = out.setdefault(market, {"configs": [], "voices": [], "categories": []})
        m["configs"].append({"config": cfg, "n": len(rs), "wer": round(float(np.mean([r["wer"] for r in rs])) * 100, 1),
                             "wer_norm": round(float(np.mean([r.get("wer_norm", r["wer"]) for r in rs])) * 100, 1),
                             "term_recall": round(float(np.mean([r["term_recall"] for r in rs if r["term_recall"] is not None])) * 100),
                             "latency_ms": _pct([r["latency_ms"] for r in rs if r["latency_ms"]], 50),
                             "translated": sum(r["translated"] for r in rs)})
    for market, m in out.items():
        best = min(m["configs"], key=lambda c: c["wer_norm"])["config"]
        ref = next(iter(dict.fromkeys(r["config"] for r in rows if r["market"] == market)))
        m["reference_config"] = ref
        m["best_config"] = best
        clean = [r for r in rows if r["market"] == market and r["config"] == ref and r["condition"] == "clean"]
        for key, target in (("voice", "voices"), ("cat", "categories")):
            g = defaultdict(list)
            for r in clean:
                g[r[key]].append(r)
            m[target] = sorted(({"name": k, "n": len(v), "wer_norm": round(float(np.mean([x.get("wer_norm", x["wer"]) for x in v])) * 100, 1)}
                                for k, v in g.items()), key=lambda x: x["wer_norm"])
        m["examples"] = sorted(clean, key=lambda r: -r.get("wer_norm", r["wer"]))[:6]
    return out


# ---------------------------------------------------------------- Q4 results
@app.get("/api/q4/results")
def q4_results(mode: str = "llm"):
    import yaml
    from q4_live_nudges.evaluate import score
    suffix = "__groq.json" if mode == "llm" else "__groq_nollm.json"
    runs = []
    tp = fp = fn = 0
    lat = defaultdict(list)
    for p in sorted((ROOT / "q4_live_nudges" / "scenarios").glob("*.yaml")):
        sc = yaml.safe_load(p.read_text(encoding="utf-8"))
        res = _json(ROOT / "q4_live_nudges" / "results" / "runs" / f"{sc['id']}{suffix}")
        tl = _json(ROOT / "q4_live_nudges" / "audio" / f"{sc['id']}.timeline.json")
        if not res or not tl:
            continue
        s = score(sc, res, tl)
        tp, fp, fn = tp + len(s["tp"]), fp + len(s["fp"]), fn + len(s["fn"])
        fp_ids = {n["id"] for n in s["fp"]}
        nudges = []
        for n in s["nudges"]:
            for k, v in n["latency_ms"].items():
                lat[k].append(v)
            nudges.append({**n, "verdict": "FP" if n["id"] in fp_ids else ("optional" if any(n["id"] == h["id"] for _, h in s["neutral"]) else "TP")})
        runs.append({"id": sc["id"], "title": sc["title"], "description": sc.get("description", ""), "nudges": nudges,
                     "missed": [e["signal"] for e in s["fn"]], "stats": res["engine_stats"], "post_call": res["post_call"],
                     "utterances": res["utterances"]})
    comp = {k: {"p50": _pct(v, 50), "p95": _pct(v, 95)} for k, v in lat.items()}
    return {"mode": mode, "runs": runs, "precision": round(tp / max(1, tp + fp) * 100), "recall": round(tp / max(1, tp + fn) * 100),
            "tp": tp, "fp": fp, "fn": fn, "nudges": sum(len(r["nudges"]) for r in runs),
            "e2e_p50": comp.get("e2e", {}).get("p50"), "e2e_p95": comp.get("e2e", {}).get("p95"), "components": comp}
