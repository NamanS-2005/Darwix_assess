"""Create (or update) Vapi assistants that use THIS server as a custom LLM, so phone/web calls on Vapi run the exact same
engine (KB grounding, tools, guards) as the built-in web call UI.

Prereqs: VAPI_API_KEY and PUBLIC_BASE_URL in .env (e.g. `cloudflared tunnel --url http://localhost:8000`).
python -m q1_voice_agent.vapi.create_assistants [--markets in_lender ph_life id_multifinance] [--customer C001]
Then: Vapi dashboard -> Assistants -> "Talk to Assistant" (web call), or attach a Vapi phone number to the assistant.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from common import config  # noqa: E402
from q1_voice_agent.engine.markets import load_market  # noqa: E402

API = "https://api.vapi.ai"
DEFAULT_CUSTOMER = {"in_lender": "C001", "ph_life": "P001", "id_multifinance": "D001"}


def assistant_body(market_id: str, customer_id: str) -> dict:
    m = load_market(market_id)
    v = m.cfg["vapi"]
    return {
        "name": f"darwix-{market_id}-{customer_id}",
        "firstMessageMode": "assistant-speaks-first-with-model-generated-message",   # opening comes from our engine (fixed disclosure line)
        "model": {"provider": "custom-llm", "url": f"{config.PUBLIC_BASE_URL}/vapi/{market_id}/{customer_id}", "model": "darwix-engine",
                  "messages": [{"role": "system", "content": "Engine-side prompt; see server."}]},
        "transcriber": v["transcriber"],
        "voice": v["voice"],
        "server": {"url": f"{config.PUBLIC_BASE_URL}/vapi/webhook"},
        "serverMessages": ["end-of-call-report"],
        "endCallPhrases": [m.phrase("closing").split(".")[0], *m.cfg.get("closing_phrases", [])],
        "artifactPlan": {"recordingEnabled": True},
        "backgroundDenoisingEnabled": True,
        "silenceTimeoutSeconds": 25,
        "maxDurationSeconds": 600,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", nargs="*", default=["in_lender", "ph_life", "id_multifinance"])
    ap.add_argument("--customer")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.dry_run and not (config.VAPI_API_KEY and config.PUBLIC_BASE_URL):
        sys.exit("Set VAPI_API_KEY and PUBLIC_BASE_URL in .env (or use --dry-run to print the payloads)")
    headers = {"Authorization": f"Bearer {config.VAPI_API_KEY}"}
    for mid in a.markets:
        body = assistant_body(mid, a.customer or DEFAULT_CUSTOMER[mid])
        if a.dry_run:
            print(json.dumps(body, indent=1, ensure_ascii=False))
            continue
        existing = httpx.get(f"{API}/assistant", headers=headers, timeout=20).json()
        match = next((x for x in existing if x.get("name") == body["name"]), None)
        if match:
            r = httpx.patch(f"{API}/assistant/{match['id']}", headers=headers, json=body, timeout=20)
        else:
            r = httpx.post(f"{API}/assistant", headers=headers, json=body, timeout=20)
        if r.status_code >= 300:
            print(f"{mid}: ERROR {r.status_code} {r.text[:500]}")
            continue
        print(f"{mid}: assistant {r.json()['id']}  ({body['name']}) -> {body['model']['url']}")


if __name__ == "__main__":
    main()
