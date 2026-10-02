"""Agent tools. Business rules are enforced HERE (deterministically), not left to the LLM.

The LLM decides *when* to call a tool; the tool decides *what is allowed* and returns an instruction the LLM must follow.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from common import config
from q2_knowledge_base.retriever import get_kb

from .numwords import spoken_digits, spoken_numbers, words_to_digits

if TYPE_CHECKING:
    from .agent import CallSession

CRM_DIR = Path(__file__).resolve().parents[1] / "crm"

TOOLS = [
    {"type": "function", "function": {
        "name": "verify_identity",
        "description": "Verify the customer before sharing ANY account detail. Pass date of birth (YYYY-MM-DD) and/or last 4 digits of the account/policy/contract number, exactly as the customer said them.",
        "parameters": {"type": "object", "properties": {
            "date_of_birth": {"type": "string", "description": "YYYY-MM-DD"},
            "account_last4": {"type": "string", "description": "4 digits"}}}}},
    {"type": "function", "function": {
        "name": "get_loan_details",
        "description": "Get the verified customer's product, amount due, due date and auto-debit status. Only works after verify_identity succeeded.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "search_knowledge_base",
        "description": "Search the company knowledge base for policies, charges, grace period, payment methods, credit bureau, date change, foreclosure, hardship options, fraud/verification, objections. Always use before answering such questions.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "the customer's question, rephrased as a short search query"}},
                       "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "record_promise_to_pay",
        "description": "Record when and how the customer will pay. Read back the date and mode after recording.",
        "parameters": {"type": "object", "properties": {
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "mode": {"type": "string", "enum": ["upi", "auto_debit", "net_banking", "branch", "app", "other"]}},
            "required": ["date", "mode"]}}},
    {"type": "function", "function": {
        "name": "confirm_auto_debit",
        "description": "Customer confirms they will keep sufficient balance for the active auto-debit on the due date.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "report_already_paid",
        "description": "Customer says they already paid this cycle. Capture what they said; missing fields are OK (pass empty).",
        "parameters": {"type": "object", "properties": {
            "payment_date": {"type": "string", "description": "YYYY-MM-DD or empty"},
            "mode": {"type": "string", "description": "upi / net_banking / branch / app / other / empty"},
            "reference": {"type": "string", "description": "UTR / receipt / reference number, or empty"}}}}},
    {"type": "function", "function": {
        "name": "schedule_callback",
        "description": "Schedule a callback ONLY after the customer has chosen or agreed to a specific date and time. If they have not, first ask for their preferred time.",
        "parameters": {"type": "object", "properties": {
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "time": {"type": "string", "description": "HH:MM 24h local time"},
            "reason": {"type": "string"}}, "required": ["date", "time", "reason"]}}},
    {"type": "function", "function": {
        "name": "escalate_to_human",
        "description": "Hand the case to a human specialist (customer asks for a person, hardship / cannot pay, dispute, complaint, distress).",
        "parameters": {"type": "object", "properties": {
            "reason": {"type": "string", "enum": ["human_request", "hardship", "dispute", "complaint", "distress", "other"]},
            "details": {"type": "string"}}, "required": ["reason", "details"]}}},
    {"type": "function", "function": {
        "name": "mark_wrong_party",
        "description": "The person on the phone is not the customer. Do not share any account information.",
        "parameters": {"type": "object", "properties": {"note": {"type": "string"}}}}},
    {"type": "function", "function": {
        "name": "end_call",
        "description": "End the call after the closing sentence. Writes the CRM summary.",
        "parameters": {"type": "object", "properties": {
            "disposition": {"type": "string", "enum": ["PTP_ON_TIME", "PTP_WITHIN_GRACE", "PTP_BEYOND_GRACE", "ALREADY_PAID_TRACE",
                                                        "AUTO_DEBIT_CONFIRMED", "CALLBACK_SCHEDULED", "ESCALATED", "HARDSHIP_REFERRED",
                                                        "REFUSED", "WRONG_PARTY", "VERIFICATION_FAILED", "INCOMPLETE"]},
            "summary": {"type": "string", "description": "one or two sentences for the CRM"}}, "required": ["disposition", "summary"]}}},
]


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s.strip()[:10])
    except ValueError:
        return None


def _append(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MONTHS_LOCAL = {"ene": 1, "peb": 2, "mar": 3, "abr": 4, "may": 5, "hun": 6, "hul": 7, "ago": 8, "set": 9, "okt": 10, "nob": 11, "dis": 12,
                "januari": 1, "februari": 2, "maret": 3, "mei": 5, "juni": 6, "juli": 7, "agustus": 8, "oktober": 10, "desember": 12}


def _customer_text(s: "CallSession") -> str:
    raw = " ".join(t["text"] for t in s.transcript if t["role"] == "customer")
    return (raw + " " + words_to_digits(raw)).lower()   # raw + number-normalised ("sarbu 178" -> "1178")


def _digits(x: str) -> str:
    return "".join(ch for ch in x if ch.isdigit())


def _heard_last4(s: "CallSession", value: str) -> bool:
    """Tool-argument hallucination guard: the 4 digits must occur in what the customer actually said."""
    v = _digits(value)[-4:]
    text = _customer_text(s)
    return len(v) == 4 and (v in _digits(text) or v in spoken_digits(text))


def _heard_dob(s: "CallSession", value: str) -> bool:
    d = _parse_date(value)
    if d is None:
        return False
    text = _customer_text(s)
    year_ok = str(d.year) in _digits(text) or str(d.year)[2:] in text or d.year in spoken_numbers(text)
    month_ok = MONTHS[d.month - 1] in text or any(k in text and m == d.month for k, m in MONTHS_LOCAL.items())         or f"/{d.month:02d}/" in text or f"/{d.month}/" in text or f"-{d.month:02d}-" in text
    return year_ok and month_ok


def execute(session: "CallSession", name: str, args: dict) -> dict:
    fn = HANDLERS.get(name)
    if fn is None:
        return {"error": f"unknown tool {name}"}
    try:
        return fn(session, **{k: v for k, v in (args or {}).items() if v is not None and k != "force"})   # force is server-only
    except TypeError as e:
        return {"error": f"bad arguments: {e}"}


# ---------------------------------------------------------------- handlers
def verify_identity(s: "CallSession", date_of_birth: str = "", account_last4: str = "") -> dict:
    if s.state["verified"]:
        return {"verified": True, "note": "already verified"}
    if s.state["verify_attempts"] >= s.market.rules["verification"]["max_attempts"]:
        return {"verified": False, "locked": True, "instruction": "Verification locked. Say the verification_failed line and end the call with VERIFICATION_FAILED."}
    if date_of_birth and not _heard_dob(s, date_of_birth):
        date_of_birth = ""          # not said by the customer -> ignore (does not consume an attempt)
    if account_last4 and not _heard_last4(s, account_last4):
        account_last4 = ""
    if not date_of_birth and not account_last4:
        return {"verified": False, "instruction": "The customer has not stated an identifier yet (never guess one). Ask for date of birth or last 4 digits."}
    dob = _parse_date(date_of_birth) if date_of_birth else None
    if dob and not (18 <= (s.market.today() - dob).days / 365.25 <= 100):
        # e.g. Whisper heard "1979" as "1779": an impossible age is an ASR error, not a wrong answer -> drop it, don't burn an attempt
        bad, date_of_birth = date_of_birth, ""
        if not account_last4:
            return {"verified": False, "implausible": True,
                    "instruction": f"The date heard ({bad}) is implausible – probably mis-heard. Read it back and ask the customer to repeat their birth year."}
    s.state["verify_attempts"] += 1
    c = s.customer
    ok = (date_of_birth and _parse_date(date_of_birth) == _parse_date(c["dob"])) or \
         (account_last4 and "".join(ch for ch in account_last4 if ch.isdigit())[-4:] == c["loan_account"][-4:])
    if ok:
        s.state["verified"] = True
        return {"verified": True, "instruction": "Thank the customer, then call get_loan_details and give the reminder."}
    left = s.market.rules["verification"]["max_attempts"] - s.state["verify_attempts"]
    if left <= 0:
        s.state["verification_failed"] = True
        return {"verified": False, "locked": True,
                "instruction": "Verification failed twice. Do NOT share any account information. Politely say you cannot verify, give the official helpline/app as the alternative, and call end_call with VERIFICATION_FAILED."}
    heard = date_of_birth or account_last4
    return {"verified": False, "attempts_left": left,
            "instruction": f"Did not match. Phone audio is error-prone: read back exactly what you heard ({heard}) and ask the customer to "
                           "confirm or correct it, or offer the other identifier. Never say which part is wrong."}


def get_loan_details(s: "CallSession") -> dict:
    if not s.state["verified"]:
        return {"error": "NOT_VERIFIED", "instruction": "Verify identity first. Do not share any details."}
    c, m = s.customer, s.market
    due = s.due_date
    out = {"product": c["product"], "amount_due": m.money(c["emi_amount"]), "due_date": due.isoformat(),
           "due_date_spoken": m.fmt_date(due), "days_until_due": (due - m.today()).days,
           "auto_debit_active": c.get("auto_debit_active", False), "auto_debit_bank": c.get("bank"),
           "grace_period_end": (due + timedelta(days=m.rules["grace_days"])).isoformat(),
           "payment_history": c.get("payment_history")}
    for k in ("tenor", "payment_mode"):
        if c.get(k):
            out[k] = c[k]
    s.state["details_shared"] = True
    s.allowed_facts.append(json.dumps(out, ensure_ascii=False))
    return out


def search_knowledge_base(s: "CallSession", query: str) -> dict:
    t0 = time.perf_counter()
    kb = get_kb()
    hits, meta = kb.search(query, market=s.market.cfg["kb_market"], k=3)
    if not hits:
        # Multi-query fallback: the LLM often rewrites a Taglish/Bahasa question into English; the customer's own words
        # match the localized KB better (e.g. "parang savings daw" objection).
        last = next((t["text"] for t in reversed(s.transcript) if t["role"] == "customer"), "")
        if last and last.strip().lower() != query.strip().lower():
            hits, meta = kb.search(last, market=s.market.cfg["kb_market"], k=3)
            meta["query_used"] = "customer_utterance"
    s.metrics["kb_ms"].append(round((time.perf_counter() - t0) * 1000, 1))
    if not hits:
        s.kb_log.append({"query": query, "results": [], "abstained": True})
        return {"results": [], "instruction": "NO_RELEVANT_INFORMATION in the knowledge base. Do not guess. Say you don't have that information and offer a callback."}
    res = [{"citation": h.citation.split(" | ")[0].strip("["), "title": h.record["title"], "content": h.record["content"][:500]} for h in hits]
    s.kb_log.append({"query": query, "results": [h.citation for h in hits], "abstained": False, "mode": meta.get("mode")})
    s.allowed_facts.extend(h.record["content"] for h in hits)
    return {"results": res, "instruction": "Answer ONLY from these results, briefly. If they don't answer the question, say you don't have that information."}


PAID_CLAIM = re.compile(r"already paid|i (have )?paid|i made the payment|sudah (saya )?(bayar|transfer)|udah (saya )?(bayar|transfer)|"
                        r"nakabayad na|bayad na po|nagbayad na", re.I)


def record_promise_to_pay(s: "CallSession", date: str, mode: str) -> dict:
    if not s.state["verified"]:
        return {"error": "NOT_VERIFIED"}
    last = next((t["text"] for t in reversed(s.transcript) if t["role"] == "customer"), "")
    if PAID_CLAIM.search(last):
        return {"ok": False, "instruction": "The customer says they ALREADY PAID. Do not record a promise to pay. Use report_already_paid "
                                            "with the past payment date (see calendar), mode and reference if given."}
    m, d = s.market, _parse_date(date)
    today = m.today()
    if d is None:
        return {"ok": False, "instruction": "Could not understand the date. Ask the customer for a specific date."}
    if d < today:
        return {"ok": False, "instruction": f"{d.isoformat()} is in the past. If they already paid, use report_already_paid; otherwise ask for a future date."}
    if (d - today).days > m.rules["promise_to_pay"]["max_days_ahead"]:
        return {"ok": False, "instruction": "Date is too far away. Explain charges may apply after the grace period and offer a callback from the assistance team (escalate_to_human, reason hardship) instead."}
    due, grace = s.due_date, timedelta(days=m.rules["grace_days"])
    if d <= due:
        cls = "PTP_ON_TIME"
        instr = "Confirm the date and mode back to the customer and thank them."
    elif d <= due + grace:
        cls = "PTP_WITHIN_GRACE"
        instr = "Allowed (within grace period). Confirm date and mode. You may say paying by the due date is best; do not invent charges."
    else:
        cls = "PTP_BEYOND_GRACE"
        instr = ("Date is AFTER the grace period. You MUST tell the customer that late payment charges and credit bureau reporting may apply "
                 "(use search_knowledge_base for exact charge if they ask), and that the case is noted for the Customer Assistance team. "
                 "Ask if an earlier date is possible; if not, confirm the date.")
    s.state["ptp"] = {"date": d.isoformat(), "mode": mode, "class": cls}
    s.state["disposition"] = cls
    return {"ok": True, "classification": cls, "date_spoken": m.fmt_date(d), "mode": mode, "instruction": instr}


def confirm_auto_debit(s: "CallSession") -> dict:
    if not s.state["verified"]:
        return {"error": "NOT_VERIFIED"}
    if not s.customer.get("auto_debit_active"):
        return {"ok": False, "instruction": "Auto-debit is NOT active for this account. Ask how they will pay instead."}
    s.state["disposition"] = "AUTO_DEBIT_CONFIRMED"
    return {"ok": True, "instruction": "Thank them; remind to keep sufficient balance one day before the due date."}


def report_already_paid(s: "CallSession", payment_date: str = "", mode: str = "", reference: str = "") -> dict:
    if not s.state["verified"]:
        return {"error": "NOT_VERIFIED"}
    m, d = s.market, _parse_date(payment_date)
    if reference and _digits(reference) and _digits(reference) not in _digits(_customer_text(s)):
        reference = ""              # never record a reference number the customer didn't say
    if s.customer.get("payment_received_this_cycle"):
        s.state["disposition"] = "ALREADY_PAID_TRACE"
        return {"status": "payment_found", "instruction": "Our records show the payment. Thank the customer and close."}
    missing = [k for k, v in {"payment_date": payment_date, "mode": mode}.items() if not v]
    if d and d > m.today():
        return {"status": "conflict", "instruction": "The payment date given is in the future, which conflicts with 'already paid'. Politely clarify: has the payment been made, or is it planned?"}
    if missing:
        return {"status": "incomplete", "missing": missing, "instruction": f"Ask for: {', '.join(missing)}. Also ask for the UTR or receipt number if available."}
    ticket = "TRC-" + uuid.uuid4().hex[:6].upper()
    s.state["disposition"] = "ALREADY_PAID_TRACE"
    s.state["tickets"].append({"type": "payment_trace", "id": ticket, "payment_date": payment_date, "mode": mode, "reference": reference or None})
    note = "" if reference else " No reference number yet: ask them to keep the UTR/receipt ready; they can share it with customer care."
    return {"status": "trace_created", "ticket": ticket, "record_shows_payment": False,
            "instruction": "Our records do not show the payment yet. Do NOT argue. Explain it can take up to 2 working days to reflect (per KB), "
                           f"that a payment trace request {ticket} is raised, and no late fee applies if it was paid on time.{note}"}


def schedule_callback(s: "CallSession", date: str, time: str, reason: str) -> dict:
    m = s.market
    d = _parse_date(date)
    try:
        hh, mm = [int(x) for x in time.split(":")[:2]]
    except Exception:
        return {"ok": False, "instruction": "Ask for a specific time."}
    if d is None:
        return {"ok": False, "instruction": "Ask for a specific date."}
    # relative-day check: "tomorrow / bukas / besok" must resolve to today + 1 (LLMs get this wrong surprisingly often)
    last = next((t["text"] for t in reversed(s.transcript) if t["role"] == "customer"), "").lower()
    rel = {1: r"\b(tomorrow|bukas|besok)\b", 0: r"\b(today|ngayong araw|hari ini)\b", 2: r"\b(day after tomorrow|sa makalawa|lusa)\b"}
    explicit = re.search(r"\b\d{1,2}\b.{0,12}(jan|feb|mar|apr|mei|may|jun|jul|ag|aug|sep|okt|oct|nov|des|dec|enero|pebrero|marso|abril|mayo|hunyo|hulyo|agosto|setyembre|oktubre|nobyembre|disyembre)", last)
    for offset, rx in rel.items():
        if explicit:
            break                    # "nanti pas tanggal 14 Oktober": an explicit date wins over relative words
        if re.search(rx, last) and not (offset == 1 and re.search(rel[2], last)):
            expected = m.today() + timedelta(days=offset)
            if d != expected:
                return {"ok": False, "instruction": f"The customer said a relative day; that is {expected.isoformat()} ({m.fmt_date(expected)}), "
                                                    f"not {d.isoformat()}. Call schedule_callback again with {expected.isoformat()}."}
            break
    start, end = m.rules["calling_hours"]["start"], m.rules["calling_hours"]["end"]
    when = datetime(d.year, d.month, d.day, hh, mm, tzinfo=m.tz)
    if when < m.now():
        return {"ok": False, "instruction": "That time has passed. Ask for a later time."}
    if not (start <= hh < end) or d.weekday() not in m.cfg.get("callback_days", range(7)):
        return {"ok": False, "instruction": f"Callbacks are possible only {start}:00–{end}:00, Monday to Saturday. Ask for a time in that window."}
    cb = {"type": "callback", "id": "CB-" + uuid.uuid4().hex[:6].upper(), "at": when.isoformat(), "reason": reason}
    s.state["tickets"].append(cb)
    if s.state["disposition"] in (None, "INCOMPLETE"):
        s.state["disposition"] = "CALLBACK_SCHEDULED"
    return {"ok": True, "callback_id": cb["id"], "spoken": f"{m.fmt_date(d)} {time}", "instruction": "Confirm the callback date and time."}


def escalate_to_human(s: "CallSession", reason: str, details: str) -> dict:
    ticket = {"type": "escalation", "id": "ESC-" + uuid.uuid4().hex[:6].upper(), "reason": reason, "details": details,
              "market": s.market.id, "customer_id": s.customer["customer_id"], "call_id": s.call_id,
              "created_at": datetime.now().isoformat(timespec="seconds"), "sla": "callback within 1 working day"}
    s.state["tickets"].append(ticket)
    s.state["disposition"] = "HARDSHIP_REFERRED" if reason == "hardship" else "ESCALATED"
    _append(CRM_DIR / "escalations.jsonl", ticket)
    delivered = "logged"
    if config.ESCALATION_WEBHOOK_URL:
        try:
            r = httpx.post(config.ESCALATION_WEBHOOK_URL, json=ticket, timeout=3)
            delivered = f"webhook {r.status_code}"
        except Exception as e:
            delivered = f"webhook failed ({type(e).__name__}), logged locally"
    ticket["delivery"] = delivered
    return {"ok": True, "ticket": ticket["id"],
            "instruction": "Tell the customer a specialist from our team will call back within 1 working day (do not promise any outcome). Ask if they prefer a time; if yes use schedule_callback."}


def mark_wrong_party(s: "CallSession", note: str = "") -> dict:
    if not s.state.get("third_party_suspected") and not s.state.get("identity_reconfirm_asked"):
        # a mis-heard name ("Sir Jose" -> "Sergio") is not a wrong party: confirm once before hanging up on the customer
        s.state["identity_reconfirm_asked"] = True
        return {"ok": False, "instruction": f"The name may have been mis-heard by speech recognition. Ask once more, politely, "
                                            f"whether you are speaking with {s.customer['first_name']} (use their honorific)."}
    if s.state["verify_attempts"] > 0 and not s.state.get("third_party_suspected"):
        return {"ok": False, "instruction": "The person said they ARE the customer; failed or unclear verification is not a wrong party. "
                                            "Read back what you heard, or offer a callback (schedule_callback)."}
    s.state["disposition"] = "WRONG_PARTY"
    s.state["wrong_party"] = True
    return {"ok": True, "instruction": "Do not reveal anything about the account or why you are calling beyond the company name. Thank them and end the call (WRONG_PARTY)."}


def end_call(s: "CallSession", disposition: str, summary: str, force: bool = False) -> dict:
    # don't hang up on the customer: offer "anything else?" first unless they are closing or the call can't continue
    last = next((t["text"] for t in reversed(s.transcript) if t["role"] == "customer"), "")
    bye = re.search(s.market.cfg.get("customer_bye_regex", "$^"), last, re.I)
    terminal = s.state.get("verification_failed") or s.state.get("wrong_party")
    if not (force or bye or terminal or s.state.get("offered_anything_else")):   # force = caller/user hung up
        s.state["offered_anything_else"] = True   # ask once; next end_call is allowed
        return {"ok": False, "instruction": "Before ending, briefly confirm the next step and ask if there is anything else you can help with. Do not say goodbye yet."}
    # deterministic disposition beats the LLM's label when a tool already classified the outcome
    final = s.state["disposition"] or disposition
    # Outcomes that need tool evidence: never trust the LLM's label alone (it can claim things that never happened)
    evidence = {"VERIFICATION_FAILED": s.state.get("verification_failed"), "WRONG_PARTY": s.state.get("wrong_party"),
                "AUTO_DEBIT_CONFIRMED": s.state["disposition"] == "AUTO_DEBIT_CONFIRMED",
                "ALREADY_PAID_TRACE": any(t["type"] == "payment_trace" for t in s.state["tickets"]) or s.state["disposition"] == "ALREADY_PAID_TRACE",
                "ESCALATED": any(t["type"] == "escalation" for t in s.state["tickets"]),
                "HARDSHIP_REFERRED": any(t["type"] == "escalation" for t in s.state["tickets"]),
                "CALLBACK_SCHEDULED": any(t["type"] == "callback" for t in s.state["tickets"])}
    if final in evidence and not evidence[final]:
        final = "INCOMPLETE"
    if final.startswith("PTP") and not s.state.get("ptp"):
        final = "INCOMPLETE"
    if s.state.get("verification_failed"):
        final = "VERIFICATION_FAILED"
    s.state["disposition"] = final
    s.state["ended"] = True
    record = {"call_id": s.call_id, "market": s.market.id, "customer_id": s.customer["customer_id"], "disposition": final,
              "llm_disposition": disposition, "summary": summary, "ptp": s.state.get("ptp"), "tickets": s.state["tickets"],
              "verified": s.state["verified"], "kb_queries": len(s.kb_log), "ended_at": datetime.now().isoformat(timespec="seconds")}
    s.crm_summary = record
    _append(CRM_DIR / "outcomes.jsonl", record)
    return {"ok": True, "instruction": "Say the closing line now (one sentence summary of next step + closing). Do not ask further questions."}


HANDLERS = {f.__name__: f for f in [verify_identity, get_loan_details, search_knowledge_base, record_promise_to_pay, confirm_auto_debit,
                                     report_already_paid, schedule_callback, escalate_to_human, mark_wrong_party, end_call]}
