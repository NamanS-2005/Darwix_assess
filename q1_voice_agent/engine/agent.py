"""Call session: LLM tool-calling loop + deterministic guards.

Turn flow:  user text -> LLM (with tools) -> tool execution (rules enforced in code) -> ... -> draft reply
            -> grounding guard (every number/amount/% in the reply must exist in KB results, CRM data, tool results,
               or the customer's own words) -> 1 regeneration on violation -> fixed safe fallback line if still ungrounded.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from datetime import date, timedelta

from common import llm

from .markets import Market, get_customer, load_market
from .numwords import words_to_digits
from .tools import TOOLS, execute

NUM_RE = re.compile(r"(?:₹|₱|Rp\.?\s?)?\d[\d,.]*\d|\d")


def _numbers(text: str) -> set[str]:
    out = set()
    text = re.sub(r"\b(\d{1,2})[.:](\d{2})\b(?!\d)", r"\1 \2", text)   # clock times: 14.00 / 14:00 -> 14 00
    for m in NUM_RE.finditer(text):
        raw = re.sub(r"^(₹|₱|Rp\.?\s?)", "", m.group(0))
        digits = raw.replace(",", "").replace(".", "")
        out.add(digits.lstrip("0") or "0")
        if "." in raw and raw.count(".") == 1 and len(raw.split(".")[1]) <= 2:  # decimals like 13.5 / 11.99
            out.add(raw.replace(",", ""))
    return out


def _similar(a: str, b: str) -> float:
    wa, wb = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    return len(wa & wb) / max(1, len(wa | wb))


class CallSession:
    def __init__(self, market_id: str = "in_lender", customer_id: str | None = None, phone: str | None = None, channel: str = "web"):
        self.market: Market = load_market(market_id)
        self.customer = get_customer(market_id, customer_id, phone)
        self.call_id = f"{market_id[:2]}-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
        self.channel = channel
        self.due_date: date = self.market.today() + timedelta(days=int(self.customer.get("due_in_days", 3)))
        self.state = {"verified": False, "verify_attempts": 0, "disposition": None, "ptp": None, "tickets": [],
                      "ended": False, "details_shared": False}
        self.history: list[dict] = []        # OpenAI-format messages (user/assistant/tool), excluding system
        self.transcript: list[dict] = []     # human-readable turns with metadata
        self.kb_log: list[dict] = []
        self.guard_log: list[dict] = []
        self.allowed_facts: list[str] = []
        self.metrics = {"kb_ms": [], "llm_ms": [], "turn_ms": [], "providers": {}}
        self.crm_summary: dict | None = None
        h = self.market.now().hour
        r = self.market.rules["calling_hours"]
        self.outside_calling_hours = not (r["start"] <= h < r["end"])

    def phrase(self, key: str) -> str:
        return self.market.phrase(key, first_name=self.customer["first_name"], honorific=self.customer.get("honorific", ""))

    # ------------------------------------------------------------ prompt
    def _rules_text(self) -> str:
        r = self.market.rules
        lines = [f"- Never: {x}." for x in r["never"]]
        lines.append(f"- Grace period used for promise-to-pay classification: {r['grace_days']} days after the due date (tools enforce this).")
        lines.append(f"- Escalate (escalate_to_human) when: {', '.join(r['escalation']['triggers'])}.")
        lines.append(f"- Verification: {' or '.join(r['verification']['methods'])}; max {r['verification']['max_attempts']} attempts.")
        return "\n".join(lines)

    def _state_text(self) -> str:
        c = self.customer
        st = {
            "customer_first_name": c["first_name"],
            "honorific": c.get("honorific", ""),
            "identity_verified": self.state["verified"],
            "verification_attempts_used": self.state["verify_attempts"],
            "promise_to_pay": self.state["ptp"],
            "current_disposition": self.state["disposition"],
            "open_tickets": [t["id"] for t in self.state["tickets"]],
        }
        s = json.dumps(st, ensure_ascii=False)
        s += f"\nCalendar for resolving dates (use ISO dates in tools): {self.market.calendar(14)}"
        if not self.state["verified"]:
            s += "\nIMPORTANT: identity NOT verified yet – do not mention amount, due date, product or account details."
        return s

    def system_prompt(self) -> str:
        m = self.market
        return m.prompt_template.format(agent_name=m.cfg["agent_name"], company=m.cfg["company"],
                                        today=m.fmt_date(m.today()), time_now=m.now().strftime("%H:%M"),
                                        script=m.script, rules=self._rules_text(), state=self._state_text())

    # ------------------------------------------------------------ turns
    def opening(self) -> dict:
        text = self.phrase("opening")
        self.history.append({"role": "assistant", "content": text})
        turn = {"role": "agent", "text": text, "ts": time.time(), "source": "fixed_script"}
        self.transcript.append(turn)
        return turn

    def respond(self, user_text: str, asr_meta: dict | None = None) -> dict:
        t0 = time.perf_counter()
        user_text = (user_text or "").strip()
        self.transcript.append({"role": "customer", "text": user_text, "ts": time.time(), **({"asr": asr_meta} if asr_meta else {})})
        if not user_text or len(re.sub(r"\W", "", user_text)) == 0:
            return self._emit(self.phrase("not_heard"), t0, source="fixed_fallback")
        if self.state["ended"]:
            return self._emit(self.phrase("closing"), t0, source="fixed_script")
        tp = self.market.cfg.get("third_party_regex")
        if tp and not self.state["verified"] and re.search(tp, user_text, re.I):
            self.state["third_party_suspected"] = True
        self.history.append({"role": "user", "content": self._normalize_asr(user_text)})

        tool_events = []
        try:
            draft, tool_events = self._llm_loop()
            reply, guard = self._guard(draft, user_text)
            if guard:
                self.guard_log.append(guard)
                if guard["action"] == "regenerate":
                    self.history.append({"role": "system", "content": guard["note"]})
                    draft2, more = self._llm_loop(allow_tools=True)
                    tool_events += more
                    self.history.pop(next(i for i in range(len(self.history) - 1, -1, -1) if self.history[i].get("content") == guard["note"]))
                    reply, guard2 = self._guard(draft2, user_text)
                    if guard2:
                        guard2["action"] = "fallback"
                        self.guard_log.append(guard2)
                        reply = self.phrase("third_party" if "third party" in guard2["reason"] else "unavailable")
            source = "llm"
        except Exception as e:  # provider outage etc. -> safe, scripted degradation
            reply, source = self.phrase("technical"), "fixed_fallback"
            tool_events.append({"error": str(e)[:300]})
            self.state["disposition"] = self.state["disposition"] or "INCOMPLETE"

        # Loop breaker: the same question asked again and again (seen with accented/regional speech) -> closed question, then human
        prev = [t["text"] for t in self.transcript if t["role"] == "agent"][-2:]
        if source == "llm" and prev and _similar(reply, prev[-1]) > 0.85:
            self.state["repeats"] = self.state.get("repeats", 0) + 1
            if self.state["repeats"] >= 2 and not any(t["type"] == "escalation" for t in self.state["tickets"]):
                from .tools import escalate_to_human
                escalate_to_human(self, "other", "Agent could not understand the customer after repeated attempts (possible accent/ASR issue).")
            reply = self.phrase("repeat_breaker")
            self.guard_log.append({"action": "inserted_fixed_line", "reason": "repeated question (loop breaker)", "draft": prev[-1][:160]})
        # Compliance disclosure enforced in code: a beyond-grace promise must be accompanied by the consequence notice
        if (self.state.get("ptp") or {}).get("class") == "PTP_BEYOND_GRACE" and not self.state.get("beyond_grace_notice_given"):
            rx = self.market.cfg.get("beyond_grace_regex")
            if rx and re.search(rx, reply, re.I):
                self.state["beyond_grace_notice_given"] = True
            elif source == "llm":
                reply = (self.phrase("beyond_grace_notice") + " " + reply).strip()
                self.state["beyond_grace_notice_given"] = True
                self.guard_log.append({"action": "inserted_fixed_line", "reason": "beyond-grace disclosure missing", "draft": reply[:160]})
        ae = self.market.cfg.get("anything_else_regex")
        if ae and re.search(ae, reply, re.I):
            self.state["offered_anything_else"] = True
        if self.state["ended"] and not re.search(self.market.cfg.get("closing_regex", "$^"), reply, re.I):
            reply = (reply.rstrip() + " " + self.phrase("closing")).strip()
        self.history.append({"role": "assistant", "content": reply})
        return self._emit(reply, t0, source=source, tools=tool_events, record_history=False)

    def _normalize_asr(self, text: str) -> str:
        """Deterministic ASR clean-up before the LLM sees the text:
        - number words -> digits in every market (Whisper writes Filipino dates as 'isang libo siyam na daan at walumpu't pito';
          LLMs mis-convert these, e.g. 1997 instead of 1987)
        - before verification, undo amount-style formatting of identifiers ('7730' -> '7,730', '4 4 2 1')."""
        text = words_to_digits(text)
        if self.state["verified"]:
            return text
        t = re.sub(r"(?<=\d)[,.](?=\d{3}\b)", "", text)
        t = re.sub(r"\b(\d)[\s-]+(\d)[\s-]+(\d)[\s-]+(\d)\b", r"\1\2\3\4", t)
        return t

    def _emit(self, text: str, t0: float, source: str, tools=None, record_history: bool = True) -> dict:
        if record_history and source != "llm":
            self.history.append({"role": "assistant", "content": text})
        ms = round((time.perf_counter() - t0) * 1000)
        self.metrics["turn_ms"].append(ms)
        turn = {"role": "agent", "text": text, "ts": time.time(), "source": source, "tools": tools or [],
                "agent_ms": ms, "state": {k: self.state[k] for k in ("verified", "disposition", "ended")}}
        self.transcript.append(turn)
        return turn

    def _llm_loop(self, allow_tools: bool = True, max_steps: int = 5) -> tuple[str, list[dict]]:
        events = []
        for _ in range(max_steps):
            msgs = [{"role": "system", "content": self.system_prompt()}] + self.history
            res = llm.chat(msgs, tier="agent", tools=TOOLS if allow_tools else None, temperature=0.2, max_tokens=300)
            self.metrics["llm_ms"].append(round(res.latency_ms))
            key = f"{res.provider}/{res.model}"
            self.metrics["providers"][key] = self.metrics["providers"].get(key, 0) + 1
            if not res.tool_calls:
                return (res.content or "").strip(), events
            self.history.append(res.raw_message)
            for tc in res.tool_calls:
                t1 = time.perf_counter()
                out = execute(self, tc["name"], tc["arguments"])
                self.history.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(out, ensure_ascii=False)})
                self.allowed_facts.append(json.dumps(out, ensure_ascii=False))
                events.append({"tool": tc["name"], "args": tc["arguments"], "result": out,
                               "ms": round((time.perf_counter() - t1) * 1000, 1), "model": f"{res.provider}/{res.model}"})
        # too many tool steps: ask once more without tools
        msgs = [{"role": "system", "content": self.system_prompt()}] + self.history
        res = llm.chat(msgs, tier="agent", temperature=0.2, max_tokens=200)
        return (res.content or "").strip(), events

    # ------------------------------------------------------------ grounding guard
    def _guard(self, draft: str, user_text: str) -> tuple[str, dict | None]:
        draft = re.sub(r"\[(?:kb_|\d)[^\]]*\]", "", draft).replace("*", "").strip()  # never speak citations / markdown
        draft = re.sub(r"\([^)]*\b(conversation|call|ends?|pause|silence|hangs? up|waiting|response|laughs|sighs)\b[^)]*\)", "", draft, flags=re.I)
        draft = re.sub(r"\[(tools? called|calling|tool)[^\]]*\]", "", draft, flags=re.I)   # leaked tool syntax
        draft = re.sub(r"```.*?```|\{[^{}]*\"\w+\"\s*:[^{}]*\}", "", draft, flags=re.S).strip()   # stage directions, leaked JSON / code
        if not draft:
            return self.phrase("not_heard"), None
        allowed_text = " ".join(self.allowed_facts) + " " + " ".join(t["text"] for t in self.transcript if t["role"] == "customer") \
            + " " + self.market.calendar(40) + " " + self._rules_text() + " " + self.market.cfg["phrases"]["opening"] + " " + self.market.cfg["company"]
        allowed = _numbers(allowed_text)
        # spoken dates: day numbers and years from the calendar are allowed
        found = _numbers(draft)
        unsupported = sorted(n for n in found if n not in allowed and not (n.isdigit() and int(n) <= 31 and self._is_date_context(draft, n)))
        leak = (not self.state["verified"]) and any(
            tok in draft for tok in [self.market.money(self.customer["emi_amount"]), self.customer["loan_account"][-4:]])
        claim = re.search(r"\b(i('ve| have)? (recorded|noted) (your|the) (payment|promise)|saya catat (rencana|janji)|sudah saya catat (rencana|janji)|"
                          r"nai-?record ko|na-?record ko|nai-?note ko)", draft, re.I)
        if claim and not self.state.get("ptp") and self.state["verified"]:
            return draft, {"action": "regenerate", "reason": "claimed an action that was not performed", "draft": draft,
                           "note": "SYSTEM CHECK: you said you recorded the payment plan but record_promise_to_pay was not called. "
                                   "Call record_promise_to_pay with the date and mode now (ask for a single date if unclear) before confirming."}
        nm = self.market.cfg.get("native_markers_regex")
        if nm and not leak:
            native_customer = len(re.findall(nm, user_text, re.I)) >= 2
            en = len(re.findall(r"\b(the|you|your|will|have|thank|and|is|are|please|to|of|we|our|for)\b", draft, re.I))
            if native_customer and not re.search(nm, draft, re.I) and en >= 3:
                return draft, {"action": "regenerate", "reason": "unexpected switch to English", "draft": draft,
                               "note": "SYSTEM CHECK: the customer is speaking their local language; your draft switched to full English. "
                                       "Rewrite the same content in the customer's language and register (keep finance terms the customer uses)."}
        if not leak and self.state.get("third_party_suspected") and not self.state["verified"]:
            at = self.market.cfg.get("account_terms_regex")
            if at and re.search(at, draft, re.I):
                return draft, {"action": "regenerate", "reason": "possible third party: account reference", "draft": draft,
                               "note": "SYSTEM CHECK: the person may NOT be the customer. Do not mention any loan, policy, payment, amount or "
                                       "account – not even that one exists. Only ask when the customer can be reached (call mark_wrong_party)."}
        if leak:
            return draft, {"action": "regenerate", "reason": "pre-verification disclosure", "draft": draft,
                           "note": "SYSTEM CHECK: your draft disclosed account details before verification. Rewrite without them and ask for verification."}
        if unsupported:
            return draft, {"action": "regenerate", "reason": "ungrounded numbers", "numbers": unsupported, "draft": draft,
                           "note": f"SYSTEM CHECK: your draft contains figures not supported by tool results or the customer's words: {unsupported}. "
                                   "Rewrite using only facts from tool results this call (call search_knowledge_base if needed). If unknown, say you don't have that information."}
        return draft, None

    @staticmethod
    def _is_date_context(text: str, n: str) -> bool:
        months = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|enero|pebrero|marso|abril|mayo|hunyo|hulyo|agosto|setyembre|oktubre|nobyembre|disyembre|januari|februari|maret|mei|juni|juli|agustus|oktober|desember|tanggal|petsa)"
        return bool(re.search(rf"(\b{n}(st|nd|rd|th)?\s+(of\s+)?{months})|({months}\w*\s+{n}\b)|(tanggal\s+{n}\b)", text, re.I))

    # ------------------------------------------------------------ export
    def export(self) -> dict:
        return {"call_id": self.call_id, "market": self.market.id, "channel": self.channel, "customer_id": self.customer["customer_id"],
                "due_date": self.due_date.isoformat(), "outside_calling_hours": self.outside_calling_hours,
                "state": self.state, "crm_summary": self.crm_summary, "kb_log": self.kb_log, "guard_log": self.guard_log,
                "metrics": self.metrics, "transcript": self.transcript}

    def transcript_markdown(self) -> str:
        L = [f"# Call {self.call_id}", f"- Market: {self.market.id} · Channel: {self.channel} · Customer: {self.customer['customer_id']} (mock CRM)",
             f"- Disposition: **{self.state['disposition']}** · Verified: {self.state['verified']} · Tickets: {[t['id'] for t in self.state['tickets']] or '-'}",
             f"- KB lookups: {len(self.kb_log)} · Guard interventions: {len(self.guard_log)}", ""]
        for t in self.transcript:
            who = "**Agent**" if t["role"] == "agent" else "**Customer**"
            extra = ""
            if t["role"] == "agent":
                cites = [c for ev in t.get("tools", []) if ev.get("tool") == "search_knowledge_base" for c in
                         [r["citation"] for r in ev["result"].get("results", [])]]
                tools = [f"{ev['tool']}({json.dumps(ev['args'], ensure_ascii=False)})" for ev in t.get("tools", []) if ev.get("tool")]
                if tools:
                    extra += f"\n  - tools: {'; '.join(tools)}"
                if cites:
                    extra += f"\n  - KB citations: {' '.join(cites)}"
                if t.get("source") and t["source"] != "llm":
                    extra += f"\n  - source: {t['source']}"
            if t["role"] == "customer" and t.get("asr"):
                extra += f"\n  - ASR: {t['asr']}"
            L.append(f"{who}: {t['text']}{extra}")
        if self.guard_log:
            L += ["", "## Grounding guard interventions"] + [f"- {g['reason']}: {g.get('numbers', '')} → {g['action']}  (draft: “{g['draft'][:160]}”)" for g in self.guard_log]
        return "\n".join(L)
