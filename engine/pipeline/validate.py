import sys as _s; _s.path.insert(0, 'pipeline'); import textsplit, pricetable
import sys, json, re, os
d = sys.argv[1]; h = json.load(open(f"{d}/hooq.raw.json")); f = json.load(open(f"{d}/facts.json")); s = json.load(open(f"{d}/scrape.json")); L = json.load(open(f"{d}/locale.json"))
MONEY = re.compile(L["money_re"])
alltext = re.sub(r"\s+", " ", " ".join(p["text"] for p in s["pages"])).lower()
norm = lambda t: re.sub(r"\s+", " ", (t or "")).strip().lower()
issues, fixes = [], []
svc = {x["name"].lower(): x for x in f["services"]}
pages = [(pg.get("url"), re.sub(r"\s+", " ", pg["text"])) for pg in s["pages"]]
STOP = {"and", "the", "for", "with", "your", "from", "work", "works", "services", "service", "installation", "installations", "new"}
def evidence(*names):
    """Return {url, snippet} where the job/service is named on the site: exact phrase first, else all key words within 160 chars."""
    for nm in names:
        if not nm: continue
        ph = norm(nm)
        for u, t in pages:
            i = t.lower().find(ph)
            if i >= 0: return {"url": u, "snippet": mask(t[max(0, i - 70): i + len(ph) + 90].strip()), "match": "exact phrase"}
    for nm in names:
        stems = [w[:5] for w in re.findall(r"[a-z]{4,}", norm(nm)) if w not in STOP]
        if not stems: continue
        for u, t in pages:
            tl = t.lower()
            for m in re.finditer(re.escape(stems[0]), tl):
                win = tl[max(0, m.start() - 160): m.start() + 160]
                if all(st in win for st in stems):
                    return {"url": u, "snippet": mask(t[max(0, m.start() - 90): m.start() + 130].strip()), "match": "key words " + "+".join(stems)}
    return None
PH = re.compile(r"(?<![\d,.$£€])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{1,4}\)[\s.-]?)?\d{2,5}[\s.-]?\d{3,4}(?:[\s.-]?\d{3,4})?(?![\d,])")   # any country's phone layout
def _isph(m): return len(re.sub(r"\D", "", m.group(0))) >= 9
def mask(x): return PH.sub(lambda m: "[phone]" if _isph(m) else m.group(0), x)
def has_phone(x): return any(_isph(m) for m in PH.finditer(x or ""))
def page_of(q):
    for u, t in pages:
        if norm(q).rstrip(".") in t.lower(): return u
# owner ranges: ONLY figures the owner typed (owner-prices.json: {job_id: {"low", "high", "basis"}}). We never source or pre-fill figures ourselves.
OWNER = json.load(open(f"{d}/owner-prices.json")) if os.path.exists(f"{d}/owner-prices.json") else {}
snips = json.load(open(f"{d}/site-prices.json")) if os.path.exists(f"{d}/site-prices.json") else []
TABLES = pricetable.find_tables(s["pages"]); LISTS = pricetable.find_lists(s["pages"])
def singular(x):
    x = (x or "").strip().lower()
    w = x.split(" ")
    if w and len(w[-1]) > 3 and w[-1].endswith("s") and not w[-1].endswith(("ss", "us", "is")): w[-1] = w[-1][:-1]
    return " ".join(w)
