"""Nudge engine: turns signals into a small number of short, approved, actionable nudges.

Controls (all configurable in PLAYBOOK / constants):
  - confidence thresholds per type (+0.15 stricter when ASR confidence is low, i.e. noisy audio)
  - corroboration policy: compliance types fire on rules alone (fast path); fuzzy types need LLM confirmation
  - topic grouping + duplicate suppression: same (type, topic) while active -> update the existing card, no new nudge
  - cooldown per type after a nudge closes; global spacing between non-critical nudges (hold queue, not drop)
  - priority (1 critical compliance … 3 opportunity), max 3 cards on screen (lowest priority evicted)
  - expiry (TTL) and auto-resolution when the agent does the recommended action (detected from agent speech)
Nudge text comes from an approved playbook (compliance-safe); the LLM only detects and supplies the evidence quote.
"""
from __future__ import annotations

import itertools
import re
import time
from dataclasses import dataclass, field

from .signals import Signal

R = lambda p: re.compile(p, re.I)

PLAYBOOK = {
    "disclosure_missing": dict(priority=1, ttl=60, cooldown=600, threshold=0.7, needs_llm=False, label="Compliance gap",
                               text="State your name, Udaan Credit Finance and that the call is recorded — before discussing the loan.",
                               resolve=R(r"\brecord")),
    "verification_skipped": dict(priority=1, ttl=60, cooldown=600, threshold=0.7, needs_llm=False, label="Compliance gap",
                                 text="Stop sharing loan details — verify date of birth or last 4 digits of the loan account first.",
                                 resolve=R(r"date of birth|last (four|4) digits|verif")),
    "risky_statement": dict(priority=1, ttl=45, cooldown=20, threshold=0.7, needs_llm=False, label="Risky statement",
                            text="Avoid threats/pressure (“{evidence}”). Say: “Late payment can attract charges as per the schedule — I'd like to help you avoid that.”",
                            resolve=None),
    "unauthorized_waiver": dict(priority=1, ttl=45, cooldown=60, threshold=0.7, needs_llm=False, label="Risky statement",
                                text="Don't promise waivers. Say: “I can raise a waiver request; Customer Assistance reviews it within 5 working days.”",
                                resolve=R(r"waiver request|customer assistance")),
    "escalation_request": dict(priority=2, ttl=40, cooldown=90, threshold=0.65, needs_llm=True, label="Escalation",
                               text="Customer asked for a manager — acknowledge, then offer a transfer or a supervisor callback within 1 working day.",
                               resolve=R(r"manager|supervisor|senior|transfer|escalat")),
    "frustration_rising": dict(priority=2, ttl=30, cooldown=75, threshold=0.6, needs_llm=True, label="Rising frustration",
                               text="Pause the push. Acknowledge first: “I understand this is frustrating, and I'm sorry for the repeated calls.” Then give one clear next step.",
                               resolve=R(r"i understand|sorry|apologi[sz]e|i hear you")),
    "already_paid_dispute": dict(priority=2, ttl=60, cooldown=120, threshold=0.65, needs_llm=True, label="Payment dispute",
                                 text="Customer says it's paid — don't insist. Ask payment date, mode and UTR; raise a payment trace (can take 2 working days to reflect).",
                                 resolve=R(r"\butr\b|transaction (id|reference)|reference number|trace|receipt")),
    "payment_difficulty": dict(priority=2, ttl=60, cooldown=120, threshold=0.65, needs_llm=True, label="Payment difficulty",
                               text="Show empathy (“{evidence}”). Offer the approved path: hardship review / Customer Assistance callback. Don't ask them to borrow.",
                               resolve=R(r"customer assistance|hardship|payment plan|sorry to hear|call you back|callback")),
    "callback_needed": dict(priority=3, ttl=40, cooldown=120, threshold=0.65, needs_llm=True, label="Callback",
                            text="Customer can't talk now — offer a callback slot (8 AM–7 PM) and confirm the exact time.",
                            resolve=R(r"call you back|callback|what time|which time")),
    "cross_sell": dict(priority=3, ttl=120, cooldown=30, threshold=0.7, needs_llm=True, label="Missed opportunity",
                       text="Opportunity: “{evidence}”. After closing the EMI topic, mention the pre-approved top-up / two-wheeler loan (subject to eligibility).",
                       resolve=R(r"top[- ]?up|pre[- ]?approved|loan offer|offer you|eligible for")),
}
GLOBAL_SPACING_S = 5.0      # min gap between non-critical nudges
MAX_ACTIVE = 3
LOW_ASR_CONF = 0.55
NOISY_PENALTY = 0.15


@dataclass
class Nudge:
    id: str
    type: str
    label: str
    text: str
    priority: int
    topic: str
    confidence: float
    source: str
    evidence: list[str]
    uid: int
    created_wall: float
    expires_wall: float
    status: str = "active"          # active | resolved | expired | evicted
    updates: int = 0
    timing: dict = field(default_factory=dict)

    def public(self) -> dict:
        return {k: getattr(self, k) for k in ("id", "type", "label", "text", "priority", "topic", "confidence", "source", "evidence", "status", "updates", "uid")}


