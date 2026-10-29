import sys, json, io, requests, urllib.parse as U, colorsys
from PIL import Image
import fonts as fontsmod
d = sys.argv[1]; s = json.load(open(f"{d}/scrape.json")); bh = s["brand_hints"]; host = U.urlparse(s["final_url"]).netloc
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36"}
def fetch(u):
    if u.startswith("data:image/"):   # a logo inlined as a data URI (seen on page builders)
        try:
            import base64; head, data = u.split(",", 1); b = base64.b64decode(data) if ";base64" in head else U.unquote(data).encode()
            if "svg" in head: return b, "svg"
            Image.open(io.BytesIO(b)).load(); return b, "raster"
        except Exception: return None, None
    for v in (u, u.replace("https://", "http://")):
        try:
            r = requests.get(v, headers=H, timeout=20)
            if r.ok and not r.content[:200].lstrip().lower().startswith((b"<!doctype", b"<html")):
                if b"<svg" in r.content[:500]: return r.content, "svg"
                im = Image.open(io.BytesIO(r.content)); im.load(); return r.content, "raster"
        except Exception: pass
    return browser_fetch(u)
CTX = None
def browser_fetch(u):
    """Sites behind a bot check: load the home page in headless Chrome once, then fetch the image with that session."""
    global CTX
    try:
        if CTX is None:
            from playwright.sync_api import sync_playwright
            CTX = sync_playwright().start().chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"]).new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36")
            pg = CTX.new_page(); pg.goto(s["final_url"], timeout=30000)
            for _ in range(6):
                pg.wait_for_timeout(3000)
                try:
                    if len(pg.evaluate("document.body ? document.body.innerText : ''")) >= 300: break
                except Exception: pass
            pg.close()
        c = b""
        for _ in range(3):
            pg = CTX.new_page(); r = pg.goto(u, timeout=20000); pg.wait_for_timeout(1500)
            try: c = r.body() if r else b""
            except Exception: c = b""
            pg.close()
            if c and not c[:200].lstrip().lower().startswith((b"<!doctype", b"<html")): break
            pg = CTX.new_page(); pg.goto(s["final_url"], timeout=30000); pg.wait_for_timeout(6000); pg.close()
        if c and not c[:200].lstrip().lower().startswith((b"<!doctype", b"<html")):
            if b"<svg" in c[:500]: return c, "svg"
            im = Image.open(io.BytesIO(c)); im.load(); return c, "raster"
    except Exception: pass
    return None, None
def _root(n):
    n = n.lower().split(":")[0]; parts = n.split(".")
    return ".".join(parts[-3:]) if len(parts) >= 3 and parts[-2] in ("co", "org", "ac", "gov", "ltd", "me", "net") and len(parts[-1]) == 2 else ".".join(parts[-2:])
own = lambda u: _root(U.urlparse(u).netloc) == _root(host)   # the business's own domain, including media./cdn. subdomains
import re as _re
BADGE = _re.compile(r"cookie|consent|cky|powered|safe|oftec|aphc|niceic|napit|trustmark|checkatrade|which|fmb|bbb|angi|homeadvisor|yelp|houzz|nextdoor|thumbtack|certif|accredit|approved|member|award|badge|google|facebook|visa|mastercard|data:image", _re.I)
# LOGO (v4.1): prefer the header/nav logo. Reject partner / supplier / manufacturer / accreditation / badge images and any image whose alt
# text or file name names a different brand. Validator: the chosen mark's alt, file name or place (header home link on the business's own site)
# must tie it to THIS business; otherwise a clean text wordmark. Every candidate and its verdict is kept for the owner's "Is this your logo?" check.
import os
ICONISH = _re.compile(r"favicon|apple-touch|touch-icon|site-?icon|cropped-.*-(32|180|192|270|512)x\d+|/icon[-_.]", _re.I)
FOLDER = _re.compile(r"partner|supplier|manufactur|vendor|/brands?/|accredit|badge|certif|award|member|affiliat|sponsor|client|chamber|associat|trust|seal|/cert", _re.I)
GEN = set("logo logos img image images png jpg jpeg svg webp gif primary secondary main site header footer nav white black dark light color colour full small large retina mobile desktop horizontal vertical stacked new final copy cropped untitled design scaled transparent trans wordmark mark icon alt no tagline with without default custom web version min format the and of a for retina2x".split())
f_ = json.load(open(f"{d}/facts.json")) if os.path.exists(f"{d}/facts.json") else {}
NAME_STOP = {"the", "and", "ltd", "llc", "inc", "co", "company", "limited", "pty", "services", "service", "group", "www", "com", "yes", "we", "do", "our", "your",
             # trade words name a kind of business, not THIS business ("standard-plumbing-logo" is a supplier, not Hyde Park Plumbing)
             "plumbing", "plumber", "plumbers", "roofing", "roofer", "roofers", "electric", "electrical", "electrician", "electricians", "homes", "home", "builders", "builder", "building",
             "construction", "bathrooms", "bathroom", "kitchens", "kitchen", "heating", "cooling", "air", "hvac", "pet", "pets", "spa", "grooming", "groomer", "dog", "salon", "landscaping",
             "painting", "painters", "flooring", "windows", "doors", "solar", "pest", "control", "cleaning", "renovations", "remodeling", "contractors", "contracting", "mechanical", "drains", "gas"}