OWN_CHECK = json.load(open(f"{d}/owner-check.json")) if os.path.exists(f"{d}/owner-check.json") else {}
UNIT = re.compile(r"\s*(?:per|an?|each|/)\s*((?:roofing |linear |square |sq\.? ?)?(?:square|sq\.? ?ft|foot|feet|ft|m²|m2|sqm|metre|meter|hour|hr|day|week|month|room|window|door|item|visit|session|point|socket|radiator|tile|panel|kw|kwh)s?)\b(?:\s*\([^)]{1,20}\))?", re.I)
def _val(m): return int(float(m.group(1).replace(",", "")))
def clauses(sent):
    """v7: split a site price sentence into money clauses (a range 'X to/-/and Y' or one figure); each clause owns the words up to the next
    boundary (comma, semicolon, 'and', 'or', 'while', 'that is', 'which', 'but') on each side, so a unit or a label is never borrowed from another clause"""
    ms = list(MONEY.finditer(sent)); out = []; i = 0
    while i < len(ms):
        j2 = i
        if i + 1 < len(ms) and re.fullmatch(r"\s*(?:to|-|–|—|and)\s*", sent[ms[i].end():ms[i + 1].start()], re.I): j2 = i + 1
        out.append({"s": ms[i].start(), "e": ms[j2].end(), "vals": [_val(ms[i])] + ([_val(ms[j2])] if j2 > i else [])}); i = j2 + 1
    BND = re.compile(r",|;|\.\s|\band\b|\bor\b|\bwhile\b|\bwhereas\b|\bthat is\b|\bwhich\b|\bbut\b", re.I)
    for k, c in enumerate(out):
        bp = sent[(out[k - 1]["e"] if k else 0):c["s"]]
        if k:
            m = BND.search(bp); bp = bp[m.end():] if m else ""
        af = sent[c["e"]:(out[k + 1]["s"] if k + 1 < len(out) else len(sent))]
        m = BND.search(af); af = af[:m.start()] if m else af
        c["before"], c["after"] = bp, af
        um = UNIT.match(af); c["unit"] = um.group(0).strip() if um else None
        c["hplus"] = len(c["vals"]) > 1 and bool(re.match(r"\+", af))   # 'from $70,000 to $400,000+': the top end stays open
        c["from"] = (not c["hplus"]) and bool(re.search(r"(?:\bfrom|starting(?: at| from)?|starts? at|minimum(?: of)?|at least)\s*$", bp, re.I) or re.match(r"\s*(?:\+|& ?up\b|and up\b|or more\b|minimum\b)", af, re.I))
        c["text"] = (bp + sent[c["s"]:c["e"]] + af).strip(" ,;.")
    return out
GEN = {"and", "the", "for", "with", "your", "from", "work", "service", "new", "job", "jobs", "project", "other", "not", "sure", "yes", "about", "under", "over", "size"}
SOFT = {"typic", "stand", "avera", "basic", "norma", "most", "some", "usual", "regul", "gener"}
def stems(t): return {w[:5] for w in re.findall(r"[a-z]{3,}", (t or "").lower()) if w not in GEN}
def gate(j, cl):
    """(clause index, why) only when ONE clause maps to this job and applies to every visitor answer; else (None, why)"""
    jt = stems(j["label"] + " " + j["service"] + " " + (j.get("noun") or ""))
    hits = [k for k, c in enumerate(cl) if stems(c["before"] + " " + c["after"]) & jt]
    if len(cl) == 1: k = 0
    elif len(hits) == 1: k = hits[0]
    else: return None, f"{len(cl)} price clauses in the sentence and {len(hits)} name this job: the mapping is not certain"
    # words after 'depending on / based on / varies' are the factors the range spans, not a row selector; generic adjectives never select a row
    ctx = stems(re.sub(r"\b(?:depending on|depends on|based on|vary|varies|according to)\b[^,;|]*", " ", cl[k]["before"] + " | " + cl[k]["after"], flags=re.I)) - jt - SOFT
    for q in j["questions"][:2]:
        ol = [stems(o["label"]) - jt - SOFT for o in q["options"][:4]]
        named = [i for i, o in enumerate(ol) if o & ctx]
        if named and len(named) < len(ol): return None, "the clause names only some answers to one question: the answers select between prices"
    return k, ("the only price in the sentence" if len(cl) == 1 else "the only clause naming this job") + ", and it applies to every answer"
jobs, report_jobs = [], []
ROUTE = json.load(open(f"{d}/route.json")) if os.path.exists(f"{d}/route.json") else {}
FLOW = h.get("flow") or ROUTE.get("flow") or "quote"   # person = the visitor's situation, not a job: no service list to match against
h["flow"] = FLOW

