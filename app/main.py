import io, json, logging, os, re, secrets, time
from pathlib import Path
from urllib.parse import urlparse
import bcrypt
from fastapi import FastAPI, Request, Form, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from PIL import Image
from . import config, db, engine, jobs, leads, publish

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("hooqed")
APP_DIR = Path(__file__).parent
app = FastAPI(title="Hooqed v0")
secret = config.SECRET_KEY or secrets.token_hex(32)
if not config.SECRET_KEY:
    log.warning("SECRET_KEY not set: using a random one (everyone is logged out on restart)")
app.add_middleware(SessionMiddleware, secret_key=secret, same_site="lax", https_only=config.BASE_URL.startswith("https"), max_age=60 * 60 * 24 * 30)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
T = Jinja2Templates(directory=APP_DIR / "templates")
from markupsafe import Markup
T.env.filters["timefmt"] = lambda t: time.strftime("%d %b %H:%M", time.localtime(t or 0))
T.env.globals["ic"] = {k: Markup(v) for k, v in json.loads((APP_DIR / "icons.json").read_text()).items()}   # Dex's icons (scene A/D)


@app.on_event("startup")
def _start():
    db.conn(); jobs.start(); leads.start()


def page(req, name, **ctx):
    ctx.setdefault("owner", current(req)); ctx.setdefault("nav", "")
    return T.TemplateResponse(req, name, ctx)


def current(req):
    oid = req.session.get("oid")
    return db.one("SELECT * FROM owners WHERE id=?", oid) if oid else None


def need_owner(req):
    o = current(req)
    if not o:
        raise HTTPException(303, headers={"Location": "/login"})
    return o


def own_hooq(req, hid):
    o = need_owner(req)
    h = db.one("SELECT * FROM hooqs WHERE id=? AND owner_id=?", hid, o["id"])
    if not h:
        raise HTTPException(404)
    return o, h


def hdir(hid):
    return config.DATA / "hooqs" / str(hid)


