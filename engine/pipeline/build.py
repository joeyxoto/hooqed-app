import sys, json, re, html, copy; sys.path.insert(0, "pipeline"); import accuracy
d = sys.argv[1]; h = json.load(open(f"{d}/hooq.json")); f = json.load(open(f"{d}/facts.json")); br = json.load(open(f"{d}/brand.json"))
URG = re.compile(h["urg_re"], re.I)
# v7 TRUST CHIPS, WHITELIST ONLY (nothing is split, nothing is rephrased beyond the canonical forms below). A chip may only be:
# (a) a rating WITH a count, exact site text; (b) 'Since YYYY' / 'Founded YYYY' (never a computed 'N yrs'); (c) licensed / bonded / insured in
# short canonical wording (+ the licence number if exact on the site); (d) a named accreditation / association from a known list (exact site
# wording), or a whole site credential line of 6 words or fewer containing certified / accredited / member / approved. Everything else is dropped.
# 0-3 chips; zero is fine. The owner check lists them (keep / remove, 1 tap).
import os
FIX = []
S_ = json.load(open(f"{d}/scrape.json")); HOME = re.sub(r"\s+", " ", (S_["pages"][0]["text"] if S_.get("pages") else ""))
SRC = [re.sub(r"\s+", " ", t).strip() for t in h.get("trust_src", [])]
CRED = " | ".join(SRC); LOC_ = json.load(open(f"{d}/locale.json")) if os.path.exists(f"{d}/locale.json") else {}
FP = re.compile(r"\b(we|we're|our|us|i|i'm|my)\b", re.I)
cand = []   # (kind, chip, source text)
rc0 = h.get("rating_claim")
if rc0 and not FP.search(rc0) and re.search(r"\b\d(?:\.\d)?\b", rc0) and re.search(r"\d[\d,]*\+?\s+(?:google\s+|verified\s+|customer\s+|5[- ]star\s+)?(?:reviews|ratings)", rc0, re.I) and len(rc0) <= 42 and not h.get("review") is None:
    cand.append(("a rating with count", rc0.strip(" ."), rc0))
for txt in (CRED, HOME):
    m = re.search(r"\b(since|established(?: in)?|est\.|founded(?: in)?)\s+((?:19|20)\d\d)\b", txt, re.I)
    if m: cand.append(("b year", ("Founded " if m.group(1).lower().startswith("found") else "Since ") + m.group(2), m.group(0))); break
NEG = re.compile(r"\b(not|un|make sure|ensure|check|ask|verify)\W+(?:\w+\W+){0,3}$", re.I)
lic = {}
for txt in (CRED, HOME):
    for m in re.finditer(r"\b(fully\s+)?(licen[cs]ed|bonded|insured)\b", txt, re.I):
        if NEG.search(txt[max(0, m.start() - 40):m.start()]): continue
        lic.setdefault(m.group(2).lower()[:5], m.group(0))
    if lic: break
if lic:
    ks = [k for k in ("licen", "bonde", "insur") if k in lic]; words = {"licen": "licensed" if LOC_.get("country") == "US" else "licensed", "bonde": "bonded", "insur": "insured"}
    chip = ", ".join(words[k] for k in ks[:-1]) + (" & " if len(ks) > 1 else "") + words[ks[-1]]
    if ks == ["insur"] and re.match(r"fully", lic["insur"], re.I): chip = "fully insured"
    cand.append(("c licensed/insured", chip[0].upper() + chip[1:], " / ".join(lic.values())))
    ln = re.search(r"\b(?:licen[cs]e|lic\.?)\s*(?:no\.?|number|#)\s*:?\s*#?\s*([A-Z0-9][A-Z0-9-]{3,})\b", CRED + " | " + HOME, re.I)
    if ln and re.search(r"\d", ln.group(1)): cand[-1] = (cand[-1][0], cand[-1][1] + " · " + ("License" if LOC_.get("country") == "US" else "Licence") + " #" + ln.group(1), cand[-1][2] + " / " + ln.group(0))
