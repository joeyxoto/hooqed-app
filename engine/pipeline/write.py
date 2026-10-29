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
- Photo scenes: a plain, realistic scene in """ + L["name"] + """ of the trade's work, no business names, logos, text, lettering. Prefer the finished work; if a person is shown, one worker fully in frame (head to feet), centred. The intro scene shows the MAIN PLANNED service."""
U = f"""FACTS: {json.dumps(facts)}
SITE_PRICES (numbered sentences with a price, exactly as on the site): {json.dumps([{"n": x["n"], "text": x["text"]} for x in snips][:80])}
Return JSON:
{{"shortName": "short brand name as the site uses it",
 "booking_kind": "call|appointment",
 "hook": {{"eyebrow": "e.g. Roofing in <town>", "headline": "max 7 words, a question about the cost of their main planned job, e.g. 'What will your new roof cost?'", "sub": "one sentence: a few quick taps, see their published price, then book (a call or an appointment, per booking_kind) with <shortName>", "cta": "2-4 words"}},
 "hook_q": {{"eyebrow": "same style", "headline": "max 7 words, inviting them to describe their job, e.g. 'Planning a new roof?'", "sub": "one sentence: a few quick taps, get your summary, then book (a call or an appointment, per booking_kind) with <shortName>", "cta": "2-4 words"}},
 "intro_scene": "photo scene of the MAIN planned service",
 "jobs": [3-5 of {{"id": "kebab", "label": "2-3 words", "noun": "singular noun phrase", "desc": "max 6 words", "brief": "lowercase noun phrase for the owner brief", "service": "exact service name from FACTS",
   "site_price_n": int|null, "site_figures": [ints] , "basis": "what a price for this job describes",
   "questions": [2 of {{"id": "kebab", "title": "question, max 8 words", "short": "1-2 word label, e.g. Size", "help": "max 10 words", "options": [{{"id": "kebab", "label": "max 4 words", "desc": "max 6 words", "brief": "lowercase phrase for owner brief", "factor": number}}]}}],
   "typical_timeline": "how long this kind of job typically takes, e.g. 'Usually 3 to 5 days on site'",
   "result": {{"title": "e.g. Your new roof range", "summary": "one sentence on what the business does for this job, from FACTS", "includes": ["3 short concrete reasons from FACTS"]}},
   "scene": "photo scene for this job"}}],
 "booking": {{"headline": "e.g. Book your call to confirm the price / Book your appointment", "sub": "one sentence: what happens next, from FACTS (e.g. free written quote after a visit)"}}}}
The first job must be the main planned service."""
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
- Photo scenes: a plain, realistic scene in """ + L["name"] + """ for this field (e.g. a person at a laptop on a video call, a gym session, a calm consulting room), no business names, logos, text, lettering, no well-known people. If a person is shown, one person fully in frame, centred."""
    U = f"""FACTS: {json.dumps(facts)}
OWNER_SAYS: {json.dumps(OWN)}
WHAT THE CALL IS FOR: {json.dumps(route.get("call_offer") or f.get("call_offer") or "")}
SITE_PRICES (numbered sentences with a price, exactly as on the site): {json.dumps([{"n": x["n"], "text": x["text"]} for x in snips][:80])}
Return JSON:
{{"shortName": "short brand or person name as the site uses it",
 "booking_kind": "call|appointment" (appointment only if FACTS.booking_style is appointment),
 "call_noun": "the call as a singular noun phrase for 'your ___', from WHAT THE CALL IS FOR, e.g. 'strategy call', 'coaching call', 'free consultation'",
 "hook": {{"eyebrow": "the field in 2-4 words, e.g. 'Business coaching' or 'Online fitness coaching'", "headline": "max 8 words, a question to the visitor about their goal in the site's words", "sub": "one sentence: a few quick taps, get your personal summary, then book <call_noun> with <shortName>", "cta": "2-4 words"}},
 "intro_scene": "photo scene for the intro",
 "situations": [3-4 of {{"id": "kebab", "label": "where the visitor is now, 2-5 words", "desc": "max 6 words", "brief": "lowercase phrase for the owner brief, e.g. 'doing under $10k a month'", "scene": "photo scene that fits this visitor"}}],
 "goal_question": {{"id": "goal", "title": "what they want, max 8 words", "short": "Goal", "help": "max 10 words", "options": [3-4 of {{"id": "kebab", "label": "max 4 words", "desc": "max 6 words", "brief": "lowercase phrase"}}]}},
 "obstacle_question": {{"id": "obstacle", "title": "what's in the way, max 8 words", "short": "In the way", "help": "max 10 words", "options": [3-4 of {{"id": "kebab", "label": "max 4 words", "desc": "max 6 words", "brief": "lowercase phrase"}}]}},
 "site_price_n": int|null, "site_figures": [ints], "basis": "what a price describes, e.g. the 12-week programme",
 "summary": {{"title": "e.g. Your coaching call", "about": "one sentence on what <shortName> does, from FACTS / OWNER_SAYS", "cover": ["3 short things the call covers for this visitor, from FACTS / OWNER_SAYS / the call offer"]}},
 "booking": {{"headline": "e.g. Book your free strategy call", "sub": "one sentence: what happens on or after the call, from FACTS / OWNER_SAYS only"}}}}"""
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
                  "scene": x.get("scene", "")} for i, x in enumerate(h["situations"][:4])]
    h["hook_q"] = h["hook"]
    h["flow"] = "person"
else:
    h["flow"] = "quote"
h["trade"] = trade
json.dump(h, open(f"{d}/hooq.raw.json", "w"), indent=1)
print("write:", h["flow"], "|", h["hook"]["headline"], "|", [(j["label"], j.get("site_price_n")) for j in h["jobs"]])
