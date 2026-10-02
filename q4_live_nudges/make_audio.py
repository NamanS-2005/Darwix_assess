"""Render Q4 test scenarios into dual-channel call recordings (agent = left, customer = right), like a contact-centre
stereo recording. Also writes a ground-truth timeline (turn start/end seconds) used for labelling and the mock-ASR mode.

python -m q4_live_nudges.make_audio
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import audio  # noqa: E402

HERE = Path(__file__).resolve().parent
SR = audio.SR


def street_noise(n: int, rng) -> np.ndarray:
    """Market/traffic-like noise: brown-ish rumble + random horn/chatter bursts."""
    brown = np.cumsum(rng.standard_normal(n))
    brown = brown - np.convolve(brown, np.ones(4000) / 4000, "same")
    brown /= np.max(np.abs(brown)) + 1e-9
    babble = sum(np.convolve(rng.standard_normal(n), np.hanning(60), "same") for _ in range(5))
    babble /= np.max(np.abs(babble)) + 1e-9
    noise = 0.6 * brown + 0.5 * babble
    for _ in range(max(1, n // (SR * 6))):  # occasional horn
        s = rng.integers(0, max(1, n - SR))
        t = np.arange(int(SR * 0.4)) / SR
        noise[s : s + len(t)] += 0.8 * np.sin(2 * np.pi * 440 * t) * np.hanning(len(t))
    return noise / (np.max(np.abs(noise)) + 1e-9)


def render(path: Path) -> dict:
    sc = yaml.safe_load(path.read_text(encoding="utf-8"))
    L, R, timeline, t = [], [], [], 0.6
    lead = audio.silence(0.6)
    L.append(lead)
    R.append(lead)
    for i, (spk, text) in enumerate(sc["turns"]):
        voice = sc["agent_voice"] if spk == "agent" else sc["customer_voice"]
        rate = sc.get("customer_rate", "+0%") if spk == "customer" else "+0%"
        mp3, _ = audio.tts_mp3(text, voice, rate)
        pcm = audio.decode_to_pcm(mp3)
        nz = np.abs(pcm) > 0.01  # trim TTS leading/trailing silence for realistic turn-taking
        if nz.any():
            idx = np.where(nz)[0]
            pcm = pcm[max(0, idx[0] - 800) : idx[-1] + 1600]
        dur = len(pcm) / SR
        timeline.append({"turn": i, "speaker": spk, "text": text, "start": round(t, 3), "end": round(t + dur, 3)})
        (L if spk == "agent" else R).append(pcm)
        (R if spk == "agent" else L).append(np.zeros_like(pcm))
        gap = audio.silence(0.45 if spk == "agent" else 0.6)
        L.append(gap)
        R.append(gap)
        t += dur + len(gap) / SR
    left, right = np.concatenate(L), np.concatenate(R)
    if sc.get("noise_snr_db") is not None:
        rng = np.random.default_rng(11)
        noise = street_noise(len(right), rng)
        sig_p = np.mean(right[np.abs(right) > 0.01] ** 2)
        k = np.sqrt(sig_p / (np.mean(noise ** 2) * 10 ** (sc["noise_snr_db"] / 10)))
        right = right + k * noise
        left = left + 0.15 * k * street_noise(len(left), rng)  # a little bleed on the agent headset
    stereo = np.clip(np.stack([left, right], axis=1), -1, 1)
    out = HERE / "audio" / f"{sc['id']}.wav"
    out.parent.mkdir(exist_ok=True)
    audio.write_wav(out, stereo)
    (HERE / "audio" / f"{sc['id']}.timeline.json").write_text(json.dumps({"id": sc["id"], "duration": round(len(left) / SR, 2), "turns": timeline}, indent=1), encoding="utf-8")
    return {"id": sc["id"], "seconds": round(len(left) / SR, 1), "turns": len(timeline)}


if __name__ == "__main__":
    for p in sorted((HERE / "scenarios").glob("*.yaml")):
        print(render(p))
