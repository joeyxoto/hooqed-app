"""Runs the v7 pipeline (engine/, copied unchanged from hooq-proof tag flowA-blind-v7) as subprocesses.

The pipeline scripts expect to run from a folder that contains `pipeline/` and `data/`. We build a small
"root" per hooq template made of symlinks, so `pipeline/template.html` points at the chosen template
folder in hooq_templates/ while every other file is the untouched engine file.
"""
import json, os, shutil, subprocess, sys, time
from pathlib import Path
from . import config

ENGINE = config.REPO / "engine"
TEMPLATES = config.REPO / "hooq_templates"

# Full build: the order of run.sh, minus shots.py (review screenshots only).
BUILD_STEPS = [
    ("scrape", "Reading your website", ["pipeline/scrape.py", "{url}", "{d}/scrape.json"], "scrape.json"),
    ("owner", "Adding your answer", ["pipeline/owner_input.py", "{d}"], None),
    ("locale", "Working out your country and currency", ["pipeline/locale_detect.py", "{d}"], None),
    ("facts", "Understanding your services", ["pipeline/facts.py", "{d}"], "facts.json"),
    ("route", "Working out what people book with you", ["pipeline/route.py", "{d}"], None),
    ("write", "Writing your questions and result page", ["pipeline/write.py", "{d}"], "hooq.raw.json"),
    ("validate", "Checking prices and claims", ["pipeline/validate.py", "{d}"], None),
    ("images", "Making your photos", ["pipeline/images.py", "{d}"], None),
    ("brand", "Matching your brand", ["pipeline/brand.py", "{d}"], None),
    ("overrides", "Applying your choices", None, None),
    ("build", "Building your hooq", ["pipeline/build.py", "{d}"], None),
    ("cost", "Logging the cost", ["pipeline/cost.py", "{d}"], None),
]
# Owner-check re-render: no AI step runs (facts/write are cached; images.py skips photos that exist).
RERENDER = ["locale", "validate", "images", "brand", "overrides", "build", "cost"]


def template_root(name: str) -> Path:
    """A folder with pipeline/* and data/ symlinked to the engine, and pipeline/template.html -> the template."""
    tdir = TEMPLATES / name
    if not (tdir / "template.html").exists():
        raise ValueError(f"unknown hooq template {name}")
    root = config.DATA / "roots" / name
    (root / "pipeline").mkdir(parents=True, exist_ok=True)
    for f in (ENGINE / "pipeline").iterdir():
        if f.name in ("template.html", "__pycache__"):
            continue
        link = root / "pipeline" / f.name
        if not link.exists():
            link.symlink_to(f.resolve())
    t = root / "pipeline" / "template.html"
    if t.is_symlink() or t.exists():
        t.unlink()
    t.symlink_to((tdir / "template.html").resolve())
    if not (root / "data").exists():
        (root / "data").symlink_to((ENGINE / "data").resolve())
    return root


def child_env() -> dict:
    env = dict(os.environ)
    key = os.environ.get("XAI_API_KEY") or os.environ.get("BT_XAI_API_KEY")
    if key:
        env["BT_XAI_API_KEY"] = key        # the engine reads BT_XAI_API_KEY (unchanged code)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for k in ("RESEND_API_KEY", "BT_RESEND_API_KEY", "SECRET_KEY"):
        env.pop(k, None)                   # the engine never needs these
    return env


def apply_overrides(d: Path):
    """App-side owner choices that v7 has no file for (hide a price, owner-typed range replacing a site figure).
    Edits hooq.json between validate and build; build.py + accuracy.py then check every figure as usual."""
    ov_p = d / "hooqed-overrides.json"
    if not ov_p.exists():
        return "no overrides"
    ov = json.loads(ov_p.read_text())
    h = json.loads((d / "hooq.json").read_text())
    done = []
    rm = set(ov.get("remove_jobs") or [])
    if rm and len([j for j in h["jobs"] if j["id"] not in rm]) >= 1:
        h["jobs"] = [j for j in h["jobs"] if j["id"] not in rm]; done.append("removed: " + ", ".join(sorted(rm)))
    for j in h["jobs"]:
        o = (ov.get("prices") or {}).get(j["id"]) or {}
        if ov.get("hide_all") or o.get("hide"):
            j["price"] = {"mode": "none"}; done.append(f"{j['id']}: hidden")
        elif o.get("low"):
            j["price"] = {"mode": "owner", "low": o["low"], "high": o.get("high"), "basis": j["price"].get("basis") or j.get("basis"), "flat": not o.get("high")}
            done.append(f"{j['id']}: owner range {o['low']}-{o.get('high')}")
    if ov.get("hide_all"):
        h["path"] = 3
    (d / "hooq.json").write_text(json.dumps(h, indent=1))
    return "; ".join(done) or "nothing to change"


ASK = 10   # a step's exit code for "needs the owner's input" (engine/pipeline/ask.py)
PLAIN = {   # what the owner sees if a step really can't finish: plain words, never an exit code
    "scrape": "We couldn't open your website. Check the address and try again.",
    "owner": "We couldn't add your answer. Try again in a minute.",
    "locale": "We couldn't work out your country and currency. Try again in a minute.",
    "images": "We couldn't make your photos this time. Try again in a minute.",
    "build": "We couldn't put your hooq together this time. Try again in a minute.",
    "cost": "We couldn't finish this build. Try again in a minute.",
}