ACC = [r"Gas Safe(?: Registered)?", r"NICEIC(?: Approved Contractor)?", r"NAPIT(?: Registered)?", r"OFTEC(?: Registered)?", r"TrustMark(?: Registered)?", r"CIPHE(?: Member)?",
       r"APHC(?: Member)?", r"SafeContractor(?: Approved)?", r"Which\?\s*Trusted Trader", r"Federation of Master Builders", r"Red Seal(?: Certified)?", r"BBB Accredited(?: Business)?",
       r"BBB A\+(?: Rating)?", r"GAF (?:Master Elite|Certified)(?: Contractor)?", r"CertainTeed (?:SELECT )?ShingleMaster", r"Owens Corning (?:Platinum )?Preferred(?: Contractor)?",
       r"NATE[- ]Certified(?: Technicians)?", r"ACCA (?:Member|Certified)(?: Contractor)?", r"Fear Free(?: Certified)?(?: Salon| Professional)?", r"National Dog Groomers Association(?: of America)?",
       r"Master Landscapers", r"Clean Energy Council(?: (?:accredited|accreditation|approved))?(?: installer)?", r"Master Builders(?: Association)?", r"Master Plumbers(?: Association)?",
       r"Housing Industry Association", r"WSIB(?: Registered| Compliant)?", r"TSSA(?: Registered| Certified)?", r"NARI", r"NKBA", r"Energy Safe Victoria", r"Landscaping Victoria", r"HomeStars Best of"]
for t in SRC:
    for rx in ACC:
        m = re.search(r"\b" + rx + r"(?=\W|$)", t, re.I)
        if m: cand.append(("d named accreditation", m.group(0).strip(), t)); break
    else:
        tt = t.strip(" .")
        if len(tt.split()) <= 6 and re.search(r"\b(certified|accredited|member|approved)\b", tt, re.I) and not re.search(r"\$|£|€|gift|off\b|discount|director|company (no|number)|\d{5,}|@|https?:", tt, re.I) and not FP.search(tt):
            cand.append(("d short credential line", tt, t))
OWN_ = json.load(open(f"{d}/owner-check.json")) if os.path.exists(f"{d}/owner-check.json") else {}
chips, seen_k = [], set()
def ctok(c): return {w for w in re.findall(r"[a-z0-9]+", c.lower()) if w not in {"the", "and", "a", "of", "certified", "member", "registered"}}
for kind, c, src in cand:
    k0 = kind[0]
    if k0 in "abc" and k0 in seen_k: continue
    if any(ctok(c) <= ctok(x) or ctok(x) <= ctok(c) for x in chips): continue
    if c in OWN_.get("chips_remove", []): FIX.append(f"chip removed by the owner: '{c}'"); continue
    seen_k.add(k0); chips.append(c); FIX.append(f"chip kept ({kind}): '{c}' <- '{src[:80]}'")
for t in SRC:
    if not any(src == t for _, _, src in cand): FIX.append(f"chip source dropped (not on the whitelist): '{t[:80]}'")
h["chips"] = chips[:3]; h["chip_candidates"] = [{"kind": k, "chip": c, "source": s_} for k, c, s_ in cand]
def tok(c): return {w for w in re.findall(r"[a-z0-9]+", c.lower()) if w not in {"the", "and", "a", "of", "their", "they", "for", "in", "on", "to", "with", "all"}}
for j in h["jobs"]:
    inc = j["result"].get("includes") or []
    j["result"]["includes"] = [x for x in inc if not any(tok(x) and (tok(x) <= tok(c) or tok(c) <= tok(x)) for c in h["chips"])] or inc
rc = h.get("rating_claim"); rating = None
if rc and not URG.search(rc) and not re.match(r"\s*(read|see|check|click|view|find)\b", rc, re.I) and re.search(r"\d|five|star", rc, re.I):
    m = re.search(r"based on (\d+) reviews", rc, re.I); w = re.match(r"\s*(excellent|great|outstanding|very good)", rc, re.I)
    rating = (f"{w.group(1).capitalize()} on Google, based on {m.group(1)} reviews" if (m and w and "google" in rc.lower()) else rc) + " (as shown on their website)"
