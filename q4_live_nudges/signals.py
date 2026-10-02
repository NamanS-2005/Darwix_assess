"""Signal extraction: two tiers.

Tier 1 – rules (sub-millisecond): regex lexicons + call-state checks. High-precision compliance rules can trigger a
         nudge on their own (fast path). Low-precision cues (cross-sell, frustration...) only nominate candidates.
Tier 2 – LLM (Groq llama-3.1-8b-instant, JSON mode) on a rolling window: confirms/rejects candidates, catches
         paraphrases, scores sentiment/frustration and tracks intent/topic shifts.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from common import llm


@dataclass
class Utterance:
    uid: int
    speaker: str
    text: str
    start_t: float
    end_t: float
    end_wall: float
    endpoint_wall: float
    asr_wall: float
    asr_ms: float
    asr_conf: float


@dataclass
class Signal:
    type: str
    confidence: float
    source: str                  # rule | state | llm | rule+llm
    evidence: str
    topic: str
    uid: int
    detected_wall: float
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------- Tier 1 lexicons
R = lambda p: re.compile(p, re.I)
CUSTOMER_RULES = [
    ("cross_sell", 0.6, R(r"\b(admission|college fees?|school fees?|tuition|wedding|marriage|renovat\w*|second (car|bike|scooter|two[- ]wheeler|vehicle)|"
                         r"buy(ing)? (a |an |another |new )?(car|bike|scooter|two[- ]wheeler|vehicle|house|flat)|expand\w* (my |the )?(business|shop))\b"),
     "new_financing_need"),
    ("payment_difficulty", 0.7, R(r"\b(lost (my )?job|laid off|no salary|salary (is |has )?(late|delayed|not (been )?credited)|medical emergency|hospital\w*|"
                                  r"can'?t pay|cannot pay|unable to pay|don'?t know how (i will|i'll|i'd) pay|payment is stuck|business is (down|slow))\b"), "affordability"),
    ("already_paid_dispute", 0.75, R(r"\b(already paid|i (have )?paid (it|the emi)|made the payment|paid (it )?(two|2|a few|three|3) days)\b"), "payment_status"),
    ("frustration_rising", 0.55, R(r"\b(third time|again and again|ridiculous|fed up|stop calling|harass\w*|useless|nonsense|not fair|how many times|"
                                   r"don'?t tell me to calm|i am not paying twice|irritat\w*)\b"), "frustration"),
    ("escalation_request", 0.8, R(r"\b(your manager|a manager|supervisor|senior (person|officer)|real person|talk to (a )?human|file a complaint|raise a complaint)\b"), "escalation"),
    ("callback_needed", 0.65, R(r"\b(call (me )?(back|later)|i'?m (driving|busy|in a meeting)|can'?t talk|not a good time)\b"), "callback"),
]
CUSTOMER_NEGATORS = {
    "cross_sell": R(r"\b(last year|already (bought|paid)|paid (it )?off|took a .{0,20}loan)\b"),
}
AGENT_RULES = [
    ("risky_statement", 0.85, R(r"\b(legal action|police|arrest\w*|recovery (team|agent)s? will (come|visit)|come to your (office|home|house)|"
                                r"ruin your (cibil|credit)|blacklist\w*|seize|borrow (from|money from) (someone|friends|relatives)|can you borrow)\b"), "conduct"),
    ("unauthorized_waiver", 0.85, R(r"\b(i (can|will) waive|we (can|will) waive|waive (the|your) (late )?(fee|charge)|remove the (late )?(fee|charge)|no (late )?(fee|charge) for you)\b"), "waiver"),
]
AGENT_NEGATORS = {"unauthorized_waiver": R(r"\b(raise|submit|log) (a )?waiver request|cannot waive|can'?t waive|not able to waive\b")}

DISCLOSURE_RE = R(r"\brecord(ed|ing)?\b")
VERIFY_ASK_RE = R(r"\b(date of birth|last (four|4) digits|verif\w*)\b")
LOAN_DETAIL_RE = R(r"(\bemi\b.{0,50}(rupees|₹|\d))|((\d[\d,]*|thousand|hundred|lakh)\s*(rupees|rs\b))|(₹\s?\d)")


class CallState:
    def __init__(self):
        self.utts: list[Utterance] = []
        self.disclosed = False
        self.verify_asked = False
        self.verified = False
        self.agent_turns = 0
        self.flags: set[str] = set()
        self.intent: str | None = None
        self.frustration: list[float] = []

    def add(self, u: Utterance):
        self.utts.append(u)


def rule_signals(u: Utterance, st: CallState) -> list[Signal]:
    now = time.perf_counter()
    out: list[Signal] = []
    if u.speaker == "customer":
        if st.verify_asked:
            st.verified = True
        for typ, conf, rx, topic in CUSTOMER_RULES:
            m = rx.search(u.text)
            if m:
                neg = CUSTOMER_NEGATORS.get(typ)
                c = conf * (0.4 if neg and neg.search(u.text) else 1.0)
                out.append(Signal(typ, c, "rule", m.group(0), topic, u.uid, now))
    else:
        st.agent_turns += 1
        if DISCLOSURE_RE.search(u.text):
            st.disclosed = True
        if VERIFY_ASK_RE.search(u.text):
            st.verify_asked = True
        talks_loan = bool(LOAN_DETAIL_RE.search(u.text))
        if not st.disclosed and "disclosure_missing" not in st.flags and (talks_loan or st.agent_turns >= 3):
            st.flags.add("disclosure_missing")
            out.append(Signal("disclosure_missing", 0.9, "state", "no recording disclosure before loan discussion", "disclosure", u.uid, now))
        if talks_loan and not st.verified and "verification_skipped" not in st.flags:
            st.flags.add("verification_skipped")
            out.append(Signal("verification_skipped", 0.9, "state", u.text[:80], "verification", u.uid, now))
        for typ, conf, rx, topic in AGENT_RULES:
            m = rx.search(u.text)
            if m:
                neg = AGENT_NEGATORS.get(typ)
                if neg and neg.search(u.text):
                    continue
                out.append(Signal(typ, conf, "rule", m.group(0), topic, u.uid, now))
    return out


# ---------------------------------------------------------------- Tier 2 LLM
LLM_SYS = """You analyse a LIVE phone call between a lender's AGENT and a CUSTOMER (India, EMI reminder / collections).
Return JSON only:
{"intent": "<greeting|verification|payment_reminder|payment_plan|payment_dispute|hardship|complaint|small_talk|offer|closing|other>",
 "customer_sentiment": <-1..1 or null if LATEST is the agent>,
 "frustration": <0..1 or null if LATEST is the agent>,
 "signals": [{"type": "<type>", "confidence": <0..1>, "evidence": "<short quote from LATEST>", "topic": "<snake_case>"}]}
