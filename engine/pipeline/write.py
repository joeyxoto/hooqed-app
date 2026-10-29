import textsplit, sys, json, re, os; sys.path.insert(0, "pipeline"); import xai, ask
d = sys.argv[1]; f = json.load(open(f"{d}/facts.json")); s = json.load(open(f"{d}/scrape.json")); L = json.load(open(f"{d}/locale.json"))
MONEY = re.compile(L["money_re"])
# code-level price finder: every sentence with a figure in the site's currency, kept EXACTLY as written on the site (the writer only points at one by number)
snips = []
for p in s["pages"]:
    for sent in textsplit.split(p["text"], newlines=True):
        t = sent.strip()
        if MONEY.search(t) and 4 <= len(t) <= 300 and t not in [x["text"] for x in snips]: snips.append({"n": len(snips), "text": t, "source": p["url"]})
json.dump(snips, open(f"{d}/site-prices.json", "w"), indent=1)
trade = (f.get("trade") or "").lower()
facts = {k: v for k, v in f.items() if k != "phone"}
# v8 VOICE: the site's own words (home page first, then the other pages), for tone and the audience's language only. Phone numbers masked; it is
# never a source of facts beyond FACTS, and its urgency / hype is never copied.
_PH = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(\d{1,4}\)[\s.-]?)?\d{2,5}[\s.-]?\d{3,4}(?:[\s.-]?\d{3,4})?")
VOICE = " | ".join(re.sub(r"\s*\n\s*", " | ", p["text"])[:n] for p, n in zip([p for p in s["pages"] if not p["url"].startswith("owner")], (1600, 500, 500)))
VOICE = _PH.sub(lambda m: "[phone]" if len(re.sub(r"\D", "", m.group(0))) >= 9 else m.group(0), VOICE)
COPY = """COPY (write like a sharp direct-response copywriter, not a form):
- Lead with what the visitor wants or what is bugging them, in the words this site's audience would use (see VOICE and FACTS.audience / situations / goals / problems). A concrete detail beats an adjective.
- Make it about THIS business: name its real offers, services, method or approach from FACTS (e.g. its programme name, the kind of door it fits, the membership types). Someone who knows the site should recognise it.
- Match the site's tone (FACTS.tone, VOICE) but never its hype, urgency, discounts or scarcity.
- Headline: the visitor's desired outcome or pain as a short question they would say yes to. No clever puns, no 'Ready to...?', no 'Unlock', no 'journey'.
- Questions read like a good consultant asking, not a form ('What's eating most of your week?' not 'Select your obstacle'). Answer labels are in the visitor's own voice, the way they would describe themselves (max 4 words), each with a concrete desc (max 7 words). Options must be clearly different from each other.
- CTA: 2-4 words, an action toward their outcome (e.g. 'Price my new door', 'Map my next step'). Never a number of taps, never 'Submit', 'Start quiz', 'Start three taps'.
- Never write generic process lines such as 'a few quick taps', 'a few quick steps', 'see the published price', 'get your summary', 'answer a few questions'. The page already shows the steps.
- Banned: 'it's not X, it's Y' and its cousins; 'No X. No Y.'; neat triples of adjectives; clichés (peace of mind, look no further, one-stop, game-changer, seamless, tailored, elevate, unlock, journey, transform your life, take it to the next level, dream body); exclamation marks; emojis.
- No invented facts: no prices, numbers, timelines, results, guarantees, client counts, credentials or testimonials that are not in FACTS. No urgency or emergency wording. No assumptions specific to one country unless FACTS shows it."""
PHOTO = """PHOTOS (one strong photo beats many):
- Show the business DELIVERING its main offer, with real people mid-action: e.g. a fitter fitting a garage door, a physio working on a client's shoulder, a trainer spotting a client, a coach on a video call with a client. Never a picture of the visitor's problem or a lonely person on their own.
- Industry plus a plain scene only: no business name, brand, logo, signage, text, lettering, readable screens, or well-known people. No emergency scenes.
- No place names (no country, city or region). Only if the look is visibly regional and matters (e.g. the style of houses for a roofer) describe it plainly in regional_look, e.g. 'a red-brick British semi-detached house'; otherwise null."""
SYS = """You write an interactive quote for a local service business (any country): an interactive quote that turns website visitors into booked calls. Never call it a landing page or lead page.
Rules:
- Voice: third person about the business (e.g. "GWR Roofing confirms the price on the call"). Plain """ + L["spelling"] + """ (spelling, words and phrasing used in """ + L["name"] + """), warm, specific. Measurements in """ + L["units"] + """. Money in """ + L["currency"] + """ only. No exclamation marks, no clichés ("look no further", "peace of mind", "one-stop"), no emojis.
- Facts only from FACTS. Never invent guarantees, years, accreditations, ratings or offers.
- Calm, planned work only: never use "emergency", "24/7", "urgent", "same day", "today", "fast response", "ASAP" or similar. Only PLANNED jobs (services with planned=true).
- Never include any phone number.
- PRICES: you never write a price. If SITE_PRICES contains a sentence that states the price of a job, give its number in site_price_n and the money figures from that sentence that belong to the job in site_figures. Otherwise null. Prefer a sentence that prices the WHOLE job (e.g. 'a typical home: $9,000 to $14,900') over a rate (per hour, per square, per m²); use a rate only if nothing else prices that job.
- BOOKING: FACTS.booking_style says whether customers book a call to get a price ("quote") or book an appointment for a set service ("appointment"). Write the hook, sub and booking copy for that: a call to talk the job through and confirm the price, or an appointment.
- Each job gets exactly TWO tap questions that genuinely change the price or scope of THAT job (e.g. re-roof: property size, roof type). 2-4 options each, each with a modest factor 0.85-1.2 (exactly one option per question has factor 1.0).
- "noun": the job as a singular noun phrase for "your ___" (e.g. "new roof", "cloakroom", "boiler service"), never plural.
- MULTI-SELECT: set "multi": true on a question only when several answers can genuinely be true at once AND the answers do not pick between prices (e.g. 'Which extras do you want?', 'What's wrong with it?'). Size, type, budget, timing and anything that changes the price stay single choice ("multi": false).
""" + COPY + "\n" + PHOTO
U = f"""FACTS: {json.dumps(facts)}
VOICE (the site's own words, for tone and the audience's language only): {json.dumps(VOICE)}
SITE_PRICES (numbered sentences with a price, exactly as on the site): {json.dumps([{"n": x["n"], "text": x["text"]} for x in snips][:80])}
Return JSON:
{{"shortName": "short brand name as the site uses it",
 "booking_kind": "call|appointment",
 "hook": {{"eyebrow": "the trade in 2-4 words, e.g. 'Garage doors' (no town)", "headline": "max 8 words, a question about what their main planned job will cost, in their words", "sub": "max 22 words: why it is worth tapping through, specific to this business (what they get from <shortName>, from FACTS), ending with the booking (a call or an appointment, per booking_kind)", "cta": "2-4 words"}},
 "hook_q": {{"eyebrow": "same style", "headline": "max 8 words, about the job they are planning, in their words", "sub": "max 22 words, same rules as hook.sub but no price promise", "cta": "2-4 words"}},
 "intro_scene": "one photo scene: the business doing its MAIN planned job, people mid-action",
 "regional_look": "string or null",
 "jobs": [3-5 of {{"id": "kebab", "label": "2-3 words", "noun": "singular noun phrase", "desc": "max 6 words", "brief": "lowercase noun phrase for the owner brief", "service": "exact service name from FACTS",
   "site_price_n": int|null, "site_figures": [ints] , "basis": "what a price for this job describes",
   "questions": [2 of {{"id": "kebab", "title": "question, max 9 words", "short": "1-2 word label, e.g. Size", "help": "max 12 words", "multi": bool, "options": [{{"id": "kebab", "label": "max 4 words", "desc": "max 7 words", "brief": "lowercase phrase for owner brief", "factor": number}}]}}],
   "typical_timeline": "how long this kind of job typically takes, e.g. 'Usually 3 to 5 days on site'",
   "result": {{"title": "e.g. Your new roof range", "summary": "one sentence on what the business does for this job, from FACTS", "includes": ["3 short concrete reasons from FACTS"]}},
   "scene": "a photo scene ONLY if this job looks clearly different from the intro photo (different work, different setting); otherwise null"}}],
 "booking": {{"headline": "max 8 words, the call or appointment framed as their next step toward the outcome, e.g. 'Book a call to lock in your price'", "sub": "one sentence: what happens next, from FACTS (e.g. free written quote after a visit)"}}}}
The first job must be the main planned service. At most 2 jobs get their own scene."""
route = json.load(open(f"{d}/route.json")) if os.path.exists(f"{d}/route.json") else {"flow": "quote"}
FLOW = route.get("flow", "quote")
OWN = ask.owner_text(d)
if FLOW == "person":   # coaches, consultants, agencies, info products, personal brands: the visitor answers about themselves
    SYS = """You write an interactive "book a call" flow for a business that sells coaching, consulting, programmes, courses, an agency service or its owner's expertise (any country). It turns website visitors into booked calls. The visitor taps three quick questions about THEMSELVES (where they are now, what they want, what's in the way), then when they want to start, leaves contact details, sees a short personal summary and books the call. No typing for the visitor.
Rules:
- Voice: third person about the business or person (e.g. "Sam goes through it with you on the call"); speak to the visitor as "you". Never "we" or "our". Plain """ + L["spelling"] + """ (spelling, words and phrasing used in """ + L["name"] + """), warm, specific. Money in """ + L["currency"] + """ only. No exclamation marks, no clichés, no emojis.
- Facts only from FACTS and OWNER_SAYS (the owner's own words, typed on Hooqed: treat them as true). Never invent results, guarantees, numbers of clients, years, credentials, testimonials, timelines or offers. Never promise an outcome.
- The tap options describe the VISITOR, not the business. Build them from the site's own words in FACTS.audience, situations, goals and problems. Where the site doesn't say, use plain, neutral stages that fit the field (e.g. for a business coach: monthly revenue bands in """ + L["currency"] + """; for a fitness coach: how often they train now). Never present these as claims about the business.
- No urgency or pressure: never use "emergency", "24/7", "urgent", "same day", "today", "limited spots", "ASAP", "act now" or similar.
- Never include any phone number. Never write a price.
- PRICES: if SITE_PRICES contains a sentence that states the price of the main paid offer or of the call, give its number in site_price_n and the figures from it in site_figures, else null.
- MULTI-SELECT: the goal and obstacle questions usually allow several answers ("multi": true) because people want more than one thing and more than one thing gets in the way. Make them single only if the options are mutually exclusive.
""" + COPY + "\n" + PHOTO + """
- Two photos only: intro_scene (the offer being delivered, e.g. the coach working with a client) and summary_scene (a different moment of the same offer, e.g. the client mid-session or on the call). Never a photo per situation."""
    U = f"""FACTS: {json.dumps(facts)}
VOICE (the site's own words, for tone and the audience's language only): {json.dumps(VOICE)}
OWNER_SAYS: {json.dumps(OWN)}
WHAT THE CALL IS FOR: {json.dumps(route.get("call_offer") or f.get("call_offer") or "")}
SITE_PRICES (numbered sentences with a price, exactly as on the site): {json.dumps([{"n": x["n"], "text": x["text"]} for x in snips][:80])}
Return JSON:
{{"shortName": "short brand or person name as the site uses it",
 "booking_kind": "call|appointment" (appointment only if FACTS.booking_style is appointment),
 "call_noun": "the call as a singular noun phrase for 'your ___', from WHAT THE CALL IS FOR, e.g. 'strategy call', 'coaching call', 'free consultation'",
 "hook": {{"eyebrow": "the field in 2-4 words, e.g. 'Business coaching' or 'Online fitness coaching'", "headline": "max 8 words, a question about the outcome they want (or the pain they want gone), in the site's own words", "sub": "max 22 words: what this call gets them, specific to <shortName>'s offer and approach (from FACTS / OWNER_SAYS), ending with booking <call_noun>", "cta": "2-4 words"}},
 "intro_scene": "photo scene: the offer being delivered, people mid-action",
 "summary_scene": "photo scene: a different moment of the same offer",
 "regional_look": null,
 "situations": [3-4 of {{"id": "kebab", "label": "where the visitor is now, in their voice, 2-5 words", "desc": "max 7 words", "brief": "lowercase phrase for the owner brief, e.g. 'doing under $10k a month'"}}],
 "goal_question": {{"id": "goal", "title": "what they want, max 9 words", "short": "Goal", "help": "max 12 words", "multi": bool, "options": [3-5 of {{"id": "kebab", "label": "max 4 words", "desc": "max 7 words", "brief": "lowercase phrase"}}]}},
 "obstacle_question": {{"id": "obstacle", "title": "what's in the way, max 9 words", "short": "In the way", "help": "max 12 words", "multi": bool, "options": [3-5 of {{"id": "kebab", "label": "max 4 words", "desc": "max 7 words", "brief": "lowercase phrase"}}]}},
 "site_price_n": int|null, "site_figures": [ints], "basis": "what a price describes, e.g. the 12-week programme",
 "summary": {{"title": "max 6 words, e.g. 'Your strategy call plan'", "about": "one sentence on what <shortName> does and for whom, in the site's words, from FACTS / OWNER_SAYS", "cover": ["3 short, concrete things the call covers for this visitor (max 9 words each), from FACTS / OWNER_SAYS / the call offer"]}},
 "booking": {{"headline": "max 8 words, the call framed as their next step toward the outcome", "sub": "one sentence: what happens on or after the call, from FACTS / OWNER_SAYS only"}}}}"""
