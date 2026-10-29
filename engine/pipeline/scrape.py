import sys, json, re, requests, urllib.parse as U
from bs4 import BeautifulSoup
url = sys.argv[1]; out = sys.argv[2]
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36", "Accept-Language": "en"}
BROWSER = None
def render(u):
    global BROWSER
    from playwright.sync_api import sync_playwright
    if BROWSER is None:
        BROWSER = sync_playwright().start().chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"]).new_context(user_agent=H["User-Agent"], locale="en-US")
    pg = BROWSER.new_page()  # one shared context, so a passed check carries to later pages
    try:
        pg.goto(u, timeout=30000); pg.wait_for_timeout(2500)
        for _ in range(4):  # interstitials reload themselves; wait until real text appears
            try: n = len(pg.evaluate("document.body ? document.body.innerText : ''"))
            except Exception: n = 0
            if n >= 300: break
            pg.wait_for_timeout(3000)
        class R: pass
        r = R(); r.url = pg.url; r.text = pg.content(); r.ok = True; return r
    except Exception: return None
    finally: pg.close()
HEADLESS = bool(__import__('os').environ.get('HOOQ_FORCE_HEADLESS'))
def get(u):
    if HEADLESS: return render(u)
    try:
        r = requests.get(u, headers=H, timeout=20)
        if not (r.ok and "html" in r.headers.get("content-type", "")): return None
    except Exception: return None
    if "location.reload" in r.text[:3000] or len(BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)) < 300: return render(u) or r
    return r
r = get(url)
if not r or len(BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)) < 800 or "location.reload" in r.text[:3000]:
    HEADLESS = True; r = render(url); print("plain fetch thin or interstitial -> headless Chrome render")
import os
def limited(why, raw=None):
    """Bot-blocked or unreadable site: never fail. Build a LIMITED-FACTS page from what is available
    (search-result title/snippet recorded at selection time, plus any title/description the blocked page returned)."""
    hint = json.load(open(os.environ["HOOQ_HINT"])) if os.environ.get("HOOQ_HINT") and os.path.exists(os.environ["HOOQ_HINT"]) else {}
    bits = [f"Search result title: {hint['title']}" if hint.get("title") else "", f"Search result snippet: {hint['snippet']}" if hint.get("snippet") else "",
            f"Trade searched: {hint['trade']}" if hint.get("trade") else "", f"Town searched: {hint['town']}" if hint.get("town") else ""]
    if raw is not None:
        sp = BeautifulSoup(raw, "html.parser"); t = sp.title.get_text(strip=True) if sp.title else ""
        md = sp.find("meta", attrs={"name": "description"})
        if t and not re.search(r"just a moment|attention|verif|denied|captcha", t, re.I): bits.append(f"Page title: {t}")
        if md and md.get("content"): bits.append(f"Page description: {md['content']}")
    txt = "\n".join(b for b in bits if b)
    json.dump({"input_url": url, "final_url": url, "limited": True, "limited_why": why, "pages": [{"url": url + " (search result / page title only)", "text": txt}],
               "brand_hints": {"logos": [], "icons": [], "og_image": None, "theme_color": None, "colours": []}}, open(out, "w"), indent=1)
    print(f"LIMITED FACTS: {why}. Continuing with {len(txt)} chars from the search result and page title (owner can add 3 details later).")
    sys.exit(0)
if not r: limited("site did not load, even in a headless browser")
base = r.url; host = U.urlparse(base).netloc
soup = BeautifulSoup(r.text, "html.parser")
def text(s):
    for t in s(["script", "style", "noscript", "svg"]): t.decompose()
    return re.sub(r"\n\s*\n+", "\n", s.get_text("\n", strip=True))
links, anchor = [], {}
for a in soup.find_all("a", href=True):
    h = U.urljoin(base, a["href"]).split("#")[0]
    if U.urlparse(h).netloc == host and not re.search(r"\.(jpg|png|pdf|webp)$|wp-login|/feed|tel:|mailto:", h):
        if h not in links: links.append(h)
        anchor[h] = (anchor.get(h, "") + " " + a.get_text(" ", strip=True))[:200]
