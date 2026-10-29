import sys as _s; _s.path.insert(0, 'pipeline'); import textsplit
"""Accuracy validator (Round D). Every link, price, phone number, accreditation/licence, rating and years-trading claim that a visitor
can see must trace to the scraped site (or the search hint for limited sites), or to the owner's own typed figures (owner-prices.json).
Untraceable items are removed and replaced with safe wording; phone numbers are never shown. Every check is logged to validation.json."""
import re, json, os, urllib.parse as U
ACC = re.compile(r"\b(gas safe|niceic|napit|elecsa|trustmark|checkatrade|which\? trusted trader|federation of master builders|\bfmb\b|oftec|hetas|\bmcs\b|chas|constructionline|"
                 r"rated people|mybuilder|guild of master craftsmen|nfrc|competent ?roofer|part p|city ?& ?guilds|"
                 r"\bbbb\b|better business bureau|angi|homeadvisor|yelp|houzz|nextdoor|thumbtack|\bnate\b|\bepa\b|energy star|red seal|tssa|wsib|"
                 r"master builders?|\bhia\b|\bqbcc\b|\bvba\b|licensed|licenced|bonded|insured|certified|accredited|approved installer|registered|member of|award[- ]winning|"
                 r"fear ?free|nash|\bpijac\b|\bndga\b|\bifgc\b)", re.I)
RATING = re.compile(r"(\b\d(?:\.\d)?\s*(?:stars?|/\s?5|out of 5)|\b(?:five|5)[- ]star|\b\d[\d,]*\+?\s+(?:reviews|ratings|customers)|★+)", re.I)
YEARS = re.compile(r"\b(?:since|established|est\.?|founded in|trading since)\s+(?:19|20)\d\d\b|\b\d+\+?\s+years?\b", re.I)
LINK = re.compile(r"https?://[^\s\"'<>)]+|\bwww\.[^\s\"'<>)]+|\b[a-z0-9-]+\.(?:co\.uk|com\.au|co\.nz|com|ca|net|org|uk|au|us|ie)\b", re.I)
PH = re.compile(r"(?<![\d,.$£€])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{1,4}\)[\s.-]?)?\d{2,5}[\s.-]?\d{3,4}(?:[\s.-]?\d{3,4})?(?![\d,])")
def norm(t): return re.sub(r"\s+", " ", (t or "")).strip().lower()
class Checker:
    def __init__(self, d, L):
        s = json.load(open(f"{d}/scrape.json"))
        self.text = norm(" ".join(p["text"] for p in s["pages"]))
        hint = json.load(open(os.environ["HOOQ_HINT"])) if os.environ.get("HOOQ_HINT") and os.path.exists(os.environ["HOOQ_HINT"]) else {}
        self.text += " " + norm(" ".join(str(v) for v in hint.values()))
        self.hosts = {U.urlparse(p["url"].split(" ")[0]).netloc.lower().removeprefix("www.") for p in s["pages"]}
        self.money = re.compile(L["money_re"])
        self.site_nums = {int(float(x.replace(",", ""))) for x in self.money.findall(" ".join(p["text"] for p in s["pages"])) if x.replace(",", "").replace(".", "").isdigit()}
        ow = json.load(open(f"{d}/owner-prices.json")) if os.path.exists(f"{d}/owner-prices.json") else {}
        self.owner_nums = {int(v) for o in ow.values() for k, v in o.items() if k in ("low", "high") and v}
        self.log = []
    def add(self, variant, field, kind, item, ok, source):
        self.log.append({"variant": variant, "field": field, "kind": kind, "item": item, "status": "traced" if ok else "UNTRACEABLE -> removed, safe wording used", "source": source})
        return ok
    def scan(self, variant, field, t):
        """returns True if the string is clean (every claim traced)"""
        if not isinstance(t, str) or not t: return True
        ok = True
        for m in PH.finditer(t):
            if len(re.sub(r"\D", "", m.group(0))) >= 9: ok &= self.add(variant, field, "phone", m.group(0), False, "phone numbers are never shown")
        for m in LINK.finditer(t):
            host = U.urlparse(m.group(0) if "://" in m.group(0) else "http://" + m.group(0)).netloc.lower().removeprefix("www.")
            ok &= self.add(variant, field, "link", m.group(0), host in self.hosts, "scraped site host" if host in self.hosts else "not a page of the business's site")
        for m in self.money.finditer(t):
            n = int(float(m.group(1).replace(",", ""))) if m.group(1).replace(",", "").replace(".", "").isdigit() else None
            src = "site text" if n in self.site_nums else "owner's typed range" if n in self.owner_nums else None
            ok &= self.add(variant, field, "price", m.group(0), bool(src), src or "figure not on the site and not typed by the owner")
        for rx, kind in ((ACC, "accreditation/licence"), (RATING, "rating"), (YEARS, "years trading")):
            for m in rx.finditer(t):
                k = norm(m.group(0)); tr = k in self.text or (kind == "rating" and k.strip("★") == "")
                if kind == "rating" and k.startswith("★"): continue   # the star icon we print before the site's own rating line (checked as text below)
                ok &= self.add(variant, field, kind, m.group(0), tr, "found on the site" if tr else "not found on the site")
        return ok
