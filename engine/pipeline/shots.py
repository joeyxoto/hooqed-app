import sys, json, os
from playwright.sync_api import sync_playwright
d = os.path.abspath(sys.argv[1]); h = json.load(open(f"{d}/hooq.json")); os.makedirs(f"{d}/screens", exist_ok=True)
J = h["jobs"]; URG = h["urg_re"]
def ans(j, pick=1, timing="weeks"):
    return ",".join([f"job:{j['id']}"] + [f"q{i}:{q['options'][min(pick, len(q['options']) - 1)]['id']}" for i, q in enumerate(j["questions"])] + [f"timing:{timing}"])
j0 = J[0]; A0 = ans(j0); n = 2 + len(j0["questions"]) + 1   # job, own questions, timing, contact
flow = [("intro", "")] + [(f"q{i}", f"s=q&i={i}&a=job:{j0['id']}") for i in range(1, n + 1)]
res = [(f"result-{j['id']}", f"s=result&a={ans(j)}&name=Sarah") for j in J] + [("result-other", "s=result&a=job:other,timing:planning&name=Sarah")]
mob = flow + res + [(f"visitor-{i}", f"s=result&a={v['a']}&name=Sarah") for i, v in enumerate(h.get("visitors", []))]
mob += [("book-calendar", f"s=result&a={A0}&tab=cal&d=1&t=10:30&scroll=book"), ("book-callback", f"s=result&a={A0}&tab=cb&cb=Afternoon&scroll=book"),
        ("book-whatsapp", f"s=result&a={A0}&tab=wa&scroll=book"), ("book-textme", f"s=result&a={A0}&tab=cal&textme=1&scroll=book"), ("done-owner", f"s=done&a={A0}&tab=cal&d=1&t=10:30&name=Sarah&owner=1")]
desk = [("intro", ""), ("q1", f"s=q&i=1"), (f"result-{j0['id']}", f"s=result&a={A0}&tab=cal&d=1&t=10:30&name=Sarah"), ("done-owner", f"s=done&a={A0}&tab=cal&d=1&t=10:30&name=Sarah&owner=1")]
p3 = [("intro", ""), ("q2", f"s=q&i=2&a=job:{j0['id']}"), ("book-textme", f"s=result&a={A0}&tab=cal&textme=1&scroll=book")] + [(f"result-{j['id']}", f"s=result&a={ans(j)}&name=Sarah") for j in J] + [("done-owner", f"s=done&a={A0}&tab=cb&cb=Afternoon&name=Sarah&owner=1")]
import re as _re
def site_pc(cc):
    """v7: the example postcode in the lead brief is the business's OWN postal code as printed on its site (pattern per country); else a country-shaped default"""
    pat = {"US": r"\b[A-Z]{2}\s+(\d{5})(?:-\d{4})?\b", "CA": r"\b([ABCEGHJ-NPRSTVXY]\d[A-Z]\s?\d[A-Z]\d)\b", "AU": r"\b(?:NSW|VIC|Vic\.?|QLD|Qld|SA|WA|TAS|Tas|ACT|NT|Victoria|Queensland|New South Wales|Tasmania|Western Australia|South Australia)\s*,?\s*(\d{4})\b",
           "NZ": r"\b(\d{4})\s*(?:New Zealand|NZ)\b", "GB": r"\b([A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})\b", "IE": r"\b([AC-FHKNPRTV-Y]\d{2}\s?[AC-FHKNPRTV-Y0-9]{4})\b"}.get(cc)
    try: pages = json.load(open(f"{d}/scrape.json"))["pages"]
    except Exception: pages = []
    if pat:
        for pg in pages:
            m = _re.search(pat, pg.get("text") or "")
            if m: return m.group(1).upper()
    return ""   # no postcode on the site: the example lead brief shows none rather than a made-up one