NEED_Q = ("hook", "jobs") if FLOW == "quote" else ("hook", "situations", "goal_question", "obstacle_question", "summary")
def shape_ok(h):
    if not isinstance(h, dict) or any(k not in h for k in NEED_Q): return False
    if not isinstance(h["hook"], dict) or not h["hook"].get("headline"): return False
    if FLOW == "quote": return isinstance(h["jobs"], list) and len(h["jobs"]) >= 1 and all(isinstance(j, dict) and j.get("questions") for j in h["jobs"])
    return isinstance(h["situations"], list) and len(h["situations"]) >= 2 and all(isinstance(h[q], dict) and len(h[q].get("options", [])) >= 2 for q in ("goal_question", "obstacle_question"))
h = None
for attempt in (1, 2):   # the AI sometimes returns an empty or wrong-shaped page: retry once, then ask the owner (never a raw crash)
    try:
        h = xai.chat("grok-4.7", SYS, U, f"{d}/costlog.jsonl", "write" if attempt == 1 else "write_retry", effort="low")
        if shape_ok(h): break
        print(f"write attempt {attempt}: reply missing", [k for k in NEED_Q if not isinstance(h, dict) or k not in h] or "parts"); h = None
    except Exception as e:
        print(f"write attempt {attempt} failed: {type(e).__name__}: {str(e)[:160]}"); h = None
