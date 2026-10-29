"""Published price tables (v4.1). A table = 3+ consecutive rows of a label line followed by a line of 'Column: $X' pairs (or 'Label: $X ...' on one line).
For a job, the column is the one whose name shares a word with the job's service/label (no synonym guessing). Each row is mapped to the visitor's
answers by the words in its label (size / coat / type words that also appear in the job's answer options; S/M/L/XL = small/medium/large/extra large).
A visitor whose answers match exactly one row sees that row's exact figure; anything else gets no figure (path 3). Never interpolated."""
import re
MONEY = re.compile(r"([$£€])\s?(\d[\d,]*(?:\.\d\d)?)(\+)?")
PAIR = re.compile(r"([A-Za-z][A-Za-z &/'-]{1,30}?)\s*:\s*([$£€])\s?(\d[\d,]*(?:\.\d\d)?)(\+)?")
STOP = set("dog dogs cat cats pet pets coat coats hair haired hairs or and the a of size type with your my lbs lb kg up to only just".split())
def stem(w):
    if w.endswith("ing") and len(w) > 5: w = w[:-3]
    if w.endswith("s") and len(w) > 3 and not w.endswith(("ss", "us", "is")): w = w[:-1]
    return w
SIZE = {"s": "small", "sm": "small", "m": "medium", "med": "medium", "l": "large", "lg": "large", "xl": "xl", "xlarge": "xl", "xxlarge": "xxl", "xxl": "xxl", "xs": "xs"}
def norm_tokens(label):
    t = label.lower().replace("extra-large", "xl").replace("extra large", "xl").replace("x-large", "xl").replace("extra-small", "xs").replace("extra small", "xs")
    t = re.sub(r"\([^)]*\)", " ", t)
    out = []
    for w in re.findall(r"[a-z]+", t):
        w = SIZE.get(w, w)
        if w not in STOP: out.append(stem(w))
    return out
def find_tables(pages):
    tabs = []
    for p in pages:
        lines = [x.strip() for x in p["text"].split("\n")]; rows = []
        for i in range(1, len(lines)):
            pairs = PAIR.findall(lines[i])
            if len(pairs) >= 1 and len(PAIR.sub("", lines[i]).strip(" ;,|")) < 4 and lines[i - 1] and not MONEY.search(lines[i - 1]) and len(lines[i - 1]) <= 60:
                rows.append({"label": lines[i - 1], "line": lines[i], "cols": {c.strip(): (cur, float(v.replace(",", "")), bool(plus)) for c, cur, v, plus in pairs}, "i": i, "url": p["url"]})
        # group into consecutive blocks
        block = []
        for r in rows:
            if block and r["i"] - block[-1]["i"] > 2: (len(block) >= 3 and tabs.append(block)); block = []
            block.append(r)
        if len(block) >= 3: tabs.append(block)
    # same table repeated across pages: keep one
    uniq, seen = [], set()
    for b in tabs:
        k = tuple(r["line"] for r in b)
        if k not in seen: seen.add(k); uniq.append(b)
    return uniq