ntok = {t for t in _re.findall(r"[a-z0-9]{3,}", (f_.get("name") or "").lower().replace("'", "").replace("\u2019", "")) if t not in NAME_STOP} | {t for t in _re.findall(r"[a-z0-9]{3,}", _root(host).split(".")[0].lower()) if t not in NAME_STOP}
dom = _root(host).split(".")[0].lower().replace("-", "")
def toks(x): return [t for t in _re.findall(r"[a-z]+", (x or "").lower())]
def hashy(t): return len(t) >= 6 and (_re.search(r"\d", t) or not _re.search(r"[aeiou]", t))
def judge(c):
    u = c.get("url") or ""; fn = U.unquote(u.split("/")[-1].split("?")[0]); alt = c.get("alt") or ""
    alt_t, fn_t = set(toks(alt)), set(t for t in toks(_re.sub(r"\.[a-z0-9]+$", "", fn)) if not hashy(t))
    m_alt = bool(alt_t & ntok) or dom in alt.lower().replace(" ", ""); m_fn = bool(fn_t & ntok) or (dom and dom in fn.lower().replace("-", "").replace("_", ""))
    if u and FOLDER.search(u.split("?")[0]): return None, "partner / supplier / accreditation / badge folder or file"
    fnc = _re.sub(r"[^a-z0-9]", "", fn.lower())   # v7: 'shaggys_logo.png' names Shaggy's: the business name inside the file name ties it, never rejects it
    if any(len(t) >= 4 and t in fnc for t in ntok): m_fn = True
    if m_alt or m_fn: return ("alt text names the business" if m_alt else "file name names the business"), None
    other_alt = alt_t - GEN - {"logo"}; other_fn = fn_t - GEN
    if other_alt: return None, f"alt text names another brand: '{alt[:40]}'"
    if other_fn: return None, f"file name names something else: '{fn[:40]}'"
    if c.get("header") and c.get("link_home") and (c.get("inline_svg") or own(u)): return "header home-link mark on the business's own site", None
    return None, "nothing ties it to the business (not in the header, no name in alt or file name)"
