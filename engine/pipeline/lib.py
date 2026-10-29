"""Shared helpers: xAI text + image calls with exact cost logging (provider-returned cost ticks)."""
import json, os, time, base64, urllib.request, datetime

XAI = "https://api.x.ai/v1"
KEY_ENV = "BT_XAI_API_KEY"  # never printed
TICK = 1e-10  # xAI cost_in_usd_ticks unit (1 tick = 1e-10 USD)
# Published list prices, read live from xAI /v1/language-models and /v1/image-generation-models on 29 Oct 2026
PRICES = {
    "grok-4.3": {"in_per_m": 1.25, "out_per_m": 2.50},
    "grok-4.7": {"in_per_m": 2.00, "out_per_m": 6.00},
    "grok-imagine-image-2.0|medium|1k": {"per_image": 0.06},
    "grok-imagine-image-2.0|low|1k": {"per_image": 0.04},
}

def _post(path, body, timeout=300):
    req = urllib.request.Request(XAI + path, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + os.environ[KEY_ENV], "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:400]
            if e.code >= 500 and attempt < 2:
                time.sleep(5); continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")

def log_cost(costlog, entry):
    entry["at"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(costlog, "a") as f:
        f.write(json.dumps(entry) + "\n")

def chat(messages, costlog, step, model="grok-4.3", json_mode=True, reasoning_effort=None):
    body = {"model": model, "messages": messages, "temperature": 0.4}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    t = time.time()
    body["stream"] = True; body["stream_options"] = {"include_usage": True}
    req = urllib.request.Request(XAI + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + os.environ[KEY_ENV], "Content-Type": "application/json"})
    parts, u = [], {}
    with urllib.request.urlopen(req, timeout=900) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            ev = json.loads(line[5:])
            if ev.get("usage"): u = ev["usage"]
            for ch in ev.get("choices", []):
                parts.append((ch.get("delta") or {}).get("content") or "")
    d = {"choices": [{"message": {"content": "".join(parts)}}]}
    ticks = u.get("cost_in_usd_ticks")
    p = PRICES.get(model, {})
    inp = u.get("prompt_tokens", 0); out = u.get("completion_tokens", 0) + ((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
    list_usd = inp / 1e6 * p.get("in_per_m", 0) + out / 1e6 * p.get("out_per_m", 0)
    log_cost(costlog, {"step": step, "kind": "text", "model": model, "prompt_tokens": inp,
        "completion_tokens": out, "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
        "cached_tokens": (u.get("prompt_tokens_details") or {}).get("cached_tokens"),
        "provider_cost_usd": ticks * TICK if ticks is not None else None,
        "list_price_usd": round(list_usd, 6), "latency_s": round(time.time() - t, 1)})
    txt = d["choices"][0]["message"]["content"]
    return json.loads(txt) if json_mode else txt

def image(prompt, out_path, costlog, step, model="grok-imagine-image-2.0", quality="medium", resolution="1k", aspect="4:3"):
    t = time.time()
    d = _post("/images/generations", {"model": model, "prompt": prompt, "n": 1, "response_format": "b64_json",
        "aspect_ratio": aspect, "quality": quality, "resolution": resolution})
    open(out_path, "wb").write(base64.b64decode(d["data"][0]["b64_json"]))
    ticks = (d.get("usage") or {}).get("cost_in_usd_ticks")
    log_cost(costlog, {"step": step, "kind": "image", "model": f"{model}|{quality}|{resolution}", "prompt": prompt,
        "file": os.path.basename(out_path), "provider_cost_usd": ticks * TICK if ticks is not None else None,
        "list_price_usd": PRICES.get(f"{model}|{quality}|{resolution}", {}).get("per_image"),
        "latency_s": round(time.time() - t, 1)})
    return out_path
