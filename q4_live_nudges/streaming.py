"""Streaming input + streaming ASR.

AudioReplayer   : replays a (stereo) call recording at real-time speed in 100 ms chunks (or reads live chunks).
ChannelSegmenter: per-channel energy VAD with adaptive noise floor -> utterance segments (endpointing).
                  Dual-channel recordings give speaker separation for free (agent = L, customer = R).
StreamingASR    : sends each finalised segment to Groq Whisper (turbo) concurrently; returns text + confidence.
                  Long turns are force-cut every MAX_SEG seconds so latency stays bounded.
MockASR         : offline fallback that uses the scenario's ground-truth text (clearly labelled as mock in reports).
"""
from __future__ import annotations

import asyncio
import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from common import audio, config, llm

CHUNK_S = 0.1
FRAME_S = 0.02


@dataclass
class Chunk:
    idx: int
    audio_t: float          # position in the recording (s)
    wall: float             # wall-clock time the chunk was received (perf_counter)
    data: np.ndarray        # [n, channels]


@dataclass
class Segment:
    channel: int
    speaker: str
    start_t: float
    end_t: float
    end_wall: float          # wall time when the last audio of the utterance arrived  (= "audio received")
    endpoint_wall: float     # wall time when VAD decided the utterance ended (includes hangover)
    pcm: np.ndarray
    forced_cut: bool = False
    meta: dict = field(default_factory=dict)


class AudioReplayer:
    def __init__(self, wav: Path, speed: float = 1.0):
        self.samples, self.sr = audio.read_wav(wav)
        if self.sr != audio.SR:
            raise ValueError("expected 16 kHz wav (use make_audio.py)")
        if self.samples.shape[1] == 1:
            self.samples = np.repeat(self.samples, 2, axis=1)  # mono: both 'speakers' on one channel (no separation)
        self.speed = speed
        self.duration = len(self.samples) / self.sr

    async def stream(self):
        n = int(CHUNK_S * self.sr)
        t0 = time.perf_counter()
        for i, s in enumerate(range(0, len(self.samples), n)):
            target = t0 + (i * CHUNK_S) / self.speed
            delay = target - time.perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
            yield Chunk(i, s / self.sr, time.perf_counter(), self.samples[s : s + n])


class ChannelSegmenter:
    """Energy VAD with adaptive noise floor. Hangover (END_SIL) is the main endpointing latency cost."""
    START_FRAMES = 4     # 80 ms of speech to open
    END_SIL = 0.5        # s of silence to close
    MAX_SEG = 6.0        # force-cut long utterances
    PRE_ROLL = 0.2

    def __init__(self, channel: int, speaker: str, sr: int = audio.SR):
        self.ch, self.speaker, self.sr = channel, speaker, sr
        self.flen = int(FRAME_S * sr)
        self.floor = 1e-4
        self.calib: list[float] = []
        self.buf: list[np.ndarray] = []
        self.history: list[np.ndarray] = []   # pre-roll
        self.in_speech = False
        self.speech_run = 0
        self.sil = 0.0
        self.seg_start = 0.0
        self.last_voice_t = 0.0
        self.last_voice_wall = 0.0

    def push(self, chunk: Chunk) -> list[Segment]:
        out = []
        x = chunk.data[:, self.ch]
        for k in range(0, len(x), self.flen):
            fr = x[k : k + self.flen]
            if len(fr) == 0:
                continue
            t = chunk.audio_t + k / self.sr
            e = float(np.mean(fr ** 2))
            if len(self.calib) < 15:                       # first 300 ms: initialise noise floor
                self.calib.append(e)
                self.floor = max(float(np.median(self.calib)), 1e-7)
            elif not self.in_speech:                       # min-tracking: fall fast, rise slowly
                self.floor = 0.9 * self.floor + 0.1 * e if e < self.floor else 0.995 * self.floor + 0.005 * e
            thr = max(self.floor * 6.0, 2e-4)
            voiced = e > thr
            if not self.in_speech:
                self.history.append(fr)
                self.history = self.history[-int(self.PRE_ROLL / FRAME_S):]
                self.speech_run = self.speech_run + 1 if voiced else 0
                if self.speech_run >= self.START_FRAMES:
                    self.in_speech = True
                    self.buf = list(self.history)
                    self.seg_start = t - len(self.history) * FRAME_S
                    self.sil = 0.0
                    self.last_voice_t, self.last_voice_wall = t, chunk.wall
            else:
                self.buf.append(fr)
                if voiced:
                    self.sil = 0.0
                    self.last_voice_t, self.last_voice_wall = t + FRAME_S, chunk.wall
                else:
                    self.sil += FRAME_S
                dur = t - self.seg_start
                if self.sil >= self.END_SIL or dur >= self.MAX_SEG:
                    out.append(Segment(self.ch, self.speaker, self.seg_start, self.last_voice_t, self.last_voice_wall,
                                       chunk.wall, np.concatenate(self.buf), forced_cut=dur >= self.MAX_SEG))
                    self.in_speech, self.speech_run, self.buf, self.history = False, 0, [], []
        return out

    def flush(self, wall: float) -> list[Segment]:
        if self.in_speech and self.buf:
            self.in_speech = False
            return [Segment(self.ch, self.speaker, self.seg_start, self.last_voice_t, self.last_voice_wall, wall, np.concatenate(self.buf))]
        return []


