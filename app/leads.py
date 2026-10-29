"""Lead capture and follow-up emails (lead summary to the visitor, lead alert with the one-line brief to the owner).
Emails go out when the visitor picks how to be contacted, or LEAD_EMAIL_DELAY seconds after they left their details."""
import html, json, logging, os, re, threading, time
from . import config, db, mail

log = logging.getLogger("hooqed.leads")
DELAY = int(os.environ.get("LEAD_EMAIL_DELAY", "180"))
E = html.escape


def _hooq_json(hid):
    try:
        return json.loads((config.DATA / "hooqs" / str(hid) / "hooq.json").read_text())
    except Exception:
        return {}


def describe(hooq_row, lead):
    """Job label, answer rows and the price shown, all read from the hooq's own content."""
    h = _hooq_json(hooq_row["id"]); a = json.loads(lead["answers"] or "{}")
    job = next((j for j in h.get("jobs", []) if j["id"] == a.get("job")), None)
    label = job["label"] if job else ("Something else" if a.get("job") == "other" else a.get("job") or "")
    rows = []
    if job:
        for i, q in enumerate(job.get("questions", [])):
            v = a.get(f"q{i}"); ids = v if isinstance(v, list) else [v]   # v8 multi-select questions store a list of option ids
            os_ = [o for o in q["options"] if o["id"] in ids]
            if os_:
                rows.append((q.get("short") or q.get("title"), ", ".join(o["label"] for o in os_)))
    m = re.search(r"shown (.+?) \((your published price|your own range)\)", lead["brief"] or "")
    return label, rows, (m.group(1) if m else ""), h.get("shortName") or hooq_row["name"]


def send_emails(lead_id):
    lead = db.one("SELECT * FROM leads WHERE id=?", lead_id)
    if not lead or lead["emailed"]:
        return
    db.run("UPDATE leads SET emailed=1 WHERE id=?", lead_id)
    hq = db.one("SELECT * FROM hooqs WHERE id=?", lead["hooq_id"])
    owner = db.one("SELECT * FROM owners WHERE id=?", hq["owner_id"])
    label, rows, price, biz = describe(hq, lead)
    # owner alert: the one-line brief
    subj = f"New lead: {lead['name'] or 'someone'} · {label}"
    body = (f"<p><b>{E(lead['brief'] or '')}</b></p><p>Name: {E(lead['name'] or '')}<br>Phone: {E(lead['phone'] or '')}<br>"
            f"Email: {E(lead['email'] or '')}<br>Postcode: {E(lead['postcode'] or '')}</p><p><a href='{config.BASE_URL}/dashboard'>Open your leads</a></p>")
    mail.send(owner["email"], subj, body, (lead["brief"] or "") + f"\n{config.BASE_URL}/dashboard", "owner-alert")
    # the lead's summary (only if they gave an email)
    if lead["email"]:
        lines = "".join(f"<tr><td style='color:#666;padding:2px 12px 2px 0'>{E(k)}</td><td><b>{E(v)}</b></td></tr>" for k, v in [("Job", label), *rows] if v)
        pr = f"<p>Price shown: <b>{E(price)}</b></p>" if price else ""
        html_ = f"<p>Hi {E(lead['name'] or 'there')},</p><p>Here is your summary from {E(biz)}.</p><table>{lines}</table>{pr}<p>{E(biz)} will be in touch.</p>"
        text = f"Hi {lead['name'] or 'there'},\nHere is your summary from {biz}.\nJob: {label}\n" + "".join(f"{k}: {v}\n" for k, v in rows) + (f"Price shown: {price}\n" if price else "") + f"{biz} will be in touch."
        mail.send(lead["email"], f"Your {label.lower()} summary from {biz}", html_, text, "lead-summary")


def _sweeper():
    while True:
        try:
            for r in db.q("SELECT id FROM leads WHERE emailed=0 AND created < ?", time.time() - DELAY):
                send_emails(r["id"])
        except Exception:
            log.exception("lead email sweep failed")
        time.sleep(5)


def start():
    threading.Thread(target=_sweeper, name="hooqed-leads", daemon=True).start()
