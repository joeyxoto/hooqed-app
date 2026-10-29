"""Detect the business's country and local conventions from its own site (TLD, currency, address/postal code, phone format, spelling).
Writes locale.json. Every decision lists the evidence it came from. Nothing assumes the UK."""
import sys, json, re, urllib.parse as U
d = sys.argv[1]; s = json.load(open(f"{d}/scrape.json"))
url = s.get("final_url") or s.get("input_url") or s["pages"][0]["url"]
host = U.urlparse(url.split(" ")[0]).netloc.lower()
hint = {}
import os
if os.environ.get("HOOQ_HINT") and os.path.exists(os.environ["HOOQ_HINT"]): hint = json.load(open(os.environ["HOOQ_HINT"]))
txt = " ".join(p["text"] for p in s["pages"])
ev, score = [], {}
def vote(c, w, why): score[c] = score.get(c, 0) + w; ev.append(f"{c} +{w}: {why}")
TLD = {".co.uk": "GB", ".uk": "GB", ".com.au": "AU", ".au": "AU", ".ca": "CA", ".co.nz": "NZ", ".nz": "NZ", ".ie": "IE", ".us": "US", ".co.za": "ZA"}
for t, c in TLD.items():
    if host.endswith(t): vote(c, 5, f"domain {host}"); break
US_ST = r"AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC"
pat = {"US": rf"\b(?:{US_ST}),?\s+\d{{5}}(?:-\d{{4}})?\b", "CA": r"\b(?:ON|QC|BC|AB|MB|SK|NS|NB|NL|PE|Ontario|Alberta|British Columbia|Quebec|Manitoba|Nova Scotia),?\s+[A-Z]\d[A-Z]\s?\d[A-Z]\d\b",
       "AU": r"\b(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+\d{4}\b", "GB": r"\b[A-Z]{1,2}\d[A-Z\d]?\s\d[A-Z]{2}\b", "NZ": r"\b(?:Auckland|Wellington|Christchurch|Hamilton|Tauranga|Dunedin)\s+\d{4}\b"}
for c, p in pat.items():
    m = re.findall(p, txt)
    if m: vote(c, min(4, 2 * len(set(m))), f"address/postal code '{m[0]}'")
# v4.1: province / state names and currency codes from the site itself; a North American phone number is +1 for BOTH the US and Canada
REG = {"CA": r"\b(?:Ontario|Quebec|Québec|British Columbia|Alberta|Manitoba|Saskatchewan|Nova Scotia|New Brunswick|Newfoundland|Prince Edward Island|Yukon|Nunavut|Northwest Territories)\b",
       "AU": r"\b(?:New South Wales|Queensland|South Australia|Western Australia|Tasmania|Northern Territory|Australian Capital Territory)\b",
       "US": r"\b(?:Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)\b",
       "GB": r"\b(?:Yorkshire|Lancashire|Essex|Surrey|Sussex|Devon|Cornwall|Norfolk|Suffolk|Cheshire|Cumbria|Northumberland|Hampshire|Dorset|Somerset|Wiltshire|Gloucestershire|Oxfordshire|Berkshire|Buckinghamshire|Hertfordshire|Cambridgeshire|Lincolnshire|Nottinghamshire|Derbyshire|Leicestershire|Staffordshire|Shropshire|Worcestershire|Warwickshire|Northamptonshire|Herefordshire|Merseyside|Tyne and Wear|West Midlands)\b"}
REGIONS = []
for c, p in REG.items():
    m = set(re.findall(p, txt)); REGIONS += sorted(m)
    if m: vote(c, min(3, 1 + len(m)) if c != "US" else min(2, len(m)), f"names a {'state' if c in ('US', 'AU') else 'province' if c == 'CA' else 'county'}: {sorted(m)[:3]}")
for c, p in {"CA": r"\bCAD\b|\bC\$|\bCA\$", "AU": r"\bAUD\b|\bA\$|\bAU\$", "US": r"\bUSD\b|\bUS\$", "GB": r"\bGBP\b"}.items():
    n = len(re.findall(p, txt))
    if n: vote(c, 2, f"currency code on the site ({n}x)")
if re.search(r"\(\d{3}\)\s?\d{3}-\d{4}|\b\d{3}[-.]\d{3}[-.]\d{4}\b|\+1[\s-]?\d{3}", txt): vote("US", 1, "North American phone format (+1: US or Canada)"); vote("CA", 1, "North American phone format (+1: US or Canada)")
ph = { "AU": r"\+61|\b04\d{2}\s?\d{3}\s?\d{3}\b|\(0[2378]\)\s?\d{4}\s?\d{4}|\b1300\s?\d{3}\s?\d{3}\b",
      "GB": r"\+44|\b0\d{3,4}\s?\d{3}\s?\d{3,4}\b|\b07\d{3}\s?\d{6}\b", "NZ": r"\+64", "IE": r"\+353"}
