"""Baleias de TradeFi na Hyperliquid (mercados HIP-3: ações, índices, commodities). clearinghouseState com o parâmetro dex
traz as posições; userFillsByTime (30 dias) traz o lucro realizado. Estado em tradefi.json (ramo `baleias`).
Entradas: BALEIAS_ESTADO (baleias.json, lista de carteiras), TRADEFI_ESTADO, TRADEFI_ORC (s)."""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

BAL = os.environ.get("BALEIAS_ESTADO", "baleias.json")
EST = os.environ.get("TRADEFI_ESTADO", "tradefi.json")
ORC = float(os.environ.get("TRADEFI_ORC", "100"))
VALID_POS = 20 * 60
VALID_FILLS = 4 * 3600
JAN = 30 * 86400
INFO = "https://api.hyperliquid.xyz/info"
UA = {"User-Agent": "Mozilla/5.0 (monitor-mercado)"}
DEX_PRINCIPAL = "xyz"


def post(corpo):
    for _ in range(2):
        try:
            r = requests.post(INFO, json=corpo, timeout=25, headers=UA)
            if r.status_code == 200: return r.json()
            if r.status_code == 429: time.sleep(2)
        except Exception:
            time.sleep(0.5)
    return None


def f(x):
    try: return float(x)
    except Exception: return 0.0


def posicoes(addr, dex):
    d = post({"type": "clearinghouseState", "user": addr, "dex": dex})
    if d is None: return None
    out = []
    for ap in d.get("assetPositions", []):
        p = ap["position"]
        szi = f(p["szi"])
        if szi == 0: continue
        lv = p.get("leverage") or {}
        out.append([p["coin"], szi, f(p["entryPx"]), f(p["positionValue"]), f(p["liquidationPx"]) if p.get("liquidationPx") else None,
                    lv.get("value"), f(p["unrealizedPnl"]), "i" if lv.get("type") == "isolated" else "c", dex])
    return {"av": f((d.get("marginSummary") or {}).get("accountValue")), "p": out}


def fills_tf(addr, agora):
    ini = int((agora - JAN) * 1000)
    fl = []
    for _ in range(4):
        r = post({"type": "userFillsByTime", "user": addr, "startTime": ini})
        if not r: break
        fl += r
        if len(r) < 2000: break
        ini = r[-1]["time"] + 1
    ordens = {}
    for x in fl:
        if ":" not in x.get("coin", ""): continue
        cp = f(x.get("closedPnl"))
        k = x.get("oid") or (x["coin"], x["time"] // 60000)
        o = ordens.setdefault(k, {"coin": x["coin"], "p": 0.0, "vol": 0.0, "t": x["time"]})
        o["p"] += cp - f(x.get("fee"))
        o["vol"] += f(x.get("px")) * f(x.get("sz"))
        o["t"] = max(o["t"], x["time"])
    if not ordens: return {"n": 0, "pnl": 0.0, "t": agora}
    L = sorted(ordens.values(), key=lambda o: o["t"])
    por = {}
    for o in L:
        a = por.setdefault(o["coin"], [0, 0.0, 0.0])
        a[0] += 1; a[1] += o["p"]; a[2] += o["vol"]
    fech = [o for o in L if o["p"] != 0]
    return {"n": len(L), "pnl": sum(o["p"] for o in L), "w": sum(1 for o in fech if o["p"] > 0), "nf": len(fech), "vol": sum(o["vol"] for o in L),
            "ativos": sorted([[k, v[0], round(v[1]), round(v[2])] for k, v in por.items()], key=lambda z: -abs(z[2]))[:6], "t": agora}


def main():
    t0 = time.time()
    agora = time.time()
    bal = json.load(open(BAL, encoding="utf-8"))["contas"]
    est = {}
    if os.path.exists(EST):
        try: est = json.load(open(EST, encoding="utf-8"))
        except Exception: est = {}
    ac = est.get("c", {})
    dexs = est.get("dexs")
    if not dexs or agora - est.get("tdex", 0) > 6 * 3600:
        d = post({"type": "perpDexs"})
        if d: dexs = [x["name"] for x in d if x and x.get("name")]; est["tdex"] = agora
    dexs = dexs or [DEX_PRINCIPAL]
    n_pos = n_fills = 0

    def tarefa_pos(a):
        if time.time() - t0 > ORC * 0.6: return None
        res = {}
        x = posicoes(a, DEX_PRINCIPAL)
        if x is None: return None
        ps, av = list(x["p"]), x["av"]
        # outras dexes só para quem já negocia TradeFi
        if ps or (ac.get(a) or {}).get("tf"):
            for dx in dexs:
                if dx == DEX_PRINCIPAL: continue
                y = posicoes(a, dx)
                if y: ps += y["p"]; av += y["av"]
        return a, {"p": ps, "av": av, "tp": agora}
    ordem = sorted(bal, key=lambda a: (ac.get(a) or {}).get("tp", 0))
    pend = [a for a in ordem if agora - (ac.get(a) or {}).get("tp", 0) > VALID_POS]
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(tarefa_pos, pend):
            if r:
                a, v = r
                c = ac.setdefault(a, {})
                c.update(v); c["tf"] = 1 if v["p"] or c.get("tf") else 0
                n_pos += 1
    # lucro realizado: só quem negocia TradeFi (tem posição agora ou já teve ordens)
    alvo = [a for a, c in ac.items() if c.get("tf") and a in bal and agora - (c.get("st") or {}).get("t", 0) > VALID_FILLS]
    alvo.sort(key=lambda a: (ac[a].get("st") or {}).get("t", 0))

    def tarefa_f(a):
        if time.time() - t0 > ORC: return None
        return a, fills_tf(a, agora)
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(tarefa_f, alvo):
            if r:
                ac[r[0]]["st"] = r[1]
                if r[1]["n"] == 0 and not ac[r[0]]["p"]: ac[r[0]]["tf"] = 0
                n_fills += 1
    for a, c in ac.items():
        b = bal.get(a)
        if b: c["nome"] = b.get("nome"); c["av0"] = b["av"]
    ac = {a: c for a, c in ac.items() if a in bal}
    est.update({"ts": agora, "dexs": dexs, "c": ac})
    json.dump(est, open(EST, "w", encoding="utf-8"), separators=(",", ":"))
    ntf = sum(1 for c in ac.values() if c.get("tf"))
    print(f"tradefi: {n_pos} posições lidas, {n_fills} históricos em {time.time() - t0:.0f}s; {ntf} carteiras TradeFi de {len(ac)}", file=sys.stderr)


if __name__ == "__main__":
    main()
