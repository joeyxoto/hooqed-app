"""Email via Resend. MAIL_MODE=outbox writes every email to DATA/outbox (testing: nothing leaves the machine).
If RESEND_API_KEY or MAIL_FROM is missing, the email is skipped and logged, and the app carries on."""
import json, logging, re, time
from pathlib import Path
import requests
from . import config

log = logging.getLogger("hooqed.mail")


def send(to: str, subject: str, html: str, text: str, tag: str) -> str:
    if not to:
        return "no recipient"
    if config.MAIL_MODE == "outbox":
        stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
        p = config.DATA / "outbox" / f"{stamp}-{tag}.html"
        head = f"<!-- outbox (not sent) --><pre style='font:12px monospace;background:#eee;padding:8px'>From: {config.MAIL_FROM or '(MAIL_FROM unset)'}\nTo: {to}\nSubject: {subject}</pre>"
        p.write_text(head + html)
        p.with_suffix(".json").write_text(json.dumps({"from": config.MAIL_FROM, "to": to, "subject": subject, "text": text}, indent=1))
        log.info("email written to outbox: %s", p.name)
        return "outbox"
    if not (config.RESEND_API_KEY and config.MAIL_FROM):
        log.warning("email skipped (RESEND_API_KEY or MAIL_FROM not set): %s", subject)
        return "email skipped"
    try:
        r = requests.post("https://api.resend.com/emails", timeout=20,
                          headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
                          json={"from": config.MAIL_FROM, "to": [to], "subject": subject, "html": html, "text": text})
        if r.status_code >= 300:
            log.error("resend error %s: %s", r.status_code, r.text[:200])
            return f"error {r.status_code}"
        return "sent"
    except Exception as e:
        log.error("resend failed: %s", e)
        return "error"
