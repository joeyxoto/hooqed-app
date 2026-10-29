"""Sentence splitting that does not cut at abbreviations (v4.1): vs., approx., etc., e.g., i.e., incl., est., no., sq., ft., Mr., Dr., St., Ltd., Inc. ..."""
import re
ABBR = r"vs|approx|appx|etc|e\.g|i\.e|incl|excl|est|sq|avg|mr|mrs|ms|dr|st|ltd|inc|corp|jr|sr|a\.m|p\.m|dept|ave|blvd|cf|esp|misc|qty"
_ABBR_END = re.compile(rf"(?:^|[\s(])(?:{ABBR})\.$", re.I)
def split(t, newlines=False):
    out, buf = [], ""
    for piece in re.split(r"(\n)" if newlines else r"(?!)", t):
        if piece == "\n":
            if buf.strip(): out.append(buf.strip())
            buf = ""; continue
        for s in re.split(r"(?<=[.!?])\s+", piece):
            buf = (buf + " " + s) if buf else s
            if not _ABBR_END.search(buf.strip()): out.append(buf.strip()); buf = ""
    if buf.strip(): out.append(buf.strip())
    return [x for x in out if x]
def ends_abbr(s): return bool(_ABBR_END.search(s.strip()))
def complete(s, text):
    """a sentence saved by an older splitter that ends at an abbreviation: extend it to the real sentence end using the page text"""
    if not ends_abbr(s): return s
    i = text.find(s)
    if i < 0: return s
    rest = text[i + len(s):]
    for m in re.finditer(r"[.!?](?=\s|$)|\n", rest):
        cand = s + rest[:m.end()]
        if not ends_abbr(cand.rstrip("\n")): return cand.rstrip("\n").strip()
    return s