for j in h["jobs"][:5]:
    sv = svc.get(j["service"].lower()) if FLOW == "quote" else {"planned": True}
    ev = (evidence(j["service"], j["label"]) if sv else None) if FLOW == "quote" else {"match": "visitor situation (person flow): an answer option, not a claim about the business"}
    if not sv or not ev:
        why = "service not in extracted facts" if not sv else "no evidence on the site"
        fixes.append(f"job {j['id']}: {why} -> dropped"); report_jobs.append({"id": j["id"], "label": j["label"], "service": j["service"], "status": "dropped", "why": why}); continue
    if sv.get("planned") is False:
        fixes.append(f"job {j['id']}: not planned work -> dropped"); report_jobs.append({"id": j["id"], "label": j["label"], "service": j["service"], "status": "dropped", "why": "not planned work"}); continue
    # grammar: a singular noun for "your ___" copy
    nn = singular(j.get("noun") or j["label"])
    if nn != (j.get("noun") or "").lower(): fixes.append(f"job {j['id']}: noun '{j.get('noun')}' -> '{nn}' (singular for 'your ___')")
    j["noun"] = nn
    # PRICE: 1) the site's own sentence, copied exactly by code; figures must appear in it
    price = {"mode": "none", "basis": j.get("basis")}
    n = j.get("site_price_n")
    if isinstance(n, int) and 0 <= n < len(snips):
        sent = textsplit.complete(snips[n]["text"], next((pg["text"] for pg in s["pages"] if pg["url"] == snips[n]["source"]), ""))
        if sent != snips[n]["text"]: fixes.append(f"job {j['id']}: site sentence was cut at an abbreviation -> completed to the real sentence end")
        cl = clauses(sent)
        if not cl: fixes.append(f"job {j['id']}: pointed at a site sentence with no money figure -> no site price")
        else:
            pick, why = gate(j, cl)
            if pick is not None:
                c = cl[pick]
                price = {"mode": "site", "flat": not c["from"], "site_quote": sent, "source_url": snips[n]["source"], "low": min(c["vals"]), "high": max(c["vals"]) if len(c["vals"]) > 1 and max(c["vals"]) != min(c["vals"]) else None, "basis": j.get("basis"), "clause": c["text"], "gate": why, "high_plus": c["hplus"]}
                if c["unit"]: price["unit"] = c["unit"]; fixes.append(f"job {j['id']}: site price is a rate ({c['unit']}, from its own clause) -> shown with its unit")
                fixes.append(f"job {j['id']}: price clause '{c['text']}' chosen ({why})")
            else:
                price = {"mode": "confirm", "site_quote": sent, "source_url": snips[n]["source"], "basis": j.get("basis"), "gate": why,
                         "rows": [{"clause": k, "text": c["text"], "low": min(c["vals"]), "high": max(c["vals"]) if len(c["vals"]) > 1 else None, "unit": c["unit"], "from": c["from"]} for k, c in enumerate(cl)]}
                fixes.append(f"job {j['id']}: price NOT shown as built ({why}) -> {len(cl)} clause(s) listed for the owner to confirm (1 tap)")
                pr = (OWN_CHECK.get("price_rows") or {}).get(j["id"])
                if pr:   # owner confirmed which clause applies to which answers (explicit 'when'); unmapped answers get no figure
                    rows = []
                    for r in pr:
                        c = cl[r["clause"]]
                        rows.append({"label": c["text"], "value": min(c["vals"]), "high": max(c["vals"]) if len(c["vals"]) > 1 and max(c["vals"]) != min(c["vals"]) else None, "unit": c["unit"], "plus": c["from"], "when": r.get("when") or {}, "quote": sent})
                    price = {"mode": "table", "picked": True, "rows": rows, "column": "owner-confirmed", "source_url": snips[n]["source"], "site_quote": sent, "basis": j.get("basis")}
                    fixes.append(f"job {j['id']}: owner confirmed {len(rows)} price row(s) -> shown only for the answers they mapped")
    # 1b) v4.1: the site publishes a price TABLE for this job (e.g. by size / coat): the visitor's answers pick the exact row; no row = no figure
    tbl = pricetable.for_job(j, TABLES) or pricetable.for_job_list(j, LISTS)
    if tbl: price = {**tbl, "basis": j.get("basis")}; fixes.append(f"job {j['id']}: site price table (column '{tbl['column']}', {len(tbl['rows'])} rows) -> exact row figure for matching answers, otherwise no figure")
    # 2) no site price: the owner's own typed range, if they gave one (never a figure we sourced)
    ow = OWNER.get(j["id"])
    if price["mode"] in ("none", "confirm") and ow and ow.get("low"):
        price = {"mode": "owner", "low": int(ow["low"]), "high": int(ow["high"]) if ow.get("high") else None, "flat": False, "basis": ow.get("basis") or j.get("basis")}   # v7: low-only shows From
    j["timeline"] = {"text": j.get("typical_timeline"), "source": None}
    j["price"] = price
    qs = j["questions"][:2]
    for q in qs:
        q["options"] = q["options"][:4]
        for o in q["options"]: o["factor"] = max(.85, min(1.2, float(o.get("factor", 1))))
    j["questions"] = qs
    if len(qs) < 1: issues.append(f"job {j['id']}: no own questions")
    jobs.append(j); report_jobs.append({"id": j["id"], "label": j["label"], "service": j["service"], "status": "kept", "evidence": ev})