class NeedsInput(Exception):
    """The build paused for an owner question (needs-input.json); it carries on from the cached steps after they answer."""
    def __init__(self, ask: dict):
        super().__init__(ask.get("title") or "Needs your input")
        self.ask = ask


class BuildError(Exception):
    """A plain-words reason for the owner (the technical detail stays in run.log and the server log)."""


def _ask(d: Path, case: str, why: str, step: str) -> dict:
    import importlib.util   # engine/pipeline/ask.py: one place for the question wording (loaded by path, so no engine module shadows an app one)
    spec = importlib.util.spec_from_file_location("hooq_ask", ENGINE / "pipeline" / "ask.py"); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
    return A.write(str(d), case, why, step=step)


def run_steps(d: Path, steps, url: str = "", template: str = "v7", on_step=None, log=None):
    """Runs the steps in order. Never ends on a raw error: an AI step that fails gets one retry; a quote flow the
    checks can't stand up is rebuilt as the person flow; then the owner is asked (NeedsInput). No colours -> clean default."""
    import re
    root = template_root(template)
    env = child_env()
    if (d / "search-hint.json").exists():
        env["HOOQ_HINT"] = str(d / "search-hint.json")
    by = {s[0]: s for s in BUILD_STEPS}
    (d / "costlog.jsonl").touch()
    logf = open(d / "run.log", "a")

    def tail():
        return [re.sub(r"xai-[A-Za-z0-9*]+", "xai-***", l.strip()) for l in open(d / "run.log", errors="replace").read().splitlines() if l.strip()][-6:]

    def exec_(key) -> int:
        _, label, cmd, _ = by[key]
        t0 = time.time()
        args = [sys.executable] + [c.format(url=url, d=str(d)) for c in cmd]
        p = subprocess.run(args, cwd=root, env=env, stdout=logf, stderr=subprocess.STDOUT, timeout=900)
        logf.write(f"[{key}] exit {p.returncode} in {time.time() - t0:.1f}s\n"); logf.flush()
        if p.returncode not in (0, ASK):
            print(f"[hooqed] step {key} failed in {d.name}:\n" + "\n".join(tail()), flush=True)
        return p.returncode

    def needs_input():
        return NeedsInput(json.loads((d / "needs-input.json").read_text()))

    def note(msg):
        logf.write(f"[recover] {msg}\n"); logf.flush()

    def owner_answered():
        try:
            return bool(json.loads((d / "owner-answer.json").read_text()).get("answers"))
        except Exception:
            return False

    def flow():
        try:
            return json.loads((d / "route.json").read_text()).get("flow", "quote")
        except Exception:
            return "quote"

    try:
        for i, name in enumerate(steps):
            key, label, cmd, skip_if = by[name]
            if on_step:
                on_step(i, len(steps), key, label)
            if skip_if and (d / skip_if).exists():
                logf.write(f"[{key}] cached\n"); logf.flush(); continue
            if key == "overrides":
                logf.write(f"[overrides] {apply_overrides(d)}\n"); logf.flush(); continue
            rc = exec_(key)
            if rc == 0:
                continue
            if rc == ASK:
                raise needs_input()
            # --- recover instead of failing ---
            if key in ("facts", "write"):
                note(f"{key} failed (exit {rc}): retrying once")
                if skip_if and (d / skip_if).exists():
                    (d / skip_if).unlink()
                rc = exec_(key)
                if rc == 0:
                    continue
                if rc == ASK:
                    raise needs_input()
            if key == "validate" and "write" in steps:
                if flow() == "quote" and not (d / "flow-override.json").exists():
                    note("the quote flow didn't pass the checks: rebuilding as the person flow (situation / goal / what's in the way)")
                    (d / "flow-override.json").write_text(json.dumps({"flow": "person", "why": "quote flow failed the checks", "at": time.time()}))
                    (d / "hooq.raw.json").unlink(missing_ok=True)
                    for k2 in ("route", "write", "validate"):
                        rc = exec_(k2)
                        if rc != 0:
                            break
                    if rc == 0:
                        continue
                    if rc == ASK:
                        raise needs_input()
            if key == "brand":   # no logo or colours: carry on with a clean default, never pause
                note(f"brand failed (exit {rc}): clean default brand used")
                (d / "brand.json").write_text(json.dumps(DEFAULT_BRAND, indent=1))
                continue
            if key in ("facts", "route", "write", "validate") and "write" in steps and not owner_answered():
                raise NeedsInput(_ask(d, "build_failed", f"{key} failed twice", key))
            raise BuildError(PLAIN.get(key) or "We couldn't finish your hooq this time. Try again in a minute, or tell us what the call is for.")
    finally:
        logf.close()


# clean default when the site gives no usable logo/colours (also the fallback if brand.py itself fails)
DEFAULT_BRAND = {"primary": "#1F2937", "brand": "#1F2937", "on_brand": "#FFFFFF", "button": "#1F2937", "on_button": "#FFFFFF", "deep": "#111827", "on_deep": "#FFFFFF",
                 "accent_text": "#1F2937", "header_bg": "#FFFFFF", "on_header": "#111827", "logo_file": None, "colour_source": "clean default (no brand colours found)", "colour_candidates": []}


def cost_pence(d: Path) -> float:
    try:
        return float(json.loads((d / "cost.json").read_text()).get("pence", 0))
    except Exception:
        return 0.0


def ai_calls(d: Path) -> int:
    p = d / "costlog.jsonl"
    return sum(1 for _ in open(p)) if p.exists() else 0