for c, p in ph.items():
    if re.search(p, txt): vote(c, 1, "phone number format")
for c, p in {"US": r"\bUSA\b|United States", "CA": r"\bCanada\b", "AU": r"\bAustralia\b", "GB": r"\bUnited Kingdom\b|\bEngland\b|\bScotland\b|\bWales\b", "NZ": r"New Zealand", "IE": r"\bIreland\b"}.items():
    n = len(re.findall(p, txt))
    if n: vote(c, min(2, n), f"names the country ({n}x)")
site_score = dict(score); site_country = max(site_score, key=site_score.get) if site_score else None
if hint.get("country"): vote(hint["country"], 1, "country fixed at selection time (search-hint.json), tie-break weight only")
cur = {"£": len(re.findall(r"£\s?\d", txt)), "$": len(re.findall(r"\$\s?\d", txt)), "€": len(re.findall(r"€\s?\d", txt))}
if cur["£"] > cur["$"] and cur["£"] > cur["€"]: vote("GB", 2, f"£ prices ({cur['£']})")
country = max(score, key=score.get) if score else "US"
if not score: ev.append("no country evidence: default US, flagged")
C = {"US": dict(name="United States", lang="en-US", currency="USD", symbol="$", spelling="American English", postal="ZIP code", units="imperial (sq ft, ft)", hour12=True, phone_label="Phone", msg_tab="Text me"),
     "CA": dict(name="Canada", lang="en-CA", currency="CAD", symbol="$", spelling="Canadian English", postal="Postal code", units="metric and imperial as the site uses", hour12=True, phone_label="Phone", msg_tab="Text me"),
     "AU": dict(name="Australia", lang="en-AU", currency="AUD", symbol="$", spelling="Australian English", postal="Postcode", units="metric (m², m)", hour12=True, phone_label="Mobile", msg_tab="WhatsApp"),
     "NZ": dict(name="New Zealand", lang="en-NZ", currency="NZD", symbol="$", spelling="New Zealand English", postal="Postcode", units="metric (m², m)", hour12=True, phone_label="Mobile", msg_tab="WhatsApp"),
     "GB": dict(name="United Kingdom", lang="en-GB", currency="GBP", symbol="£", spelling="British English", postal="Postcode", units="metric, imperial where the site uses it", hour12=False, phone_label="Mobile", msg_tab="WhatsApp"),
     "IE": dict(name="Ireland", lang="en-IE", currency="EUR", symbol="€", spelling="Irish/British English", postal="Eircode", units="metric (m², m)", hour12=False, phone_label="Mobile", msg_tab="WhatsApp"),
     "ZA": dict(name="South Africa", lang="en-ZA", currency="ZAR", symbol="R", spelling="South African English", postal="Postal code", units="metric (m², m)", hour12=False, phone_label="Mobile", msg_tab="WhatsApp")}
L = dict(C.get(country, C["US"])); L["country"] = country
# spelling check on the site itself (the site's own habit wins over the country default)
us = len(re.findall(r"\b(colors?|favorite|organiz\w+|speciali[z]\w+|centers?|neighbor\w*|labor)\b", txt, re.I))
uk = len(re.findall(r"\b(colours?|favourite|organis\w+|speciali[s]\w+|centres?|neighbour\w*|labour)\b", txt, re.I))
L["spelling_evidence"] = {"us_forms": us, "uk_forms": uk}
if country in ("CA",) and us > uk * 2: L["spelling"] = "Canadian English (the site uses American spellings such as 'color')"
if country in ("GB", "AU", "NZ", "IE") and us > uk * 2 and us >= 4: L["spelling"] += " (note: the site mostly uses American spellings)"
L["date_example"] = "Thu, Oct 30" if country in ("US", "CA") else "Thu 30 Oct"
L["money_re"] = {"GBP": r"£\s?(\d[\d,]*(?:\.\d{2})?)", "EUR": r"€\s?(\d[\d,.]*)", "ZAR": r"\bR\s?(\d[\d,\s]*)"}.get(L["currency"], r"(?:US|CA|C|A|AU|NZ)?\$\s?(\d[\d,]*(?:\.\d{2})?)")
L["evidence"] = ev; L["scores"] = score; L["site_only_country"] = site_country; L["regions_found"] = REGIONS; L["site_only_agrees"] = site_country == country
json.dump(L, open(f"{d}/locale.json", "w"), indent=1)
print(f"locale: {country} {L['currency']} {L['lang']} | {L['spelling']} | {L['postal']} | evidence: {ev[:4]}")