def rj(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default if default is not None else {}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def home(req: Request):
    return RedirectResponse("/dashboard" if current(req) else "/login", 303)


# ---------- accounts ----------
@app.get("/signup", response_class=HTMLResponse)
def signup_form(req: Request):
    return page(req, "auth.html", mode="signup", error=None)


@app.post("/signup")
def signup(req: Request, email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+$", email) or len(password) < 8:
        return page(req, "auth.html", mode="signup", error="Use a real email and a password of 8 or more characters.")
    if db.one("SELECT 1 FROM owners WHERE email=?", email):
        return page(req, "auth.html", mode="signup", error="That email already has an account. Log in instead.")
    oid = db.run("INSERT INTO owners(email,pw_hash,created) VALUES(?,?,?)", email, bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(), time.time())
    req.session["oid"] = oid
    return RedirectResponse("/new", 303)


@app.get("/login", response_class=HTMLResponse)
def login_form(req: Request):
    return page(req, "auth.html", mode="login", error=None)


@app.post("/login")
def login(req: Request, email: str = Form(...), password: str = Form(...)):
    o = db.one("SELECT * FROM owners WHERE email=?", email.strip().lower())
    if not o or not bcrypt.checkpw(password.encode(), o["pw_hash"].encode()):
        return page(req, "auth.html", mode="login", error="Email or password is wrong.")
    req.session["oid"] = o["id"]
    return RedirectResponse("/dashboard", 303)


@app.get("/logout")
def logout(req: Request):
    req.session.clear()
    return RedirectResponse("/login", 303)


# ---------- build ----------
@app.get("/new", response_class=HTMLResponse)
def new_form(req: Request):
    need_owner(req)
    return page(req, "new.html", nav="hooqs", error=None)


@app.post("/new")
def new(req: Request, url: str = Form(...)):
    o = need_owner(req)
    url = url.strip()
    if not re.match(r"https?://", url):
        url = "https://" + url
    u = urlparse(url)
    if not u.netloc or "." not in u.netloc:
        return page(req, "new.html", nav="hooqs", error="That doesn't look like a website address.")
    hid = db.run("INSERT INTO hooqs(owner_id,url,name,created,status,kind) VALUES(?,?,?,?, 'queued','build')", o["id"], url, u.netloc.removeprefix("www."), time.time())
    return RedirectResponse(f"/hooq/{hid}/build", 303)


@app.get("/hooq/{hid}/build", response_class=HTMLResponse)
def build_page(req: Request, hid: int):
    o, h = own_hooq(req, hid)
    return page(req, "build.html", nav="hooqs", h=h)


@app.get("/hooq/{hid}/status")
def status(req: Request, hid: int):
    o, h = own_hooq(req, hid)
    d = hdir(hid); extra = {}
    sc = rj(d / "scrape.json")
    if sc.get("pages"):
        extra["pages"] = len(sc["pages"])
    hj = rj(d / "hooq.raw.json") or {}
    if hj.get("jobs"):
        extra["services"] = [j["label"] for j in hj["jobs"]]
    br = rj(d / "brand.json")
    if br.get("primary"):
        extra["colours"] = [c["hex"] for c in (br.get("colour_candidates") or [])[:4]] or [br["primary"]]
    el = (h["finished"] or time.time()) - (h["started"] or time.time()) if h["started"] else 0
    return {"status": h["status"], "step": h["step"], "steps": h["steps"], "label": h["step_label"], "error": h["error"], "kind": h["kind"],
            "elapsed": round(el), "name": h["name"], "labels": _labels(h["kind"]), **extra}


def _labels(kind):
    lab = {k: l for k, l, *_ in engine.BUILD_STEPS}
    keys = engine.RERENDER if kind == "rerender" else [s[0] for s in engine.BUILD_STEPS]
    return [lab.get(k, k) for k in keys]


# ---------- owner check ----------
def check_ctx(hid):
    d = hdir(hid)
    hq, br, vj = rj(d / "hooq.json"), rj(d / "brand.json"), rj(d / "validate.json")
    oc, ov, bk = rj(d / "owner-check.json"), rj(d / "hooqed-overrides.json"), rj(d / "booking-embed.json")
    sym = (hq.get("locale") or {}).get("symbol") or (vj.get("owner_prompt") or {}).get("symbol", "")
    removed = set(ov.get("remove_jobs") or [])
    raw = rj(d / "hooq.raw.json")
    all_jobs = raw.get("jobs") or hq.get("jobs") or []
    built = {j["id"]: j for j in hq.get("jobs", [])}
    vjobs = {j.get("id"): j for j in (vj.get("jobs") or []) if isinstance(j, dict)}
    jobs_ = []
    for j in all_jobs:
        b = built.get(j["id"], j); p = b.get("price") or {}
        o = (ov.get("prices") or {}).get(j["id"]) or {}
        fig = ""
        if p.get("mode") in ("site", "owner") and p.get("low"):
            fig = (f"{sym}{p['low']:,}" + (f" – {sym}{p['high']:,}" if p.get("high") else "")) + (f" {p['unit']}" if p.get("unit") else "")
        elif p.get("mode") == "table":
            fig = f"{len(p.get('rows', []))} rows from your price table"
        jobs_.append({"id": j["id"], "label": j["label"], "mode": p.get("mode", "none"), "figure": fig, "quote": p.get("site_quote") or "",
                      "removed": j["id"] in removed, "o": o})
    cands = [c for c in (br.get("logo_candidates") or []) if c.get("url") and c.get("status") != "rejected" and c["url"] != br.get("logo_url")][:6]
    sw = [c for c in (br.get("colour_candidates") or [])[:5]]
    if br.get("primary") and br["primary"] not in [c["hex"] for c in sw]:
        sw.insert(0, {"hex": br["primary"], "source": "current"})
    photos = [{"id": p["id"], "label": "Intro photo" if p["id"] == "p-intro" else "Photo for " + next((j["label"] for j in all_jobs if "p-" + j["id"] == p["id"]), p["id"]),
               "own": (d / "images" / f"{p['id']}.owner").exists()} for p in hq.get("photos", [])]
    return dict(hq=hq, br=br, oc=oc, ov=ov, bk=bk, sym=sym, jobs=jobs_, cands=cands, swatches=sw, photos=photos,
                chips=hq.get("chips") or [], chips_removed=oc.get("chips_remove") or [], hide_all=bool(ov.get("hide_all")))


@app.get("/hooq/{hid}/check", response_class=HTMLResponse)
def check_page(req: Request, hid: int):
    o, h = own_hooq(req, hid)
    if h["status"] != "ready":
        return RedirectResponse(f"/hooq/{hid}/build", 303)
    return page(req, "check.html", nav="hooqs", h=h, **check_ctx(hid), saved=req.query_params.get("saved"))


def _num(v):
    v = re.sub(r"[^\d.]", "", v or "")
    try:
        return int(float(v)) if v else None
    except ValueError:
        return None


EMBED_KINDS = [(r"iclosed\.io", "iclosed", "https://app.iclosed.io/assets/widget.js"), (r"calendly\.com", "calendly", ""), (r"cal\.com", "calcom", "")]


@app.post("/hooq/{hid}/check")
async def check_save(req: Request, hid: int):
    o, h = own_hooq(req, hid)
    d = hdir(hid); f = await req.form(); hq = rj(d / "hooq.json"); raw = rj(d / "hooq.raw.json")
    oc = rj(d / "owner-check.json")
    # logo
    lg = f.get("logo", "keep")
    if lg == "wordmark":
        oc["logo"] = "wordmark"
    elif lg.startswith("http"):
        oc["logo"] = lg
    # colour
    col = (f.get("colour_custom") or "").strip() or f.get("colour") or ""
    if re.match(r"#[0-9a-fA-F]{6}$", col):
        oc["colour"] = col.lower()
    # chips
    keep = set(f.getlist("chip_keep"))
    oc["chips_remove"] = sorted(set(oc.get("chips_remove") or []) | {c for c in hq.get("chips", []) if c not in keep})
    oc["by"] = "owner check (Hooqed v0)"
    (d / "owner-check.json").write_text(json.dumps(oc, indent=1))
    # services + prices
    ov = {"prices": {}, "remove_jobs": [], "hide_all": f.get("hide_all") == "1"}
    owner_prices = {}
    jobs_all = raw.get("jobs") or hq.get("jobs") or []
    for j in jobs_all:
        jid = j["id"]
        if f.get(f"show_{jid}") != "1":
            ov["remove_jobs"].append(jid)
        choice = f.get(f"price_{jid}", "keep")
        lo, hi = _num(f.get(f"low_{jid}")), _num(f.get(f"high_{jid}"))
        if choice == "hide":
            ov["prices"][jid] = {"hide": True}
        elif choice == "range" and lo:
            if hi and hi < lo:
                lo, hi = hi, lo
            ov["prices"][jid] = {"low": lo, "high": hi if hi and hi != lo else None}
            owner_prices[jid] = {"low": lo, "high": hi if hi and hi != lo else None, "basis": j.get("basis")}
    if len(ov["remove_jobs"]) >= len(jobs_all):
        ov["remove_jobs"] = ov["remove_jobs"][1:]   # keep at least one service
    (d / "hooqed-overrides.json").write_text(json.dumps(ov, indent=1))
    (d / "owner-prices.json").write_text(json.dumps(owner_prices, indent=1))
    # booking link
    bl = (f.get("booking_url") or "").strip()
    if bl and re.match(r"https://", bl):
        kind, script = next(((k, s) for rx, k, s in EMBED_KINDS if re.search(rx, bl)), ("link", ""))
        (d / "booking-embed.json").write_text(json.dumps({"kind": kind if kind == "iclosed" else kind, "url": bl, "script": script or "/static/noop.js", "title": "Booking calendar", "note": ""}, indent=1))
        db.run("UPDATE hooqs SET booking_url=? WHERE id=?", bl, hid)
    elif not bl:
        (d / "booking-embed.json").unlink(missing_ok=True); db.run("UPDATE hooqs SET booking_url=NULL WHERE id=?", hid)
    # own photos: saved as images/<id>.png so images.py treats them as done (0 AI calls)
    for p in hq.get("photos", []):
        up = f.get(f"photo_{p['id']}")
        if up is not None and getattr(up, "filename", "") and (data := await up.read()):
            try:
                im = Image.open(io.BytesIO(data)).convert("RGB")
            except Exception:
                continue
            im.thumbnail((1600, 1600))
            (d / "images").mkdir(exist_ok=True)
            orig = d / "images" / f"{p['id']}.ai.png"
            if (d / "images" / f"{p['id']}.png").exists() and not orig.exists():
                (d / "images" / f"{p['id']}.png").rename(orig)   # keep the AI photo in case the owner switches back
            im.save(d / "images" / f"{p['id']}.png")
            (d / "images" / f"{p['id']}.owner").write_text(up.filename[:120])
        elif f.get(f"photo_reset_{p['id']}") == "1" and (d / "images" / f"{p['id']}.ai.png").exists():
            (d / "images" / f"{p['id']}.ai.png").replace(d / "images" / f"{p['id']}.png"); (d / "images" / f"{p['id']}.owner").unlink(missing_ok=True)
    jobs.enqueue(hid, "rerender")
    return RedirectResponse(f"/hooq/{hid}/build", 303)


# ---------- preview / publish ----------
@app.get("/hooq/{hid}/preview/{path:path}")
def preview(req: Request, hid: int, path: str = ""):
    own_hooq(req, hid)
    d = hdir(hid).resolve()
    p = (d / (path or "hooq.html")).resolve()
    if not str(p).startswith(str(d)) or not p.is_file() or p.suffix not in (".html", ".jpg", ".png", ".svg", ".webp"):
        raise HTTPException(404)
    return FileResponse(p)


@app.post("/hooq/{hid}/publish")
def do_publish(req: Request, hid: int):
    o, h = own_hooq(req, hid)
    if h["status"] != "ready":
        raise HTTPException(400, "not ready")
    publish.publish(hid)
    return RedirectResponse(f"/hooq/{hid}/share", 303)


@app.post("/hooq/{hid}/unpublish")
def do_unpublish(req: Request, hid: int):
    own_hooq(req, hid); publish.unpublish(hid)
    return RedirectResponse("/dashboard", 303)


@app.get("/hooq/{hid}/share", response_class=HTMLResponse)
def share(req: Request, hid: int):
    o, h = own_hooq(req, hid)
    url = f"{config.BASE_URL}/h/{h['slug']}/"
    embed = f'<iframe src="{url}" title="{h["name"]}" style="width:100%;height:900px;border:0" loading="lazy"></iframe>'
    return page(req, "share.html", nav="hooqs", h=h, url=url, embed=embed)


@app.get("/h/{slug}")
def hooq_noslash(slug: str):
    return RedirectResponse(f"/h/{slug}/", 301)


@app.get("/h/{slug}/{path:path}")
def hooq_public(slug: str, path: str = ""):
    if not re.match(r"^[a-z0-9-]+$", slug):
        raise HTTPException(404)
    d = (config.DATA / "published" / slug).resolve()
    p = (d / (path or "index.html")).resolve()
    if not str(p).startswith(str(d)) or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p)


# ---------- visitor leads ----------
_hits = {}


def _limited(ip):
    now = time.time(); h = [t for t in _hits.get(ip, []) if now - t < 60]; h.append(now); _hits[ip] = h
    return len(h) > 20


@app.post("/api/h/{slug}/lead")
async def lead_new(req: Request, slug: str):
    if _limited(req.client.host if req.client else "?"):
        raise HTTPException(429)
    hq = db.one("SELECT * FROM hooqs WHERE slug=? AND published=1", slug)
    if not hq:
        raise HTTPException(404)
    b = await req.json()
    s = lambda k, n=200: str(b.get(k) or "")[:n]
    answers = b.get("answers") if isinstance(b.get("answers"), dict) else {}
    lid = db.run("INSERT INTO leads(hooq_id,created,name,phone,email,postcode,job,brief,answers) VALUES(?,?,?,?,?,?,?,?,?)",
                 hq["id"], time.time(), s("name"), s("phone", 40), s("email"), s("postcode", 12), str(answers.get("job", ""))[:80], s("brief", 600), json.dumps(answers)[:2000])
    return {"id": lid}


@app.post("/api/h/{slug}/lead/{lid}/action")
async def lead_action(req: Request, slug: str, lid: int):
    hq = db.one("SELECT * FROM hooqs WHERE slug=? AND published=1", slug)
    lead = db.one("SELECT * FROM leads WHERE id=?", lid)
    if not hq or not lead or lead["hooq_id"] != hq["id"]:
        raise HTTPException(404)
    b = await req.json()
    kind = str(b.get("kind") or "")[:20]
    detail = {"cal": "picked a time", "cb": "call me back", "wa": "text me"}.get(str(b.get("tab")), "") if kind == "confirm" else "text me this"
    brief = str(b.get("brief") or "")[:600] if kind == "confirm" else lead["brief"]
    db.run("UPDATE leads SET action=?, action_detail=?, brief=? WHERE id=?", kind, detail + (f" ({b.get('cb')})" if b.get("cb") else ""), brief, lid)
    if kind == "confirm":
        leads.send_emails(lid)
    return {"ok": True}


# ---------- dashboard ----------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(req: Request):
    o = need_owner(req)
    hs = db.q("SELECT * FROM hooqs WHERE owner_id=? ORDER BY id DESC", o["id"])
    ls = db.q("SELECT l.*, h.name AS hname, h.id AS hid FROM leads l JOIN hooqs h ON h.id=l.hooq_id WHERE h.owner_id=? ORDER BY l.id DESC LIMIT 200", o["id"])
    rows = []
    for l in ls:
        label, ans, price, _ = leads.describe(db.one("SELECT * FROM hooqs WHERE id=?", l["hid"]), l)
        rows.append({**dict(l), "label": label, "ans": ans, "price": price})
    sel = next((r for r in rows if str(r["id"]) == req.query_params.get("lead")), rows[0] if rows else None)
    def col(r):
        a = r["action_detail"] or ""
        return "Call me back" if a.startswith("call me back") else "Picked a time" if a.startswith("picked a time") else "Text me" if a.startswith("text me") else "New enquiry"
    counts = {k: sum(1 for r in rows if col(r) == k) for k in ("New enquiry", "Call me back", "Picked a time", "Text me")}
    return page(req, "dashboard.html", nav="dashboard", counts=counts, hooqs=hs, leads=rows, sel=sel, base=config.BASE_URL)