h["rating"] = rating
loc = f.get("location") or {}
logo = f'<img src="{br["logo_file"]}" alt="{html.escape(f["name"])}">' if br.get("logo_file") else f'<span class="wm">{html.escape(h["shortName"])}</span>'
import fonts as fontsmod
try: FONT_CSS = fontsmod.css(json.load(open(f"{d}/fonts.json")))
except Exception as e_: FONT_CSS = ""; print("fonts: template fonts kept:", str(e_)[:120])
def page(hh, example):
    data = {k: hh.get(k) for k in ("shortName", "hook", "jobs", "booking", "review", "chips", "rating", "path", "locale", "booking_kind", "booking_embed", "flow")}; data["example"] = example
    t = open("pipeline/template.html").read().replace('<html lang="en-GB">', f'<html lang="{hh["locale"]["lang"]}">')
    for k, v in {"__TITLE__": html.escape(hh["hook"]["headline"] + " · " + f["name"]), "__BRAND__": br["brand"], "__ON_BRAND__": br["on_brand"], "__DEEP__": br["deep"], "__ON_DEEP__": br["on_deep"],
                 "__BUTTON__": br["button"], "__ON_BUTTON__": br["on_button"], "__ACCENT_TEXT__": br["accent_text"], "__HEADER_BG__": br["header_bg"], "__ON_HEADER__": br["on_header"],
                 "__LOGO__": logo, "__NAME__": html.escape(f["name"]), "__AREA__": html.escape(loc.get("area") or ""), "__TAG__": "Personal summary" if hh.get("flow") == "person" else "Interactive quote", "__DATA__": json.dumps(data).replace("</", "<\\/")}.items():
        t = t.replace(k, v)
    if FONT_CSS:   # v8 font match: the site's own fonts (or closest free ones), template fonts as fallback
        t = t.replace("</head>", FONT_CSS + "</head>", 1)
    if br.get("cta"):   # the site's own button colour (e.g. green on a navy site) for the main call-to-action; templates without --cta ignore it
        t = t.replace("</head>", f'<style>:root{{--cta:{br["cta"]};--on-cta:{br["on_cta"]}}}</style></head>', 1)
    return t
# primary: visitors see the site's own figures exactly, or the owner's own typed ranges; otherwise no figure (path 3: job summary + booking)
L = json.load(open(f"{d}/locale.json")); ck = accuracy.Checker(d, L)
prim = copy.deepcopy(h); example = False
for j in prim["jobs"]:
    if h["path"] == 3 or j["price"]["mode"] not in ("site", "owner", "table"): j["price"] = {"mode": "none"}
prim = accuracy.apply(ck, prim, "primary")
if prim["jobs"][0]["price"]["mode"] == "none": prim["hook"] = h["hook_q"]; prim = accuracy.apply(ck, prim, "primary")   # never promise a price the main job will not show
open(f"{d}/hooq.html", "w").write(page(prim, example))
q = copy.deepcopy(h); q["hook"] = h["hook_q"]
for j in q["jobs"]:
    j["price"] = {"mode": "none"}
    if re.search(r"range|estimate|cost|price", j["result"]["title"], re.I): j["result"]["title"] = "Your " + j["noun"] + " summary"
q = accuracy.apply(ck, q, "path3")
open(f"{d}/hooq-path3.html", "w").write(page(q, False))
bad = [x for x in ck.log if x["status"] != "traced"]
json.dump({"rule": "every link, price, phone number, accreditation/licence, rating and years-trading claim visible on the hooq must trace to the scraped site (or search hint) or the owner's typed figures; phone numbers are never shown",
           "build": "PASS" if not bad else f"FAILED {len(bad)} check(s) -> untraceable items removed, safe wording used", "untraceable": bad, "checks": ck.log,
           "chip_fixes": FIX, "logo_check": {"picked": br.get("logo_url"), "kind": br.get("logo_kind"), **(br.get("logo_check") or {})}, "allowed_figures": sorted(ck.site_nums | ck.owner_nums), "money_re": L["money_re"]}, open(f"{d}/validation.json", "w"), indent=1)
print("accuracy:", len(ck.log), "checks |", "PASS" if not bad else f"{len(bad)} untraceable -> removed: " + "; ".join(f"{x['kind']} '{x['item']}' in {x['field']}" for x in bad[:6]))
# test panel visitors: cheapest job + lowest answers, biggest job + highest answers, out of scope
def ref(j):
    p = j["price"]
    return p.get("low") or 0, (p.get("high") or p.get("low") or 0)