if len(jobs) < (1 if s.get("limited") or FLOW == "person" else 2): issues.append("FATAL too few valid jobs")   # limited facts: one evidenced job + "Something else" is enough
h["jobs"] = jobs
# PATH: 1 = site prices (exact), 2 = owner's typed ranges, 3 = job summary + booking (no figure)
n_site = sum(j["price"]["mode"] in ("site", "table") for j in jobs); n_owner = sum(j["price"]["mode"] == "owner" for j in jobs)
h["path"] = 1 if n_site else 2 if n_owner else 3
if s.get("limited"): h["path"] = 3   # bot-blocked / unreadable site: job qualifier from limited facts
h["path_why"] = {1: f"{n_site} job(s) priced from the site's own words, used exactly", 2: f"no site prices; {n_owner} job(s) priced with the owner's own typed range", 3: "limited facts (site could not be read): job summary + booking" if s.get("limited") else "no prices on the site and the owner chose 'hide prices' (simulated): job summary + booking"}[h["path"]]
need = [j for j in jobs if j["price"]["mode"] == "none"]
h["owner_prompt"] = {"needed": bool(need), "message": "We couldn't find your prices. What's a typical range for your main jobs?", "currency": L["currency"], "symbol": L["symbol"],
                     "inputs": [{"job": j["id"], "label": j["label"], "low": None, "high": None} for j in need[:4]], "choices": ["Add my ranges", "Hide prices (show a job summary)"],
                     "simulated_choice": "Hide prices (show a job summary)" if need else None}
if s.get("limited"):
    h["owner_prompt_details"] = {"message": "We couldn't read your website. Tell us 3 things: your business name, your main services, and the town or area you cover", "inputs": ["Business name", "Main services", "Town or area you cover"], "optional": True}
b0 = h.get("booking") or {}
if not (b0.get("headline") and b0.get("sub")):
    h["booking"] = {"headline": b0.get("headline") or "Book your call with " + h["shortName"], "sub": b0.get("sub") or (h["shortName"] + " goes through it with you on the call." if FLOW == "person" else h["shortName"] + " talks the job through with you and confirms the price.")}
    fixes.append("writer left the booking copy empty -> standard booking copy used")
