"""Automated test calls (Q1 + Q3): an LLM plays the customer from a scenario persona, the real engine plays the agent.

With --asr-loop (default when GROQ key present) every customer line is synthesised with a neural voice and transcribed
by Whisper before reaching the agent, so ASR errors are part of the test – exactly what a live call would see.

Outputs per scenario in <results_dir>/<scenario_id>/: transcript.md, call.json, recording.mp3, recording_stereo.wav
and a summary.md with pass/fail checks.

python -m q1_voice_agent.simulate_calls --scenarios q1_voice_agent/tests/scenarios.yaml --out q1_voice_agent/results/simulated
"""
from __future__ import annotations

import argparse
import os
import json
import re
import sys
import time
from pathlib import Path

import jiwer
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import audio, llm  # noqa: E402
from q1_voice_agent.engine.agent import CallSession  # noqa: E402

CUSTOMER_SYS = """You are role-playing a CUSTOMER receiving a phone call. Stay in character.
{persona}
How to play:
- Say ONLY your next line in reply to the agent's LATEST message (1-2 short spoken sentences). Do not jump ahead:
  pursue your goals one at a time across turns, only when they fit what the agent just said.
- Answer what the agent asked. No stage directions, no narration.
- Only when the agent has clearly closed the call (said goodbye) reply with exactly: [HANGUP]"""


def customer_reply(persona: str, transcript: list[dict]) -> str:
    msgs = [{"role": "system", "content": CUSTOMER_SYS.format(persona=persona)}]
    for t in transcript:
        if t["role"] == "agent":
            msgs.append({"role": "user", "content": t["text"]})
        elif t["role"] == "customer":
            msgs.append({"role": "assistant", "content": t.get("intended", t["text"])})
    for attempt in range(3):   # reasoning models occasionally spend the whole budget thinking -> empty reply
        res = llm.chat(msgs, tier="sim", temperature=0.7, max_tokens=300, reasoning="medium",
                       providers=["gemini", "gemini2", "groq", "groq2", "openrouter"])   # keep Groq quota for the agent under test
        text = res.content.strip().strip('"')
        if text and text != "[HANGUP]" and "[HANGUP]" in text:
            text = text.replace("[HANGUP]", "").strip()   # spoke a line AND hung up -> keep the line
        if text:
            return text
    return "[HANGUP]"


