"""One background worker thread inside the web service. Jobs live in the hooqs table (status queued/running/ready/needs_input/failed),
so a restart re-queues anything that was running; cached step outputs make the retry cheap."""
import json, logging, re, shutil, threading, time, traceback
from pathlib import Path
from urllib.parse import urlparse
from . import config, db, engine

log = logging.getLogger("hooqed.worker")
_started = False


def hooq_dir(hid: int) -> Path:
    return config.DATA / "hooqs" / str(hid)


def _slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "hooq").lower()).strip("-")[:40] or "hooq"
    s, n = base, 2
    while db.one("SELECT 1 FROM hooqs WHERE slug=?", s):
        s = f"{base}-{n}"; n += 1
    return s


def _seed_from_cache(d: Path, url: str):
    if not config.SCRAPE_CACHE:
        return
    host = urlparse(url).netloc.lower().removeprefix("www.")
    src = Path(config.SCRAPE_CACHE) / host / "scrape.json"
    if src.exists() and not (d / "scrape.json").exists():
        shutil.copy(src, d / "scrape.json")
        log.info("hooq %s: using cached scrape for %s (testing aid)", d.name, host)


def _run(row):
    hid, kind = row["id"], row["kind"] or "build"
    d = hooq_dir(hid); d.mkdir(parents=True, exist_ok=True)
    db.run("UPDATE hooqs SET status='running', started=?, finished=NULL, error=NULL WHERE id=?", db.now(), hid)

    def on_step(i, n, key, label):
        db.run("UPDATE hooqs SET step=?, steps=?, step_label=? WHERE id=?", i + 1, n, label, hid)

    try:
        if kind == "build":
            _seed_from_cache(d, row["url"])
            steps = [s[0] for s in engine.BUILD_STEPS]
        else:
            steps = engine.RERENDER
        calls_before = engine.ai_calls(d)
        engine.run_steps(d, steps, url=row["url"], template=row["template"] or "v7", on_step=on_step)
        calls_after = engine.ai_calls(d)
        name = row["name"]
        try:
            name = json.loads((d / "facts.json").read_text()).get("name") or name
        except Exception:
            pass
        slug = row["slug"] or _slug(json.loads((d / "hooq.json").read_text()).get("shortName") or name)
        db.run("UPDATE hooqs SET status='ready', finished=?, name=?, slug=?, cost_p=?, step_label=? WHERE id=?",
               db.now(), name, slug, engine.cost_pence(d), f"Done ({calls_after - calls_before} AI calls this run)", hid)
        with open(d / "run.log", "a") as f:
            f.write(f"[{kind}] AI calls this run: {calls_after - calls_before}\n")
        if row["published"]:
            from . import publish
            publish.publish(hid)
    except engine.NeedsInput as e:   # paused for an owner question (not a failure): the build page shows it, the answer resumes it
        log.info("hooq %s needs the owner's input: %s", hid, e.ask.get("case"))
        db.run("UPDATE hooqs SET status='needs_input', finished=?, error=NULL, step_label=? WHERE id=?", db.now(), "Needs your input", hid)
    except engine.BuildError as e:
        log.error("hooq %s failed: %s", hid, traceback.format_exc())
        db.run("UPDATE hooqs SET status='failed', finished=?, error=? WHERE id=?", db.now(), str(e)[:300], hid)
    except Exception as e:   # unexpected: the owner sees plain words; the detail stays in the server log and run.log
        log.error("hooq %s failed: %s", hid, traceback.format_exc())
        db.run("UPDATE hooqs SET status='failed', finished=?, error=? WHERE id=?", db.now(), "We couldn't finish your hooq this time. Try again in a minute.", hid)


def _loop():
    db.run("UPDATE hooqs SET status='queued' WHERE status='running'")
    while True:
        row = db.one("SELECT * FROM hooqs WHERE status='queued' ORDER BY id LIMIT 1")
        if row:
            _run(row)
        else:
            time.sleep(1)


def start():
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=_loop, name="hooqed-worker", daemon=True).start()


def enqueue(hid: int, kind: str):
    db.run("UPDATE hooqs SET status='queued', kind=?, step=0, error=NULL WHERE id=?", kind, hid)