# v5.2 plain next-step wording: one short standard line under the booking headline (the writer's sentence is kept for reference only)
h["booking"]["sub_writer"] = h["booking"].get("sub"); h["booking"]["sub"] = "Pick a time that suits you."
# URGENCY filter over ALL visible copy (general rule)
URG = re.compile(r"\b(same[- ]day|emergenc\w*|24/7|24 ?hours?|24hr|urgent\w*|today|tonight|asap|immediate\w*|right away|rapid|fast response|quick response|within the hour|call[- ]out)\b", re.I)
def scrub(t, where):
    if not isinstance(t, str) or not URG.search(t): return t
    parts = [x for x in textsplit.split(t) if not URG.search(x)]
    nt = " ".join(parts).strip()
    if not nt: nt = URG.sub("", t); nt = re.sub(r"\s{2,}", " ", nt).strip(" ,-")
    fixes.append(f"urgency wording removed from {where}: '{t[:60]}'"); return nt
for hk in ("hook", "hook_q", "booking"):
    for k in list(h.get(hk, {})): h[hk][k] = scrub(h[hk][k], f"{hk}.{k}")
for j in jobs:
    for k in ("label", "desc", "brief"): j[k] = scrub(j[k], f"{j['id']}.{k}")
    j["result"]["title"] = scrub(j["result"]["title"], f"{j['id']}.result.title"); j["result"]["summary"] = scrub(j["result"]["summary"], f"{j['id']}.result.summary")
    j["result"]["includes"] = [x for x in j["result"]["includes"] if not (URG.search(x) and fixes.append(f"urgency item dropped from {j['id']}.includes: '{x[:50]}'") is None)]
    for q in j["questions"]:
        q["title"] = scrub(q["title"], f"{j['id']}.{q['id']}")
        for o in q["options"]: o["label"] = scrub(o["label"], "option"); o["desc"] = scrub(o.get("desc", ""), "option")
    if j["timeline"].get("text"): j["timeline"]["text"] = scrub(j["timeline"]["text"], f"{j['id']}.timeline")
h["urg_re"] = URG.pattern
# path enumeration: every answer path shows the job's price exactly as sourced (site sentence or owner's typed range), or no figure
import itertools
paths = []
for j in jobs:
    combos = list(itertools.product(*[q["options"] for q in j["questions"]]))
    ok_result = bool(j.get("result", {}).get("title"))
    p = j["price"] if h["path"] != 3 else {"mode": "none"}
    src = {"site": "site's own published price (exact)", "table": "site's own price table: exact row for matching answers, otherwise no figure", "owner": "owner's own typed range", "none": "no figure: job summary + booking", "confirm": "no figure until the owner confirms which price row fits which answers"}[p["mode"]]
    paths.append({"job": j["id"], "variant": "primary", "paths": len(combos) * 3, "result_screen": ok_result, "price_source": src, "shown_low": p.get("low"), "shown_high": p.get("high")})
    if not ok_result: issues.append(f"job {j['id']}: result screen incomplete")
paths.append({"job": "other", "variant": "both", "paths": 3, "result_screen": True, "price_source": "none: 'Book a call to discuss'", "range_min": None, "range_max": None, "within_source": True})
def shown(j):
    p = j["price"]
    sy = L["symbol"]
    if p["mode"] == "table": return "exact row per answers: " + "; ".join(f"{r['label']} {'From ' if r.get('plus') else ''}{sy}{r['value']:,.0f}" + (f" – {sy}{r['high']:,.0f}" if r.get('high') else "") + (f" {r['unit']}" if r.get('unit') else "") for r in p["rows"]), "site price " + ("owner-confirmed rows" if p.get("picked") else "list" if p.get("list") else "table"), p["rows"][0]["quote"], p["source_url"], None
    if p["mode"] == "confirm": return "no figure as built (owner to confirm rows)", "none", p["site_quote"], p["source_url"], None
    if p["mode"] == "site": return ("" if p.get("flat", True) or p.get("high") else "From ") + f"{sy}{p['low']:,}" + (f" – {sy}{p['high']:,}" + ("+" if p.get("high_plus") else "") if p.get("high") else "") + (f" {p['unit']}" if p.get("unit") else ""), "site (exact clause)", p["site_quote"], p["source_url"], None
    if p["mode"] == "owner": return ("" if p.get("high") else "From ") + f"{sy}{p['low']:,}" + (f" – {sy}{p['high']:,}" if p.get("high") else ""), "owner's typed range", None, "owner-prices.json", None
    return "no figure (job summary)", "none", None, None, None