def for_job(job, tables):
    """price dict with mode 'table' or None"""
    jt = set(norm_tokens(job.get("service", "") + " " + job.get("label", "")))
    qs = job.get("questions", [])
    opt_tok = {(qi, o["id"]): set(norm_tokens(o["label"])) for qi, q in enumerate(qs) for o in q["options"]}
    vocab = set().union(*opt_tok.values()) if opt_tok else set()
    for tab in tables:
        cols = list(tab[0]["cols"]); scores = {c: len(set(norm_tokens(c)) & jt) for c in cols}
        best = max(scores.values()) if scores else 0
        win = [c for c in cols if scores[c] == best and best > 0]
        if len(win) != 1: continue
        col = win[0]; rows = []
        for r in tab:
            if col not in r["cols"]: continue
            parts = re.split(r"\s+or\s+", re.sub(r"\([^)]*\)", " ", r["label"]), flags=re.I)
            w0 = norm_tokens(parts[0]); alts = [t for p in parts[1:] for t in norm_tokens(p)]
            req, one = (w0[:-1], [w0[-1]] + alts) if alts and w0 else (w0, [])
            if any(t not in vocab for t in req): continue          # the row needs a word none of the answers can give: never matched
            one = [t for t in one if t in vocab]
            if alts and not one: continue
            if not (req or one): continue
            # which option of each question this row needs: options whose words hit the row
            when, ok = {}, True
            for qi, q in enumerate(qs):
                hits = [o["id"] for o in q["options"] if opt_tok[(qi, o["id"])] & set(req + one)]
                if hits: when["q" + str(qi)] = hits
            cover = lambda sel: set().union(*[opt_tok[(int(k[1:]), v)] for k, v in sel.items()]) if sel else set()
            cur, val, plus = r["cols"][col]
            rows.append({"label": r["label"], "req": req, "one_of": one, "when": when, "value": val, "plus": plus,
                         "quote": r["label"] + " — " + next(m.group(0) for m in PAIR.finditer(r["line"]) if m.group(1).strip() == col), "url": r["url"]})
        if len(rows) >= 3:
            return {"mode": "table", "column": col, "rows": rows, "opt_tokens": {f"q{qi}:{oid}": sorted(t) for (qi, oid), t in opt_tok.items()}, "source_url": rows[0]["url"],
                    "rule": "exact row only: every required word of the row label (and one of its 'or' alternatives) must be in the visitor's answers, and every answer must hit the row"}
    return None
def match(price, answers):
    """python mirror of the template lookup; answers {q0: optid, ...}"""
    ot = {k: set(v) for k, v in price["opt_tokens"].items()}
    sel = set().union(*[ot.get(f"{k}:{v}", set()) for k, v in answers.items()]) if answers else set()
    found = []
    for r in price["rows"]:
        rowt = set(r["req"] + r["one_of"])
        if not set(r["req"]) <= sel: continue
        if r["one_of"] and not (set(r["one_of"]) & sel): continue
        if any(not (ot.get(f"{k}:{v}", set()) & rowt) for k, v in answers.items()): continue
        found.append(r)
    return found[0] if len(found) == 1 else None

# v5.2 inline price LISTS: 3+ consecutive lines 'Label: $X' / 'Label $X' / 'Label – $X' (e.g. 'Cat Bathing: $86', 'Bath + Haircut: $154').
# Mapped to the visitor's answers like a table: the answers to the questions that name list items must equal one row's words exactly.
LINE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 &+/'().,-]{1,60}?)\s*(?::|–|-)?\s*([$£€])\s?(\d[\d,]*(?:\.\d\d)?)(\+)?\s*$")
def raw_tokens(x): return {stem(w) for w in re.findall(r"[a-z]+", x.lower()) if w not in ("or", "and", "the", "a", "of", "with", "your", "my", "only", "just")}
GRID = re.compile(r"^\s*([$£€])\s?(\d[\d,]*(?:\.\d\d)?)\s*(\+|&\s*up|and up|or more)?\s*$", re.I)
LABEL = re.compile(r"^\s*[A-Za-z][A-Za-z0-9 &+/'().,-]{1,38}$")
def find_lists(pages):
    out, seen = [], set()
    for p in pages:
        lines = [x.replace("\xa0", " ").strip() for x in p["text"].split("\n")]; block = []
        for i, ln in enumerate(lines):
            m = LINE.match(ln)
            g = GRID.match(ln) if not m and i and LABEL.match(lines[i - 1]) and not GRID.match(lines[i - 1]) else None
            if g:   # v7 price grid: the label on one line, the price alone on the line below ('Small' / '$70 & up')
                if block and i - block[-1]["i"] > 3:
                    if len(block) >= 3: out.append(block)
                    block = []
                if not block:   # heading context: the lines above the grid, back to the previous price line
                    k0 = i - 1
                    while k0 > max(0, i - 5) and not re.search(r"[$£€]\s?\d", lines[k0 - 1]): k0 -= 1
                    ctx = " ".join(lines[k0:i - 1])
                block.append({"label": lines[i - 1].strip(" :–-"), "line": lines[i - 1] + " " + ln, "cur": g.group(1), "value": float(g.group(2).replace(",", "")), "plus": bool(g.group(3)), "i": i, "url": p["url"], "ctx": ctx}); continue
            if m and len(re.sub(r"\([^)]*\)", "", m.group(1)).strip()) >= 3:
                if block and i - block[-1]["i"] > 2:
                    if len(block) >= 3: out.append(block)
                    block = []
                block.append({"label": re.sub(r"\s+", " ", m.group(1)).strip(" :–-"), "line": re.sub(r"\s+", " ", ln), "cur": m.group(2), "value": float(m.group(3).replace(",", "")), "plus": bool(m.group(4)), "i": i, "url": p["url"]})
        if len(block) >= 3: out.append(block)
    uniq = []
    for b in out:
        k = tuple(r["line"] for r in b)
        if k not in seen: seen.add(k); uniq.append(b)
    return uniq