Signal types (report ONLY if evidenced in the LATEST utterance):
- cross_sell: customer reveals a NEW, upcoming financing need (education fees, buying a vehicle/home, renovation, wedding, business expansion). NOT past purchases, NOT already financed/paid off.
- payment_difficulty: customer indicates they may MISS or DELAY this payment (job loss, salary delay, medical, business problem). General budget remarks while confirming payment are NOT this.
- already_paid_dispute: customer says they already paid.
- frustration_rising: customer is clearly annoyed or angry (not mild impatience).
- escalation_request: customer asks for a manager/supervisor/human/complaint.
- callback_needed: customer explicitly asks to be called later or says they cannot continue the call now (driving, in a meeting). Background noise alone is NOT this.
- risky_statement: AGENT threatens (legal/recovery visit/police), harasses, gives false guarantees, or pressures to borrow.
- unauthorized_waiver: AGENT promises to waive/remove charges (raising a waiver *request* is fine).
One utterance can contain SEVERAL signals (e.g. a budget remark AND a new financing need): list each one separately.
Be conservative. Jokes, figures of speech ("this traffic is killing me"), sarcasm, background chatter and past events are NOT signals.
If the latest utterance is garbled or ambiguous, return no signals."""


# Agent utterances only go to the LLM when they touch money/consequences (cost + rate-limit control; rules cover the rest)
AGENT_LLM_PREFILTER = R(r"\b(pay|paid|payment|fee|charge|waive|legal|court|police|office|home|visit|team|cibil|credit|guarantee|borrow|"
                        r"must|have to|need to|otherwise|consequence|action|penalt\w*|interest|offer|loan)\b")


def needs_llm(u: "Utterance") -> bool:
    return u.speaker == "customer" or bool(AGENT_LLM_PREFILTER.search(u.text))


async def llm_signals(u: Utterance, st: CallState, window: int = 6) -> tuple[list[Signal], dict]:
    import asyncio

    ctx = st.utts[-window - 1 : -1]
    convo = "\n".join(f"{x.speaker.upper()}: {x.text}" for x in ctx) or "(start of call)"
    user = f"Recent transcript:\n{convo}\n\nLATEST ({u.speaker.upper()}): {u.text}"
    t0 = time.perf_counter()
    try:
        data, res = await asyncio.to_thread(llm.chat_json, [{"role": "system", "content": LLM_SYS}, {"role": "user", "content": user}],
                                            tier="signals", max_tokens=250)
    except Exception as e:
        return [], {"error": str(e)[:200], "llm_ms": (time.perf_counter() - t0) * 1000}
    ms = (time.perf_counter() - t0) * 1000
    now = time.perf_counter()
    sigs = []
    for s in data.get("signals") or []:
        try:
            sigs.append(Signal(str(s["type"]), float(s.get("confidence", 0)), "llm", str(s.get("evidence", ""))[:120],
                               str(s.get("topic") or s["type"]), u.uid, now))
        except (KeyError, TypeError, ValueError):
            continue
    meta = {"llm_ms": ms, "intent": data.get("intent"), "sentiment": data.get("customer_sentiment"),
            "frustration": data.get("frustration"), "model": f"{res.provider}/{res.model}"}
    return sigs, meta
