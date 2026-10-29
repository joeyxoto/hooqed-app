"""Step 4b - fixed automatic rule, identical for every business. If validate finds issues, ONE repair pass:
 - text issues (emergency wording, phone numbers, £ figures not on the site, identity words in photo scenes, non-call CTAs):
   only the offending strings are sent to the model to be rewritten; everything else stays byte-identical;
 - a review that is not verbatim is swapped for the first exact review in facts.json (or removed);
 - structural issues (unreachable result / path without result) are not patched; they stay flagged for the judge.
Then validate runs again. No human edits."""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(__file__))
from lib import chat
import validate
EMERG = r"emergenc|urgent|out[- ]of[- ]hours|24/7|asap|right now"
PHONE = r"\b0\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}\b"
def leaves(o, path=()):
    if isinstance(o, dict):
        for k, v in o.items(): yield from leaves(v, path + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from leaves(v, path + (i,))
    elif isinstance(o, str): yield path, o
def setp(o, path, v):
    for k in path[:-1]: o = o[k]
    o[path[-1]] = v
def main(d):
    issues = validate.main(d)
    if not issues: return []
    h = json.load(open(f"{d}/hooq.json")); f = json.load(open(f"{d}/facts.json"))
    json.dump(h, open(f"{d}/hooq.pre-repair.json", "w"), indent=1, ensure_ascii=False)
    badprices = re.findall(r"price (£\S+) not found", "\n".join(issues))
    todo = []
    for p, t in leaves({k: v for k, v in h.items() if k != "strategy"}):
        why = []
        if re.search(EMERG, t, re.I): why.append("remove any mention of emergency/urgency entirely")
        if re.search(PHONE, t): why.append("remove the phone number")
        if any(b in t for b in badprices): why.append("remove the £ figure that is not in FACTS")
        if p[0] == "photos" and p[-1] == "scene" and any(f"photo {h['photos'][p[1]]['id']} " in i for i in issues):
            why.append("remove the business name, place name and possessive words")
        if p[0] == "results" and p[-1] == "cta" and any(f"result {h['results'][p[1]]['id']} CTA" in i for i in issues):
            why.append("make it a short book-a-call action naming the topic, max 5 words")
        if why: todo.append({"path": list(p), "text": t, "fix": "; ".join(why)})
    for r in h["results"]:
        if any(f"review in {r['id']}" in i for i in issues):
            r["review"] = (f.get("reviews") or [None])[0] and {"quote": f["reviews"][0]["quote"], "by": f["reviews"][0].get("by", "")}
    if todo:
        sys_p = ("Rewrite each string only as far as needed to apply its 'fix'. Keep meaning, tone and length. Use only facts in "
                 "FACTS. Return JSON {\"fixed\": [{\"path\": same path, \"text\": new text}]}.")
        out = chat([{"role": "system", "content": sys_p},
                    {"role": "user", "content": "FACTS:\n" + json.dumps(f, ensure_ascii=False) + "\n\nSTRINGS:\n" + json.dumps(todo, ensure_ascii=False)}],
                   f"{d}/costlog.jsonl", "repair_strings", model="grok-4.3")
        for x in out.get("fixed", []):
            try: setp(h, tuple(x["path"]), x["text"])
            except Exception as e: print("could not patch", x.get("path"), e)
    json.dump(h, open(f"{d}/hooq.json", "w"), indent=1, ensure_ascii=False)
    print("after repair:"); return validate.main(d)
if __name__ == "__main__":
    main(sys.argv[1])
