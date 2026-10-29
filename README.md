# Hooqed (v0)

Owners paste their website, Hooqed drafts an interactive quote (a "hooq") from it, the owner checks it, publishes it, and leads land in their dashboard with an email alert.

- `app/`: FastAPI web app (sign up/log in, build, owner check, publish, public hooqs, leads, email). Owner screens use Dex's Hooqed app design (`app/static/m8.css`, unchanged).
- `engine/`: the v7 hooq pipeline, vendored as-is from the proof repo (tag `flowA-blind-v7`). Not rewritten.
- `hooq_templates/`: plug-in hooq designs (`v7` = current). See `hooq_templates/README.md` and `engine/THEMING.md`.
- One process: web + a background build thread. SQLite and all files live on the disk at `DATA_DIR` (`/data` on Render).

## Run locally
```
pip install -r requirements.txt          # needs Google Chrome at /usr/bin/google-chrome
cp .env.example .env                     # fill in locally, never commit
DATA_DIR=./data-local MAIL_MODE=outbox uvicorn app.main:app --port 8000
```
`MAIL_MODE=outbox` writes every email to `DATA_DIR/outbox/` instead of sending. Use it for all testing.

## Environment
| Name | What |
|---|---|
| `XAI_API_KEY` | xAI API key (pipeline AI calls, about 18p per new hooq) |
| `RESEND_API_KEY` | Resend API key. If empty, emails are skipped and logged. |
| `MAIL_FROM` | Sender, e.g. `Hooqed <leads@yourdomain.com>` (domain verified in Resend) |
| `SECRET_KEY` | Session signing key (Render generates it) |
| `BASE_URL` | Public URL of the app, e.g. `https://hooqed.onrender.com` |

Optional: `DATA_DIR` (default `/data`), `MAIL_MODE` (`send`/`outbox`), `LEAD_EMAIL_DELAY` (seconds, default 180).

Deploying: see `DEPLOY.md`.
