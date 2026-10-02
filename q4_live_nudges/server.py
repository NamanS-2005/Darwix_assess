"""Live nudge dashboard: replays a call at real-time speed (audio plays in the browser in sync) and pushes transcript,
signals and nudges over a WebSocket as they are produced.

uvicorn q4_live_nudges.server:app --port 8001   ->  http://localhost:8001
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from q4_live_nudges.pipeline import HERE, LivePipeline, load_scenario  # noqa: E402

app = FastAPI(title="Live nudges")
CLIENTS: set[WebSocket] = set()
RUN: dict = {"task": None}


async def broadcast(kind: str, payload: dict):
    msg = json.dumps({"type": kind, "data": payload, "server_ts": time.time()}, default=str)
    dead = []
    for ws in CLIENTS:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        CLIENTS.discard(ws)


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(HERE / "static" / "dashboard.html")


@app.get("/api/scenarios")
def scenarios():
    import yaml
    out = []
    for p in sorted((HERE / "scenarios").glob("*.yaml")):
        sc = yaml.safe_load(p.read_text(encoding="utf-8"))
        out.append({"id": sc["id"], "title": sc["title"], "description": sc.get("description", "")})
    return out


@app.get("/audio/{sid}.wav")
def wav(sid: str):
    p = (HERE / "audio" / f"{sid}.wav").resolve()
    if (HERE / "audio").resolve() not in p.parents or not p.exists():
        return HTMLResponse(status_code=404)
    return FileResponse(p, media_type="audio/wav")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    CLIENTS.add(ws)
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            if msg.get("action") == "run":
                if RUN["task"] and not RUN["task"].done():
                    RUN["task"].cancel()
                wav, tl = load_scenario(msg["scenario"])
                p = LivePipeline(wav, tl, float(msg.get("speed", 1.0)), msg.get("asr", "groq"), bool(msg.get("llm", True)), deliver=broadcast)

                async def go(p=p):
                    res = await p.run()
                    out = HERE / "results" / "runs"
                    out.mkdir(parents=True, exist_ok=True)
                    (out / f"{msg['scenario']}__{p.asr.name}__dashboard.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
                RUN["task"] = asyncio.create_task(go())
    except WebSocketDisconnect:
        CLIENTS.discard(ws)