# INLINE SVG LOGOS (ask-not-fail): the scrape reads the header SVG with an HTML parser, which lower-cases attribute names (viewbox, gradientunits)
# and keeps prefixes (xlink:href) without their namespace. As a stand-alone file that is broken XML and the <img> shows nothing (Gym Group).
# Restore the SVG names, declare the namespaces, size it from its viewBox (rem/em/% sizes mean nothing outside the page) and drop page classes.
SVG_CAMEL = {a.lower(): a for a in "viewBox preserveAspectRatio gradientUnits gradientTransform patternUnits patternContentUnits patternTransform clipPathUnits maskUnits maskContentUnits markerUnits markerWidth markerHeight refX refY spreadMethod stdDeviation textLength lengthAdjust startOffset baseFrequency numOctaves kernelMatrix tableValues filterUnits primitiveUnits".split()}
SVG_TAGS = {t.lower(): t for t in "clipPath linearGradient radialGradient foreignObject textPath feGaussianBlur feOffset feBlend feColorMatrix feComposite feFlood feMerge feMergeNode feMorphology feTurbulence feDropShadow".split()}
def fix_svg(b):
    t = b.decode("utf-8", "replace")
    t = _re.sub(r'(?<=[\s<])([a-zA-Z]+)(?==)', lambda m: SVG_CAMEL.get(m.group(1).lower(), m.group(1)), t)
    t = _re.sub(r'(</?)([a-zA-Z]+)', lambda m: m.group(1) + SVG_TAGS.get(m.group(2).lower(), m.group(2)), t)
    head = _re.match(r"<svg\b[^>]*>", t)
    if head:
        h0 = head.group(0); h1 = h0
        if 'xmlns="' not in h1: h1 = h1.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
        if "xlink:" in t and "xmlns:xlink" not in h1: h1 = h1.replace("<svg", '<svg xmlns:xlink="http://www.w3.org/1999/xlink"', 1)
        h1 = _re.sub(r'\s(class|aria-hidden|role|data-testid|focusable)="[^"]*"', "", h1)
        vb = _re.search(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', h1)
        for dim in ("width", "height"):
            m_ = _re.search(rf'\s{dim}="([^"]*)"', h1)
            if m_ and not _re.fullmatch(r"[\d.]+(px)?", m_.group(1).strip()): h1 = h1.replace(m_.group(0), "")
        if vb and not _re.search(r'\swidth="', h1): h1 = h1.replace("<svg", f'<svg width="{vb.group(1)}" height="{vb.group(2)}"', 1)
        t = t.replace(h0, h1, 1)
    return t.encode()
OWNER = json.load(open(f"{d}/owner-check.json")) if os.path.exists(f"{d}/owner-check.json") else {}
# ONE RENDERED VISIT (ask-not-fail), generic for every site: the home page in headless Chrome at desktop (1280x800) and phone (390x844) width,
# consent banners hidden, no mouse event ever sent (so nothing is in a :hover/:focus/:active state). Saved: render-top.png (the real top of the
# page), home-fold.png (same view with photos hidden), render-logo.png (the header mark as painted) and render.json: wide coloured bars in the
# top 600px (header / nav / promo), the site's buttons at rest, and the header logo as the browser resolved it. Cached: re-renders never reload the site.
# cookie/consent banners and their dark page overlays are hidden before any colour is read: an overlay dims every colour under it
# (Gym Group: the OneTrust 50% overlay turned the resting button green #b2ff00 into #597f00 and the blue #0050ef into #002776).
# No mouse event is ever sent, so no :hover/:focus/:active state applies: every colour read is the element's resting colour.
CONSENT_HIDE = ("#onetrust-consent-sdk,#onetrust-banner-sdk,.onetrust-pc-dark-filter,#CybotCookiebotDialog,#CybotCookiebotDialogBodyUnderlay,#usercentrics-root,"
                ".cky-consent-container,.cky-overlay,#cookie-law-info-bar,.cc-window,.cc-banner,#cmplz-cookiebanner-container,.fc-consent-root,#qc-cmp2-container,"
                "[id*=cookie-banner i],[class*=cookie-banner i],[id*=consent-banner i],[class*=consent-banner i]{display:none!important}")
# RENDERED BARS (ask-not-fail): the colours the site actually paints on its header / nav / promo bars, read from the live page's computed
# styles in their resting state (wide elements in the top 600px, consent banners hidden). Weighted by painted area. When the site's own
# header or top bar is a real colour (Gym Group: royal blue header, lime promo bar) that is the brand colour; the logo comes next.
BARS_JS = r"""() => { const out = [], vw = innerWidth;
 for (const el of document.querySelectorAll('body *')) {
  const r = el.getBoundingClientRect(); if (r.top > 600 || r.bottom < 0 || r.width < vw * .6 || r.height < 16 || r.height > 220) continue;
  const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < .5) continue;
  if (el.closest('[id*=cookie i],[class*=cookie i],[id*=consent i],[class*=consent i],[id*=onetrust i],[aria-modal=true]')) continue;
  const bg = cs.backgroundColor; if (/rgba\(0, 0, 0, 0\)|transparent/.test(bg)) continue;
  out.push({bg, top: Math.round(r.top), h: Math.round(r.height), w: Math.round(r.width), tag: el.tagName.toLowerCase(), cls: String(el.className || '').slice(0, 60)});
 } return out; }"""
CTA_JS = r"""() => {
 const out = [], seen = new Set();
 const skip = el => el.closest('[id*=cookie i],[class*=cookie i],[id*=consent i],[class*=consent i],[id*=onetrust i],[class*=onetrust i],[id*=gdpr i],[class*=gdpr i],[aria-modal=true]');
 for (const el of document.querySelectorAll('a,button,input[type=submit],input[type=button],[role=button]')) {
  const r = el.getBoundingClientRect(); if (r.width < 40 || r.height < 22 || r.width > 640 || r.height > 110) continue;
  const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < .4) continue;
  if (skip(el)) continue;
  const txt = (el.innerText || el.value || '').trim(); if (!txt || txt.length > 40 || /cookie|accept|reject|consent|preferences/i.test(txt)) continue;
  let bg = cs.backgroundColor, src = 'self';
  if (/rgba\(0, 0, 0, 0\)|transparent/.test(bg)) {   // painted by an inner span / ::before
   const k = el.firstElementChild; const ks = k ? getComputedStyle(k) : null; const bf = getComputedStyle(el, '::before');
   if (ks && !/rgba\(0, 0, 0, 0\)|transparent/.test(ks.backgroundColor) && k.getBoundingClientRect().width >= r.width * .8) { bg = ks.backgroundColor; src = 'child'; }
   else if (bf && bf.content !== 'none' && !/rgba\(0, 0, 0, 0\)|transparent/.test(bf.backgroundColor)) { bg = bf.backgroundColor; src = 'before'; }
   else continue;
  }
  const key = bg + '|' + Math.round(r.top) + '|' + Math.round(r.left); if (seen.has(key)) continue; seen.add(key);
  let fx = false; for (let a = el; a && a !== document.body; a = a.parentElement) { const p = getComputedStyle(a).position; if (p === 'fixed') { fx = true; break; } }
  out.push({bg, txt: txt.slice(0, 30), w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top + scrollY), src, fx, href: (el.getAttribute('href') || '').slice(0, 60)});
 }
 return out; }"""
LOGO_JS = r"""() => {   // the header home-link mark as the browser shows it: <img> currentSrc (srcset / lazy-load resolved), inline <svg>, or a CSS background
 const home = [...document.querySelectorAll('a[href]')].filter(a => { try { const u = new URL(a.href, location.href); return u.host.replace(/^www\./, '') === location.host.replace(/^www\./, '') && /^\/?(index\.html?|home|en|en-gb|en-us)?\/?$/i.test(u.pathname); } catch (e) { return false; } });
 const vis = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return r.width >= 24 && r.height >= 14 && r.top < 260 && r.bottom > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > .3; };
 const pool = home.concat([...document.querySelectorAll('header [class*=logo i],header [id*=logo i],[class*=logo i],[id*=logo i]')]);
 const box = el => { const r = el.getBoundingClientRect(); return {x: r.x, y: r.y + scrollY, w: r.width, h: r.height}; };
 for (const a of pool) {
  if (!vis(a)) continue;
  const img = a.matches('img') ? a : [...a.querySelectorAll('img')].find(vis);
  if (img && (img.currentSrc || img.src) && !/^data:image\/(gif|svg\+xml)/.test(img.currentSrc || img.src)) return {kind: 'img', url: img.currentSrc || img.src, alt: img.alt || '', box: box(img)};
  const svg = a.matches('svg') ? a : [...a.querySelectorAll('svg')].find(vis);
  if (svg) {
   const c = svg.cloneNode(true), src = [svg, ...svg.querySelectorAll('*')], dst = [c, ...c.querySelectorAll('*')];
   src.forEach((e, i) => { const cs = getComputedStyle(e); for (const k of ['fill', 'stroke']) { const v = cs[k]; if (v && !/url\(/.test(v)) dst[i].setAttribute(k, v); } if (cs.display === 'none') dst[i].setAttribute('display', 'none'); });
   const sr = svg.getBoundingClientRect(); ['class', 'style', 'aria-hidden', 'role'].forEach(k => c.removeAttribute(k)); c.setAttribute('width', Math.round(sr.width)); c.setAttribute('height', Math.round(sr.height));
   if (!c.getAttribute('xmlns')) c.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
   return {kind: 'svg', svg: new XMLSerializer().serializeToString(c), alt: a.getAttribute('aria-label') || a.title || '', box: box(svg)}; }
  for (const e of [a, ...a.querySelectorAll('*')]) { if (!vis(e)) continue; for (const ps of [null, '::before', '::after']) { const bi = getComputedStyle(e, ps).backgroundImage; const m = bi && bi.match(/url\(["']?([^"')]+)/); if (m) return {kind: 'bg', url: new URL(m[1], location.href).href, alt: a.getAttribute('aria-label') || a.title || '', box: box(e)}; } }
 }
 return null; }"""
render_p = f"{d}/render.json"; top_png = f"{d}/render-top.png"; fold = f"{d}/home-fold.png"
if os.path.exists(render_p): R = json.load(open(render_p))
else:
    R = {"bars": [], "buttons": [], "logo": None, "error": None}
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            bz = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
            for vw, vh in ((1280, 800), (390, 844)):   # desktop and phone: sites often hide the main button on one of them
                pg = bz.new_page(viewport={"width": vw, "height": vh}, user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36")
                pg.goto(s["final_url"], timeout=30000); pg.wait_for_timeout(3500); pg.add_style_tag(content=CONSENT_HIDE); pg.wait_for_timeout(300)
                R["buttons"] += [dict(b_, vw=vw) for b_ in pg.evaluate(CTA_JS)]
                if vw == 1280:
                    R["bars"] = pg.evaluate(BARS_JS); R["logo"] = pg.evaluate(LOGO_JS); pg.screenshot(path=top_png)
                    try:   # v8 FONT MATCH: the site's own heading / body / button type, as the browser painted it (+ crops for the side-by-side)
                        R["fonts"] = pg.evaluate(fontsmod.FONTS_JS)
                        for role in ("heading", "body"):
                            bx_ = ((R["fonts"] or {}).get(role) or {}).get("box")
                            if bx_ and bx_["w"] >= 20 and bx_["h"] >= 8:
                                pg.screenshot(path=f"{d}/font-{role}.png", full_page=True, clip={"x": max(0, bx_["x"] - 4), "y": max(0, bx_["y"] - 4), "width": min(bx_["w"] + 8, 1270), "height": min(bx_["h"] + 8, 260)})
                    except Exception as e_: R["fonts_error"] = str(e_)[:160]
                    bx = (R["logo"] or {}).get("box")
                    if bx and bx["w"] >= 24 and bx["y"] < 800:   # the mark exactly as painted on the page: last-resort logo when no file loads
                        try: pg.screenshot(path=f"{d}/render-logo.png", clip={"x": max(0, bx["x"]), "y": max(0, bx["y"]), "width": min(bx["w"], 1280), "height": min(bx["h"], 400)})
                        except Exception: pass
                    pg.add_style_tag(content="img,video,picture,iframe,canvas,svg image{visibility:hidden!important}*{background-image:none!important}")
                    pg.wait_for_timeout(300); pg.screenshot(path=fold)
                pg.close()
            bz.close()
    except Exception as e: R["error"] = str(e)[:160]
    if R["bars"] or R["buttons"] or R["logo"]: json.dump(R, open(render_p, "w"), indent=1)
if "fonts" not in R and not R.get("error"):   # render.json from before font match: one short visit for the fonts only
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            bz = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"]); pg = bz.new_page(viewport={"width": 1280, "height": 800})
            pg.goto(s["final_url"], timeout=30000); pg.wait_for_timeout(3500); pg.add_style_tag(content=CONSENT_HIDE); pg.wait_for_timeout(300)
            R["fonts"] = pg.evaluate(fontsmod.FONTS_JS)
            for role in ("heading", "body"):
                bx_ = ((R["fonts"] or {}).get(role) or {}).get("box")
                if bx_ and bx_["w"] >= 20 and bx_["h"] >= 8:
                    pg.screenshot(path=f"{d}/font-{role}.png", full_page=True, clip={"x": max(0, bx_["x"] - 4), "y": max(0, bx_["y"] - 4), "width": min(bx_["w"] + 8, 1270), "height": min(bx_["h"] + 8, 260)})
            bz.close()
        json.dump(R, open(render_p, "w"), indent=1)
    except Exception as e: R["fonts_error"] = str(e)[:160]
if not R.get("fonts"):
    try: R["fonts"] = fontsmod.from_css(s["final_url"]); R["fonts_from"] = "css"
    except Exception as e: R["fonts_error"] = str(e)[:160]
FONTS = fontsmod.resolve(R.get("fonts"))
if R.get("fonts_from") == "css":
    for v in FONTS.values():
        if v.get("why"): v["why"] += " (read from the site's CSS: the browser visit was refused)"
json.dump(FONTS, open(f"{d}/fonts.json", "w"), indent=1)
print("fonts:", "; ".join(f"{r} {v.get('detected') or '-'} -> {v.get('family') or 'template'} ({v['source']})" for r, v in FONTS.items()))
def rgb_hex(c):
    m = _re.match(r"rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?", c or "")
    if not m or (m.group(4) is not None and float(m.group(4)) < .8): return None
    return "#%02x%02x%02x" % tuple(int(float(m.group(i))) for i in (1, 2, 3))
cands = bh.get("logo_cands")
if cands is None: cands = [{"url": u, "alt": "", "header": False, "link_home": False, "order": k} for k, u in enumerate(dict.fromkeys(bh["logos"]))]
cands = sorted(cands, key=lambda c: (not c.get("header"), c.get("footer", False), c.get("order", 0)))
report, ok = [], []
for c in cands:
    if c.get("url") and ICONISH.search(c["url"]): report.append({**{k: c.get(k) for k in ("url", "alt", "header")}, "status": "rejected", "why": "favicon / site icon"}); continue
    why_ok, why_no = judge(c)
    report.append({**{k: c.get(k) for k in ("url", "alt", "header")}, "inline_svg": bool(c.get("inline_svg")), "status": "candidate" if why_ok else "rejected", "why": why_ok or why_no})
    if why_ok: ok.append((c, why_ok))
logo, rejected = None, []
if OWNER.get("logo") == "wordmark": ok = []
elif OWNER.get("logo"): ok = [({"url": OWNER["logo"], "alt": "owner-picked"}, "picked by the owner (simulated owner check)")]
for c, why in ok:
    if c.get("inline_svg"):
        logo = {"kind": "logo", "url": "inline svg in the header home link", "type": "svg", "bytes": c["inline_svg"].encode(), "check": why}; break
    u = c["url"]; full = _re.sub(r"-\d{2,4}x\d{2,4}(?=\.\w+(\?|$))", "", u)   # WordPress thumbnail: use the full-size original when it exists
    b, t = fetch(full) if full != u else (None, None)
    if b: u = full
    else: b, t = fetch(u)
    if not b: rejected.append((u, "could not load")); continue
    if t == "raster":
        im = Image.open(io.BytesIO(b)).convert("RGBA"); bb = im.getbbox(); im2 = im.crop(bb) if bb else im
        w, hgt = im2.size; ar = w / max(1, hgt)
        if (w < 120 or hgt < 24) and not (OWNER.get("logo") and w >= 64 and hgt >= 24): rejected.append((u, f"too small {w}x{hgt}")); continue
        if ar < 1.25 and w < 240 and not OWNER.get("logo") and not (c.get("header") and c.get("link_home") and w >= 100): rejected.append((u, f"icon-shaped {w}x{hgt}")); continue
    logo = {"kind": "logo", "url": u, "type": t, "bytes": b, "check": why}; break
# the header mark as the browser resolved it (render.json): an inline SVG is taken from the live page (computed fills, proper XML) rather
# than the HTML parser's copy; an <img> uses currentSrc (srcset / lazy-load resolved); a CSS background uses its url(). If none of the
# scraped candidates loaded, the live mark is used, and as the last resort the mark exactly as painted (render-logo.png).
RL = R.get("logo") or {}
if OWNER.get("logo") != "wordmark" and not OWNER.get("logo"):
    live_ok = bool(RL) and (not RL.get("url") or RL["url"].startswith("data:image/") or own(RL["url"]) or judge({"url": RL["url"], "alt": RL.get("alt"), "header": True, "link_home": True})[0])
    if RL.get("kind") == "svg" and live_ok and (logo is None or logo.get("type") == "svg"):
        logo = {"kind": "logo", "url": "inline svg in the header (as rendered)", "type": "svg", "bytes": RL["svg"].encode(), "check": (logo or {}).get("check") or "the header mark on the business's own site"}
    elif logo is None and RL.get("url") and live_ok:
        b, t = fetch(RL["url"])
        if b: logo = {"kind": "logo", "url": RL["url"], "type": t, "bytes": b, "check": f"the header mark on the business's own site ({RL['kind']})"}
    if logo is None and RL and os.path.exists(f"{d}/render-logo.png"):
        logo = {"kind": "logo", "url": "the header mark as painted on the page (screenshot)", "type": "raster", "bytes": open(f"{d}/render-logo.png", "rb").read(), "check": "the header mark on the business's own site (as painted)"}
out = {"logo_kind": None, "logo_url": None, "logo_rejected": rejected, "logo_candidates": report, "logo_check": {"status": "PASS", "why": logo["check"]} if logo else {"status": "no traceable logo -> text wordmark", "why": None}, "owner_logo": OWNER.get("logo")}
prim = None; MARK = None
if logo:
    ext = "svg" if logo["type"] == "svg" else "png"
    if ext == "png":
        im = Image.open(io.BytesIO(logo["bytes"])).convert("RGBA"); bb = im.getbbox()
        if bb: im = im.crop(bb)
        im.save(f"{d}/logo.png"); MARK = im
    else:
        logo["bytes"] = fix_svg(logo["bytes"]); open(f"{d}/logo.svg", "wb").write(logo["bytes"])
        try:
            import cairosvg; MARK = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=logo["bytes"], output_width=400))).convert("RGBA")
        except Exception as e:
            MARK = None; out["mark_check_error"] = str(e)[:120]
            if os.path.exists(f"{d}/render-logo.png"):   # an SVG no renderer can read is never shipped: use the mark as painted
                im = Image.open(f"{d}/render-logo.png").convert("RGBA"); im.save(f"{d}/logo.png"); MARK = im; ext = "png"; out["logo_note"] = "svg unreadable -> the mark as painted on the page"
    out.update(logo_kind="logo", logo_url=logo["url"], logo_file="logo." + ext)