if h is None: ask.ask(d, "build_failed", "the AI could not write the questions twice", step="write")
if FLOW == "person":   # same data shape as the quote flow (jobs -> q0, q1 -> timing -> contact -> result), so v7 and v5 render it unchanged
    call_noun = (h.get("call_noun") or "call").strip()
    goal = dict(h["goal_question"], id="goal"); obst = dict(h["obstacle_question"], id="obstacle")
    for q in (goal, obst):
        for i, o in enumerate(q["options"]): o["factor"] = 1.0; o.setdefault("id", f"{q['id']}-{i}")
    sm = h.get("summary") or {}
    h["jobs"] = [{"id": x.get("id") or f"s{i}", "label": x["label"], "noun": call_noun, "desc": x.get("desc", ""), "brief": x.get("brief") or x["label"].lower(),
                  "service": call_noun, "site_price_n": h.get("site_price_n"), "site_figures": h.get("site_figures") or [], "basis": h.get("basis", ""),
                  "questions": [json.loads(json.dumps(goal)), json.loads(json.dumps(obst))], "typical_timeline": None,
                  "result": {"title": sm.get("title") or f"Your {call_noun}", "summary": sm.get("about", ""), "includes": sm.get("cover", [])[:3]},
                  "scene": None} for i, x in enumerate(h["situations"][:4])]
    h["hook_q"] = h["hook"]
    h["flow"] = "person"
