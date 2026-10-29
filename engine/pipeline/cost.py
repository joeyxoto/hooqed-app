import sys, json
d = sys.argv[1]; FX = 0.75258  # GBP per USD, ECB reference rate via frankfurter.dev (as used in the earlier rounds)
rows = [json.loads(l) for l in open(f"{d}/costlog.jsonl")]
usd = sum(r["usd"] if r["usd"] is not None else r.get("list_usd", 0) for r in rows); pence = round(usd * FX * 100, 1)
json.dump({"calls": len(rows), "usd_provider_billed": round(usd, 4), "pence": pence, "target_pence": 40, "within_target": pence <= 40, "fx_gbp_per_usd": FX,
  "fx_source": "ECB reference rate via frankfurter.dev", "by_step": rows}, open(f"{d}/cost.json", "w"), indent=1)
print(f"cost: ${usd:.4f} = {pence}p vs 40p ({'OK' if pence <= 40 else 'OVER'})")