PC = site_pc((h.get("locale") or {}).get("country")); V = json.load(open(f"{d}/validation.json")); ALLOW = V["allowed_figures"]; MRE = V["money_re"]
CHECK = """([urg,allow,mre])=>{const p=[];const t=document.body.innerText;if(/\\{[a-z_]+\\}|undefined|NaN|\\bnull\\b|\\[object/.test(t))p.push('token');
[...document.images].forEach(i=>{if(!i.naturalWidth)p.push('broken img '+i.src.split('/').pop())});
if(document.documentElement.scrollWidth>window.innerWidth+1)p.push('overflow '+document.documentElement.scrollWidth);
if(/landing page|lead page/i.test(t))p.push('banned text');
for(const m of t.matchAll(/(?<![\\d,.$£€])(?:\\+\\d{1,3}[\\s.-]?)?(?:\\(\\d{1,4}\\)[\\s.-]?)?\\d{2,5}[\\s.-]?\\d{3,4}(?:[\\s.-]?\\d{3,4})?(?![\\d,])/g))if(m[0].replace(/\\D/g,'').length>=9)p.push('PHONE NUMBER SHOWN '+m[0]);
for(const m of t.matchAll(new RegExp(mre,'g'))){const n=Math.trunc(parseFloat(m[1].replace(/,/g,'')));if(!allow.includes(n))p.push('UNTRACED PRICE '+m[0])}
const m=t.match(new RegExp(urg,'i'));if(m)p.push('urgency word: '+m[0]);
if(/\\bevery [a-z]+s (job|project)|\\ba [aeiou]/i.test(t))p.push('grammar: '+(t.match(/\\bevery [a-z]+s (job|project)|\\ba [aeiou]\\w*/i)||[''])[0]);return p}"""
probs = []; briefs = {}
names = ["Sarah", "James", "Priya", "Tom", "Aisha"]; tabs = [("cal", "&d=1&t=10:30"), ("cb", "&cb=Afternoon"), ("wa", ""), ("cal", "&d=3&t=14:00"), ("cb", "&cb=Morning")]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    for file, tag, sets in (("hooq.html", "", (("mobile", {"width": 390, "height": 844}, 2, mob), ("desktop", {"width": 1280, "height": 800}, 1, desk))),
                            ("hooq-path3.html", "p3-", (("mobile", {"width": 390, "height": 844}, 2, p3),))):
        base = "file://" + d + "/" + file
        for kind, vp, dpr, lst in sets:
            pg = b.new_page(viewport=vp, device_scale_factor=dpr); jserr = []; pg.on("pageerror", lambda e: jserr.append(str(e)))
            for name, q in lst:
                pg.goto(base + ("?" + q if q else "")); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(350)
                for x in pg.evaluate(CHECK, [URG, ALLOW, MRE]): probs.append(f"{tag}{kind}-{name}: {x}")
                if jserr: probs.append(f"{tag}{kind}-{name}: SCRIPT ERROR {jserr[0]}"); jserr.clear()
                if len(pg.evaluate("document.getElementById('app').innerText.trim()")) < 80: probs.append(f"{tag}{kind}-{name}: BLANK SCREEN")
                pg.screenshot(path=f"{d}/screens/{tag}{kind}-{name}.png")
                if name.startswith("result-") and kind == "mobile": pg.add_style_tag(content=".sticky{display:none!important}"); pg.screenshot(path=f"{d}/screens/{tag}{kind}-{name}-full.png", full_page=True)
            pg.close()
        pg = b.new_page(); bl = []
        for i, j in enumerate(J):
            a = ans(j, i, ["weeks", "months", "planning"][i % 3])
            pg.goto(base + f"?s=result&a={a}&tab={tabs[i][0]}{tabs[i][1]}&pc={PC}"); pg.wait_for_timeout(200)
            bl.append(pg.evaluate(f"leadBrief('{names[i]}')"))
        briefs[file] = bl; pg.close()
    b.close()
json.dump(probs, open(f"{d}/render-check.json", "w"), indent=1)
V["render"] = {"screens_checked": len(os.listdir(f"{d}/screens")), "untraced_prices": [x for x in probs if "UNTRACED PRICE" in x], "phones_shown": [x for x in probs if "PHONE NUMBER" in x]}
V["render"]["status"] = "PASS" if not (V["render"]["untraced_prices"] or V["render"]["phones_shown"]) else "FAIL"; json.dump(V, open(f"{d}/validation.json", "w"), indent=1); json.dump(briefs["hooq.html"], open(f"{d}/lead-briefs.json", "w"), indent=1); json.dump(briefs["hooq-path3.html"], open(f"{d}/lead-briefs-path3.json", "w"), indent=1)
print("screens:", len(os.listdir(f"{d}/screens")), "| render problems:", probs or "none")
[print(" brief:", x) for x in briefs["hooq.html"]]
if any("SCRIPT ERROR" in x or "BLANK" in x or "UNTRACED PRICE" in x or "PHONE NUMBER" in x for x in probs): sys.exit(5)
