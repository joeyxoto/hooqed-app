"""Contact sheet of generated images with their prompts."""
import sys, json, textwrap
from PIL import Image, ImageDraw, ImageFont
d = sys.argv[1]; h = json.load(open(f"{d}/hooq.json"))
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15) if __import__("os").path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") else ImageFont.load_default()
W, IH, TH, cols = 480, 360, 110, 4
ph = [p for p in h["photos"]]; rows = (len(ph) + cols - 1) // cols
sheet = Image.new("RGB", (W * cols, (IH + TH) * rows), "white"); dr = ImageDraw.Draw(sheet)
for i, p in enumerate(ph):
    x, y = (i % cols) * W, (i // cols) * (IH + TH)
    try: im = Image.open(f"{d}/images/{p['id']}.jpg").convert("RGB"); im.thumbnail((W - 10, IH - 10)); sheet.paste(im, (x + 5, y + 5))
    except Exception: dr.text((x + 10, y + 10), "missing", fill="red", font=F)
    dr.text((x + 6, y + IH), p["id"] + ": " + "\n".join(textwrap.wrap(p.get("prompt", p["scene"]), 52))[:400], fill="black", font=F)
sheet.save(f"{d}/contact-sheet.jpg", quality=85); print("ok")
