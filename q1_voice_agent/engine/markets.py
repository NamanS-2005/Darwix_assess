"""Market (use-case + language) configuration loader. Q1 and the Q3 localized bots share one engine."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[2]
MARKET_DIRS = {
    "in_lender": ROOT / "q1_voice_agent" / "market",
    "ph_life": ROOT / "q3_multilingual" / "markets" / "ph",
    "id_multifinance": ROOT / "q3_multilingual" / "markets" / "id",
}
CRM_PATH = ROOT / "q1_voice_agent" / "crm" / "customers.json"


class _SafeDict(dict):
    def __missing__(self, key):
        return ""


@dataclass
class Market:
    id: str
    cfg: dict
    rules: dict
    prompt_template: str
    script: str

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.cfg["timezone"])

    def now(self) -> datetime:
        return datetime.now(self.tz)

    def today(self) -> date:
        return self.now().date()

    def greeting(self) -> str:
        """Time-of-day greeting, e.g. id: pagi/siang/sore/malam (a literal 'good morning' all day would sound off)."""
        h, out = self.now().hour, ""
        for start, text in self.cfg.get("greetings", [[0, "Hello"]]):
            if h >= start:
                out = text
        return out

    def phrase(self, key: str, **kw) -> str:
        vals = _SafeDict(agent_name=self.cfg["agent_name"], company=self.cfg["company"], greeting=self.greeting(), **kw)
        return " ".join(self.cfg["phrases"][key].format_map(vals).split())

    def money(self, amount: int | float) -> str:
        cur = self.cfg["currency"]
        n = int(round(amount))
        if cur == "₹":  # Indian grouping 12,34,567
            s = str(n)
            if len(s) > 3:
                head, tail = s[:-3], s[-3:]
                parts = []
                while len(head) > 2:
                    parts.insert(0, head[-2:])
                    head = head[:-2]
                if head:
                    parts.insert(0, head)
                s = ",".join(parts) + "," + tail
            return f"₹{s}"
        if cur == "Rp":
            return "Rp" + f"{n:,}".replace(",", ".")
        return f"{cur}{n:,}"

    def fmt_date(self, d: date) -> str:
        style = self.cfg.get("date_style", "en")
        if style == "id":
            bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            return f"{hari[d.weekday()]}, {d.day} {bulan[d.month - 1]} {d.year}"
        if style == "ph":
            return d.strftime("%B %d, %Y (%A)").replace(" 0", " ")
        return d.strftime("%A, %d %B %Y").replace(" 0", " ")

    def calendar(self, days: int = 21) -> str:
        t = self.today()
        # includes the past week so "paid two days ago" / "kemarin" resolve to real dates
        return "; ".join(f"{(t + timedelta(i)).strftime('%a')} {(t + timedelta(i)).isoformat()}{' (today)' if i == 0 else ''}"
                         for i in range(-7, days))


@lru_cache(maxsize=None)
def load_market(market_id: str) -> Market:
    d = MARKET_DIRS[market_id]
    cfg = yaml.safe_load((d / "market.yaml").read_text(encoding="utf-8"))
    rules = yaml.safe_load((d / cfg["rules_file"]).read_text(encoding="utf-8"))
    return Market(market_id, cfg, rules, (d / cfg["prompt_file"]).read_text(encoding="utf-8"),
                  (d / cfg["script_file"]).read_text(encoding="utf-8"))


def load_customers(market_id: str) -> list[dict]:
    data = json.loads(CRM_PATH.read_text(encoding="utf-8"))
    return data.get(market_id, [])


def get_customer(market_id: str, customer_id: str | None = None, phone: str | None = None) -> dict:
    custs = load_customers(market_id)
    for c in custs:
        if (customer_id and c["customer_id"] == customer_id) or (phone and c["phone"] == phone):
            return dict(c)
    return dict(custs[0])
