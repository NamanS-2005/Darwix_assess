"""Spoken-number normalisation for English, Filipino/Tagalog and Indonesian.

ASR often writes numbers as words, e.g. Whisper on Filipino speech: "isang libo siyam na raan at walumpu't pito" (1987),
Indonesian: "sembilan belas sembilan puluh satu" (1991), English: "nineteen eighty seven", "seven seven three zero".
Used by the tool-argument guards to check that an identifier was really spoken.
"""
from __future__ import annotations

import re

UNITS = {
    # English
    "zero": 0, "oh": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
    # Tagalog (linker forms -ng / -ung handled by stripping)
    "sero": 0, "isa": 1, "dalawa": 2, "tatlo": 3, "apat": 4, "lima": 5, "anim": 6, "pito": 7, "walo": 8, "siyam": 9, "sampu": 10,
    "labing": 10, "dalawampu": 20, "tatlumpu": 30, "apatnapu": 40, "limampu": 50, "animnapu": 60, "pitumpu": 70, "walumpu": 80, "siyamnapu": 90,
    # Indonesian
    "nol": 0, "kosong": 0, "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9,
    "sepuluh": 10, "sebelas": 11,
    # Sundanese (su-ID speakers / TTS read numbers in Sundanese: "sarebu salapan ratus salapan puluh tilu" = 1993)
    "hiji": 1, "tilu": 3, "opat": 4, "genep": 6, "dalapan": 8, "salapan": 9, "sapuluh": 10, "sabelas": 11,
    # Javanese
    "siji": 1, "loro": 2, "telu": 3, "papat": 4, "limo": 5, "enem": 6, "pitu": 7, "wolu": 8, "songo": 9, "sanga": 9,
    "sewelas": 11, "seket": 50,
}
SCALES = {"hundred": 100, "daan": 100, "raan": 100, "ratus": 100, "seratus": 100, "thousand": 1000, "libo": 1000, "ribu": 1000, "seribu": 1000,
          "million": 1_000_000, "milyon": 1_000_000, "juta": 1_000_000, "sejuta": 1_000_000,
          "rebu": 1000, "sarebu": 1000, "sarbu": 1000, "saratus": 100, "ewu": 1000, "sewu": 1000, "atus": 100, "satus": 100}
IGNORE = {"and", "at", "na", "ng", "t"}


def _norm(tok: str) -> str:
    tok = tok.lower().replace("’", "'")
    tok = tok.removesuffix("'t")
    if tok in UNITS or tok in SCALES:
        return tok
    for suf in ("ng", "g", "t"):        # isang -> isa, walumpung / walumput -> walumpu
        base = tok[: -len(suf)]
        if tok.endswith(suf) and (base in UNITS or base in SCALES):
            return base
    return tok


def spoken_digits(text: str) -> str:
    """Digit string for single-digit words in order ('seven seven three zero' -> '7730'); plus literal digits."""
    out = []
    for raw in re.findall(r"[a-zA-Z'’]+|\d", text):
        t = _norm(raw)
        if raw.isdigit():
            out.append(raw)
        elif t in UNITS and UNITS[t] < 10:
            out.append(str(UNITS[t]))
    return "".join(out)


def spoken_numbers(text: str) -> list[int]:
    """Integers expressed in words: 'isang libo siyam na raan at walumpu't pito' -> 1987, 'nineteen eighty seven' -> 1987,
    'sembilan belas sembilan puluh satu' -> 1991, 'seribu sembilan ratus sembilan puluh satu' -> 1991."""
    nums, run = [], []
    for raw in re.findall(r"[a-zA-Z'’]+", text.lower()):
        t = _norm(raw)
        if t in UNITS or t in SCALES or t in ("belas", "welas", "puluh") or (run and t in IGNORE):
            run.append(t)
        else:
            if run:
                nums += _parse_run(run)
            run = []
    if run:
        nums += _parse_run(run)
    return nums


def _parse_run(run: list[str]) -> list[int]:
    run = [t for t in run if t not in IGNORE]
    total, cur, last_unit, groups, scaled = 0, 0, 0, [], False
    for t in run:
        if t in ("belas", "welas"):                       # Indonesian teens: sembilan belas = 19
            cur += 10
        elif t == "puluh":                     # Indonesian tens: sembilan puluh = 90
            cur = cur - last_unit + last_unit * 10
        elif t in SCALES:
            sc = SCALES[t]
            scaled = True
            if sc >= 1000:
                total += max(cur, 1) * sc
                cur = 0
            else:
                cur = (cur - last_unit) + max(last_unit, 1) * sc if cur % 100 else max(cur, 1) * sc
        elif t.isdigit():
            cur += int(t)
            last_unit = 0
            continue
        else:
            v = UNITS[t]
            combinable = (cur == 0) or (cur >= 100 and cur % 100 == 0) or (cur % 10 == 0 and cur % 100 >= 20 and v < 10)
            if not combinable and not scaled and not total:
                groups.append(cur)             # pair form: "nineteen | eighty seven"
                cur = 0
            cur += v
            last_unit = v if v < 10 else 0
    out = [total + cur]
    if groups and all(g < 100 for g in groups):
        out.append(int("".join(str(g) for g in groups) + str(cur)))
    return out


def words_to_digits(text: str) -> str:
    """Replace runs of number words with digits, keeping punctuation ('June siyam, isang libo ... pito po' -> 'June 9, 1987 po')."""
    PUNCT = ".,!?;:\"()"
    out, run, tail = [], [], ""

    def flush():
        nonlocal tail
        if run:
            vals = _parse_run([_norm(x) for x in run])
            out.append((str(vals[-1] if len(vals) > 1 else vals[0]) if vals else " ".join(run)) + tail)
            run.clear()
            tail = ""

    for tok in text.split():
        core = tok.strip(PUNCT)
        n = _norm(core)
        is_num = n in UNITS or n in SCALES or n in ("belas", "welas", "puluh") or (run and n in IGNORE)             or (core.isdigit() and len(core) <= 3 and run and _norm(run[-1]) in SCALES)   # ASR mix: "sarbu 178" = 1178
        if is_num and not (n in IGNORE and tok != core):
            if tail:              # punctuation inside a run ends it ("siyam, isang") -> separate numbers
                flush()
            run.append(core)
            tail = tok[len(tok.rstrip(PUNCT)):]
            if tail:
                flush()
        else:
            flush()
            out.append(tok)
    flush()
    return " ".join(out)