prices = [dict(zip(("shown", "source", "quote", "url", "fetched"), shown(j)), job=j["id"]) for j in jobs]
for pr in prices:
    if pr["source"] not in ("none",) and not pr["url"]: issues.append(f"price for {pr['job']} has no source page")
# review: real named person, verbatim, 60-280 chars, no emoji, no emergency words
def real_name(b): return bool(re.fullmatch(r"[A-Z][a-z'\-]+(?: [A-Z][a-z'\-]*\.?){1,2}", (b or "").strip().title())) and any(c in "aeiou" for c in (b or "").lower().split()[0][1:]) and len((b or "").split()) >= 2
rev = None
for r in f.get("reviews", []):
    q = r["quote"].strip()
    if real_name(r["by"]) and 60 <= len(q) <= 280 and norm(q)[:60] in alltext and not re.search(r"[\U0001F300-\U0001FAFF]|leak", q, re.I) and not URG.search(q):
        rev = {"quote": q, "by": r["by"].strip().title(), "source": r.get("source")}; break
h["review"] = rev
rating = None
for rc in f.get("rating_claims", []):
    if re.search(r"\b(we|we're|we've|our|us|i|i'm|my)\b", rc["text"], re.I): fixes.append(f"first-person rating line rejected: '{rc['text'][:60]}'"); continue   # v7
    if norm(rc["text"])[:40] in alltext: rating = rc["text"].strip(); break
h["rating_claim"] = rating
if not rev: fixes.append("no named review usable -> site's own rating claim shown" if rating else "no review or rating claim -> none shown")
# trust chips: verbatim-ish from credentials/offers
trust = []
for c in f.get("credentials", []) + f.get("offers", []):
    t = c["text"].strip()
    if re.search(r"company no|registered in|vat", t, re.I): continue
    if norm(t)[:30] in alltext and len(t) <= 80: trust.append(t)
h["trust_src"] = [t for t in trust if not (URG.search(t) and fixes.append(f"urgency trust line dropped: {t[:50]}") is None)][:12]
# copy scans
blob = json.dumps({k: h.get(k) for k in ("hook", "hook_q", "jobs", "booking")})
if has_phone(blob): issues.append("phone number")
for pat, why in [(URG.pattern, "urgency wording left"),
                 (r"!", "exclamation"), (r"landing page|lead page", "banned term"), (r"peace of mind|look no further|one-stop", "cliché"), (r"\b(we|our|us)\b", "first person")]:
    if re.search(pat, blob, re.I): issues.append(why)
if re.search(r"\bfree\b", blob, re.I) and "free" not in alltext: issues.append("'free' not on site")
# photos: intro (main planned job) + one per job, max 6
h["photos"] = [{"id": "p-intro", "scene": h["intro_scene"]}] + [{"id": "p-" + j["id"], "scene": j["scene"]} for j in jobs][:5]
for ph in h["photos"]:
    ph["prompt"] = f"Editorial documentary photograph, {L['name']}: {ph['scene']}. Wide shot with the subject centred in the middle of the frame; any person is fully in frame from head to feet with clear space above their head, nothing cut off at the edges. Realistic, natural daylight, 35mm, no text, no logos, no signage, no lettering on clothing or vehicles."
