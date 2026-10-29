import os, json, time, requests
KEY = os.environ["BT_XAI_API_KEY"]; B = "https://api.x.ai/v1"
def _log(logf, row):
    with open(logf, "a") as f: f.write(json.dumps(row) + "\n")
def chat(model, system, user, logf, step, effort=None, schema=None):
    body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if effort: body["reasoning_effort"] = effort
    body["response_format"] = {"type": "json_object"}
    for a in range(3):
        r = requests.post(B + "/chat/completions", headers={"Authorization": "Bearer " + KEY}, json=body, timeout=300)
        if r.ok: break
        print("retry", r.status_code, r.text[:200]); time.sleep(4)
    r.raise_for_status(); j = r.json(); u = j.get("usage", {})
    _log(logf, {"step": step, "model": model, "usd": (u.get("cost_in_usd_ticks") or 0) / 1e10, "ticks": u.get("cost_in_usd_ticks"), "tokens_in": u.get("prompt_tokens"), "tokens_out": u.get("completion_tokens")})
    c = j["choices"][0]["message"]["content"].strip()
    if c.startswith("```"): c = c.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(c)
def image(prompt, path, logf, step):
    body = {"model": "grok-imagine-image-2.0", "prompt": prompt, "n": 1, "response_format": "b64_json", "quality": "low", "resolution": "1k", "aspect_ratio": "4:3"}
    for a in range(3):
        r = requests.post(B + "/images/generations", headers={"Authorization": "Bearer " + KEY}, json=body, timeout=300)
        if r.ok: break
        print("img retry", r.status_code, r.text[:300]); time.sleep(4)
        if r.status_code == 400 and a == 0:
            for k in ("quality", "resolution", "aspect_ratio"): body.pop(k, None)
    r.raise_for_status(); j = r.json(); u = j.get("usage", {})
    import base64; open(path, "wb").write(base64.b64decode(j["data"][0]["b64_json"]))
    _log(logf, {"step": step, "model": "grok-imagine-image-2.0", "usd": (u.get("cost_in_usd_ticks") or 0) / 1e10 if u.get("cost_in_usd_ticks") else None, "list_usd": 0.04, "params": {k: body[k] for k in body if k != "prompt"}, "raw_usage": u})