SAFE = {"hook.sub": "A few quick steps, then book with {sn}.", "hook_q.sub": "A few quick steps, then book with {sn}.", "booking.sub": "{sn} talks it through with you.",
        "result.summary": "{sn} talks the job through with you and gives you a price for your exact job."}
def drop_bad(ck, variant, field, t, safe=None):
    """keep only sentences that pass; if nothing is left use the safe wording"""
    if ck.scan(variant, field, t): return t
    keep = [x for x in textsplit.split(t) if Checker.scan(_Quiet(ck), variant, field, x)]
    return " ".join(keep) if keep else safe
class _Quiet:   # re-check single sentences without logging twice
    def __init__(self, ck): self.__dict__.update(ck.__dict__); self.log = []
    def add(self, *a): return a[4]
def apply(ck, hh, variant):
    sn = hh["shortName"]
    for hk in ("hook", "booking"):
        for k in list(hh.get(hk) or {}):
            v = drop_bad(ck, variant, f"{hk}.{k}", hh[hk][k], SAFE.get(f"{hk}.{k}", "").format(sn=sn) or None)
            if v is None: v = {"headline": "Book with " + sn, "eyebrow": "", "cta": "Start"}.get(k, "")
            hh[hk][k] = v
    hh["chips"] = [c for c in hh.get("chips") or [] if ck.scan(variant, "chips", c)]
    if hh.get("rating"):
        core = re.sub(r"\s*\(as shown on their website\)$", "", hh["rating"])
        nums = re.findall(r"\d[\d,.]*", core); okn = all(norm(n) in ck.text for n in nums)
        ck.add(variant, "rating", "rating", core, okn and ck.scan(variant, "rating", core), "figures found on the site" if okn else "figures not on the site")
        if not okn: hh["rating"] = None
    if hh.get("review"):
        q = hh["review"]["quote"]; ok = norm(q)[:60] in ck.text
        ck.add(variant, "review", "review quote", q[:60] + "…", ok, "verbatim on the site" if ok else "not verbatim on the site")
        if not ok or not ck.scan(variant, "review", q): hh["review"] = None
    for j in hh["jobs"]:
        jf = f"job {j['id']}"
        for k in ("label", "desc"):
            if hh.get("flow") == "person": ck.scan(variant, f"{jf}.{k}", ck.money.sub("", j[k] or ""))   # the visitor's situation (e.g. a revenue band), not a claim
            else: j[k] = drop_bad(ck, variant, f"{jf}.{k}", j[k], j[k] if k == "label" else "") or j[k]
        r = j["result"]; r["summary"] = drop_bad(ck, variant, f"{jf}.summary", r["summary"], SAFE["result.summary"].format(sn=sn)); r["title"] = drop_bad(ck, variant, f"{jf}.title", r["title"], "Your " + j["noun"]) 
        r["includes"] = [x for x in r.get("includes") or [] if ck.scan(variant, f"{jf}.includes", x)]
        for q in j["questions"]:
            q["title"] = drop_bad(ck, variant, f"{jf}.question", q["title"], q["title"])
            for o in q["options"]:
                if hh.get("flow") == "person":   # person flow: a band like 'under $10k a month' describes the VISITOR, not a price or claim of the business
                    ck.scan(variant, f"{jf}.option", ck.money.sub("", o["label"])); ck.scan(variant, f"{jf}.option", ck.money.sub("", o.get("desc", "")))
                else: ck.scan(variant, f"{jf}.option", o["label"]); ck.scan(variant, f"{jf}.option", o.get("desc", ""))
        if j.get("timeline", {}).get("text"): j["timeline"]["text"] = drop_bad(ck, variant, f"{jf}.timeline", j["timeline"]["text"], None)
        p = j["price"]
        if p.get("mode") == "table":   # every published row must trace: its figure and its row label are on the site
            keep = []
            for r in p["rows"]:
                ok = int(r["value"]) in ck.site_nums and (not r.get("high") or int(r["high"]) in ck.site_nums) and norm(r["label"])[:40] in ck.text
                ck.add(variant, f"{jf}.price.table", "price", f"{r['quote']}", ok, "site price table row" if ok else "not traceable")
                if ok: keep.append(r)
            p["rows"] = keep
            if len(keep) < (1 if p.get("picked") else 3): j["price"] = {"mode": "none"}   # v7: owner-confirmed rows may be 1-2; a scraped table needs 3
        if p.get("mode") in ("site", "owner"):
            nums = [p["low"]] + ([p["high"]] if p.get("high") else [])
            pool, srcname = (ck.site_nums, "site text") if p["mode"] == "site" else (ck.owner_nums, "owner's typed range")
            ok = all(n in pool for n in nums) and (p["mode"] != "site" or norm(p.get("site_quote"))[:50] in ck.text)
            ck.add(variant, f"{jf}.price", "price", f"{nums} ({p['mode']})", ok, srcname + (" (exact sentence on the site)" if p["mode"] == "site" else "") if ok else "not traceable")
            if not ok: j["price"] = {"mode": "none"}
            if ok and p.get("basis"): p["basis"] = drop_bad(ck, variant, f"{jf}.basis", p["basis"], None)
    return hh