h["locale"] = {k: L[k] for k in ("country", "name", "lang", "currency", "symbol", "postal", "hour12", "phone_label", "msg_tab", "date_example")}
# v4.1 booking wording: "appointment" only for appointment businesses (grooming, salons, clinics...), "call" for trades; copy made consistent
APPT = re.compile(r"groom|salon|spa\b|barber|beaut|nail|lash|brow|wax|massage|dental|dentist|orthodont|clinic|vet\b|veterin|physio|chiro|osteo|therap|tutor|lesson|driving instructor|fitness|personal trainer|yoga|pilates|photograph|tattoo|optic|optom|hair", re.I)
# v5.1 consult: coaching/advice businesses (not a local job): a call about the person's situation; no job, postcode or price wording
CONSULT = re.compile(r"\bcoach|consult|advis|mentor|relationship", re.I)
h["booking_kind"] = "consult" if CONSULT.search(f.get("trade") or "") else "appointment" if APPT.search(f.get("trade") or "") else "call"
if FLOW == "person": h["booking_kind"] = "consult"   # person flow is always a call; owner can pick appointment on the outcome row
# outcome row on the owner check: the engine's guess, or the owner's pick (owner-check.json 'outcome'). checkout is not built yet: it stays a call
GUESS = {"call": "quote", "consult": "call", "appointment": "appointment"}[h["booking_kind"]]
oc = OWN_CHECK.get("outcome")
if oc in ("quote", "call", "appointment", "checkout"):
    want = {"quote": "call", "call": "consult" if FLOW == "person" else "call", "appointment": "appointment", "checkout": "consult" if FLOW == "person" else "call"}[oc]
    if want != h["booking_kind"]: fixes.append(f"owner picked outcome '{oc}' -> booking wording '{want}' (was '{h['booking_kind']}')")
    h["booking_kind"] = want
h["outcome"] = {"guess": GUESS, "owner": oc, "shown": oc or GUESS}
# person flow: the tap count in the intro line must match the page's own step list, so the copy never states a number
if FLOW == "person" and isinstance(h.get("hook"), dict) and h["hook"].get("sub"):
    sub0 = h["hook"]["sub"]; sub1 = re.sub(r"\b(two|three|four|five|2|3|4|5) quick taps\b", "a few quick taps", sub0, flags=re.I)
    if sub1 != sub0: sub1 = sub1[0].upper() + sub1[1:]; h["hook"]["sub"] = sub1; fixes.append("tap count in the intro made 'a few quick taps'")
def kindfix(t):
    if not isinstance(t, str): return t
    if h["booking_kind"] != "appointment":
        t2 = re.sub(r"\ban appointment\b", "a call", t); t2 = re.sub(r"\bappointments\b", "calls", t2); t2 = re.sub(r"\bappointment\b", "call", t2); t2 = re.sub(r"\bAppointment\b", "Call", t2)
    else:
        t2 = re.sub(r"\b(book|schedule|arrange|request) (a|your) (quick |free |short )?call\b", lambda m: f"{m.group(1)} {'an' if m.group(2) == 'a' else 'your'} appointment", t, flags=re.I)
        t2 = re.sub(r"\bon the call\b", "at the appointment", t2)
    if t2 != t: fixes.append(f"booking wording made consistent ({h['booking_kind']}): '{t[:50]}'")
    return t2
for hk in ("hook", "hook_q", "booking"):
    for k in list(h.get(hk, {})): h[hk][k] = kindfix(h[hk][k])
for j in jobs: j["result"]["summary"] = kindfix(j["result"]["summary"]); j["result"]["title"] = kindfix(j["result"]["title"])
# owner's own booking widget (owner-supplied embed code, booking-embed.json): used instead of the demo calendar
if os.path.exists(f"{d}/booking-embed.json"): h["booking_embed"] = json.load(open(f"{d}/booking-embed.json")); fixes.append("owner's own booking widget used: " + h["booking_embed"]["url"])
json.dump(h, open(f"{d}/hooq.json", "w"), indent=1)
json.dump({"path": h["path"], "path_why": h["path_why"], "limited": bool(s.get("limited")), "issues": issues, "fixes": fixes, "jobs": report_jobs, "paths": paths, "prices": prices, "owner_prompt": h["owner_prompt"], "owner_prompt_details": h.get("owner_prompt_details"), "total_paths": sum(x["paths"] for x in paths if x["variant"] in ("primary", "both"))}, open(f"{d}/validate.json", "w"), indent=1)
print("validate: PATH", h["path"], "|", len(issues), "issues", issues, "| fixes", fixes, "| review", bool(rev), "| rating", rating, "| photos", len(h["photos"]))
if any(i.startswith("FATAL") for i in issues): sys.exit(4)
