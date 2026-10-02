"""Thin LLM/ASR/embedding client over OpenAI-compatible endpoints (Groq, Gemini).

Design choices
- One SDK (openai) for both providers -> identical message/tool formats.
- Automatic provider fallback: if the primary errors or is rate-limited, retry on the other.
- Every call returns latency so callers can report component timings (Q4 needs this).
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from . import config


@dataclass
class LLMResult:
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    raw_message: dict | None = None


_clients: dict[str, OpenAI] = {}


def _client(provider: str) -> OpenAI | None:
    if provider in _clients:
        return _clients[provider]
    key, base = config.PROVIDERS.get(provider, ("", ""))
    if key:
        _clients[provider] = OpenAI(api_key=key, base_url=base, timeout=30, max_retries=0)
    return _clients.get(provider)


def available_providers() -> list[str]:
    order = [config.LLM_PRIMARY] + [p for p in config.PROVIDER_ORDER if p != config.LLM_PRIMARY]
    return [p for p in order if _client(p) is not None and any(config.MODELS.get(p, {}).values())]


def has_llm() -> bool:
    return bool(available_providers())


_cooldown: dict[str, float] = {}


def _flatten_tool_history(messages: list[dict]) -> list[dict]:
    """Gemini 3 rejects replayed tool calls it did not produce ("missing thought signature"). When a conversation falls
    back to Gemini mid-call, earlier tool calls/results are rewritten as plain text so the fallback keeps working."""
    if not any(m.get("tool_calls") or m.get("role") == "tool" for m in messages):
        return messages
    out, names = [], {}
    for m in messages:
        if m.get("tool_calls"):
            for tc in m["tool_calls"]:
                names[tc["id"]] = tc["function"]["name"]
            if (m.get("content") or "").strip():
                out.append({"role": "assistant", "content": m["content"]})
        elif m.get("role") == "tool":
            # earlier tool outputs become context notes (not assistant text, so the model doesn't imitate a fake syntax)
            out.append({"role": "user", "content": f"(context – result of {names.get(m.get('tool_call_id'), 'a tool')} earlier in this call, "
                                                   f"not said by the customer: {m.get('content', '')})"})
        else:
            out.append(m)
    return out


def _candidates(tier: str, providers: list[str] | None) -> list[tuple[str, str]]:
    """(provider, model) chain for a tier. Each tier lists several models per provider (comma-separated in config):
    free tiers have per-model daily/minute token quotas, so spreading load keeps calls alive. Models in cooldown
    (recently rate-limited) are tried last."""
    now = time.time()
    out = []
    for p in providers or available_providers():
        if _client(p) is None:
            continue
        for m in [x.strip() for x in config.MODELS[p].get(tier, "").split(",") if x.strip()]:
            out.append((p, m))
    ready = [pm for pm in out if _cooldown.get(f"{pm[0]}/{pm[1]}", 0) <= now]
    if ready:   # skip rate-limited models entirely while any other model is available (saves a failing round-trip each)
        return ready
    return sorted(out, key=lambda pm: _cooldown.get(f"{pm[0]}/{pm[1]}", 0))


def _note_failure(key: str, e: Exception) -> None:
    msg = str(e)
    if "429" not in msg and "503" not in msg:
        return
    wait = 30.0
    m = re.search(r"try again in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s", msg)
    if m:
        wait = int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3))
    elif "per day" in msg or "TPD" in msg or "RPD" in msg or "quota" in msg:
        wait = 3600.0
    _cooldown[key] = time.time() + wait


def chat(
    messages: list[dict],
    *,
    tier: str = "agent",
    tools: list[dict] | None = None,
    temperature: float = 0.2,
    max_tokens: int = 400,
    json_mode: bool = False,
    providers: list[str] | None = None,
    reasoning: str | None = None,
) -> LLMResult:
    """Chat completion with provider fallback. tier: 'agent' (quality) or 'fast' (latency)."""
    errors = []
    for provider, model in _candidates(tier, providers):
        client = _client(provider)
        msgs = _flatten_tool_history(messages) if provider.startswith("gemini") else messages
        kwargs: dict[str, Any] = dict(model=model, messages=msgs, temperature=temperature, max_tokens=max_tokens)
        if model.startswith("openai/gpt-oss"):
            kwargs.update(reasoning_effort="low", max_tokens=max_tokens + 400)   # reasoning tokens count toward the limit
        elif model.startswith("qwen/") and provider.startswith("groq"):
            kwargs.update(reasoning_effort="none")                                 # voice latency: no thinking pass
        elif model.startswith("gemini-3"):
            kwargs.update(reasoning_effort="minimal")                              # otherwise thinking eats the token budget
        if reasoning and model.startswith("openai/gpt-oss"):
            kwargs.update(reasoning_effort=reasoning, max_tokens=max_tokens + 1200)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        t0 = time.perf_counter()
        try:
            resp = client.chat.completions.create(**kwargs)
        except Exception as e:  # rate limit / outage / bad tool call -> next model / provider
            errors.append(f"{provider}/{model}:{type(e).__name__}:{str(e)[:200]}")
            _note_failure(f"{provider}/{model}", e)
            continue
        latency = (time.perf_counter() - t0) * 1000
        msg = resp.choices[0].message
        if msg.content and "<think>" in msg.content:
            msg.content = re.sub(r"<think>.*?</think>", "", msg.content, flags=re.S).strip()
        calls = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append({"id": tc.id, "name": tc.function.name, "arguments": args, "raw_arguments": tc.function.arguments})
        raw = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            raw["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}}
                for tc in msg.tool_calls
            ]
        _wait_budget.pop("left", None)
        return LLMResult(msg.content or "", calls, provider, model, latency, raw)
    if errors and RATE_LIMIT_WAIT_S > 0 and _wait_budget.get("left", RATE_LIMIT_WAIT_S) > 0 and any("429" in e for e in errors):
        # offline runs (simulations/benchmarks) wait for quota instead of failing; live calls never wait
        soonest = min((_cooldown.get(f"{p}/{m}", 0) for p, m in _candidates(tier, providers)), default=0) - time.time()
        pause = min(max(soonest, 5.0), 65.0)
        _wait_budget["left"] = _wait_budget.get("left", RATE_LIMIT_WAIT_S) - pause
        time.sleep(pause)
        return chat(messages, tier=tier, tools=tools, temperature=temperature, max_tokens=max_tokens,
                    json_mode=json_mode, providers=providers, reasoning=reasoning)
    _wait_budget.pop("left", None)
    raise RuntimeError("All LLM providers failed or none configured: " + " | ".join(errors or ["no API keys in .env"]))


RATE_LIMIT_WAIT_S = 0.0          # set >0 by offline harnesses
_wait_budget: dict[str, float] = {}


def chat_json(messages: list[dict], *, tier: str = "fast", max_tokens: int = 400, temperature: float = 0.0,
              providers: list[str] | None = None) -> tuple[dict, LLMResult]:
    res = chat(messages, tier=tier, json_mode=True, max_tokens=max_tokens, temperature=temperature, providers=providers)
    text = res.content.strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
    try:
        return json.loads(text), res
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1]), res
            except json.JSONDecodeError:
                pass
    return {}, res


def transcribe(audio: bytes, filename: str = "audio.webm", language: str | None = None, prompt: str | None = None,
               model: str | None = None) -> tuple[str, float]:
    """Groq Whisper transcription. Returns (text, latency_ms)."""
    clients = [c for c in (_client("groq"), _client("groq2")) if c is not None]
    if not clients:
        raise RuntimeError("GROQ_API_KEY required for ASR")
    client = clients[0]
    t0 = time.perf_counter()
    kwargs: dict[str, Any] = dict(model=model or config.ASR_MODEL, file=(filename, audio), temperature=0.0)
    if language:
        kwargs["language"] = language
    if prompt:
        kwargs["prompt"] = prompt[:800]
    for attempt in range(6):
        try:
            resp = client.audio.transcriptions.create(**kwargs)
            break
        except Exception as e:  # Whisper free tier: 20 requests/min -> other key, else short backoff
            if "429" not in str(e) or attempt == 5:
                raise
            if len(clients) > 1:
                client = clients[(clients.index(client) + 1) % len(clients)]
                continue
            m = re.search(r"try again in ([\d.]+)s", str(e))
            time.sleep(min(float(m.group(1)) + 0.5 if m else 3.0, 20.0))
    return resp.text.strip(), (time.perf_counter() - t0) * 1000


def embed(texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]] | None:
    """Gemini embeddings via the OpenAI-compatible endpoint; None if unavailable."""
    client = _client("gemini") or _client("gemini2")
    if client is None:
        return None
    if _client("gemini2") is not None and _cooldown.get("gemini/embed", 0) > time.time():
        client = _client("gemini2")
    out: list[list[float]] = []
    batch_size = 16 if len(texts) > 1 else 1      # free tier counts every input against a per-minute quota
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        for attempt in range(6):
            try:
                resp = client.embeddings.create(model=config.EMBED_MODEL_GEMINI, input=batch)
                out.extend(d.embedding for d in resp.data)
                break
            except Exception as e:
                if attempt == 5:
                    return None
                time.sleep(20 if "429" in str(e) else 2 ** attempt)
    return out