else:
    out["logo_kind"] = "text wordmark (owner chose the wordmark)" if OWNER.get("logo") == "wordmark" else "text wordmark (no logo image tied to this business passed the checks)"
# v7 BRAND COLOUR: (1) the logo's dominant non-neutral colour; (2) else the most-painted non-neutral colour on the homepage above the fold
# (headless screenshot, photos/videos hidden, pixel histogram by area); (3) else the most-USED colour across the site's CSS (usage count, never CSS order).
# Never a near-white, near-black or grey (HLS saturation < .25, lightness > .90 or < .08); never a darkened near-white.
from collections import Counter
def usable(hx):
    r, g, b = [int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)]; hh_, ll_, ss_ = colorsys.rgb_to_hls(r, g, b)
    return ss_ >= .25 and .08 <= ll_ <= .90 and (max(r, g, b) - min(r, g, b)) >= .12
def hist(pxs):
    """bucket usable pixels; each bucket keeps the true mean colour of its pixels (not the bucket corner)"""
    c = {}
    for p in pxs:
        if len(p) == 4 and p[3] < 200: continue
        k = tuple(v // 16 for v in p[:3]); e = c.setdefault(k, [0, 0, 0, 0]); e[0] += 1; e[1] += p[0]; e[2] += p[1]; e[3] += p[2]
    out_ = Counter()
    for e in c.values():
        hx = "#%02x%02x%02x" % (e[1] // e[0], e[2] // e[0], e[3] // e[0])
        if usable(hx): out_[hx] += e[0]
    return out_
def merge(c, tot):
    """group near colours (distance < 48): count-weighted mean colour per group; returns [(hex, share)]"""
    out_ = []
    for hx, n in c.most_common(60):
        rgb = [int(hx[i:i + 2], 16) for i in (1, 3, 5)]
        for o in out_:
            if sum((a_ - b_) ** 2 for a_, b_ in zip(rgb, o[2])) ** .5 < 48: o[3] = [o[3][i] + rgb[i] * n for i in range(3)]; o[1] += n; break
        else: out_.append([hx, n, rgb, [v * n for v in rgb]])
    return [("#%02x%02x%02x" % tuple(int(v / o[1]) for v in o[3]), round(o[1] / max(1, tot), 4)) for o in sorted(out_, key=lambda o: -o[1])]
cands_c, src = [], None
PLATFORM = {"#116dff", "#0073aa", "#007bff", "#0d6efd", "#2271b1", "#3858e9", "#ff4040", "#32373c", "#0693e3", "#cf2e2e", "#ff6900", "#fcb900", "#7bdcb5", "#00d084", "#8ed1fc", "#abb8c3", "#f78da7", "#9b51e0", "#eb144c", "#fb5607"}   # Wix / WordPress / Bootstrap theme defaults (not a brand)
if MARK is not None:
    px = list(MARK.resize((120, max(1, int(120 * MARK.height / MARK.width)))).get_flattened_data()); vis = [p for p in px if p[3] >= 200]
    lc = merge(hist(vis), len(vis))
    if lc and lc[0][1] >= .03: cands_c += [{"hex": h_, "share": sh, "source": "logo"} for h_, sh in lc[:5] if sh >= .05]   # not anti-aliased edge blends
    if cands_c: src = "logo (dominant non-neutral colour of the mark)"; src = "logo (dominant non-neutral colour of the mark)"
# RENDERED COLOURS, cross-checked: every colour the computed styles report (header / nav / promo bars, buttons at rest) must also be
# visible in the real top-of-page screenshot by pixel area, or it is dropped. The site's own coloured bars come first (they are what a
# visitor sees as the brand), then the logo, then the most-painted colour of the photo-free fold, then visible CSS colours as swatches.
dist = lambda a_, b_: sum((int(a_[i:i + 2], 16) - int(b_[i:i + 2], 16)) ** 2 for i in (1, 3, 5)) ** .5
PIX = []
if os.path.exists(top_png):
    _im = Image.open(top_png).convert("RGB"); _px = list(_im.resize((320, 200)).get_flattened_data()); PIX = merge(hist(_px), len(_px))
def seen_px(hx): return round(sum(sh for h_, sh in PIX if dist(h_, hx) < 40), 4)
out["screen_colours"] = [{"hex": h_, "share": sh} for h_, sh in PIX[:6]]
bar_w = Counter(); TOP_BAR = None
for b_ in R.get("bars") or []:
    hx = rgb_hex(b_["bg"])
    if not hx: continue
    if b_["top"] <= 4 and b_["h"] >= 40 and TOP_BAR is None: TOP_BAR = hx   # the header band as painted (may be white)
    if usable(hx) and hx not in PLATFORM and b_["h"] >= 40: bar_w[hx] += b_["w"] * b_["h"]   # a header band or promo bar, not a thin phone/email strip
bars = [(h_, seen_px(h_)) for h_, sh in (merge(bar_w, sum(bar_w.values())) if bar_w else [])]
out["rendered_bars"] = [{"hex": h_, "on_screen": v} for h_, v in bars[:4]]; out["site_header_bg"] = TOP_BAR
bars = sorted([(h_, v) for h_, v in bars if v >= .02], key=lambda x: -x[1])   # a bar colour that is really on screen (2%+ of the top of the page)
if bars:
    cands_c = [{"hex": h_, "share": v, "source": "site header / promo bars as rendered (checked on screen)"} for h_, v in bars[:3]] + [c for c in cands_c if all(dist(c["hex"], h_) >= 48 for h_, _ in bars[:3])]
    src = "the site's header / promo bars as rendered (computed colour, checked by pixel area on the real screenshot)"
if not cands_c and os.path.exists(fold):
    im = Image.open(fold).convert("RGB"); pxs = list(im.resize((320, 200)).get_flattened_data()); pc = merge(hist(pxs), len(pxs))
    if pc and pc[0][1] >= .002: cands_c += [{"hex": h_, "share": sh, "source": "homepage above the fold (painted area, photos hidden)"} for h_, sh in pc[:5]]; src = "homepage above the fold, by painted area (photos hidden)"
css_used = [(c, n) for c, n in bh["colours"] if _re.fullmatch(r"#[0-9a-f]{6}", c) and usable(c)]
css_used.sort(key=lambda x: -x[1])
for c, n in css_used:
    if len(cands_c) >= 5: break
    if c.lower() in PLATFORM: continue
    if PIX and seen_px(c) < .004: continue   # in the CSS but barely (or never) visible: hover/focus shades, unused variables
    if all(sum((int(c[i:i + 2], 16) - int(x["hex"][i:i + 2], 16)) ** 2 for i in (1, 3, 5)) ** .5 >= 48 for x in cands_c): cands_c.append({"hex": c, "share": n, "source": "CSS usage count (visible on screen)"})
if not src and cands_c: src = "site CSS, most-used non-neutral colour (usage count, not order)"
painted_neutral = os.path.exists(fold) and not any(not c["source"].startswith("CSS usage count") for c in cands_c)
if OWNER.get("colour"): prim = OWNER["colour"]; src = "picked by the owner (simulated owner check)"
elif painted_neutral:   # v7: the logo and the painted page show no brand colour (a neutral site): CSS-only colours are usually theme/platform defaults, so they stay as owner swatches only
    prim = "#1f2a44"; src = "logo and painted page are neutral -> neutral dark blue (CSS-only colours offered as owner swatches)"; cands_c = [{"hex": prim, "share": 0, "source": "neutral default"}] + cands_c
elif cands_c: prim = cands_c[0]["hex"]
else: prim = "#1f2a44"; src = "no usable brand colour on the logo or site -> neutral dark blue"
out["colour_source"] = src; out["colour_candidates"] = cands_c[:5]; out["colour_v52_would_be"] = next((c for c, n in bh["colours"] if c not in ("#ffffff", "#000000", "#fefefe", "#cccccc", "#ededed", "#f5f5f5", "#eeeeee", "#333333", "#222222", "#666666", "#999999")), None)
def lumi(h):
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)
def contrast(a, b):
    la, lb = sorted([lumi(a), lumi(b)], reverse=True); return (la + .05) / (lb + .05)
INK, WHITE = "#14181a", "#ffffff"
def shade(hx, k):
    r, g, b = [int(hx[i:i + 2], 16) for i in (1, 3, 5)]
    if k < 1: return "#%02x%02x%02x" % (int(r * k), int(g * k), int(b * k))
    return "#%02x%02x%02x" % tuple(int(c + (255 - c) * (k - 1)) for c in (r, g, b))
def on(bg):
    """Text colour for a background: white or ink, whichever passes WCAG 4.5:1 with more margin; if neither passes, darken the background."""
    while True:
        cw, ci = contrast(bg, WHITE), contrast(bg, INK)
        if max(cw, ci) >= 4.5: return bg, (WHITE if cw >= ci else INK), round(max(cw, ci), 2)
        bg = shade(bg, .9)
log = []
brand, on_brand, cb = on(prim)
if brand != prim: log.append(f"brand {prim} darkened to {brand} so text passes 4.5:1")
# BUTTON / CTA COLOUR (ask-not-fail): the colour the site paints its own buttons with (computed background of visible buttons and
# button-styled links, weighted by area and by being above the fold; cookie/consent banners skipped). Many sites keep the logo
# colour for panels and a separate accent for buttons (e.g. navy brand, green buttons). Cached in cta-scan.json (re-renders don't reload the site).
# not the site's main button: click-to-call / chat / WhatsApp / email widgets and small floating bubbles (often a third-party colour)
CONTACT_W = _re.compile(r"^(call|call us|call now|chat|live chat|whatsapp|text|text us|sms|phone|email|email us)$|^skip to", _re.I)
def widget(b_):
    return bool(CONTACT_W.match((b_.get("txt") or "").strip()) or _re.match(r"(tel|mailto|sms):|https?://(wa\.me|api\.whatsapp)", b_.get("href") or "", _re.I)
                or (b_.get("fx") and b_["w"] <= 90 and b_["h"] <= 90))
bw = Counter()
for b_ in R["buttons"]:
    if widget(b_): continue
    hx = rgb_hex(b_["bg"])
    if not hx or not usable(hx) or hx.lower() in PLATFORM: continue
    fold_h = 800 if b_["vw"] == 1280 else 844
    bw[hx] += b_["w"] * b_["h"] * (2.5 if b_["top"] < fold_h else 1)
ctas = merge(bw, sum(bw.values())) if bw else []
ctas = [(h_, sh) for h_, sh in ctas if not PIX or seen_px(h_) >= .001 or sh >= .5]   # computed but never painted (hidden variants) -> dropped
# the PRIMARY call-to-action: the biggest coloured button in the desktop hero (above the fold) is what the site asks visitors to press;
# when there is one, it decides the button colour (area across the whole page only breaks ties when nothing coloured is above the fold)
hero = sorted([b_ for b_ in R["buttons"] if b_["vw"] == 1280 and b_["top"] < 800 and not widget(b_) and rgb_hex(b_["bg"]) and usable(rgb_hex(b_["bg"])) and rgb_hex(b_["bg"]).lower() not in PLATFORM],
              key=lambda b_: -b_["w"] * b_["h"])
if hero:
    hx0 = rgb_hex(hero[0]["bg"]); out["primary_cta"] = {"hex": hx0, "text": hero[0]["txt"][:40]}
    ctas = [(hx0, 1.0)] + [(h_, sh) for h_, sh in ctas if dist(h_, hx0) >= 48]
out["cta_candidates"] = [{"hex": h_, "share": sh, "source": "site buttons"} for h_, sh in ctas[:4]]
out["cta_buttons_seen"] = len(R["buttons"]); out["render_error"] = R.get("error")
dist = lambda a_, b_: sum((int(a_[i:i + 2], 16) - int(b_[i:i + 2], 16)) ** 2 for i in (1, 3, 5)) ** .5
cta_hex, bsrc = None, None
if OWNER.get("button_colour") == "brand": bsrc = "owner chose the brand colour for buttons"
elif OWNER.get("button_colour"): cta_hex, bsrc = OWNER["button_colour"], "picked by the owner"
elif hero:
    cta_hex = ctas[0][0]; bsrc = f"the site's main button at rest ('{hero[0]['txt'][:30]}', above the fold)"
elif ctas and ctas[0][1] >= .25:
    cta_hex = ctas[0][0]; bsrc = f"the site's own buttons ({round(ctas[0][1] * 100)}% of coloured button area)"
if cta_hex and dist(cta_hex, prim) < (12 if hero else 48): cta_hex = None; bsrc = (bsrc or "") + " -> same as the brand colour"
# v7: the button keeps the brand colour unless the site paints its buttons in a different colour; text is white or ink, whichever passes 4.5:1
btn, on_btn, _cbtn = on(cta_hex or prim)
if btn != (cta_hex or prim): log.append(f"button {cta_hex or prim} darkened to {btn}: neither white nor ink text passes 4.5:1")
out["button_source"] = bsrc or "brand colour (no separate button colour on the site)"
if cta_hex: out["cta"], out["on_cta"] = btn, on_btn
r, g, b = [int(prim[i:i + 2], 16) / 255 for i in (1, 3, 5)]; hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
deep = "#%02x%02x%02x" % tuple(int(x * 255) for x in colorsys.hls_to_rgb(hh, min(ll, .16), min(ss, .55)))
if .10 <= hh <= .20: deep = "#1c1c1a"; log.append(f"brand {prim} is a yellow/gold: its dark shade would be olive -> near-black ink used for dark panels")   # v7: never an olive panel
deep, on_deep, cd = on(deep)
accent = prim if contrast(prim, "#f4f3ee") >= 4.5 else deep   # brand-coloured text on paper; a light brand uses its deep shade, never a muddy darkening
if accent != prim: log.append(f"brand {prim} too light for text on paper -> its deep shade {deep} used for brand text")
# v5.2 light / white logos: share of the mark's visible pixels that nearly vanish on the header (contrast < 1.6:1). Mostly invisible on white ->
# dark header band in the brand's deep colour; if the mark also vanishes on that band -> clean text wordmark instead
def vanish(im, bg):
    px = [p for p in im.resize((120, max(1, int(120 * im.height / im.width)))).get_flattened_data() if p[3] > 128]
    if not px: return 0
    return sum(1 for p in px if contrast("#%02x%02x%02x" % p[:3], bg) < 1.6) / len(px)
header_bg, on_header = WHITE, INK
if MARK is not None:
    vw = vanish(MARK, WHITE); out["mark_vanish_on_white"] = round(vw, 2); out["mark_is_light"] = vw >= .5
    if out["mark_is_light"]:
        vd = vanish(MARK, deep); out["mark_vanish_on_band"] = round(vd, 2)
        if vd < .5: header_bg, on_header = deep, WHITE; log.append(f"logo is light ({vw:.0%} of it vanishes on white) -> dark header band {deep}")
        else:
            log.append(f"logo is light and also vanishes on the dark band -> text wordmark"); out.update(logo_kind="text wordmark (the site logo is not legible on a white or dark header)", logo_file=None, logo_fallback_from=out["logo_url"])
# the site's own coloured header band (Gym Group: royal blue) when its logo is made for it (a light / negative mark that reads on that colour)
# What is painted right behind the logo on the live page (a ring just outside its box in the desktop screenshot) is the most direct evidence
# of the background the mark was designed for; the top header band is the second source.
LOGO_BG = None
try:
    bx = (R.get("logo") or {}).get("box")
    if bx and os.path.exists(f"{d}/render-top.png") and bx["y"] < 760:
        shot = Image.open(f"{d}/render-top.png").convert("RGB"); W_, H_ = shot.size; ring = Counter()
        x0, y0, x1, y1 = int(bx["x"]), int(bx["y"]), int(bx["x"] + bx["w"]), int(bx["y"] + bx["h"])
        for pad in (4, 8):
            for x in range(max(0, x0 - pad), min(W_, x1 + pad), 2):
                for y in (y0 - pad, y1 + pad): 
                    if 0 <= y < H_: ring[tuple(c // 8 * 8 for c in shot.getpixel((x, y)))] += 1
            for y in range(max(0, y0 - pad), min(H_, y1 + pad), 2):
                for x in (x0 - pad, x1 + pad):
                    if 0 <= x < W_: ring[tuple(c // 8 * 8 for c in shot.getpixel((x, y)))] += 1
        (q, n), tot = ring.most_common(1)[0], sum(ring.values())
        if n / tot >= .6:   # a flat colour, not a photo
            pts = [shot.getpixel((x, y)) for x in range(max(0, x0 - 8), min(W_, x1 + 8), 2) for y in (max(0, y0 - 6), min(H_ - 1, y1 + 6))]
            pts = [p_ for p_ in pts if tuple(c // 8 * 8 for c in p_) == q] or [q]
            LOGO_BG = "#%02x%02x%02x" % tuple(sum(p_[i] for p_ in pts) // len(pts) for i in range(3))
except Exception as e: out["logo_bg_error"] = str(e)[:120]
out["painted_behind_logo"] = LOGO_BG
for BG, what in ((LOGO_BG, "the colour painted behind its logo"), (TOP_BAR, "header band")):
    if MARK is None or not BG or not out.get("mark_is_light") or not out.get("logo_file"): continue
    if not (usable(BG) or contrast(BG, WHITE) >= 3) or vanish(MARK, BG) >= .3: continue
    hb, oh, _ch = on(BG)
    if hb == BG: header_bg, on_header = hb, oh; log.append(f"logo is made for the site's own {BG} background ({what}) -> same header colour"); break
out.update(primary=prim, brand=brand, on_brand=on_brand, brand_contrast=cb, button=btn, on_button=on_btn, button_contrast=round(contrast(btn, on_btn), 2), deep=deep, on_deep=on_deep, deep_contrast=cd,
           accent_text=accent, accent_contrast=round(contrast(accent, "#f4f3ee"), 2), header_bg=header_bg, on_header=on_header, contrast_fixes=log)
json.dump(out, open(f"{d}/brand.json", "w"), indent=1); print("brand:", {k: v for k, v in out.items() if k != "logo_rejected"}, "| rejected logos:", rejected)
