import sys, json, os; sys.path.insert(0, "pipeline"); import xai
from concurrent.futures import ThreadPoolExecutor
d = sys.argv[1]; h = json.load(open(f"{d}/hooq.json")); os.makedirs(f"{d}/images", exist_ok=True)
def go(ph):
    p = f"{d}/images/{ph['id']}.png"
    if os.path.exists(p): return ph["id"] + " cached"
    xai.image(ph["prompt"], p, f"{d}/costlog.jsonl", "image:" + ph["id"]); return ph["id"] + " ok"
with ThreadPoolExecutor(3) as ex:
    for r in ex.map(go, h["photos"]): print(r)
from PIL import Image
for ph in h["photos"]:
    src = f"{d}/images/{ph['id']}.png"; im = Image.open(src).convert("RGB"); print(ph["id"], im.size)
    im.save(f"{d}/images/{ph['id']}.jpg", quality=84)
