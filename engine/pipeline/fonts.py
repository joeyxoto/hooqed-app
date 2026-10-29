"""v8 FONT MATCH: the hooq uses the site's own type. The render step (brand.py, real browser) reads the computed font of the main heading,
the body text and the buttons, and the family the browser actually painted with. resolve() then decides per role:
  exact   - the family is on Google Fonts (open licence: OFL / Apache), so the hooq loads that exact family from Google Fonts, even when the
            site self-hosts it;
  mapped  - a paid, custom or system font we cannot reuse: the closest free Google Font by style (known-font table first, then a style
            guess from the name, the stack's generic fallback and the measured letter width);
  template- nothing usable was read; the template's own fonts stay.
The template keeps its sizes; a scale for wider letters and a fit-to-width guard keep big display lines on screen, and if a font fails to
load in the visitor's browser the template fonts come back (build.py)."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
GF = json.load(open(os.path.join(HERE, "gfonts.json")))   # Google Fonts catalogue (family -> category, weights), saved from fonts.google.com/metadata
def _k(s): return re.sub(r"[^a-z0-9]", "", s.lower())
GFK = {_k(f): f for f in GF}
GENERIC = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace", "-apple-system",
           "blinkmacsystemfont", "emoji", "math", "fangsong", "inherit", "initial"}
SYSTEM_UI = {"system-ui", "-apple-system", "blinkmacsystemfont", "segoe ui", "ui-sans-serif", "san francisco", "sf pro text", "sf pro display", ".sfnstext"}
# paid / system families -> closest free Google Font (by look: structure, width, x-height)
KNOWN = {
 "helvetica": "Inter", "helveticaneue": "Inter", "neuehaasgrotesk": "Inter", "neuehaasunica": "Inter", "aktivgrotesk": "Inter", "graphik": "Inter",
 "arial": "Arimo", "liberationsans": "Arimo", "univers": "Inter", "akzidenzgrotesk": "Inter Tight", "suisseintl": "Inter", "sfprotext": "Inter",
 "sfprodisplay": "Inter", "sanfrancisco": "Inter", "systemui": "Inter", "segoeui": "Noto Sans", "roboto": "Roboto", "tahoma": "Noto Sans",
 "verdana": "PT Sans", "trebuchetms": "Fira Sans", "calibri": "Carlito", "candara": "Cabin", "cambria": "Caladea", "georgia": "Gelasio",
 "timesnewroman": "Tinos", "times": "Tinos", "garamond": "EB Garamond", "adobegaramond": "EB Garamond", "garamondpremierpro": "EB Garamond",
 "baskerville": "Libre Baskerville", "caslon": "Libre Caslon Text", "didot": "Playfair Display", "bodoni": "Bodoni Moda", "palatino": "Gelasio",
 "bookantiqua": "Gelasio", "minionpro": "Crimson Pro", "minion": "Crimson Pro", "chronicledisplay": "Playfair Display", "freightdisplay": "Playfair Display",
 "freighttext": "Source Serif 4", "tiempos": "Source Serif 4", "tiemposheadline": "Playfair Display", "canela": "Cormorant Garamond", "recoleta": "Fraunces",
 "cooper": "Fraunces", "rockwell": "Roboto Slab", "museoslab": "Roboto Slab", "futura": "Jost", "futurapt": "Jost", "avenir": "Nunito Sans",
 "avenirnext": "Nunito Sans", "gotham": "Montserrat", "proximanova": "Figtree", "brandongrotesque": "Josefin Sans", "gillsans": "Cabin",
 "frutiger": "Hind", "myriadpro": "PT Sans", "myriad": "PT Sans", "museosans": "Mulish", "sofiapro": "Outfit", "gilroy": "Plus Jakarta Sans",
 "circular": "DM Sans", "circularstd": "DM Sans", "circularxx": "DM Sans", "apercu": "Work Sans", "eina": "Outfit", "cerapro": "Outfit", "cera": "Outfit",
 "ttcommons": "Figtree", "ttnorms": "Outfit", "euclidcircularb": "Plus Jakarta Sans", "euclidcirculara": "Plus Jakarta Sans", "foundersgrotesk": "Hanken Grotesk",
 "pphatton": "Playfair Display", "ppneuemontreal": "Inter", "neuemontreal": "Inter", "generalsans": "Manrope", "satoshi": "Manrope", "clashdisplay": "Space Grotesk",
 "cabinetgrotesk": "Bricolage Grotesque", "aeonik": "Inter", "haffer": "Inter", "matter": "Inter", "gtamerica": "Inter", "gtwalsheim": "DM Sans",
 "gteesti": "Jost", "nationale": "Inter", "sharpgrotesk": "Archivo", "tradegothic": "Archivo Narrow", "tradegothicnext": "Archivo", "din": "Barlow",
 "dinpro": "Barlow", "dinnextltpro": "Barlow", "dinnext": "Barlow", "dincondensed": "Barlow Condensed", "dinalternate": "Barlow",
 "knockout": "Oswald", "trumpgothic": "Oswald", "impact": "Anton", "alternategothic": "Oswald", "franklingothic": "Libre Franklin",
 "franklingothicurw": "Libre Franklin", "newsgothic": "News Cycle", "bentonsans": "Libre Franklin", "acumin": "Inter", "acuminpro": "Inter",
 "acuminprocondensed": "Barlow Condensed", "sourcesanspro": "Source Sans 3", "opensanshebrew": "Open Sans", "segoeprint": "Patrick Hand",
 "helveticaneuecondensed": "Archivo Narrow", "helveticacondensed": "Archivo Narrow", "arialnarrow": "Arimo", "ubuntu": "Ubuntu",
 "bebas": "Bebas Neue", "geomanist": "Outfit", "nexa": "Montserrat", "mont": "Montserrat", "objectivity": "Montserrat", "kollektif": "Montserrat",
 "brother1816": "Figtree", "termina": "Syne", "monumentextended": "Syne", "druk": "Anton", "drukwide": "Syne", "tablet gothic": "Libre Franklin",
}
STYLE_DEFAULT = {"serif": "Source Serif 4", "display-serif": "Playfair Display", "slab": "Roboto Slab", "mono": "IBM Plex Mono", "condensed": "Oswald",
                 "geometric": "Montserrat", "grotesk": "Inter", "humanist": "Source Sans 3", "rounded": "Nunito", "script": "Caveat"}
def clean(fam):
    f = fam.strip().strip("'\"").strip()
    m = re.match(r"^__(.+?)_(?:Fallback_)?[0-9a-f]{5,8}$", f)          # Next.js next/font names: __Inter_d65c78
    if m: f = m.group(1).replace("_", " ")
    f = re.sub(r"(?i)[-_ ]?(webfont|web|variable|var|vf|regular|roman|book|medium|semibold|demibold|bold|extrabold|black|light|thin|italic|normal)\b", "", f)
    f = re.sub(r"(?i)\b(std|pro|w0[0-9]|ot|lt)$", lambda m_: m_.group(0) if _k(f) in GFK else "", f).strip(" -_")
    return f or fam.strip("'\" ")
def on_gf(fam):
    k = _k(clean(fam)); 
    if k in GFK: return GFK[k]
    k2 = _k(fam.strip("'\" "))
    return GFK.get(k2)
def style_guess(fam, generic, ratio):
    n = _k(fam)
    if re.search(r"mono|code|courier", n): return "mono"
    if re.search(r"script|hand|brush|signature|marker", n): return "script"
    if re.search(r"slab|egypt|clarendon|rockwell", n): return "slab"
    if re.search(r"cond|narrow|compress|gothic(?!a)|knockout|oswald|bebas|impact", n) or (ratio and ratio < .80): return "condensed"
    if re.search(r"serif(?!sans)|garamond|didot|bodoni|caslon|times|georgia|baskerville|playfair|tiempos|canela|freight", n) and "sans" not in n: return "serif"
    if generic == "serif": return "serif"
    if re.search(r"rounded|round", n): return "rounded"
    if re.search(r"geo|futura|circular|gotham|avenir|sofia|gilroy|poppins|montserrat|eina|cera|euclid|nexa", n) or (ratio and ratio > 1.08): return "geometric"
    if re.search(r"gill|frutiger|myriad|humanist|optima|syntax|lato|source|fira|open", n): return "humanist"
    return "grotesk"
def pick_weight(fam, want):
    ws = GF.get(fam, {}).get("w") or [400, 700]
    return min(ws, key=lambda w: (abs(w - want), -w))
def resolve_role(info, role):
    """info: {stack, used, loaded_webfont, weight, transform, ratio}"""
    if not info: return {"role": role, "source": "template", "why": "not read from the page"}
    stack = [s.strip().strip("'\"") for s in (info.get("stack") or "").split(",") if s.strip()]
    generic = next((s.lower() for s in stack if s.lower() in ("serif", "sans-serif", "monospace", "cursive")), "sans-serif")
    used = info.get("used") or (stack[0] if stack else "")
    out = {"role": role, "detected": clean(used), "raw": used, "stack": ", ".join(stack[:5]), "weight": info.get("weight"), "transform": info.get("transform"),
           "ratio": info.get("ratio"), "site_webfont": bool(info.get("loaded_webfont"))}
    if not used: return dict(out, source="template", why="no font family on the page")
    if used.lower() in GENERIC or _k(used) in {_k(x) for x in SYSTEM_UI}:
        fam = KNOWN["systemui"] if generic != "serif" else "Source Serif 4"
        return dict(out, source="mapped", family=fam, why=f"site uses the device's system font ({used}); closest free font: {fam}")
    g = on_gf(used)
    if g: return dict(out, source="exact", family=g, why=f"{used} is a free Google Font (open licence); loaded from Google Fonts" + (" (the site self-hosts it)" if info.get("loaded_webfont") and not info.get("google_link") else ""))
    k = _k(clean(used))
    for key in (k, _k(used), re.sub(r"(pro|std|next|lt|w\d+)$", "", k)):
        if key in KNOWN and KNOWN[key] in GF: return dict(out, source="mapped", family=KNOWN[key], why=f"{used} is a paid or system font we cannot reuse; closest free look-alike: {KNOWN[key]}")
    for key, fam in KNOWN.items():   # e.g. 'Gotham SSm A', 'ProximaNova-Bold', 'Avenir LT Std'
        if len(key) >= 5 and k.startswith(key) and fam in GF: return dict(out, source="mapped", family=fam, why=f"{used} looks like {key} (paid); closest free look-alike: {fam}")
    st = style_guess(used, generic, info.get("ratio"))
    if st == "serif" and role == "heading" and (info.get("ratio") or 1) > 1.0: st = "display-serif"
    fam = STYLE_DEFAULT[st]
    return dict(out, source="mapped", family=fam, style=st, why=f"{used} is a custom font we cannot reuse; style read as {st}, closest free font: {fam}")
FONTS_JS = r"""() => {
 const W = window.innerWidth, decl = new Map();
 for (const f of document.fonts) { const n = f.family.replace(/["']/g, '').trim(); if (f.status === 'loaded') decl.set(n.toLowerCase(), 'loaded'); else if (!decl.has(n.toLowerCase())) decl.set(n.toLowerCase(), f.status); }
 const gl = !!document.querySelector('link[href*="fonts.googleapis.com"],style:not(:empty)') && Array.from(document.querySelectorAll('link[href*="fonts.googleapis.com"]')).map(l => l.href).join(' ');
 const vis = e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e); return r.width > 20 && r.height > 8 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > .3; };
 const own = e => Array.from(e.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').replace(/\s+/g, ' ').trim();
 const c = document.createElement('canvas').getContext('2d');
 const wid = (fam, w) => { c.font = `${w} 100px "${fam}", monospace`; const a = c.measureText('Hamburgefonstiv Quote').width; c.font = `${w} 100px monospace`; const m = c.measureText('Hamburgefonstiv Quote').width;
   if (Math.abs(a - m) < .5) return null; c.font = `${w} 100px Arimo, Arial, "Liberation Sans", sans-serif`; return +(a / c.measureText('Hamburgefonstiv Quote').width).toFixed(2); };
 const used = (cs) => { const st = cs.fontFamily.split(',').map(x => x.trim().replace(/^["']|["']$/g, ''));
   for (const f of st) { const k = f.toLowerCase(), d = decl.get(k);
     if (d === 'loaded') return [f, true];
     if (d) continue;                    // declared webfont that never loaded: the browser fell through
     return [f, false]; }               // not a webfont: a system / generic family (what Mac / Windows visitors see)
   return [st[st.length - 1] || '', false]; };
 const info = (e, txt) => { const cs = getComputedStyle(e); const [u, wf] = used(cs); const r = e.getBoundingClientRect();
   return {stack: cs.fontFamily, used: u, loaded_webfont: wf, google_link: gl && gl.toLowerCase().includes(u.toLowerCase().replace(/ /g, '+')), weight: cs.fontWeight, transform: cs.textTransform,
           size: cs.fontSize, ratio: wf ? wid(u, cs.fontWeight) : null, text: (txt || '').slice(0, 60), box: {x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height}}; };
 let H = Array.from(document.querySelectorAll('h1')).filter(e => vis(e) && e.innerText.trim().length > 2)[0];
 if (!H || parseFloat(getComputedStyle(H).fontSize) < 22) { let best = null, bs = 0;
   for (const e of document.querySelectorAll('h1,h2,h3,p,div,span,a,strong')) { const t = own(e); if (t.length < 4 || !vis(e)) continue; const r = e.getBoundingClientRect(); if (r.top + scrollY > 1400) continue;
     const fs = parseFloat(getComputedStyle(e).fontSize); if (fs > bs) { bs = fs; best = e; } }
   if (best && (!H || bs > parseFloat(getComputedStyle(H).fontSize))) H = best; }
 const painted = e => { for (let a = e, i = 0; a && i < 3; a = a.parentElement, i++) { const cs = getComputedStyle(a); if (!/rgba\(0, 0, 0, 0\)|transparent/.test(cs.backgroundColor) || parseFloat(cs.borderTopWidth) >= 1) return true; } return false; };
 const tally = (sel, minLen, btn) => { const m = new Map();
   for (const e of document.querySelectorAll(sel)) { let t = own(e) || (btn ? e.innerText.trim() : ''); if (t.length < minLen || !vis(e)) continue;
     if (btn && (t.length > 40 || !painted(e))) continue;   // a real button: short label, painted background or border
     const cs = getComputedStyle(e); const k = cs.fontFamily + '|' + cs.fontWeight;
     const v = m.get(k) || {n: 0, e, t}; v.n += btn ? 1 : t.length; m.set(k, v); }
   return Array.from(m.values()).sort((a, b) => b.n - a.n)[0]; };
 const B = tally('p,li,dd,blockquote,td', 25) || tally('div,span', 25);
 const btn = tally('button,a[class*=btn],a[class*=button],a[class*=Button],a[class*=cta],[role=button],input[type=submit]', 2, true);
 return {heading: H ? info(H, H.innerText) : null, body: B ? info(B.e, B.t) : info(document.body, ''), button: btn ? info(btn.e, btn.t) : null, vw: W};
}"""
def resolve(fonts_raw):
    R = {r: resolve_role((fonts_raw or {}).get(r), r) for r in ("heading", "body", "button")}
    b = R["body"]
    if b.get("family") and GF[b["family"]]["c"] in ("Display", "Handwriting"):   # body text stays readable
        R["body"] = dict(b, family="Inter" if b["source"] != "exact" else b["family"], why=b["why"] + "; display / script face kept off body text" if b["source"] != "exact" else b["why"])
        if b["source"] == "exact": R["body"] = dict(b, source="mapped", family="Inter", why=f"{b['detected']} is a display face; body text uses Inter for legibility")
    h = R["heading"]
    if h.get("family") and GF[h["family"]]["c"] == "Handwriting": R["heading"] = dict(h, source="template", why=h["why"] + "; handwriting face not used for big headlines (legibility)")
    bt = R["button"]   # a button font that is not a loaded webfont on a site whose text is (a widget / theme default) -> the body's choice
    if bt.get("family") and not bt.get("site_webfont") and (R["body"].get("site_webfont") or R["heading"].get("site_webfont")):
        R["button"] = dict(R["body"], role="button", why=f"button font {bt.get('detected')} is not loaded by the site (widget or default); buttons use the body font")
    return R
def css(R):
    """Theme overrides + font links for build.py. Template defaults stay as the fallback (and come back if loading fails)."""
    links, vars_, fams = [], [], {}
    def need(fam, w):
        fams.setdefault(fam, set()).add(pick_weight(fam, w))
    h, b, bt = R["heading"], R["body"], R["button"]
    if h.get("family"):
        sans_floor = 400 if GF[h["family"]]["c"] == "Serif" else 500
        hw = pick_weight(h["family"], max(sans_floor, min(900, int(h.get("weight") or 700))))
        need(h["family"], hw)
        w = GF[h["family"]].get("wd") or 7
        cond = h.get("style") == "condensed" or "Condensed" in h["family"] or h["family"] in ("Oswald", "Anton", "Bebas Neue", "Barlow Condensed", "Archivo Narrow", "Fjalla One", "League Gothic")
        upper = (h.get("transform") == "uppercase")
        scale = 1 if cond else (.80 if w <= 7 else .74) * (1.06 if not upper else 1)
        vars_ += [f"--font-display:'{h['family']}',var(--font-display-t)", f"--display-weight:{hw}", f"--display-case:{'uppercase' if upper else 'none'}",
                  f"--disp-scale:{min(1, round(scale, 2))}", f"--disp-lh:{'.95' if upper or cond else '1.04'}", f"--disp-ls:{'-.01em' if upper or cond else '-.02em'}"]
    if b.get("family"):
        for w_ in (400, 500, 700): need(b["family"], w_)
        vars_.append(f"--font-body:'{b['family']}',var(--font-body-t)")
    if bt.get("family"):
        bw = pick_weight(bt["family"], max(600, min(800, int(bt.get("weight") or 700))))
        need(bt["family"], bw)
        same_as_h = bt["family"] == h.get("family")
        if not same_as_h:
            cond = "Condensed" in bt["family"] or bt["family"] in ("Oswald", "Anton", "Bebas Neue", "Archivo Narrow")
            vars_ += [f"--font-button:'{bt['family']}',var(--font-display-t)", f"--button-weight:{bw}", f"--button-case:{'uppercase' if bt.get('transform') == 'uppercase' else 'none'}",
                      f"--btn-scale:{1 if cond else .82}"]
    for fam, ws in fams.items():
        ws = sorted(ws); ax = GF[fam].get("ax", {}).get("wght")
        spec = f"family={fam.replace(' ', '+')}" + (f":wght@{';'.join(map(str, ws))}" if ws != [400] else "")
        links.append(f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{spec}&display=swap" data-font="{fam}">')
    if not vars_: return ""
    roles = {r: R[r]["family"] for r in ("heading", "body", "button") if R[r].get("family")}
    # if a family does not load (blocked, offline, Google down), the template's own fonts come back for that role
    js = ("<script>(function(){var R=" + json.dumps(roles) + ",H=document.documentElement;function ok(f){return Array.from(document.fonts).some(function(x){return x.family.replace(/[\"']/g,'')===f&&x.status==='loaded'})}"
          "var t=setTimeout(chk,3500);function chk(){clearTimeout(t);if(R.heading&&!ok(R.heading))H.classList.add('ff-h');if(R.body&&!ok(R.body))H.classList.add('ff-b');if(R.button&&!ok(R.button))H.classList.add('ff-bt');window.dispatchEvent(new Event('fontsdone'))}"
          "Promise.all(Object.values(R).map(function(f){return document.fonts.load('700 40px \"'+f+'\"').catch(function(){})})).then(function(){setTimeout(chk,50)})})()</script>")
    return "".join(links) + f"<style>:root{{{';'.join(vars_)}}}html.ff-h{{--font-display:var(--font-display-t);--display-weight:800;--display-case:uppercase;--disp-scale:1;--disp-lh:.95;--disp-ls:-.01em}}html.ff-b{{--font-body:var(--font-body-t)}}html.ff-bt{{--font-button:var(--font-display);--button-weight:var(--display-weight);--button-case:var(--display-case);--btn-scale:1}}</style>" + js