def for_job_list(job, lists):
    jt = raw_tokens(job.get("service", "") + " " + job.get("label", "")) - {"groom", "service", "clean", "work", "job", "new"}
    qs = job.get("questions", [])
    opt_tok = {(qi, o["id"]): set(norm_tokens(o["label"])) for qi, q in enumerate(qs) for o in q["options"]}
    vocab = set().union(*opt_tok.values()) if opt_tok else set()
    best = None
    for lst in lists:
        share = sum(1 for r in lst if raw_tokens(r["label"]) & jt)
        if share < 2 and lst[0].get("ctx") and raw_tokens(lst[0]["ctx"]) & jt: share = 2   # v7: a grid's heading names the job (e.g. 'Full Grooming' above Small/Medium/Large)
        if share < 2: continue
        rows = []
        for r in lst:
            req = sorted(set(norm_tokens(r["label"])))
            if not req or any(t not in vocab for t in req): continue
            rows.append({"label": r["label"], "req": req, "one_of": [], "value": r["value"], "plus": r["plus"], "quote": r["line"], "url": r["url"]})
        if len(rows) >= 2 and len({tuple(x["req"]) for x in rows}) == len(rows) and (best is None or share > best[0]): best = (share, rows)
    if not best: return None
    rows = best[1]; rowtok = set(t for r in rows for t in r["req"])
    for r in rows:   # the answer(s) that pick this row (used for example screens)
        r["when"] = {f"q{qi}": [oid] for qi, q in enumerate(qs) for oid in [next((o["id"] for o in q["options"] if opt_tok[(qi, o["id"])] == set(r["req"])), None)] if oid}
    # v7: a question selects rows only if most of its options name a row (dog size: 4/4); one stray shared word (coat 'medium') does not make it relevant
    rel = sorted({f"q{qi}" for qi, q in enumerate(qs) if sum(1 for o in q["options"] if opt_tok[(qi, o["id"])] & rowtok) * 2 > len(q["options"])})
    for r in rows: r["when"] = {k: v for k, v in r["when"].items() if k in rel}
    return {"mode": "table", "list": True, "column": "list", "rows": rows, "relevant": rel, "opt_tokens": {f"q{qi}:{oid}": sorted(t) for (qi, oid), t in opt_tok.items()}, "source_url": rows[0]["url"],
            "rule": "inline price list: the visitor's answers to the questions naming list items must match exactly one row's words (no more, no less); otherwise no figure"}
def match_list(price, answers):
    ot = {k: set(v) for k, v in price["opt_tokens"].items()}
    sel = set().union(*[ot.get(f"{k}:{v}", set()) for k, v in answers.items() if k in price["relevant"]]) if answers else set()
    found = [r for r in price["rows"] if set(r["req"]) == sel]
    return found[0] if len(found) == 1 else None
