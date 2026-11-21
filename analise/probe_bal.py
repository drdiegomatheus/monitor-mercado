import json, time, requests
out = {}
t = time.time()
try:
    r = requests.get("https://stats-data.hyperliquid.xyz/Mainnet/leaderboard", timeout=120)
    out["lb_status"] = r.status_code; out["lb_bytes"] = len(r.content); out["lb_s"] = round(time.time() - t, 1)
    d = r.json(); rows = d["leaderboardRows"]
    out["lb_keys"] = list(d.keys()); out["lb_n"] = len(rows); out["lb_sample"] = rows[0]
    av = sorted((float(x["accountValue"]) for x in rows), reverse=True)
    out["lb_top"] = av[:5]
    for lim in (1e5, 5e5, 1e6, 5e6): out[f"n_{int(lim)}"] = sum(1 for v in av if v >= lim)
    top = sorted(rows, key=lambda x: -float(x["accountValue"]))
except Exception as e:
    out["lb_err"] = str(e); top = []
def cs(u):
    return requests.post("https://api.hyperliquid.xyz/info", json={"type": "clearinghouseState", "user": u}, timeout=30)
t = time.time(); ok = 0; ex = None; err = []
for x in top[:80]:
    r = cs(x["ethAddress"])
    if r.status_code == 200:
        ok += 1
        if ex is None and r.json().get("assetPositions"): ex = r.json()
    else: err.append(r.status_code)
out["cs_ok"] = ok; out["cs_s"] = round(time.time() - t, 1); out["cs_err"] = err[:5]; out["cs_sample"] = ex
# batch variants
for body in ({"type": "clearinghouseStates", "users": [top[0]["ethAddress"], top[1]["ethAddress"]]},):
    try:
        r = requests.post("https://api.hyperliquid.xyz/info", json=body, timeout=30); out["batch"] = [r.status_code, r.text[:300]]
    except Exception as e: out["batch"] = str(e)
# prices e meta
r = requests.post("https://api.hyperliquid.xyz/info", json={"type": "allMids"}, timeout=30); out["mids_n"] = len(r.json())
json.dump(out, open("analise/probe_bal.json", "w"), default=str)
