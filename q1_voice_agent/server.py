"""Voice agent server (Q1 + Q3 markets).

Channels
  1. Web calling interface  : GET /            (browser mic -> Groq Whisper -> engine -> edge-tts neural voice)
  2. Vapi (phone / web)     : POST /vapi/{market}/{customer_id}/chat/completions   (Vapi "custom-llm" -> same engine)
                              POST /vapi/webhook  (end-of-call reports, recordings)
  3. KB retrieval interface : GET /kb, /api/kb/search, /api/kb/answer

Run:  uvicorn q1_voice_agent.server:app --port 8000
"""
from __future__ import annotations

import asyncio
import base64
import json
import sys
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import audio, llm  # noqa: E402
from q1_voice_agent.engine.agent import CallSession  # noqa: E402
from q1_voice_agent.engine.markets import MARKET_DIRS, load_customers, load_market  # noqa: E402
from q2_knowledge_base.answer import grounded_answer  # noqa: E402
from q2_knowledge_base.retriever import get_kb  # noqa: E402

HERE = Path(__file__).resolve().parent
REC_DIR = HERE / "recordings"
app = FastAPI(title="Darwix voice agent")

SESSIONS: dict[str, CallSession] = {}
SEGMENTS: dict[str, list[tuple[str, np.ndarray]]] = {}   # call_id -> [(role, pcm16k)]
VAPI: dict[str, dict] = {}                                # vapi call id -> {"session", "user_count", "last"}


# ---------------------------------------------------------------- helpers
async def speak(session: CallSession, text: str) -> tuple[str, float]:
    t0 = time.perf_counter()
    tts = session.market.cfg["tts"]
    try:
        mp3 = await audio.tts_mp3_async(text, tts["voice"], tts.get("rate", "+0%"))
    except Exception:
        return "", 0.0
    ms = (time.perf_counter() - t0) * 1000
    try:
        SEGMENTS.setdefault(session.call_id, []).append(("agent", audio.decode_to_pcm(mp3)))
    except Exception:
        pass
    return base64.b64encode(mp3).decode(), ms


def asr_for(session: CallSession, data: bytes, filename: str) -> tuple[str, float]:
    a = session.market.cfg["asr"]
    return llm.transcribe(data, filename=filename, language=a.get("language"), prompt=a.get("prompt"), model=a.get("model"))


