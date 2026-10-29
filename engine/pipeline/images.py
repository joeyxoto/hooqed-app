import sys, json, os; sys.path.insert(0, "pipeline"); import xai
from concurrent.futures import ThreadPoolExecutor
d = sys.argv[1]; h = json.load(open(f"{d}/hooq.json")); os.makedirs(f"{d}/images", exist_ok=True)
SOFT = " Everyone is fully clothed in everyday clothes; a calm, ordinary, professional moment."
def go(ph):
    p = f"{d}/images/{ph['id']}.png"
    if os.path.exists(p): return ph["id"], "cached"
    try: xai.image(ph["prompt"], p, f"{d}/costlog.jsonl", "image:" + ph["id"]); return ph["id"], "ok"
    except xai.Moderated:   # v8: one softened retry, then the photo is dropped (the job reuses the intro photo) instead of failing the build
        try: xai.image(ph["prompt"].replace(" Candid,", SOFT + " Candid,", 1) if " Candid," in ph["prompt"] else ph["prompt"] + SOFT, p, f"{d}/costlog.jsonl", "image:" + ph["id"] + ":soft"); return ph["id"], "ok (softened after a moderation reject)"
        except xai.Moderated: return ph["id"], "dropped"
with ThreadPoolExecutor(3) as ex:
    out = dict(ex.map(go, h["photos"]))
for k, v in out.items(): print(k, v)
gone = {k for k, v in out.items() if v == "dropped"}
if gone:
    keep = [ph for ph in h["photos"] if ph["id"] not in gone]
    if not keep: raise SystemExit("no photo could be made")
    if "p-intro" in gone:   # the first photo that worked stands in as the intro
        import shutil; shutil.copy(f"{d}/images/{keep[0]['id']}.png", f"{d}/images/p-intro.png"); keep.insert(0, dict(keep[0], id="p-intro"))
    for j in h["jobs"]:
        if j.get("photo") in gone: j["photo"] = "p-intro"
    h["photos"] = keep; h.setdefault("photo_notes", []).append(f"dropped after moderation rejects: {sorted(gone)}")
    json.dump(h, open(f"{d}/hooq.json", "w"), indent=1)
from PIL import Image
for ph in h["photos"]:
    src = f"{d}/images/{ph['id']}.png"; im = Image.open(src).convert("RGB"); print(ph["id"], im.size)
    im.save(f"{d}/images/{ph['id']}.jpg", quality=84)
