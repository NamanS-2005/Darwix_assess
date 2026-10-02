"""Language-specific ASR evaluation for the Philippines and Indonesia markets.

For every utterance x voice it synthesises audio (neural TTS, cached), optionally a noisy copy (call-centre babble-like
noise at ~15 dB SNR, 8 kHz telephone band-limit), then transcribes with several ASR configurations and reports
WER / CER / finance-term recall / language-ID behaviour / translation-to-English failures.

python -m q3_multilingual.asr_eval.run_asr_eval [--markets ph_life id_multifinance] [--configs ...] [--no-noise]
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import jiwer
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from common import audio, config, llm  # noqa: E402

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
RESULTS = HERE / "results"

LANG = {"ph_life": "tl", "id_multifinance": "id"}
PROMPTS = {
    "ph_life": "Taglish na usapan tungkol sa insurance: premium, policy, beneficiary, rider, lapse, coverage, grace period, GCash, BancoBayan, po, opo, sweldo.",
    "id_multifinance": "Percakapan soal angsuran: cicilan, jatuh tempo, denda, tenor, DP, BPKB, virtual account, Indomaret, Alfamart, gajian, nggak, udah.",
}
CONFIGS = {
    "whisper-v3 | lang hint + prompt": {"provider": "groq", "model": "whisper-large-v3", "lang": True, "prompt": True},
    "whisper-v3 | auto-detect + prompt": {"provider": "groq", "model": "whisper-large-v3", "lang": False, "prompt": True},
    "whisper-v3 | lang hint, no prompt": {"provider": "groq", "model": "whisper-large-v3", "lang": True, "prompt": False},
    "whisper-v3-turbo | lang hint + prompt": {"provider": "groq", "model": "whisper-large-v3-turbo", "lang": True, "prompt": True},
    "gemini-flash-lite | audio prompt": {"provider": "gemini", "model": "gemini-flash-lite-latest"},
}

_last_call: dict[str, float] = defaultdict(float)


def throttle(provider: str, per_min: int):
    gap = 60.0 / per_min
    wait = _last_call[provider] + gap - time.time()
    if wait > 0:
        time.sleep(wait)
    _last_call[provider] = time.time()


def norm(s: str) -> str:
    s = s.lower().replace("’", "'")
    s = re.sub(r"[^\w\s'-]", " ", s)
    s = s.replace("-", " ")
    return " ".join(s.split())


def norm_numbers(s: str, market: str) -> str:
    """Formatting-insensitive normalisation: number words -> digits, '1.250.000'/'4,250' -> plain digits, '%' -> word."""
    from q1_voice_agent.engine.numwords import words_to_digits
    s = s.lower().replace("rp", " ")
    s = re.sub(r"(?<=\d)[.,](?=\d{3}\b)", "", s)
    s = s.replace("%", " persen" if market == "id_multifinance" else " percent")
    s = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s)
    return words_to_digits(norm(s))


def synth(text: str, voice: str, key: str) -> Path:
    p = AUDIO / f"{key}.wav"
    if not p.exists():
        AUDIO.mkdir(parents=True, exist_ok=True)
        mp3, _ = audio.tts_mp3(text, voice)
        audio.write_wav(p, audio.decode_to_pcm(mp3))
    return p


def telephone_noisy(src: Path, dst: Path, snr_db: float = 15.0) -> Path:
    if dst.exists():
        return dst
    x, sr = audio.read_wav(src)
    x = x[:, 0]
    rng = np.random.default_rng(7)
    # babble-like noise: sum of band-limited random "voices" + hum
    noise = sum(np.convolve(rng.standard_normal(len(x)), np.hanning(40), "same") * rng.uniform(0.5, 1.0) for _ in range(6))
    noise += 0.3 * np.sin(2 * np.pi * 50 * np.arange(len(x)) / sr)
    p_sig, p_noise = np.mean(x ** 2) + 1e-9, np.mean(noise ** 2) + 1e-9
    y = x + noise * np.sqrt(p_sig / (p_noise * 10 ** (snr_db / 10)))
    # 8 kHz narrowband telephone channel, back to 16 kHz
    y8 = y[::2]
    y = np.repeat(y8, 2)[: len(x)]
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.9
    audio.write_wav(dst, y.astype(np.float32))
    return dst


def transcribe(cfg: dict, wav: Path, market: str) -> tuple[str, float, str | None]:
    data = wav.read_bytes()
    if cfg["provider"] == "groq":
        throttle("groq", 18)
        client = llm._client("groq")
        kwargs = dict(model=cfg["model"], file=(wav.name, data), temperature=0.0, response_format="verbose_json")
        if cfg.get("lang"):
            kwargs["language"] = LANG[market]
        if cfg.get("prompt"):
            kwargs["prompt"] = PROMPTS[market]
        t0 = time.perf_counter()
        for attempt in range(4):
            try:
                r = client.audio.transcriptions.create(**kwargs)
                break
            except Exception as e:
                if attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))
        ms = (time.perf_counter() - t0) * 1000
        return r.text.strip(), ms, getattr(r, "language", None)
    # Gemini: audio understanding through the OpenAI-compatible chat endpoint
    throttle("gemini", 9)
    client = llm._client("gemini")
    for attempt in range(4):
        try:
            return _gemini_once(client, cfg, data, market)
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(15 if ("429" in str(e) or "503" in str(e)) else 3)


def _gemini_once(client, cfg: dict, data: bytes, market: str):
    lang_name = {"ph_life": "Filipino/Tagalog with English code-switching (Taglish)", "id_multifinance": "Indonesian (may contain Javanese/Sundanese words and English loanwords)"}[market]
    t0 = time.perf_counter()
    extra = {"reasoning_effort": "minimal"} if cfg["model"].startswith("gemini-3") else {}
    r = client.chat.completions.create(model=cfg["model"], temperature=0, **extra, messages=[{"role": "user", "content": [
        {"type": "text", "text": f"Transcribe this phone audio verbatim. Language: {lang_name}. Do not translate. Output only the transcript."},
        {"type": "input_audio", "input_audio": {"data": base64.b64encode(data).decode(), "format": "wav"}}]}])
    return (r.choices[0].message.content or "").strip().strip('"'), (time.perf_counter() - t0) * 1000, None


def looks_translated(ref: str, hyp: str, market: str) -> bool:
    """Whisper failure mode: mis-detects language and outputs an English *translation*."""
    en = {"the", "i", "my", "is", "will", "want", "to", "you", "please", "already", "paid", "yet", "not", "your", "of", "what", "how", "when"}
    native = {"ph_life": {"po", "ko", "ang", "ng", "yung", "na", "sa", "ba", "pa", "ako"},
              "id_multifinance": {"saya", "yang", "kalau", "sudah", "belum", "nggak", "ini", "itu", "bayar", "lewat"}}[market]
    h = set(norm(hyp).split())
    r = set(norm(ref).split())
    return len(h & en) >= 3 and len(h & native) <= 1 and len(r & native) >= 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", nargs="*", default=["ph_life", "id_multifinance"])
    ap.add_argument("--configs", nargs="*", default=list(CONFIGS))
    ap.add_argument("--no-noise", action="store_true")
    a = ap.parse_args()
    spec = yaml.safe_load((HERE / "utterances.yaml").read_text(encoding="utf-8"))
    configs = {k: v for k, v in CONFIGS.items() if k in a.configs and (llm._client(v["provider"]) is not None)}
    if not configs:
        sys.exit("No ASR provider configured (GROQ_API_KEY / GEMINI_API_KEY)")
    RESULTS.mkdir(parents=True, exist_ok=True)
    cache_path = RESULTS / "asr_cache.jsonl"
    cache = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                cache[d["key"]] = tuple(d["v"])
    rows = []
    for market in a.markets:
        ms = spec[market]
        cases = []
        for it in ms["items"]:
            voices = list(ms["voices"])
            if it["cat"] in ("javanese_insertions",):
                voices = [v for v in ms.get("regional_voices", []) if v.startswith("jv")] + voices[:1]
            elif it["cat"] in ("sundanese_insertions",):
                voices = [v for v in ms.get("regional_voices", []) if v.startswith("su")] + voices[:1]
            elif ms.get("regional_voices"):
                voices = voices + ms["regional_voices"][:1] + ms["regional_voices"][2:3]  # one jv + one su voice on every item
            for v in voices:
                wav = synth(it["text"], v, f"{it['id']}_{v}")
                cases.append({**it, "voice": v, "wav": wav, "condition": "clean"})
                if not a.no_noise and v == voices[0]:
                    cases.append({**it, "voice": v, "wav": telephone_noisy(wav, AUDIO / f"{it['id']}_{v}_noisy.wav"), "condition": "telephone+noise"})
        real_dir = AUDIO / "real" / market
        for w in sorted(real_dir.glob("*.wav")) if real_dir.exists() else []:
            ref = w.with_suffix(".txt")
            if ref.exists():
                cases.append({"id": w.stem, "cat": "real_speaker", "text": ref.read_text(encoding="utf-8").strip(), "terms": [], "voice": "human", "wav": w, "condition": "real"})
        for name, cfg in configs.items():
            for c in cases:
                key = f"{name}||{Path(c['wav']).name}"
                if key in cache:
                    hyp, lat, lang = cache[key]
                else:
                    try:
                        hyp, lat, lang = transcribe(cfg, c["wav"], market)
                    except Exception as e:
                        hyp, lat, lang = f"<error {type(e).__name__}>", 0, None
                    if not hyp.startswith("<error"):   # cache successes only, so quota failures are retried next run
                        cache[key] = (hyp, lat, lang)
                        with cache_path.open("a", encoding="utf-8") as cf:
                            cf.write(json.dumps({"key": key, "v": [hyp, lat, lang]}, ensure_ascii=False) + "\n")
                ref_n, hyp_n = norm(c["text"]), norm(hyp)
                terms = c.get("terms", [])
                recall = sum(norm(t) in hyp_n for t in terms) / len(terms) if terms else None
                rows.append({"market": market, "config": name, "id": c["id"], "cat": c["cat"], "voice": c["voice"], "condition": c["condition"],
                             "ref": c["text"], "hyp": hyp, "wer": jiwer.wer(ref_n, hyp_n) if hyp_n else 1.0, "cer": jiwer.cer(ref_n, hyp_n) if hyp_n else 1.0,
                             "term_recall": recall, "latency_ms": round(lat), "detected_lang": lang, "translated": looks_translated(c["text"], hyp, market)})
                print(f"{market:16s} {name:38s} {c['id']} {c['voice']:22s} {c['condition']:16s} WER={rows[-1]['wer']:.2f}")
    (RESULTS / "asr_results.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    write_report(rows)


def agg(rs):
    w = [r["wer"] for r in rs]
    wn = [r["wer_norm"] for r in rs if "wer_norm" in r]
    t = [r["term_recall"] for r in rs if r["term_recall"] is not None]
    lat = [r["latency_ms"] for r in rs if r["latency_ms"]]
    return {"n": len(rs), "wer": float(np.mean(w)) if w else 0, "wer_norm": float(np.mean(wn)) if wn else 0, "cer": float(np.mean([r["cer"] for r in rs])) if rs else 0,
            "term": float(np.mean(t)) if t else None, "lat": float(np.median(lat)) if lat else None, "translated": sum(r["translated"] for r in rs)}


def write_report(rows):
    for r in rows:
        if "wer_norm" not in r:
            rn, hn = norm_numbers(r["ref"], r["market"]), norm_numbers(r["hyp"], r["market"])
            r["wer_norm"] = jiwer.wer(rn, hn) if hn else 1.0
    L = ["# ASR evaluation – Philippines & Indonesia\n",
         "Audio: neural TTS voices (fil-PH, en-PH, id-ID, jv-ID, su-ID) + a telephone-band/noise copy; optional real recordings. "
         "WER/CER on normalised text (lower-case, punctuation removed). **TTS speech is cleaner than real callers, so absolute WER is optimistic; "
         "relative comparisons between configurations and accents are the useful signal.**\n"]
    for market in sorted({r["market"] for r in rows}):
        mr = [r for r in rows if r["market"] == market]
        L += [f"\n## {market}\n", "| Config | n | WER | WER (numbers normalised) | CER | Term recall | Translated→EN | p50 latency ms |", "|---|---|---|---|---|---|---|---|"]
        for cfgname in dict.fromkeys(r["config"] for r in mr):
            a = agg([r for r in mr if r["config"] == cfgname])
            L.append(f"| {cfgname} | {a['n']} | {a['wer']:.1%} | **{a['wer_norm']:.1%}** | {a['cer']:.1%} | {'' if a['term'] is None else f'{a['term']:.0%}'} | {a['translated']} | {a['lat'] or ''} |")
        best = next(iter(dict.fromkeys(r["config"] for r in mr)))
        L += [f"\n**Breakdown for `{best}`** (clean audio unless stated)\n"]
        br = [r for r in mr if r["config"] == best]
        for key in ("cat", "voice"):
            L += [f"\n| {key} | n | WER | WER (num-norm) | Term recall |", "|---|---|---|---|---|"]
            for val in sorted({r[key] for r in br}):
                a = agg([r for r in br if r[key] == val and r["condition"] != "telephone+noise"])
                if a["n"]:
                    L.append(f"| {val} | {a['n']} | {a['wer']:.1%} | {a['wer_norm']:.1%} | {'' if a['term'] is None else f'{a['term']:.0%}'} |")
        noisy = [r for r in br if r["condition"] == "telephone+noise"]
        pairs = [(next(c for c in br if c["id"] == r["id"] and c["voice"] == r["voice"] and c["condition"] == "clean"), r) for r in noisy]
        if pairs:
            a_c, a_n = agg([c for c, _ in pairs]), agg([n for _, n in pairs])
            L += ["\n| condition (same utterances & voice) | n | WER (num-norm) | Term recall |", "|---|---|---|---|",
                  f"| clean | {a_c['n']} | {a_c['wer_norm']:.1%} | {a_c['term']:.0%} |",
                  f"| telephone 8 kHz + babble noise 15 dB | {a_n['n']} | {a_n['wer_norm']:.1%} | {a_n['term']:.0%} |"]
        detected = defaultdict(int)
        for r in mr:
            if r["detected_lang"] and "auto" in r["config"]:
                detected[r["detected_lang"]] += 1
        if detected:
            L.append(f"\nAuto language-ID decisions (whisper auto-detect): {dict(detected)}")
        worst = sorted(br, key=lambda r: -r["wer_norm"])[:6]
        L += [f"\n**Largest errors (`{best}`, number-normalised WER)**\n"] + [f"- `{r['id']}` {r['voice']} {r['condition']}: WER {r['wer']:.0%} (num-norm {r['wer_norm']:.0%})  \n  ref: {r['ref']}  \n  hyp: {r['hyp']}" for r in worst]
    (RESULTS / "asr_report.md").write_text("\n".join(L), encoding="utf-8")
    print("wrote", RESULTS / "asr_report.md")


if __name__ == "__main__":
    main()