def save_call(session: CallSession) -> dict:
    d = REC_DIR / session.call_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "call.json").write_text(json.dumps(session.export(), indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (d / "transcript.md").write_text(session.transcript_markdown(), encoding="utf-8")
    files = {"transcript": str(d / "transcript.md"), "json": str(d / "call.json")}
    segs = SEGMENTS.get(session.call_id, [])
    if segs:
        gap = audio.silence(0.35)
        mono = np.concatenate([np.concatenate([pcm, gap]) for _, pcm in segs])
        audio.write_wav(d / "recording.wav", mono)
        audio.wav_to_mp3(d / "recording.wav", d / "recording.mp3")
        (d / "recording.wav").unlink()
        # stereo: agent left / customer right, time-aligned -> reusable as Q4 input (channel = speaker)
        L, R = [], []
        for role, pcm in segs:
            z = np.zeros_like(pcm)
            L += [pcm if role == "agent" else z, gap]
            R += [pcm if role == "customer" else z, gap]
        stereo = np.stack([np.concatenate(L), np.concatenate(R)], axis=1)
        audio.write_wav(d / "recording_stereo.wav", stereo)
        files.update({"recording": str(d / "recording.mp3"), "stereo": str(d / "recording_stereo.wav")})
    return files


def turn_payload(session: CallSession, turn: dict, audio_b64: str, tts_ms: float, user_text: str = "", asr_ms: float | None = None) -> dict:
    cites = [r["citation"] for ev in turn.get("tools", []) if ev.get("tool") == "search_knowledge_base" for r in ev["result"].get("results", [])]
    return {"call_id": session.call_id, "user_text": user_text, "reply": turn["text"], "audio_b64": audio_b64,
            "ended": session.state["ended"], "state": {**session.state, "tickets": [t["id"] for t in session.state["tickets"]]},
            "tools": [{"tool": e.get("tool"), "args": e.get("args"), "result": e.get("result")} for e in turn.get("tools", []) if e.get("tool")],
            "citations": cites, "guard": session.guard_log[-1] if session.guard_log and session.guard_log[-1].get("draft") and turn.get("source") == "llm" else None,
            "latency_ms": {"asr": round(asr_ms) if asr_ms is not None else None, "agent": turn.get("agent_ms"), "tts": round(tts_ms)}}


# ---------------------------------------------------------------- web calling interface
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(HERE / "static" / "call.html")


@app.get("/kb", response_class=HTMLResponse)
def kb_page():
    return FileResponse(HERE / "static" / "kb.html")


@app.get("/api/markets")
def markets():
    out = []
    for mid in MARKET_DIRS:
        m = load_market(mid)
        out.append({"id": mid, "company": m.cfg["company"], "agent": m.cfg["agent_name"], "locale": m.cfg["locale"],
                    "customers": [{"id": c["customer_id"], "name": c["name"], "product": c["product"], "hint": c.get("scenario_hint", "")}
                                  for c in load_customers(mid)]})
    return {"markets": out, "llm": llm.available_providers(), "kb_version": get_kb().kb_version, "dense": get_kb().dense_enabled}


class StartReq(BaseModel):
    market: str = "in_lender"
    customer_id: str | None = None


@app.post("/api/calls")
async def start_call(req: StartReq):
    s = CallSession(req.market, req.customer_id, channel="web")
    SESSIONS[s.call_id] = s
    turn = s.opening()
    b64, ms = await speak(s, turn["text"])
    return {**turn_payload(s, turn, b64, ms), "outside_calling_hours": s.outside_calling_hours, "due_date": s.due_date.isoformat()}


def _get(call_id: str) -> CallSession:
    if call_id not in SESSIONS:
        raise HTTPException(404, "unknown call")
    return SESSIONS[call_id]


@app.post("/api/calls/{call_id}/turn")
async def voice_turn(call_id: str, file: UploadFile = File(...)):
    s = _get(call_id)
    data = await file.read()
    try:
        SEGMENTS.setdefault(s.call_id, []).append(("customer", audio.decode_to_pcm(data)))
    except Exception:
        pass
    try:
        text, asr_ms = await asyncio.to_thread(asr_for, s, data, file.filename or "speech.webm")
    except Exception as e:
        text, asr_ms = "", 0.0
        s.transcript.append({"role": "system", "text": f"ASR error: {e}", "ts": time.time()})
    turn = await asyncio.to_thread(s.respond, text, {"provider": "groq", "model": llm.config.ASR_MODEL, "ms": round(asr_ms)})
    b64, ms = await speak(s, turn["text"])
    return turn_payload(s, turn, b64, ms, user_text=text, asr_ms=asr_ms)


class TextReq(BaseModel):
    text: str
    speak: bool = True


@app.post("/api/calls/{call_id}/text")
async def text_turn(call_id: str, req: TextReq):
    s = _get(call_id)
    turn = await asyncio.to_thread(s.respond, req.text)
    b64, ms = (await speak(s, turn["text"])) if req.speak else ("", 0.0)
    return turn_payload(s, turn, b64, ms, user_text=req.text)


@app.post("/api/calls/{call_id}/end")
def end(call_id: str):
    s = _get(call_id)
    if not s.crm_summary:
        from q1_voice_agent.engine.tools import end_call
        end_call(s, s.state["disposition"] or "INCOMPLETE", "Call ended by user before the agent closed it.", force=True)
    files = save_call(s)
    return {"call_id": call_id, "crm_summary": s.crm_summary, "files": files, "metrics": s.metrics}


@app.get("/api/calls/{call_id}")
def get_call(call_id: str):
    return JSONResponse(json.loads(json.dumps(_get(call_id).export(), default=str)))


@app.get("/recordings/{call_id}/{name}")
def recording(call_id: str, name: str):
    p = (REC_DIR / call_id / name).resolve()
    if REC_DIR.resolve() not in p.parents or not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


# ---------------------------------------------------------------- KB interface
@app.get("/api/kb/search")
def kb_search(q: str, market: str = "in_lender", k: int = 3):
    hits, meta = get_kb().search(q, market=market, k=k)
    return {"meta": meta, "hits": [h.to_dict() for h in hits]}


@app.get("/api/kb/answer")
def kb_answer(q: str, market: str = "in_lender"):
    return grounded_answer(q, market)


# ---------------------------------------------------------------- Vapi custom LLM
def _sse(text: str, model: str = "darwix-engine"):
    base = {"id": f"chatcmpl-{int(time.time() * 1000)}", "object": "chat.completion.chunk", "created": int(time.time()), "model": model}
    yield "data: " + json.dumps({**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": text}, "finish_reason": None}]}) + "\n\n"
    yield "data: " + json.dumps({**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}) + "\n\n"
    yield "data: [DONE]\n\n"


@app.post("/vapi/{market}/{customer_id}/chat/completions")
async def vapi_llm(market: str, customer_id: str, request: Request):
    body = await request.json()
    call = body.get("call") or {}
    vid = call.get("id") or "vapi-unknown"
    entry = VAPI.get(vid)
    if entry is None:
        phone = (call.get("customer") or {}).get("number")
        s = CallSession(market, customer_id=None if customer_id == "auto" else customer_id, phone=phone, channel="vapi")
        SESSIONS[s.call_id] = s
        entry = VAPI[vid] = {"session": s, "user_count": 0, "last": None}
    s: CallSession = entry["session"]
    users = [m for m in body.get("messages", []) if m.get("role") == "user"]
    if not s.transcript:
        reply = s.opening()["text"]
    elif len(users) > entry["user_count"]:
        entry["user_count"] = len(users)
        content = users[-1].get("content")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        reply = (await asyncio.to_thread(s.respond, content or ""))["text"]
    else:  # Vapi retry / interruption replay -> do not double-process
        reply = entry["last"] or s.phrase("not_heard")
    entry["last"] = reply
    if body.get("stream", True):
        return StreamingResponse(_sse(reply), media_type="text/event-stream")
    return {"id": "chatcmpl-x", "object": "chat.completion", "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}]}


@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    body = await request.json()
    msg = body.get("message", {})
    if msg.get("type") == "end-of-call-report":
        vid = (msg.get("call") or {}).get("id", "unknown")
        d = REC_DIR / "vapi"
        d.mkdir(parents=True, exist_ok=True)
        entry = VAPI.get(vid)
        report = {"vapi_call_id": vid, "recordingUrl": (msg.get("artifact") or {}).get("recordingUrl") or msg.get("recordingUrl"),
                  "transcript": (msg.get("artifact") or {}).get("transcript") or msg.get("transcript"),
                  "endedReason": msg.get("endedReason"), "engine_call_id": entry["session"].call_id if entry else None}
        (d / f"{vid}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
        if entry:
            save_call(entry["session"])
    return {"ok": True}
