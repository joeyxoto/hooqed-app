"""Ask, don't fail. A step that can't go on without the owner writes needs-input.json and exits with ASK (10).
The app shows the question on the build page; the owner's answer goes into owner-answer.json and the build carries on
from the cached steps (owner_input.py folds the answer in). Question wording for no offers / site empty is Joey's, word for word."""
import json, os, sys, time
ASK = 10
LINK_FIELD = {"name": "link", "label": "Got a page that explains it, like your coaching or booking page? Paste the link (optional)", "type": "url", "required": False,
              "placeholder": "https://"}
CASES = {
    "no_offers": {"title": "What do you want people to book a call for?",
                  "help": "We read your site but couldn't find a service or offer for people to book a call about. One line is enough.",
                  "fields": [{"name": "answer", "label": "The call is for…", "type": "text", "required": True, "placeholder": "e.g. a free 30-minute call about 1:1 coaching"}, LINK_FIELD]},
    "site_empty": {"title": "Tell us in a sentence what you do.",
                   "help": "We couldn't read enough of your website to build from. It may block automated readers or be mostly images.",
                   "fields": [{"name": "answer", "label": "What you do", "type": "text", "required": True, "placeholder": "e.g. I coach gym owners to grow their membership"}, LINK_FIELD]},
    "build_failed": {"title": "What do you want people to book a call for?",
                     "help": "We couldn't turn your site into questions this time. Tell us in a line and we'll build from that.",
                     "fields": [{"name": "answer", "label": "The call is for…", "type": "text", "required": True, "placeholder": "e.g. a free consultation about your treatment options"}, LINK_FIELD]},
}


def answers(d):
    p = f"{d}/owner-answer.json"
    return (json.load(open(p)).get("answers") or []) if os.path.exists(p) else []


def owner_text(d):
    """the owner's own words, newest last, for the AI prompts"""
    return [a["answer"] for a in answers(d) if a.get("answer")]


def write(d, case, why="", suggestion=None, step=""):
    q = dict(CASES[case]); q.update(case=case, why=why, step=step, at=time.time())
    if suggestion: q["suggestion"] = suggestion[:140]
    json.dump(q, open(f"{d}/needs-input.json", "w"), indent=1)
    return q


def ask(d, case, why="", suggestion=None, step=""):
    write(d, case, why, suggestion, step)
    print(f"NEEDS OWNER INPUT ({case}): {why}")
    sys.exit(ASK)
