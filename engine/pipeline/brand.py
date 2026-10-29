import sys, json, io, requests, urllib.parse as U, colorsys
from PIL import Image
d = sys.argv[1]; s = json.load(open(f"{d}/scrape.json")); bh = s["brand_hints"]; host = U.urlparse(s["final_url"]).netloc
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36"}
def fetch(u):
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
OWNER = json.load(open(f"{d}/owner-check.json")) if os.path.exists(f"{d}/owner-check.json") else {}
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
out = {"logo_kind": None, "logo_url": None, "logo_rejected": rejected, "logo_candidates": report, "logo_check": {"status": "PASS", "why": logo["check"]} if logo else {"status": "no traceable logo -> text wordmark", "why": None}, "owner_logo": OWNER.get("logo")}
prim = None; MARK = None
if logo:
    ext = "svg" if logo["type"] == "svg" else "png"
    if ext == "png":
        im = Image.open(io.BytesIO(logo["bytes"])).convert("RGBA"); bb = im.getbbox()
        if bb: im = im.crop(bb)
        im.save(f"{d}/logo.png"); MARK = im
    else:
        open(f"{d}/logo.svg", "wb").write(logo["bytes"])
        try:
            import cairosvg; MARK = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=logo["bytes"], output_width=400))).convert("RGBA")
        except Exception as e: MARK = None; out["mark_check_error"] = str(e)[:120]
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
    if lc and lc[0][1] >= .03: cands_c += [{"hex": h_, "share": sh, "source": "logo"} for h_, sh in lc[:5]]; src = "logo (dominant non-neutral colour of the mark)"
fold = f"{d}/home-fold.png"
if not cands_c and not os.path.exists(fold):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            bz = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"]); pg = bz.new_page(viewport={"width": 1280, "height": 800}, user_agent=H["User-Agent"])
            pg.goto(s["final_url"], timeout=30000); pg.wait_for_timeout(3500)
            pg.add_style_tag(content="img,video,picture,iframe,canvas,svg image{visibility:hidden!important}*{background-image:none!important}")
            pg.wait_for_timeout(300); pg.screenshot(path=fold); bz.close()
    except Exception as e: out["fold_error"] = str(e)[:120]
if not cands_c and os.path.exists(fold):
    im = Image.open(fold).convert("RGB"); pxs = list(im.resize((320, 200)).get_flattened_data()); pc = merge(hist(pxs), len(pxs))
    if pc and pc[0][1] >= .002: cands_c += [{"hex": h_, "share": sh, "source": "homepage above the fold (painted area, photos hidden)"} for h_, sh in pc[:5]]; src = "homepage above the fold, by painted area (photos hidden)"
css_used = [(c, n) for c, n in bh["colours"] if _re.fullmatch(r"#[0-9a-f]{6}", c) and usable(c)]
css_used.sort(key=lambda x: -x[1])
for c, n in css_used:
    if len(cands_c) >= 5: break
    if c.lower() in PLATFORM: continue
    if all(sum((int(c[i:i + 2], 16) - int(x["hex"][i:i + 2], 16)) ** 2 for i in (1, 3, 5)) ** .5 >= 48 for x in cands_c): cands_c.append({"hex": c, "share": n, "source": "CSS usage count"})
if not src and cands_c: src = "site CSS, most-used non-neutral colour (usage count, not order)"
painted_neutral = os.path.exists(fold) and not any(c["source"] != "CSS usage count" for c in cands_c)
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
# v7: the button keeps the brand colour; its text is white or ink, whichever passes 4.5:1 (a light brand such as gold gets ink text, never an olive darkening)
btn, on_btn, _cbtn = on(prim)
if btn != prim: log.append(f"button {prim} darkened to {btn}: neither white nor ink text passes 4.5:1")
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
out.update(primary=prim, brand=brand, on_brand=on_brand, brand_contrast=cb, button=btn, on_button=on_btn, button_contrast=round(contrast(btn, on_btn), 2), deep=deep, on_deep=on_deep, deep_contrast=cd,
           accent_text=accent, accent_contrast=round(contrast(accent, "#f4f3ee"), 2), header_bg=header_bg, on_header=on_header, contrast_fixes=log)
json.dump(out, open(f"{d}/brand.json", "w"), indent=1); print("brand:", {k: v for k, v in out.items() if k != "logo_rejected"}, "| rejected logos:", rejected)