def pick(j, fn): return ",".join([f"job:{j['id']}"] + [f"q{i}:{fn(q['options'], key=lambda o: o['factor'])['id']}" for i, q in enumerate(j["questions"])])
cheap = min(h["jobs"], key=lambda j: ref(j)[0]); big = max(h["jobs"], key=lambda j: ref(j)[1])
if cheap is big: big = [j for j in h["jobs"] if j is not cheap][-1]
h["visitors"] = [{"who": "Cheap job", "job": cheap["label"], "a": pick(cheap, min) + ",timing:weeks"},
                 {"who": "Big job", "job": big["label"], "a": pick(big, max) + ",timing:months"},
                 *([{"who": "Table row match", "job": tj["label"], "a": ",".join([f"job:{tj['id']}"] + [f"{k}:{v[0]}" for k, v in tj["price"]["rows"][min(2, len(tj["price"]["rows"]) - 1)]["when"].items()]) + ",timing:weeks"}]
                   if (tj := next((j for j in prim["jobs"] if j["price"].get("mode") == "table"), None)) else []),
                 {"who": "Out of scope", "job": "Something else", "a": "job:other,timing:planning"}]
h["variants"] = {"primary": "hooq.html", "path3": "hooq-path3.html"}; h["example_confirmation"] = example
json.dump(h, open(f"{d}/hooq.json", "w"), indent=1)
print("built: PATH", h["path"], "| hooq.html + hooq-path3.html | example owner confirmation:", example, "| chips", h["chips"], "| rating", rating)
# v4.1 owner check (shown after the build, next to the price prompt): "Is this your logo?" Confirm, or upload / pick another from the site's own candidates or a text wordmark
vj = json.load(open(f"{d}/validate.json"))
tiles = []
for c in (br.get("logo_candidates") or [])[:8]:
    if c.get("url") and c["url"] != br.get("logo_url"):
        tiles.append(f'<button class="tile"><img src="{html.escape(c["url"])}" alt=""><small>{html.escape((c.get("alt") or c["url"].split("/")[-1].split("?")[0])[:34])}</small></button>')
