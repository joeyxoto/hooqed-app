"""Folds the owner's answers (owner-answer.json, typed on the 'needs your input' screen) into the build, so it carries on
from where it paused: the answer is added to the site text as the owner's own words (so every later check can trace it), the
optional second link is read and added as a page, and facts.json is patched (one-line answer) or re-extracted (new page / new text)."""
import sys, os, json, re, time, requests
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
d = sys.argv[1]; p = f"{d}/owner-answer.json"
if not os.path.exists(p): print("owner input: none"); sys.exit(0)
oa = json.load(open(p)); s = json.load(open(f"{d}/scrape.json"))
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36", "Accept-Language": "en"}
def text_of(html):
    sp = BeautifulSoup(html, "html.parser")
    for t in sp(["script", "style", "noscript", "svg"]): t.decompose()
    return re.sub(r"\n\s*\n+", "\n", sp.get_text("\n", strip=True))
def read(u):
    tx = ""
    try:
        r = requests.get(u, headers=H, timeout=20)
        if r.ok and "html" in r.headers.get("content-type", ""): tx = text_of(r.text)
    except Exception: pass
    if len(tx) < 300:   # JS page (e.g. a booking page): headless render, no clicking, no forms
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"]); pg = b.new_page(user_agent=H["User-Agent"])
                pg.goto(u, timeout=30000); pg.wait_for_timeout(3000); tx2 = text_of(pg.content()); b.close()
                if len(tx2) > len(tx): tx = tx2
        except Exception as e: print("owner link: headless read failed:", str(e)[:120])
    return tx[:12000]
new_text, new_page = False, False
for a in oa.get("answers", []):
    if a.get("applied"): continue
    if a.get("answer"):
        s["pages"].append({"url": "owner answer (typed on Hooqed)", "text": a["answer"].strip(), "owner": True}); new_text = True
    if a.get("link"):
        tx = read(a["link"])
        if re.search(r"just a moment|verify you are human|captcha", tx[:2000], re.I): tx = ""   # never try to get past a bot check
        a["link_chars"] = len(tx)
        if tx: s["pages"].append({"url": a["link"], "text": tx, "owner_link": True}); new_page = True
        print(f"owner link {a['link']}: {len(tx)} chars")
    a["applied"] = time.time()
json.dump(s, open(f"{d}/scrape.json", "w"), indent=1); json.dump(oa, open(p, "w"), indent=1)
last = (oa.get("answers") or [{}])[-1]
if (new_text or new_page) and os.path.exists(f"{d}/facts.json"):
    if new_page or last.get("case") == "site_empty":
        os.remove(f"{d}/facts.json"); print("owner input: new page or new description -> facts re-read")
    else:   # one line about the call: patch the facts, no AI call
        f = json.load(open(f"{d}/facts.json"))
        f["call_offer"] = last["answer"].strip()
        f.setdefault("offers_sold", []).append({"name": last["answer"].strip()[:120], "detail": "", "kind": "call", "price": "", "source": "owner answer (typed on Hooqed)"})
        json.dump(f, open(f"{d}/facts.json", "w"), indent=1); print("owner input: call offer set from the owner's answer (no AI call)")
for x in ("route.json", "hooq.raw.json", "hooq.json", "needs-input.json"):
    if (new_text or new_page) and os.path.exists(f"{d}/{x}"): os.remove(f"{d}/{x}")
print("owner input:", len(oa.get("answers", [])), "answer(s) folded in")
