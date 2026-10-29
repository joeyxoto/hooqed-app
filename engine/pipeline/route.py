"""Picks the flow from the facts (no AI): 'quote' (trades and local services with a list of jobs, unchanged) or 'person'
(coaches, consultants, agencies, info products, personal brands: where you are now / what you want / what's in the way / timing).
Asks the owner instead of failing when the site is too thin to build from, or there is nothing to book a call for."""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import ask
d = sys.argv[1]; s = json.load(open(f"{d}/scrape.json")); f = json.load(open(f"{d}/facts.json"))
own = ask.owner_text(d); ov = json.load(open(f"{d}/flow-override.json")) if os.path.exists(f"{d}/flow-override.json") else {}
site_chars = sum(len(p.get("text", "")) for p in s["pages"] if not p.get("owner") and not p.get("owner_link"))
link_chars = sum(len(p.get("text", "")) for p in s["pages"] if p.get("owner_link"))
PERSON = {"coaching", "consulting", "agency", "course_or_info_product", "personal_brand"}
CONSULT = re.compile(r"\bcoach|consult|advis|mentor|agency|course|programme\b|program\b|personal brand", re.I)
planned = [x for x in f.get("services", []) if x.get("planned", True)]
model = (f.get("business_model") or "other").lower()
offers = f.get("offers_sold", []) or []
call_offer = (f.get("call_offer") or "").strip() or (own[-1] if own else "")
why = []
if ov.get("flow"): flow = ov["flow"]; why.append("owner/app override")
elif model in PERSON or f.get("booking_style") == "call" or CONSULT.search(f.get("trade", "")): flow = "person"; why.append(f"business model {model}, trade '{f.get('trade')}'")
elif len(planned) < (1 if s.get("limited") else 2) and model not in ("trade", "local_appointment", "clinic"): flow = "person"; why.append(f"only {len(planned)} planned services and model {model}")
else: flow = "quote"; why.append(f"{len(planned)} planned services, model {model}")
out = {"flow": flow, "why": "; ".join(why), "business_model": model, "call_offer": call_offer, "site_chars": site_chars, "planned_services": len(planned), "offers_sold": len(offers)}
json.dump(out, open(f"{d}/route.json", "w"), indent=1)
print("route:", json.dumps(out))
# --- ask instead of failing ---
if (s.get("limited") or site_chars < 600) and not own and link_chars < 600 and not planned and not call_offer:
    ask.ask(d, "site_empty", f"only {site_chars} characters of readable text" + (" (the site blocked our reader)" if s.get("limited") else ""), step="route")
if flow == "person" and not call_offer:
    sug = (offers[0].get("name") if offers else "") or f.get("main_planned_service") or ""
    ask.ask(d, "no_offers", f"no call or consultation offer found ({len(offers)} things sold, {len(planned)} services)", suggestion=sug, step="route")
if flow == "quote" and not planned and not own:
    ask.ask(d, "no_offers", "no services found", step="route")
