import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("DATA_DIR", "/data"))
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
MAIL_FROM = os.environ.get("MAIL_FROM", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
# MAIL_MODE=outbox writes every email to DATA/outbox instead of sending (use for all testing)
MAIL_MODE = os.environ.get("MAIL_MODE", "send")
# Testing aid: a folder of cached scrapes (<host>/scrape.json) so local tests do not re-read a site
SCRAPE_CACHE = os.environ.get("HOOQED_SCRAPE_CACHE", "")

for sub in ("hooqs", "published", "outbox", "roots"):
    (DATA / sub).mkdir(parents=True, exist_ok=True)
