import sys, json; sys.path.insert(0, "pipeline"); import xai, ask
d = sys.argv[1]; s = json.load(open(f"{d}/scrape.json"))
OWN = ask.owner_text(d)
LIM = s.get("limited")
corpus = "\n\n".join(f"=== PAGE {p['url']}\n{p['text'][:9000]}" for p in s["pages"])[:90000]
SYS = ("""The website blocked our reader, so the text below is only the search result (title and snippet) and page title for the business. Treat that text as the business describing itself: every kind of work it names (e.g. "extensions", "loft conversions", "boiler installation") is a service, planned unless it is emergency work. Use only what it says.
""" if LIM else "") + """You extract facts about a business (local or online, any country) from its own website text. Copy, never invent. Every string must appear on the site (verbatim or near-verbatim). If a fact is absent, leave it empty and list it in not_found. Return JSON only.""" + ("""
The page 'owner answer (typed on Hooqed)' is the business owner's own words about what they do or what people book a call for: treat it as the business describing itself, and use it for call_offer / services / offers_sold.""" if OWN else "")
U = """Return JSON:
{"name": "trading name", "trade": "the business type in 1-3 lowercase words as a customer would say it, e.g. plumber, roofer, general contractor, dog groomer", "location": {"address": "", "area": "town", "postal_code": "full postcode / ZIP / postal code if shown", "country": "country if shown or clear from the address", "areas_served": []},
 "phone": {"numbers": []},
 "booking_style": "how customers buy: 'quote' (price given after a call/visit), 'appointment' (book a set service at a time, e.g. grooming, cleaning, a clinic visit) or 'call' (book a call or consultation about their situation, e.g. coaching, consulting, agencies, programmes)",
 "business_model": "one of: trade, local_appointment, clinic, coaching, consulting, agency, course_or_info_product, personal_brand, ecommerce, other",
 "call_offer": "what the site invites visitors to book a call, consultation or application for, near-verbatim (e.g. 'Book a Free Strategy Call', 'free consultation call', 'Apply for coaching'); empty if the site has none",
 "offers_sold": [{"name": "", "detail": "one line from site", "kind": "coaching|consulting|programme|course|product|membership|service|other", "price": "verbatim with currency, or empty", "source": "url"}] (everything the business sells: programmes, courses, coaching, memberships, packages),
 "audience": ["who the site says it is for, in the site's words"],
 "situations": ["where the visitor is now, as the site describes its audience or their starting point (e.g. 'stuck in a dieting cycle', 'doing $500K+ in revenue')"],
 "goals": ["results or goals the site talks about, in its words"],
 "problems": ["problems or obstacles the site names, in its words"],
 "services": [{"name": "", "detail": "one line from site", "planned": true/false (false if it's emergency/urgent call-out work), "source": "url"}]  (list EVERY distinct service the business offers, usually 4-12: read the menus, headings, service pages and lists on every page, not just the home page),
 "emergency_led": true/false (is the site mainly selling emergency / 24-7 call-outs?),
 "main_planned_service": "the planned (non-emergency) service the site leads with",
 "prices": [{"item": "", "price": "verbatim, with its currency, e.g. From $950", "source": "url"}],
 "reviews": [{"quote": "verbatim", "by": "name as shown", "source": "url"}],
 "rating_claims": [{"text": "verbatim rating/feedback claim, e.g. '5 star rated on Google' or '4.9 from 120 reviews'", "source": "url"}],
 "credentials": [{"text": "verbatim, e.g. guarantees, licences/licenses, accreditations, certifications, years trading", "source": "url"}],
 "offers": [{"text": "verbatim, e.g. free quotes, no call-out charge"}],
 "tone": {"words": ["3-5 words describing the site's voice"]},
 "not_found": []}

SITE TEXT:
""" + corpus
DEF = {"name": "", "trade": "", "location": {}, "phone": {"numbers": []}, "booking_style": "", "business_model": "other", "call_offer": "", "offers_sold": [], "audience": [], "situations": [],
       "goals": [], "problems": [], "services": [], "emergency_led": False, "main_planned_service": "", "prices": [], "reviews": [], "rating_claims": [], "credentials": [], "offers": [], "tone": {"words": []}, "not_found": []}
f = None
for attempt in (1, 2):   # bad JSON / wrong shape from the model: one retry, then the app asks the owner instead of failing
    try:
        f = xai.chat("grok-4.3", SYS, U, f"{d}/costlog.jsonl", "facts" if attempt == 1 else "facts_retry")
        if not isinstance(f, dict) or not isinstance(f.get("services", []), list): raise ValueError("facts: not the expected shape")
        break
    except Exception as e:
        print(f"facts attempt {attempt} failed: {type(e).__name__}: {str(e)[:160]}"); f = None
if f is None: ask.ask(d, "build_failed", "the AI could not read the site's facts twice", step="facts")
for k, v in DEF.items():
    if not isinstance(f.get(k), type(v)): f[k] = v
f["services"] = [x for x in f["services"] if isinstance(x, dict) and x.get("name")]
f["offers_sold"] = [x for x in f["offers_sold"] if isinstance(x, dict) and x.get("name")]
for k in ("reviews", "rating_claims", "credentials", "offers", "prices"): f[k] = [x for x in f[k] if isinstance(x, dict)]
if OWN and not f["call_offer"]: f["call_offer"] = OWN[-1]
json.dump(f, open(f"{d}/facts.json", "w"), indent=1)
print("facts:", f["name"], "|", len(f["services"]), "services,", len(f["prices"]), "prices,", len(f["reviews"]), "reviews,", len(f.get("rating_claims", [])), "rating claims | emergency_led", f.get("emergency_led"), "| main", f.get("main_planned_service"), "| model", f.get("business_model"), "| call offer", f.get("call_offer"), "|", len(f["offers_sold"]), "offers sold")
