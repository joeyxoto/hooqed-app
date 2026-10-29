import sys, json; sys.path.insert(0, "pipeline"); import xai
d = sys.argv[1]; s = json.load(open(f"{d}/scrape.json"))
LIM = s.get("limited")
corpus = "\n\n".join(f"=== PAGE {p['url']}\n{p['text'][:9000]}" for p in s["pages"])[:90000]
SYS = ("""The website blocked our reader, so the text below is only the search result (title and snippet) and page title for the business. Treat that text as the business describing itself: every kind of work it names (e.g. "extensions", "loft conversions", "boiler installation") is a service, planned unless it is emergency work. Use only what it says.
""" if LIM else "") + """You extract facts about a local business (any country) from its own website text. Copy, never invent. Every string must appear on the site (verbatim or near-verbatim). If a fact is absent, leave it empty and list it in not_found. Return JSON only."""
U = """Return JSON:
{"name": "trading name", "trade": "the business type in 1-3 lowercase words as a customer would say it, e.g. plumber, roofer, general contractor, dog groomer", "location": {"address": "", "area": "town", "postal_code": "full postcode / ZIP / postal code if shown", "country": "country if shown or clear from the address", "areas_served": []},
 "phone": {"numbers": []},
 "booking_style": "how customers buy: 'quote' (price given after a call/visit) or 'appointment' (book a set service at a time, e.g. grooming, cleaning)",
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
f = xai.chat("grok-4.3", SYS, U, f"{d}/costlog.jsonl", "facts")
json.dump(f, open(f"{d}/facts.json", "w"), indent=1)
print("facts:", f["name"], "|", len(f["services"]), "services,", len(f["prices"]), "prices,", len(f["reviews"]), "reviews,", len(f.get("rating_claims", [])), "rating claims | emergency_led", f.get("emergency_led"), "| main", f.get("main_planned_service"))