tiles.append(f'<button class="tile wmt"><span>{html.escape(h["shortName"])}</span><small>Text wordmark</small></button>')
cur = f'<img src="{br["logo_file"]}" alt="">' if br.get("logo_file") else f'<span class="wmk">{html.escape(h["shortName"])}</span>'
op = vj.get("owner_prompt") or {}
pr = "".join(f'<div class="pr"><b>{html.escape(i["label"])}</b><span>{op.get("symbol","")} <i>low</i> – <i>high</i></span></div>' for i in op.get("inputs", []))
# v7 owner check additions (functional only): price rows to confirm, chips keep/remove, brand colour swatches
sy_ = op.get("symbol") or L.get("symbol", "")
def _fig(r): return ("From " if r.get("from") and not r.get("high") else "") + f"{sy_}{r['low']:,}" + (f" – {sy_}{r['high']:,}" if r.get("high") and r["high"] != r["low"] else "") + (f" {r['unit']}" if r.get("unit") else "")
conf = [j for j in h["jobs"] if (j.get("price") or {}).get("mode") == "confirm"]
conf_html = "".join(f'<div class="cj"><b>{html.escape(j["label"])}</b><p class="m">Your site says: “{html.escape(j["price"]["site_quote"])}” We were not sure which figure fits which answer, so no price shows yet.</p>' + "".join(f'<div class="pr"><span>{html.escape(r["text"])}</span><span><b>{html.escape(_fig(r))}</b> <button class="b2 sm">Use for…</button></span></div>' for r in j["price"]["rows"]) + '<div class="btns"><button class="b2 sm">None of these: hide price</button></div></div>' for j in conf)
chip_html = "".join(f'<div class="pr"><span class="chip">{html.escape(c)}</span><span><button class="b1 sm">Keep</button> <button class="b2 sm">Remove</button></span></div>' for c in h["chips"]) or '<p class="m">No badges found that we can show exactly as your site words them. That is fine.</p>'
sw = "".join(f'<button class="sw{" on" if c["hex"] == br.get("primary") else ""}"><i style="background:{c["hex"]}"></i><small>{c["hex"]}<br>{html.escape(c["source"])}</small></button>' for c in (br.get("colour_candidates") or [])[:5])
colour_html = f'<p class="m">We picked <b>{br.get("primary")}</b> from {html.escape(br.get("colour_source") or "")}. Tap to confirm, or choose another.</p><div class="tiles">{sw}</div><div class="btns"><button class="b1">Use this colour</button></div>'
oc = f'''<!doctype html><html><head><meta charset="utf-8"><title>Owner check · {html.escape(f["name"])}</title><style>
body{{font:15px/1.45 system-ui,sans-serif;margin:0;background:#f4f4f2;color:#1b1b1b}}.w{{max-width:760px;margin:0 auto;padding:28px 22px}}h1{{font-size:22px;margin:0 0 4px}}h2{{font-size:18px;margin:26px 0 8px}}
.card{{background:#fff;border:1px solid #ddd;border-radius:14px;padding:18px}}.cur{{display:flex;align-items:center;justify-content:center;min-height:90px;background:{br["header_bg"]};border-radius:10px;padding:14px}}
.cur img{{max-height:70px;max-width:320px}}.wmk{{font-weight:800;font-size:22px;color:{br["on_header"]}}}.btns{{display:flex;gap:10px;margin:14px 0 4px}}.b1{{background:#111;color:#fff;border:0;border-radius:999px;padding:11px 20px;font-weight:700}}
.b2{{background:#fff;color:#111;border:2px solid #111;border-radius:999px;padding:9px 18px;font-weight:700}}.tiles{{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}}.tile{{width:150px;height:96px;border:1px solid #ccc;border-radius:10px;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;padding:8px}}
.tile img{{max-width:130px;max-height:50px;background:repeating-conic-gradient(#eee 0 25%,#fff 0 50%) 0 0/12px 12px}}.tile small{{font-size:11px;color:#555;overflow:hidden;white-space:nowrap;max-width:135px;text-overflow:ellipsis}}.wmt span{{font-weight:800}}
.up{{border:2px dashed #aaa;border-radius:10px;padding:12px;text-align:center;color:#444;margin-top:10px}}.pr{{display:flex;justify-content:space-between;border-bottom:1px solid #eee;padding:8px 0}}.pr i{{display:inline-block;width:60px;border:1px solid #ccc;border-radius:6px;padding:2px 6px;color:#999}}.m{{color:#555;font-size:13px}}.sm{{padding:4px 12px;font-size:13px}}.chip{{border:1px solid #bbb;border-radius:999px;padding:3px 10px}}.cj{{border-top:1px solid #eee;padding-top:8px;margin-top:8px}}
.sw{{width:120px;border:1px solid #ccc;border-radius:10px;background:#fff;padding:8px;text-align:left}}.sw i{{display:block;height:40px;border-radius:6px}}.sw small{{font-size:10.5px;color:#555}}.sw.on{{outline:3px solid #111}}
</style></head><body><div class="w"><h1>Your hooq is ready. A few quick checks.</h1><p class="m">About 30 seconds. Nothing goes live until you confirm.</p>
<h2>1. Is this your logo?</h2><div class="card"><div class="cur">{cur}</div><p class="m">{html.escape(br.get("logo_kind") or "")}{(" · from " + html.escape(br["logo_url"][:90])) if br.get("logo_url") else ""}</p>
<div class="btns"><button class="b1">Yes, that's my logo</button><button class="b2">Upload or pick another</button></div>
<p class="m" style="margin-top:14px">Other logos we found on your site (1 tap to use), or use your name as a text wordmark:</p><div class="tiles">{"".join(tiles)}</div><div class="up">⬆ Upload your logo (PNG, SVG or JPG)</div></div>
<h2>2. Prices</h2><div class="card">{('<p>' + html.escape(op.get("message", "")) + '</p>' + pr + '<div class="btns"><button class="b1">Add my ranges</button><button class="b2">Hide prices (show a job summary)</button></div>') if op.get("needed") and h.get("booking_kind") != "consult" else ('<p>No prices on this hooq: visitors pick their situation and book a call. Nothing to do.</p>' if h.get("booking_kind") == "consult" else '<p>Your prices come from your own website, exactly as written. Nothing to do.</p>')}{conf_html}</div>
<h2>3. Badges</h2><div class="card">{chip_html}</div>
<h2>4. Your brand colour</h2><div class="card">{colour_html}</div>
</div></body></html>'''
open(f"{d}/owner-check.html", "w").write(oc)