HALLUCINATIONS = {"thank you.", "thank you", "thanks for watching.", "thanks for watching!", "you", "bye.", "okay.", "."}


class StreamingASR:
    name = "groq"

    def __init__(self, model: str | None = None, language: str = "en", prompt: str = ""):
        self.model = model or config.ASR_MODEL_FAST
        self.language, self.prompt = language, prompt

    # Client-side rate limiter over (organisation, model) buckets: free tier = 20 Whisper requests/min per org per model.
    # Real-time dual-channel streaming bursts above that, so requests are spread over all buckets and wait rather than fail.
    _lock = threading.Lock()
    _sent: dict[tuple[str, str], deque] = {}
    RPM = 19

    def _acquire(self) -> tuple:
        orgs = [p for p in ("groq", "groq2") if llm._client(p) is not None]
        models = [self.model] + [m for m in (config.ASR_MODEL, config.ASR_MODEL_FAST) if m != self.model]
        buckets = [(o, m) for m in models for o in orgs]
        while True:
            with StreamingASR._lock:
                now = time.time()
                for b in buckets:
                    q = StreamingASR._sent.setdefault(b, deque())
                    while q and now - q[0] > 60:
                        q.popleft()
                    if len(q) < StreamingASR.RPM:
                        q.append(now)
                        return b
            time.sleep(0.1)

    def _call(self, seg: Segment) -> dict:
        wav = audio.pcm_to_wav_bytes(seg.pcm)
        t0 = time.perf_counter()
        r, last_err, used = None, None, None
        for attempt in range(6):
            org, model = self._acquire()
            used = model
            try:
                r = llm._client(org).audio.transcriptions.create(model=model, file=("seg.wav", wav), language=self.language,
                                                                 prompt=self.prompt or None, temperature=0.0, response_format="verbose_json")
                break
            except Exception as e:
                last_err = e
                if "429" not in str(e):
                    raise
                with StreamingASR._lock:   # server says this bucket is full: mark it full for this minute
                    q = StreamingASR._sent.setdefault((org, model), deque())
                    q.extend([time.time()] * max(0, StreamingASR.RPM - len(q)))
        if r is None:
            raise last_err
        segs = getattr(r, "segments", None) or []
        get = lambda s, k: (s.get(k) if isinstance(s, dict) else getattr(s, k, None))
        lp = [get(s, "avg_logprob") for s in segs if get(s, "avg_logprob") is not None]
        ns = [get(s, "no_speech_prob") for s in segs if get(s, "no_speech_prob") is not None]
        conf = float(np.mean([math.exp(v) for v in lp])) if lp else 0.8
        no_speech = float(np.mean(ns)) if ns else 0.0
        text = (r.text or "").strip()
        if text.lower() in HALLUCINATIONS and (conf < 0.6 or no_speech > 0.3):
            text = ""  # classic Whisper hallucination on noise
        return {"text": text, "asr_ms": (time.perf_counter() - t0) * 1000, "asr_conf": round(conf, 3), "no_speech": round(no_speech, 3), "model": used}

    async def transcribe(self, seg: Segment) -> dict:
        return await asyncio.to_thread(self._call, seg)


class MockASR:
    """Offline: returns the ground-truth text of the timeline turn that overlaps the segment. Latency = 0 (labelled MOCK)."""
    name = "mock"

    def __init__(self, timeline: dict):
        self.turns = timeline["turns"]
        self.used: dict[int, float] = {}

    async def transcribe(self, seg: Segment) -> dict:
        mid = (seg.start_t + seg.end_t) / 2
        best = min(self.turns, key=lambda t: 0 if t["start"] <= mid <= t["end"] else min(abs(mid - t["start"]), abs(mid - t["end"])))
        if best["speaker"] != seg.speaker:
            return {"text": "", "asr_ms": 0.0, "asr_conf": 0.0, "no_speech": 1.0}
        # forced cuts: return the proportional slice of words
        words = best["text"].split()
        span = max(1e-3, best["end"] - best["start"])
        a = max(0, int(len(words) * (seg.start_t - best["start"]) / span))
        b = min(len(words), math.ceil(len(words) * (seg.end_t - best["start"]) / span) + 1)
        return {"text": " ".join(words[a:b]), "asr_ms": 0.0, "asr_conf": 1.0, "no_speech": 0.0}
