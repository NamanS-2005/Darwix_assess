"""Audio helpers: neural TTS (edge-tts, free, has fil-PH / id-ID / jv-ID / su-ID voices) and ffmpeg conversion."""
from __future__ import annotations

import asyncio
import subprocess
import tempfile
import time
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SR = 16000


async def tts_mp3_async(text: str, voice: str, rate: str = "+0%") -> bytes:
    comm = edge_tts.Communicate(text, voice, rate=rate)
    chunks = []
    async for item in comm.stream():
        if item["type"] == "audio":
            chunks.append(item["data"])
    return b"".join(chunks)


def tts_mp3(text: str, voice: str, rate: str = "+0%") -> tuple[bytes, float]:
    t0 = time.perf_counter()
    data = asyncio.run(tts_mp3_async(text, voice, rate))
    return data, (time.perf_counter() - t0) * 1000


def decode_to_pcm(data: bytes, sr: int = SR) -> np.ndarray:
    """Any container (mp3/webm/wav) -> mono float32 PCM at `sr`."""
    proc = subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", str(sr), "pipe:1"],
        input=data, capture_output=True, check=True,
    )
    return np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def pcm_to_wav_bytes(pcm: np.ndarray, sr: int = SR, channels: int = 1) -> bytes:
    import io
    import wave

    arr = np.clip(pcm, -1, 1)
    ints = (arr * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(ints.tobytes())
    return buf.getvalue()


def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Returns (samples[n, channels] float32, sr)."""
    import wave

    with wave.open(str(path), "rb") as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    return data.reshape(-1, ch), sr


def write_wav(path: str | Path, samples: np.ndarray, sr: int = SR) -> None:
    ch = 1 if samples.ndim == 1 else samples.shape[1]
    Path(path).write_bytes(pcm_to_wav_bytes(samples.reshape(-1) if ch == 1 else samples.reshape(-1), sr, ch))


def wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav_path), "-b:a", "64k", str(mp3_path)], check=True)


def silence(seconds: float, sr: int = SR) -> np.ndarray:
    return np.zeros(int(seconds * sr), dtype=np.float32)
