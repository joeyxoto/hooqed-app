"""Logo candidates from a page (v4.1). Header/nav logos first; every candidate keeps its alt text, file name and where it sat, so brand.py
can reject partner / supplier / accreditation logos and check that the chosen mark belongs to THIS business."""
import re, urllib.parse as U
from bs4 import BeautifulSoup
def _in(el, rx):
    for p in el.parents:
        if p.name in ("html", "body", "[document]", None): continue
        if p.name in rx[0] or re.search(rx[1], " ".join(p.get("class", []) if isinstance(p.get("class"), list) else []) + " " + (p.get("id") or ""), re.I): return True
    return False
HDR = (("header", "nav"), r"header|navbar|masthead|site-branding|top-?bar|nav-?brand|site-logo")
FTR = (("footer",), r"footer")
def extract(html, base):
    soup = BeautifulSoup(html, "html.parser"); host = U.urlparse(base).netloc.lower().removeprefix("www."); out = []
    for i, im in enumerate(soup.find_all(["img", "svg"])):
        a = im.find_parent("a"); href = U.urljoin(base, a.get("href", "")) if a else ""
        link_home = bool(a) and U.urlparse(href).netloc.lower().removeprefix("www.") in (host, "") and U.urlparse(href).path.strip("/") in ("", "home", "index.html")
        hdr = _in(im, HDR); ftr = _in(im, FTR)
        if im.name == "img":
            src = im.get("src") or im.get("data-src") or ""
            if not src or src.startswith("data:"): continue
            alt = (im.get("alt") or "").strip(); cls = " ".join(im.get("class", []))
            if not (re.search(r"logo", src + " " + cls + " " + alt, re.I) or (hdr and link_home)): continue
            out.append({"url": U.urljoin(base, src), "alt": alt, "header": hdr, "footer": ftr, "link_home": link_home, "order": i})
        else:   # inline SVG mark: only when it is the header's home link (a real site mark, not an icon)
            if not (hdr and link_home): continue
            cls = " ".join((a.get("class") or []) if a else []); svg = str(im)
            if len(svg) < 400 or re.search(r"menu|toggle|icon|phone|search|close|burger", " ".join(im.get("class", [])), re.I): continue
            out.append({"url": None, "inline_svg": svg, "alt": (a.get("aria-label") or a.get("title") or "") if a else "", "header": True, "footer": False, "link_home": True, "order": i, "anchor_class": cls})
    seen, res = set(), []
    for c in out:
        k = c.get("url") or c["inline_svg"][:200]
        if k in seen: continue
        seen.add(k); res.append(c)
    return res[:16]
