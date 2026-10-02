"""Real-time pipeline: audio chunks -> VAD -> streaming ASR -> signals (rules + LLM) -> nudge engine -> delivery.

Every utterance and nudge carries wall-clock timestamps for each stage, so latency is measured, not estimated:
  speech_end (last audio of the evidence received) -> endpoint (VAD hangover) -> asr_done -> signal_done -> nudge_created -> delivered

CLI:  python -m q4_live_nudges.pipeline --scenario s1_missed_cross_sell [--asr groq|mock] [--no-llm] [--speed 1.0]
      python -m q4_live_nudges.pipeline --wav q1_voice_agent/results/simulated/q1_02_objection_salary_waiver/recording_stereo.wav
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import config, llm  # noqa: E402

from .nudges import Nudge, NudgeEngine  # noqa: E402
from .signals import CallState, Utterance, llm_signals, needs_llm, rule_signals  # noqa: E402
from .streaming import AudioReplayer, ChannelSegmenter, MockASR, StreamingASR  # noqa: E402

HERE = Path(__file__).resolve().parent
ASR_PROMPT = "Phone call about a loan EMI reminder. Udaan Credit Finance, EMI, auto-debit, UPI, UTR, CIBIL, rupees, top-up loan, two-wheeler."


class LivePipeline:
    def __init__(self, wav: Path, timeline: dict | None = None, speed: float = 1.0, asr: str = "groq", use_llm: bool = True, deliver=None):
        self.wav, self.timeline, self.speed = Path(wav), timeline, speed
        if asr == "groq" and not config.GROQ_API_KEY:
            asr = "mock"
        if asr == "mock" and timeline is None:
            raise ValueError("mock ASR needs a scenario timeline")
        self.asr = StreamingASR(prompt=ASR_PROMPT) if asr == "groq" else MockASR(timeline)
        self.use_llm = use_llm and llm.has_llm()
        self.state = CallState()
        self.engine = NudgeEngine(self._emit)
        self.queue: asyncio.Queue = asyncio.Queue()
        self.deliver = deliver or self._print
        self.utts: list[dict] = []
        self.nudges: list[dict] = []
        self.dropped_segments = 0
        self.chunk_proc_us: list[float] = []
        self.llm_ms: list[float] = []
        self.rule_us: list[float] = []
        self.topic_shifts: list[dict] = []
        self.llm_skipped = 0
        self.asr_errors = 0
        self.t0 = 0.0
        self._uid = 0

    # ------------------------------------------------------------ events
    def _emit(self, kind: str, payload):
        self.queue.put_nowait((kind, payload, time.perf_counter()))

    async def _consumer(self):
        while True:
            kind, payload, _ = await self.queue.get()
            if kind == "__end__":
                break
            if isinstance(payload, Nudge):
                n = payload
                data = {**n.public(), "t_call": round(n.timing.get("speech_end", self.t0) - self.t0, 2)}
                await self.deliver("nudge", data)
                n.timing["delivered"] = time.perf_counter()
                lat = self._latency(n.timing)
                rec = {**data, "latency_ms": lat, "path": n.timing.get("path")}
                self.nudges.append(rec)
                await self.deliver("nudge_latency", {"id": n.id, "latency_ms": lat})
            else:
                await self.deliver(kind, payload)

    @staticmethod
    def _latency(t: dict) -> dict:
        ms = lambda a, b: round((t[b] - t[a]) * 1000, 1) if a in t and b in t else None
        return {"endpointing": ms("speech_end", "endpoint"), "asr": ms("endpoint", "asr_done"), "signal": ms("asr_done", "signal_done"),
                "llm": ms("llm_start", "llm_done"), "engine": ms("signal_done", "nudge_created"), "delivery": ms("nudge_created", "delivered"),
                "e2e": ms("speech_end", "delivered")}

    async def _print(self, kind: str, p: dict):
        t = time.perf_counter() - self.t0
        if kind == "transcript":
            print(f"[{t:6.1f}s] {p['speaker'].upper():8s} {p['text']}   (asr {p['asr_ms']:.0f} ms, conf {p['asr_conf']})")
        elif kind == "nudge":
            print(f"[{t:6.1f}s]   >>> NUDGE P{p['priority']} {p['label']}: {p['text']}  [{p['source']} {p['confidence']}]")
        elif kind == "nudge_latency":
            print(f"            latency {p['latency_ms']}")
        elif kind == "topic_shift":
            print(f"[{t:6.1f}s]   ~ topic: {p['from']} -> {p['to']}")
        elif kind in ("nudge_update", "nudge_close"):
            print(f"[{t:6.1f}s]   ({kind} {p['id']} {p.get('status', '')} updates={p.get('updates')})")

    # ------------------------------------------------------------ main loop
    async def run(self) -> dict:
        rep = AudioReplayer(self.wav, self.speed)
        segs = [ChannelSegmenter(0, "agent"), ChannelSegmenter(1, "customer")]
        consumer = asyncio.create_task(self._consumer())
        tasks = set()
        self.t0 = time.perf_counter()
        await self.deliver("start", {"wav": self.wav.name, "duration": round(rep.duration, 1), "asr": self.asr.name, "llm": self.use_llm, "speed": self.speed})
        async for chunk in rep.stream():
            c0 = time.perf_counter()
            for sg in segs:
                for seg in sg.push(chunk):
                    t = asyncio.create_task(self._process(seg))
                    tasks.add(t)
                    t.add_done_callback(tasks.discard)
            self.engine.tick()
            self.chunk_proc_us.append((time.perf_counter() - c0) * 1e6)
        for sg in segs:
            for seg in sg.flush(time.perf_counter()):
                tasks.add(asyncio.create_task(self._process(seg)))
        if tasks:
            await asyncio.gather(*tasks)
        await asyncio.sleep(0.05)
        self.engine.tick()
        closed = self.engine.finish()
        summary = self._summary(closed)
        self._emit("summary", summary)
        self.queue.put_nowait(("__end__", None, 0))
        await consumer
        summary["nudges"] = self.nudges
        return summary

    async def _process(self, seg):
        timing = {"speech_end": seg.end_wall, "endpoint": seg.endpoint_wall}
        try:
            r = await self.asr.transcribe(seg)
        except Exception as e:                      # one failed segment must never kill the live pipeline
            self.asr_errors += 1
            self._emit("asr_error", {"error": str(e)[:160]})
            return
        timing["asr_done"] = time.perf_counter()
        text = r["text"].strip()
        if not text:
            self.dropped_segments += 1
            return
        self._uid += 1
        u = Utterance(self._uid, seg.speaker, text, seg.start_t, seg.end_t, seg.end_wall, seg.endpoint_wall, timing["asr_done"], r["asr_ms"], r["asr_conf"])
        self.state.add(u)
        rec = {"uid": u.uid, "speaker": u.speaker, "text": text, "start_t": round(u.start_t, 2), "end_t": round(u.end_t, 2),
               "asr_ms": round(r["asr_ms"]), "asr_conf": r["asr_conf"], "forced_cut": seg.forced_cut,
               "audio_to_text_ms": round((timing["asr_done"] - seg.end_wall) * 1000)}
        self.utts.append(rec)
        self._emit("transcript", rec)
        if u.speaker == "agent":
            self.engine.on_agent_utterance(text)

        r0 = time.perf_counter()
        rs = rule_signals(u, self.state)
        timing["signal_done"] = time.perf_counter()
        self.rule_us.append((timing["signal_done"] - r0) * 1e6)
        self.engine.consider(rs, None, u.asr_conf, {**timing, "path": "rules"}, final=False)

        if self.use_llm and needs_llm(u):
            timing["llm_start"] = time.perf_counter()
            ls, meta = await llm_signals(u, self.state)
            timing["llm_done"] = timing["signal_done"] = time.perf_counter()
            if "llm_ms" in meta:
                self.llm_ms.append(meta["llm_ms"])
            intent = meta.get("intent")
            if intent and intent != self.state.intent and intent not in ("other",):
                self.topic_shifts.append({"uid": u.uid, "from": self.state.intent, "to": intent, "t": round(u.end_t, 1)})
                self._emit("topic_shift", {"from": self.state.intent, "to": intent, "uid": u.uid})
                self.state.intent = intent
            if meta.get("frustration") is not None and u.speaker == "customer":
                self.state.frustration.append(float(meta["frustration"]))
                self._emit("sentiment", {"uid": u.uid, "frustration": meta["frustration"], "sentiment": meta.get("sentiment")})
            self.engine.consider(rs, ls, u.asr_conf, {**timing, "path": "llm"}, final=True)
        elif self.use_llm:
            self.llm_skipped += 1  # prefiltered agent small-talk: LLM not needed, fuzzy types simply not evaluated
        else:
            self.engine.consider(rs, None, u.asr_conf, {**timing, "path": "rules"}, final=True)

    def _summary(self, closed: list[Nudge]) -> dict:
        missed = [n.public() for n in closed if n.type == "cross_sell" and n.status != "resolved"]
        gaps = [n.public() for n in closed if n.priority == 1 and n.status != "resolved"]
        return {"utterances": len(self.utts), "dropped_segments": self.dropped_segments, "llm_skipped_prefilter": self.llm_skipped, "asr_errors": self.asr_errors, "engine_stats": self.engine.stats,
                "post_call": {"missed_opportunities": missed, "unresolved_compliance": gaps,
                              "acted_on": sum(n.status == "resolved" for n in closed), "total_nudges": len(closed)},
                "topic_shifts": self.topic_shifts, "frustration_trace": self.state.frustration,
                "component_latency": {
                    "chunk_processing_us_p50": round(float(np.median(self.chunk_proc_us)), 1) if self.chunk_proc_us else None,
                    "asr_ms": [u["asr_ms"] for u in self.utts], "audio_to_text_ms": [u["audio_to_text_ms"] for u in self.utts],
                    "rules_us": [round(x, 1) for x in self.rule_us], "llm_ms": [round(x) for x in self.llm_ms]},
                "transcript": self.utts, "asr": self.asr.name, "llm": self.use_llm}


def load_scenario(sid: str) -> tuple[Path, dict]:
    wav = HERE / "audio" / f"{sid}.wav"
    tl = json.loads((HERE / "audio" / f"{sid}.timeline.json").read_text(encoding="utf-8"))
    return wav, tl


async def _main(a):
    if a.wav:
        p = LivePipeline(Path(a.wav), None, a.speed, "groq", not a.no_llm)
        name = Path(a.wav).parent.name or Path(a.wav).stem
    else:
        wav, tl = load_scenario(a.scenario)
        p = LivePipeline(wav, tl, a.speed, a.asr, not a.no_llm)
        name = a.scenario
    res = await p.run()
    out = HERE / "results" / "runs"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}__{p.asr.name}{'' if p.use_llm else '_nollm'}.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("engine_stats", "post_call")}, indent=1, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="s1_missed_cross_sell")
    ap.add_argument("--wav")
    ap.add_argument("--asr", default="groq", choices=["groq", "mock"])
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--speed", type=float, default=1.0)
    asyncio.run(_main(ap.parse_args()))
