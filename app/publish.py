"""Publish = copy the built hooq (hooq.html + logo + images) to DATA/published/<slug>/ and add the live script
(lead capture + the owner's booking iframe). The hooq template itself is untouched."""
import json, shutil
from pathlib import Path
from . import config, db

LIVE = '<script>window.HOOQED={api:"%s/api/h/%s"};</script><script src="%s/static/live.js?v=2" defer></script>'


def publish(hid: int) -> str:
    h = db.one("SELECT * FROM hooqs WHERE id=?", hid)
    src = config.DATA / "hooqs" / str(hid)
    out = config.DATA / "published" / h["slug"]
    tmp = out.with_name(out.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
    html = (src / "hooq.html").read_text()
    base = ""   # same origin; the iframe embed loads /h/<slug>/ so relative API paths work
    html = html.replace("</body>", LIVE % (base, h["slug"], base) + "</body>", 1)
    (tmp / "index.html").write_text(html)
    (tmp / "images").mkdir()
    for f in (src / "images").glob("*.jpg"):
        shutil.copy(f, tmp / "images" / f.name)
    br = json.loads((src / "brand.json").read_text())
    if br.get("logo_file") and (src / br["logo_file"]).exists():
        shutil.copy(src / br["logo_file"], tmp / br["logo_file"])
    shutil.rmtree(out, ignore_errors=True); tmp.rename(out)
    db.run("UPDATE hooqs SET published=1 WHERE id=?", hid)
    return h["slug"]


def unpublish(hid: int):
    h = db.one("SELECT * FROM hooqs WHERE id=?", hid)
    if h["slug"]:
        shutil.rmtree(config.DATA / "published" / h["slug"], ignore_errors=True)
    db.run("UPDATE hooqs SET published=0 WHERE id=?", hid)