def norm_for_wer(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s']", " ", s)
    return " ".join(s.split())


def run_scenario(sc: dict, out_dir: Path, asr_loop: bool) -> dict:
    s = CallSession(sc["market"], sc.get("customer_id"), channel="simulated")
    m = s.market
    segs: list[tuple[str, np.ndarray]] = []
    asr_pairs, lat = [], {"asr_ms": [], "agent_ms": [], "tts_ms": []}

    def tts(role: str, text: str):
        voice = m.cfg["tts"]["voice"] if role == "agent" else sc.get("customer_voice", m.cfg["tts"]["customer_voice"])
        mp3, ms = audio.tts_mp3(text, voice, sc.get("customer_rate", "+0%") if role == "customer" else m.cfg["tts"].get("rate", "+0%"))
        if role == "agent":
            lat["tts_ms"].append(round(ms))
        pcm = audio.decode_to_pcm(mp3)
        segs.append((role, pcm))
        return mp3, pcm

    opening = s.opening()
    tts("agent", opening["text"])
    for _ in range(sc.get("max_turns", 12)):
        said = customer_reply(sc["persona"], s.transcript)
        if "[HANGUP]" in said:
            break
        heard, asr_meta = said, None
        mp3, pcm = tts("customer", said)
        if asr_loop:
            wav = audio.pcm_to_wav_bytes(pcm)
            heard, ms = llm.transcribe(wav, "turn.wav", language=m.cfg["asr"].get("language"), prompt=m.cfg["asr"].get("prompt"),
                                       model=os.getenv("SIM_ASR_MODEL") or m.cfg["asr"].get("model"))
            lat["asr_ms"].append(round(ms))
            asr_pairs.append((said, heard))
            asr_meta = {"intended": said, "ms": round(ms)}
        turn = s.respond(heard, asr_meta)
        s.transcript[-2]["intended"] = said  # customer turn: keep what the persona meant to say
        lat["agent_ms"].append(turn.get("agent_ms"))
        tts("agent", turn["text"])
        if s.state["ended"]:
            break
    if not s.crm_summary:
        from q1_voice_agent.engine.tools import end_call
        end_call(s, s.state["disposition"] or "INCOMPLETE", "Simulation stopped (max turns or customer hung up).", force=True)

    d = out_dir / sc["id"]
    d.mkdir(parents=True, exist_ok=True)
    exp = s.export()
    exp["scenario"] = {k: v for k, v in sc.items() if k != "persona"}
    exp["latency"] = lat
    if asr_pairs:
        refs = [norm_for_wer(a) for a, _ in asr_pairs]
        hyps = [norm_for_wer(b) for _, b in asr_pairs]
        exp["asr_wer"] = round(jiwer.wer(refs, hyps), 3)
        exp["asr_pairs"] = [{"intended": a, "asr": b} for a, b in asr_pairs]
    (d / "call.json").write_text(json.dumps(exp, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    md = s.transcript_markdown()
    if asr_pairs:
        md += f"\n\n## ASR in the loop (customer voice `{sc.get('customer_voice', m.cfg['tts']['customer_voice'])}`) – WER {exp['asr_wer']:.1%}\n"
        md += "\n".join(f"- said: “{a}”  \n  heard: “{b}”" for a, b in asr_pairs)
    (d / "transcript.md").write_text(md, encoding="utf-8")
    gap = audio.silence(0.35)
    mono = np.concatenate([np.concatenate([p, gap]) for _, p in segs])
    audio.write_wav(d / "recording.wav", mono)
    audio.wav_to_mp3(d / "recording.wav", d / "recording.mp3")
    (d / "recording.wav").unlink()
    L, R = [], []
    for role, p in segs:
        z = np.zeros_like(p)
        L += [p if role == "agent" else z, gap]
        R += [p if role == "customer" else z, gap]
    audio.write_wav(d / "recording_stereo.wav", np.stack([np.concatenate(L), np.concatenate(R)], axis=1))
    return evaluate(sc, s, exp)


def evaluate(sc: dict, s: CallSession, exp: dict) -> dict:
    e = sc.get("expect", {})
    checks = []
    agent_text = " ".join(t["text"] for t in s.transcript if t["role"] == "agent")
    tools = [ev["tool"] for t in s.transcript if t["role"] == "agent" for ev in t.get("tools", []) if ev.get("tool")]
    if "disposition_in" in e:
        checks.append(("disposition", s.state["disposition"] in e["disposition_in"], f"{s.state['disposition']} ∈ {e['disposition_in']}"))
    if "verified" in e:
        checks.append(("verified", s.state["verified"] == e["verified"], f"verified={s.state['verified']}"))
    for t in e.get("tools_called", []):
        checks.append((f"tool:{t}", t in tools, "called" if t in tools else "NOT called"))
    for t in e.get("tools_not_called", []):
        checks.append((f"no-tool:{t}", t not in tools, "not called" if t not in tools else "CALLED"))
    for pat in e.get("agent_says_any", []):
        ok = re.search(pat, agent_text, re.I) is not None
        checks.append((f"says /{pat}/", ok, "found" if ok else "missing"))
    for pat in e.get("agent_never_says", []):
        ok = re.search(pat, agent_text, re.I) is None
        checks.append((f"never /{pat}/", ok, "absent" if ok else "PRESENT"))
    if e.get("kb_used"):
        ok = any(not k["abstained"] for k in s.kb_log)
        checks.append(("grounded KB answer", ok, f"{len(s.kb_log)} lookups"))
    if e.get("unavailable_fallback"):
        ok = any(k["abstained"] for k in s.kb_log) or re.search(e.get("unavailable_regex", r"don't have that information|outside what I can help"), agent_text, re.I) is not None
        checks.append(("safe fallback for unsupported question", ok, "fallback given" if ok else "NO fallback"))
    if e.get("escalated"):
        ok = any(t["type"] == "escalation" for t in s.state["tickets"])
        checks.append(("escalation ticket", ok, ",".join(t["id"] for t in s.state["tickets"]) or "none"))
    if e.get("language_judge"):
        ok, note = language_judge(s, e["language_judge"])
        checks.append(("language/register consistency", ok, note))
    passed = all(c[1] for c in checks)
    return {"id": sc["id"], "title": sc.get("title", sc["id"]), "market": sc["market"], "passed": passed, "checks": checks,
            "disposition": s.state["disposition"], "turns": sum(t["role"] == "customer" for t in s.transcript),
            "guard": len(s.guard_log), "kb_lookups": len(s.kb_log), "asr_wer": exp.get("asr_wer"),
            "providers": s.metrics.get("providers"),
            "agent_ms_p50": float(np.median([x for x in exp["latency"]["agent_ms"] if x])) if exp["latency"]["agent_ms"] else None}


def language_judge(s: CallSession, spec: str) -> tuple[bool, str]:
    convo = "\n".join(f"{t['role'].upper()}: {t['text']}" for t in s.transcript if t["role"] in ("agent", "customer"))
    q = (f"Evaluate the AGENT turns only. Expected language/register: {spec}\n"
         "Return JSON {\"consistent\": true/false, \"unexpected_switches\": [quotes], \"note\": \"one sentence\"}.\n"
         "Natural code-switching that mirrors the customer (e.g. Taglish, finance loanwords like 'premium', 'DP', 'tenor') is NOT a violation. "
         "A violation is the agent switching to a full English sentence when the customer speaks Filipino/Indonesian, or switching register abruptly.\n\n" + convo)
    out, _ = llm.chat_json([{"role": "user", "content": q}], tier="sim", max_tokens=300, providers=["gemini", "gemini2", "groq", "groq2", "openrouter"])
    return bool(out.get("consistent")), (out.get("note") or "") + (f" switches={out.get('unexpected_switches')}" if out.get("unexpected_switches") else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=str(ROOT / "q1_voice_agent" / "tests" / "scenarios.yaml"))
    ap.add_argument("--out", default=str(ROOT / "q1_voice_agent" / "results" / "simulated"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--no-asr-loop", action="store_true")
    a = ap.parse_args()
    llm.RATE_LIMIT_WAIT_S = 600.0   # offline test: wait for free-tier quota rather than fail the scenario
    if not llm.has_llm():
        sys.exit("No LLM configured: add GROQ_API_KEY and/or GEMINI_API_KEY to .env")
    scenarios = yaml.safe_load(Path(a.scenarios).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for sc in scenarios:
        if a.only and sc["id"] not in a.only:
            continue
        t0 = time.time()
        r = run_scenario(sc, out, asr_loop=not a.no_asr_loop and bool(llm.config.GROQ_API_KEY))
        results.append(r)
        print(f"{'PASS' if r['passed'] else 'FAIL'}  {r['id']:32s} disp={r['disposition']} turns={r['turns']} wer={r['asr_wer']} ({time.time() - t0:.0f}s)")
        for name, ok, note in r["checks"]:
            if not ok:
                print(f"      ✗ {name}: {note}")
    prev = {}
    sp = out / "summary.json"
    if sp.exists():
        prev = {r["id"]: r for r in json.loads(sp.read_text(encoding="utf-8"))}
    prev.update({r["id"]: r for r in results})
    allr = sorted(prev.values(), key=lambda r: r["id"])
    sp.write_text(json.dumps(allr, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    write_summary(out, allr)


def write_summary(out: Path, allr: list[dict]) -> None:
    L = ["# Simulated test calls\n", f"{sum(r['passed'] for r in allr)}/{len(allr)} scenarios passed. Customer turns are TTS → Whisper ASR → agent (ASR-in-the-loop).\n",
         "Agent latency here includes free-tier rate-limit waits (the harness waits for quota instead of failing) – not production turn latency.\n",
         "| Scenario | Market | Result | Disposition | Turns | KB lookups | Guard | ASR WER | Models used | Recording |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in allr:
        models = ", ".join(sorted({k.split("/", 1)[1] for k in (r.get("providers") or {})}))
        L.append(f"| [{r['title']}]({r['id']}/transcript.md) | {r['market']} | {'✅ pass' if r['passed'] else '❌ fail'} | {r['disposition']} | {r['turns']} | "
                 f"{r['kb_lookups']} | {r['guard']} | {'' if r['asr_wer'] is None else f'{r['asr_wer']:.1%}'} | {models} | [mp3]({r['id']}/recording.mp3) |")
    L.append("\n## Checks\n")
    for r in allr:
        L.append(f"**{r['title']}**")
        L += [f"- {'✅' if ok else '❌'} {name} — {note}" for name, ok, note in r["checks"]]
        L.append("")
    (out / "summary.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