else:
    h["flow"] = "quote"
h["trade"] = trade
# v8 COPY POLISH: one short second pass over the visible words only (no structure, ids, prices or facts), by an editor told to make every line
# specific and outcome-led. Code keeps a line only if it adds no figure that is not already in the draft or FACTS and stays short; else the draft line stays.
def _paths(h):
    out = {}
    for hk in ("hook", "hook_q"):
        for k in ("headline", "sub", "cta"):
            if isinstance(h.get(hk), dict) and h[hk].get(k): out[f"{hk}.{k}"] = h[hk][k]
    if isinstance(h.get("booking"), dict) and h["booking"].get("headline"): out["booking.headline"] = h["booking"]["headline"]
    js = h["jobs"][:1] if h["flow"] == "person" else h["jobs"]
    for ji, j in enumerate(h["jobs"]):
        if h["flow"] != "person" or True:
            for k in ("label", "desc"): 
                if j.get(k): out[f"jobs.{ji}.{k}"] = j[k]
    for ji, j in enumerate(js):
        for qi, q in enumerate(j["questions"]):
            for k in ("title", "help"):
                if q.get(k): out[f"jobs.{ji}.questions.{qi}.{k}"] = q[k]
            for oi, o in enumerate(q["options"]):
                for k in ("label", "desc"):
                    if o.get(k): out[f"jobs.{ji}.questions.{qi}.options.{oi}.{k}"] = o[k]
        r = j.get("result") or {}
        for k in ("title", "summary"):
            if r.get(k): out[f"jobs.{ji}.result.{k}"] = r[k]
        for ii, x in enumerate(r.get("includes") or []): out[f"jobs.{ji}.result.includes.{ii}"] = x
    return out
