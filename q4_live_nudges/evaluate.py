"""Run every scenario through the live pipeline at real-time speed and produce:
  results/latency_report.md  – P50/P95 end-to-end and per component (endpointing, ASR, rules, LLM, engine, delivery)
  results/fp_analysis.md     – TP/FP/FN vs labelled expectations, suppression statistics, noisy-call behaviour

python -m q4_live_nudges.evaluate [--asr groq|mock] [--speed 1.0] [--only s1_missed_cross_sell ...]
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import numpy as np
import yaml

from .pipeline import HERE, LivePipeline, load_scenario

EQUIV = {"escalation_request": {"escalation_request", "frustration_rising"}}


def turn_of(utt: dict, timeline: dict) -> int:
    mid = (utt["start_t"] + utt["end_t"]) / 2
    best = min(timeline["turns"], key=lambda t: 0 if t["start"] - 0.3 <= mid <= t["end"] + 0.3 else min(abs(mid - t["start"]), abs(mid - t["end"])))
    return best["turn"]


def score(sc: dict, res: dict, timeline: dict) -> dict:
    utt_turn = {u["uid"]: turn_of(u, timeline) for u in res["transcript"]}
    nudges = [{**n, "turn": utt_turn.get(n["uid"])} for n in res["nudges"]]
    expected = [e for e in sc.get("expected") or [] if not e.get("duplicate_of_previous")]
    matched_n, tp, fn, fp, neutral = set(), [], [], [], []
    for e in expected:
        hit = next((n for n in nudges if n["id"] not in matched_n and n["type"] in EQUIV.get(e["signal"], {e["signal"]})
                    and n["turn"] is not None and e["turn"] <= n["turn"] <= e["turn"] + 2), None)
        if hit:
            matched_n.add(hit["id"])
            (neutral if e.get("optional") else tp).append((e, hit))
        elif not e.get("optional"):
            fn.append(e)
    for n in nudges:
        if n["id"] not in matched_n:
            fp.append(n)
    return {"tp": tp, "fn": fn, "fp": fp, "neutral": neutral, "nudges": nudges}


def pct(xs, q):
    xs = [x for x in xs if x is not None]
    return round(float(np.percentile(xs, q)), 1) if xs else None


async def run_all(ids, asr, speed, use_llm):
    out = {}
    for sid in ids:
        wav, tl = load_scenario(sid)
        print(f"\n=== {sid} ({tl['duration']}s audio, asr={asr}, speed={speed}) ===")
        p = LivePipeline(wav, tl, speed, asr, use_llm)
        res = await p.run()
        (HERE / "results" / "runs").mkdir(parents=True, exist_ok=True)
        (HERE / "results" / "runs" / f"{sid}__{p.asr.name}{'' if p.use_llm else '_nollm'}.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
        out[sid] = (res, tl)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asr", default="groq", choices=["groq", "mock"])
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    scen = {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted((HERE / "scenarios").glob("*.yaml"))}
    ids = [s for s in scen if not a.only or s in a.only]
    runs = asyncio.run(run_all(ids, a.asr, a.speed, not a.no_llm))

    all_n, rows, totals = [], [], {"tp": 0, "fp": 0, "fn": 0}
    comp = {"asr_ms": [], "audio_to_text_ms": [], "llm_ms": [], "rules_us": []}
    fp_lines = []
    for sid, (res, tl) in runs.items():
        s = score(scen[sid], res, tl)
        totals["tp"] += len(s["tp"])
        totals["fp"] += len(s["fp"])
        totals["fn"] += len(s["fn"])
        all_n += res["nudges"]
        for k in comp:
            comp[k] += res["component_latency"][k]
        st = res["engine_stats"]
        raw = st["signals_in"]
        rows.append(f"| {sid} | {len(res['nudges'])} | {len(s['tp'])} | {len(s['fp'])} | {len(s['fn'])} | {len(s['neutral'])} | {raw} | "
                    f"{st['below_threshold']} | {st['duplicates_merged']} | {st['cooldown_suppressed']} | {st['awaiting_llm_rejected']} | {res['dropped_segments']} |")
        fp_lines.append(f"\n### {sid} – {scen[sid]['title']}\n")
        for e, n in s["tp"]:
            fp_lines.append(f"- ✅ TP `{n['type']}` at turn {n['turn']} ({n['source']} {n['confidence']}) – e2e {n['latency_ms']['e2e']} ms – “{(n['evidence'] or [''])[0]}”")
        for e, n in s["neutral"]:
            fp_lines.append(f"- ➖ optional `{n['type']}` at turn {n['turn']} (acceptable, not counted)")
        for n in s["fp"]:
            fp_lines.append(f"- ❌ FP `{n['type']}` at turn {n['turn']} ({n['source']} {n['confidence']}) – “{(n['evidence'] or [''])[0]}”")
        for e in s["fn"]:
            fp_lines.append(f"- ⚠️ FN expected `{e['signal']}` at turn {e['turn']} – not delivered")
        pc = res["post_call"]
        fp_lines.append(f"- post-call: acted-on {pc['acted_on']}/{pc['total_nudges']}, missed opportunities {len(pc['missed_opportunities'])}, unresolved compliance {len(pc['unresolved_compliance'])}")

    from common import config
    llm_models = config.MODELS["groq"]["signals"] + " → " + config.MODELS["gemini"]["signals"]
    lat = lambda k: [n["latency_ms"][k] for n in all_n]
    asr_name = next(iter(runs.values()))[0]["asr"]
    L = ["# Q4 latency report\n",
         f"Mode: ASR **{asr_name}**{' (MOCK – ground-truth text, ASR latency not real)' if asr_name == 'mock' else ' (Groq whisper-large-v3-turbo, per-utterance requests)'} · "
         f"LLM **{'signal tier: ' + llm_models if not a.no_llm else 'off (rules + call-state only)'}** · replay speed {a.speed}×{' (real-time)' if a.speed == 1.0 else ' (FASTER than real-time — dev only)'} · {len(all_n)} nudges over {len(runs)} calls.\n",
         "Stage definitions: **speech_end** = the last audio chunk of the evidence utterance was received → **endpoint** (VAD decides the turn ended, 500 ms hangover) "
         "→ **asr_done** → **signal_done** (rules: sub-ms; LLM path: after LLM) → **nudge_created** → **delivered** (consumer output: WebSocket send / CLI print).\n",
         "## End-to-end (speech end → nudge delivered)\n", "| Metric | P50 ms | P95 ms | max ms |", "|---|---|---|---|"]
    for k in ("e2e", "endpointing", "asr", "signal", "llm", "engine", "delivery"):
        L.append(f"| {k} | {pct(lat(k), 50)} | {pct(lat(k), 95)} | {pct(lat(k), 100)} |")
    fast = [n["latency_ms"]["e2e"] for n in all_n if n.get("path") == "rules"]
    slow = [n["latency_ms"]["e2e"] for n in all_n if n.get("path") == "llm"]
    L += [f"\nRules fast-path nudges (compliance): n={len(fast)} P50 {pct(fast, 50)} ms · P95 {pct(fast, 95)} ms  ",
          f"LLM-confirmed nudges: n={len(slow)} P50 {pct(slow, 50)} ms · P95 {pct(slow, 95)} ms\n",
          "## Component latency over all utterances\n", "| Component | n | P50 | P95 |", "|---|---|---|---|",
          f"| ASR request (ms) | {len(comp['asr_ms'])} | {pct(comp['asr_ms'], 50)} | {pct(comp['asr_ms'], 95)} |",
          f"| Audio received → text (ms, incl. endpointing) | {len(comp['audio_to_text_ms'])} | {pct(comp['audio_to_text_ms'], 50)} | {pct(comp['audio_to_text_ms'], 95)} |",
          f"| Rule signal extraction (µs) | {len(comp['rules_us'])} | {pct(comp['rules_us'], 50)} | {pct(comp['rules_us'], 95)} |",
          f"| LLM signal extraction (ms) | {len(comp['llm_ms'])} | {pct(comp['llm_ms'], 50)} | {pct(comp['llm_ms'], 95)} |",
          "\n## Per-nudge timings\n", "| Call | Nudge | Type | Path | endpointing | ASR | signal | engine | delivery | **e2e** |", "|---|---|---|---|---|---|---|---|---|---|"]
    for sid, (res, _) in runs.items():
        for n in res["nudges"]:
            l = n["latency_ms"]
            L.append(f"| {sid} | {n['id']} | {n['type']} | {n.get('path')} | {l['endpointing']} | {l['asr']} | {l['signal']} | {l['engine']} | {l['delivery']} | **{l['e2e']}** |")
    (HERE / "results" / "latency_report.md").write_text("\n".join(L), encoding="utf-8")

    prec = totals["tp"] / max(1, totals["tp"] + totals["fp"])
    rec = totals["tp"] / max(1, totals["tp"] + totals["fn"])
    F = ["# Q4 false-positive analysis\n",
         f"Labelled expectations per scenario (`scenarios/*.yaml`). A nudge matches a label if same type and triggered within the labelled turn +2 turns. "
         f"Labels marked `duplicate_of_previous` must NOT produce a new nudge (repetition = FP).\n",
         f"**Precision {prec:.0%} · Recall {rec:.0%}** (TP {totals['tp']}, FP {totals['fp']}, FN {totals['fn']}).\n",
         "| Call | Nudges | TP | FP | FN | optional | raw signals | below threshold | merged dups | cooldown | LLM-rejected rule hits | dropped ASR segments |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"] + rows + [
         "\n`raw signals` = every rule/state/LLM candidate before controls; the gap between raw signals and nudges is what thresholds, LLM corroboration, "
         "topic grouping, duplicate suppression and cooldowns removed.\n"] + fp_lines
    (HERE / "results" / "fp_analysis.md").write_text("\n".join(F), encoding="utf-8")
    print(f"\nprecision {prec:.0%} recall {rec:.0%}  -> results/latency_report.md, results/fp_analysis.md")


if __name__ == "__main__":
    main()