class NudgeEngine:
    def __init__(self, emit):
        self.emit = emit                      # callback(event_type, payload)
        self.active: dict[tuple[str, str], Nudge] = {}
        self.closed: list[Nudge] = []
        self.last_closed: dict[str, float] = {}
        self.last_shown_wall = -1e9
        self.held: list[tuple[Nudge, dict]] = []
        self.ids = itertools.count(1)
        self.stats = {"signals_in": 0, "below_threshold": 0, "awaiting_llm_rejected": 0, "duplicates_merged": 0,
                      "cooldown_suppressed": 0, "held_then_shown": 0, "held_expired": 0, "evicted": 0, "unknown_type": 0}

    # ---------------------------------------------------------- decision
    def consider(self, rule_sigs: list[Signal], llm_sigs: list[Signal] | None, asr_conf: float, timing: dict, final: bool) -> list[Nudge]:
        """rule_sigs arrive first (fast path). Called again with llm_sigs (final=True) once the LLM returns."""
        made = []
        by_type: dict[str, list[Signal]] = {}
        for s in rule_sigs + (llm_sigs or []):
            by_type.setdefault(s.type, []).append(s)
        for typ, sigs in by_type.items():
            self.stats["signals_in"] += sum((s.source == "llm") == final for s in sigs)
            pb = PLAYBOOK.get(typ)
            if pb is None:
                self.stats["unknown_type"] += 1
                continue
            rule = max((s for s in sigs if s.source in ("rule", "state")), key=lambda s: s.confidence, default=None)
            llm_s = max((s for s in sigs if s.source == "llm"), key=lambda s: s.confidence, default=None)
            if pb["needs_llm"] and not final:
                continue                                   # wait for corroboration
            if not pb["needs_llm"] and final and rule is not None:
                continue                                   # already handled on the fast path
            thr = pb["threshold"] + (NOISY_PENALTY if asr_conf < LOW_ASR_CONF else 0.0)
            if llm_sigs is None and pb["needs_llm"]:      # LLM unavailable -> rules only, stricter
                conf, src = (rule.confidence if rule else 0.0), "rule-only"
                thr += 0.05
            elif rule and llm_s:
                conf, src = min(1.0, max(rule.confidence, llm_s.confidence) + 0.1), "rule+llm"
            elif llm_s:
                conf, src = llm_s.confidence, "llm"
            elif rule and not pb["needs_llm"]:
                conf, src = rule.confidence, rule.source
            else:
                conf, src = (rule.confidence * 0.5 if rule else 0.0), "rule-unconfirmed"   # LLM disagreed
                if rule:
                    self.stats["awaiting_llm_rejected"] += 1
            if asr_conf < LOW_ASR_CONF and pb["needs_llm"] and src != "rule+llm":
                conf -= 0.1                                # noisy audio: require agreement of both tiers
            if conf < thr:
                self.stats["below_threshold"] += 1
                continue
            best = llm_s or rule
            n = self._create(typ, best.topic or typ, conf, src, best.evidence, best.uid, timing)
            if n:
                made.append(n)
        return made

    def _create(self, typ, topic, conf, src, evidence, uid, timing) -> Nudge | None:
        pb = PLAYBOOK[typ]
        now = time.perf_counter()
        topic_key = typ if typ in ("frustration_rising", "cross_sell", "payment_difficulty", "already_paid_dispute") else f"{typ}:{topic}"
        key = (typ, topic_key)
        if key in self.active:                             # topic grouping / duplicate suppression
            n = self.active[key]
            n.updates += 1
            if evidence and evidence not in n.evidence:
                n.evidence.append(evidence)
            n.expires_wall = now + pb["ttl"]
            n.confidence = max(n.confidence, conf)
            self.stats["duplicates_merged"] += 1
            self.emit("nudge_update", n.public())
            return None
        if now - self.last_closed.get(typ, -1e9) < pb["cooldown"]:
            self.stats["cooldown_suppressed"] += 1
            return None
        n = Nudge(f"N{next(self.ids)}", typ, pb["label"], pb["text"].format(evidence=(evidence or "")[:70]), pb["priority"], topic_key,
                  round(conf, 2), src, [evidence] if evidence else [], uid, now, now + pb["ttl"], timing=dict(timing))
        if pb["priority"] > 1 and now - self.last_shown_wall < GLOBAL_SPACING_S:
            self.held.append((n, key))                     # spacing: hold, don't drop
            return None
        self._show(n, key)
        return n

    def _show(self, n: Nudge, key):
        now = time.perf_counter()
        if len(self.active) >= MAX_ACTIVE:
            worst_key = max(self.active, key=lambda k: (self.active[k].priority, -self.active[k].created_wall))
            if self.active[worst_key].priority >= n.priority:
                self._close(worst_key, "evicted")
                self.stats["evicted"] += 1
        n.timing["nudge_created"] = now
        self.active[key] = n
        self.last_shown_wall = now
        self.emit("nudge", n)

    def _close(self, key, status):
        n = self.active.pop(key)
        n.status = status
        self.closed.append(n)
        self.last_closed[n.type] = time.perf_counter()
        self.emit("nudge_close", n.public())

    # ---------------------------------------------------------- housekeeping
    def on_agent_utterance(self, text: str):
        for key in list(self.active):
            r = PLAYBOOK[self.active[key].type]["resolve"]
            if r and r.search(text):
                self._close(key, "resolved")

    def tick(self):
        now = time.perf_counter()
        for key in list(self.active):
            if now > self.active[key].expires_wall:
                self._close(key, "expired")
        if self.held and now - self.last_shown_wall >= GLOBAL_SPACING_S:
            self.held.sort(key=lambda x: (x[0].priority, x[0].created_wall))
            while self.held:
                n, key = self.held.pop(0)
                if now > n.expires_wall:
                    self.stats["held_expired"] += 1
                    continue
                if key in self.active:
                    self.stats["duplicates_merged"] += 1
                    continue
                self.stats["held_then_shown"] += 1
                self._show(n, key)
                break

    def finish(self) -> list[Nudge]:
        for key in list(self.active):
            self._close(key, "open_at_end")
        return self.closed
