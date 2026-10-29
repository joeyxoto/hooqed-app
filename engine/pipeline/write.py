import textsplit, sys, json, re, os; sys.path.insert(0, "pipeline"); import xai
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
h = xai.chat("grok-4.7", SYS, U, f"{d}/costlog.jsonl", "write", effort="low")
h["trade"] = trade
json.dump(h, open(f"{d}/hooq.raw.json", "w"), indent=1)
print("write:", h["hook"]["headline"], "|", [(j["label"], j.get("site_price_n")) for j in h["jobs"]])