def _set(h, path, v):
    ks = path.split("."); o = h
    for k in ks[:-1]: o = o[int(k)] if isinstance(o, list) else o[k]
    if isinstance(o, list): o[int(ks[-1])] = v
    else: o[ks[-1]] = v
POLISH_SYS = """You are a sharp direct-response copy editor. You get the draft words of a short interactive flow on a business's site (the visitor taps answers, then books a call). Rewrite each line so it is specific to THIS business and leads with what the visitor wants or what is bugging them, in their words. Keep the meaning, the facts and the order of options. Same keys back.
""" + COPY + """
- Keep each line about the same length or shorter (labels max 4 words, descs max 7 words, headlines max 8 words, CTAs 2-4 words, subs max 22 words).
- Use no figure, price, number, time span or claim that is not already in the draft line or in FACTS. Keep "you" to the visitor; third person for the business (never "we", "our", "us").
- Every line must read cleanly on its own: subs are full, grammatical sentences (no fragments, no stacked clauses); headlines name the visitor's outcome or problem in plain words they would say.
- Do not add offers or promises (free, guarantee, same-day, fast, best, no obligation, estimate, discount) unless the exact idea is already in the draft line or FACTS.
- Change a line only when your version is clearly sharper for this business; otherwise return it unchanged."""
POLISH = os.environ.get("HOOQ_POLISH", "0") != "0"
if POLISH:
    P0 = _paths(h)
    try:
        pol = xai.chat("grok-4.7", POLISH_SYS, f"""FACTS: {json.dumps(facts)}
VOICE (the site's own words, tone only): {json.dumps(VOICE[:1200])}
FLOW: {h["flow"]} ({'the visitor describes themselves and books ' + (h["jobs"][0].get("noun") or "a call") if h["flow"] == "person" else 'the visitor picks a job, answers 2 questions about it and sees the price or a job summary, then books'})
DRAFT (key -> line): {json.dumps(P0)}
Return JSON: {{"lines": {{same keys -> polished line}}}}""", f"{d}/costlog.jsonl", "polish", effort="low")
        new = (pol or {}).get("lines") or {}
        allowed = set(re.findall(r"\d+", json.dumps(facts)))
        kept = rej = 0; log = []
        for k, v0 in P0.items():
            v = new.get(k)
            if not isinstance(v, str) or not v.strip() or v.strip() == v0: continue
            v = v.strip()
            bad = [n for n in re.findall(r"\d+", v) if n not in re.findall(r"\d+", v0) and n not in allowed]
            ft = json.dumps(facts).lower()
            newp = [w for w in re.findall(r"\b(free|guarantee\w*|same[- ]day|fast\w*|best|no obligation|estimate|discount\w*|quick\w*|today|instant\w*|cheap\w*)\b", v, re.I) if w.lower() not in v0.lower() and w.lower() not in ft]
            if newp: bad = bad + ["claim:" + w for w in newp]
            if bad or len(v) > len(v0) * 1.6 + 20 or "!" in v or re.search(r"\b(we|our|us)\b", v, re.I):
                rej += 1; log.append({"key": k, "draft": v0, "polish": v, "kept": False, "why": "new figure / claim " + ",".join(bad) if bad else "too long / banned"}); continue
            _set(h, k, v); kept += 1; log.append({"key": k, "draft": v0, "polish": v, "kept": True})
        if h["flow"] == "person":   # the goal / obstacle questions are the same for every situation
            for j in h["jobs"][1:]: j["questions"] = json.loads(json.dumps(h["jobs"][0]["questions"])); j["result"] = json.loads(json.dumps(h["jobs"][0]["result"]))
        json.dump({"kept": kept, "rejected": rej, "lines": log}, open(f"{d}/polish.json", "w"), indent=1)
        print(f"polish: {kept} lines rewritten, {rej} rejected by the checks")
    except Exception as e:
        print(f"polish skipped: {type(e).__name__}: {str(e)[:160]}")
json.dump(h, open(f"{d}/hooq.raw.json", "w"), indent=1)
print("write:", h["flow"], "|", h["hook"]["headline"], "|", [(j["label"], j.get("site_price_n")) for j in h["jobs"]])