# ask-not-fail: pages that say what people buy or book come first (Work with me, Coaching, Apply, Book a call, Services, Programs), by link address or link text
OFFER = re.compile(r"work[- ]?with|coach|consult|apply|application|book|call|program|services?\b|offer|mentor|session|strateg|join|start[- ]here|pricing|packages|membership|courses?\b", re.I)
pri = sorted(links, key=lambda h: (not OFFER.search(h + " " + anchor.get(h, "")), not re.search(r"servic|price|pricing|prices|rates|cost|menu|packages|book|review|testimon|about|area|contact|faq|repair|install", h, re.I), len(h)))
# brand hints from home page
icons = [U.urljoin(base, l["href"]) for l in soup.find_all("link", href=True) if any(x in " ".join(l.get("rel", [])).lower() for x in ("icon", "apple-touch"))]
logos = []
for im in soup.find_all("img"):
    src = im.get("src") or im.get("data-src") or ""
    if src and re.search(r"logo", src + " " + " ".join(im.get("class", [])) + (im.get("alt") or ""), re.I): logos.append(U.urljoin(base, src))
logos = [l for l in logos if not re.search(r"cookie|consent|cky|powered|badge|accredit|certif|award|member|gas-?safe|oftec|niceic|napit|trustmark|checkatrade|which|fmb|bbb|angi|homeadvisor|yelp|houzz|nextdoor|thumbtack|google|facebook|payment|visa|mastercard", l, re.I)] or logos  # drop third-party / accreditation badges
import logos as _lg
logo_cands = _lg.extract(r.text, base)
og = soup.find("meta", property="og:image")
STATE = re.compile(r":(hover|focus|focus-visible|focus-within|active|visited)\b", re.I)
def resting_css(t):   # drop CSS rules that only style a :hover/:focus/:active/:visited state: those colours are never the resting look
    # v8: only inside <style> blocks, with bounded runs (the old whole-page pattern backtracked for minutes on big pages with stray braces)
    rule = re.compile(r"([^{}]{1,3000})\{([^{}]{0,20000})\}")
    fix = lambda css: rule.sub(lambda m: "" if all(STATE.search(sel) for sel in m.group(1).split(",")) else m.group(0), css)
    return re.sub(r"(<style[^>]*>)(.*?)(</style>)", lambda m: m.group(1) + fix(m.group(2)) + m.group(3), t, flags=re.S | re.I)
colors = re.findall(r"#[0-9a-fA-F]{6}\b", resting_css(r.text))
theme = soup.find("meta", attrs={"name": "theme-color"})
pages = [{"url": base, "text": text(BeautifulSoup(r.text, "html.parser"))[:20000]}]
for h in pri[:14]:
    if h.rstrip("/") == base.rstrip("/"): continue
    rr = get(h)
    if rr:
        tx = text(BeautifulSoup(rr.text, "html.parser"))[:12000]
        if len(tx) < 300 and re.search(r"one moment|being verified|just a moment|checking your browser|verify you are human", tx, re.I): continue  # still a check page: skip it
        pages.append({"url": rr.url, "text": tx})
from collections import Counter
json.dump({"input_url": url, "final_url": base, "pages": pages, "brand_hints": {"logos": logos[:6], "logo_cands": logo_cands, "icons": icons, "og_image": og["content"] if og else None,
  "theme_color": theme["content"] if theme else None, "colours": Counter(c.lower() for c in colors).most_common(12)}}, open(out, "w"), indent=1)
print("scraped", len(pages), "pages,", sum(len(p["text"]) for p in pages), "chars; logos", logos[:2], "icons", icons[:3])

tot = sum(len(p["text"]) for p in pages); wall = re.search(r"just a moment|verify you are human|access denied|captcha|attention required", pages[0]["text"], re.I)
if tot < 1500 or (wall and tot < 6000):
    if not HEADLESS:
        HEADLESS = True; rr = render(url)
        if rr and len(BeautifulSoup(rr.text, "html.parser").get_text(" ", strip=True)) > 1500 and not re.search(r"just a moment|verify you are human|access denied|captcha|attention required", rr.text[:20000], re.I):
            print("blocked on plain fetch; headless retry worked: re-run with headless"); os.environ["HOOQ_FORCE_HEADLESS"] = "1"; os.execv(sys.executable, [sys.executable] + sys.argv)
    limited(f"bot check or block ({tot} chars{', bot wall' if wall else ''}) after a headless retry", r.text)
