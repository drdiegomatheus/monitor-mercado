"""Carteiras vencedoras da Hyperliquid: histórico de ordens fechadas dos últimos 30 dias (userFillsByTime) das carteiras
mais lucrativas de baleias.json; calcula taxa de acerto, fator de lucro, queda máxima e nota. Estado em carteiras.json."""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

BAL = os.environ.get("BALEIAS_ESTADO", "baleias.json")
EST = os.environ.get("CARTEIRAS_ESTADO", "carteiras.json")
ORC = float(os.environ.get("CARTEIRAS_ORC", "75"))
NCAND = int(os.environ.get("CARTEIRAS_N", "250"))
VALID = 3 * 3600
JAN = 30 * 86400
INFO = "https://api.hyperliquid.xyz/info"
UA = {"User-Agent": "Mozilla/5.0 (monitor-mercado)"}


def post(corpo):
    for _ in range(2):
        try:
            r = requests.post(INFO, json=corpo, timeout=30, headers=UA)
            if r.status_code == 200: return r.json()
            if r.status_code == 429: time.sleep(2)
        except Exception:
            time.sleep(0.5)
    return None


def f(x):
    try: return float(x)
    except Exception: return 0.0


def fills(addr, ini_ms):
    out, ini = [], ini_ms
    for _ in range(4):
        r = post({"type": "userFillsByTime", "user": addr, "startTime": ini})
        if not r: break
        out += r
        if len(r) < 2000: return out, False
        ini = r[-1]["time"] + 1
    return out, True


def stats(addr, c, agora):
    fl, parcial = fills(addr, int((agora - JAN) * 1000))
    if fl is None: return None
    ordens = {}
    vol = 0.0
    lv = sv = 0.0
    por_ativo = {}
    for x in fl:
        px, sz = f(x.get("px")), f(x.get("sz"))
        vol += px * sz
        d = x.get("dir", "")
        if "Long" in d and "Short" not in d: lv += px * sz
        elif "Short" in d and "Long" not in d: sv += px * sz
        cp = f(x.get("closedPnl"))
        if cp == 0 and not d.startswith("Close") and "> " not in d: continue
        k = x.get("oid") or (x["coin"], x["time"] // 60000)
        o = ordens.setdefault(k, {"t": x["time"], "coin": x["coin"], "p": 0.0})
        o["p"] += cp - f(x.get("fee"))
        o["t"] = max(o["t"], x["time"])
    L = sorted(ordens.values(), key=lambda o: o["t"])
    if not L: return {"n": 0, "t": agora}
    gan = [o["p"] for o in L if o["p"] > 0]
    per = [-o["p"] for o in L if o["p"] <= 0]
    acum = pico = dd = 0.0
    for o in L:
        acum += o["p"]
        pico = max(pico, acum)
        dd = max(dd, pico - acum)
        a = por_ativo.setdefault(o["coin"], [0, 0.0, 0])
        a[0] += 1; a[1] += o["p"]; a[2] += 1 if o["p"] > 0 else 0
    sg, sp = sum(gan), sum(per)
    top = sorted(por_ativo.items(), key=lambda kv: -abs(kv[1][1]))[:4]
    return {"n": len(L), "w": len(gan), "wr": len(gan) / len(L), "mg": sg / len(gan) if gan else 0, "mp": sp / len(per) if per else 0,
            "fl": (sg / sp) if sp > 0 else (99.0 if sg > 0 else 0), "pnl": acum, "dd": dd, "pior": max(per) if per else 0, "vol": vol,
            "lp": lv / (lv + sv) if lv + sv else None, "ativos": [[k, v[0], round(v[1]), v[2]] for k, v in top], "parcial": parcial, "t": agora}


def clip(x): return max(0.0, min(1.0, x))


def nota(s, av, pnl_all):
    if not s or s.get("n", 0) < 15 or s["pnl"] <= 0 or pnl_all <= 0: return None
    pf = clip((min(s["fl"], 4) - 1) / 2.5)
    wr = clip((s["wr"] - .4) / .35)
    ret = clip(s["pnl"] / max(av * .25, 1))
    dd = clip(1 - s["dd"] / max(s["pnl"] * 1.5, 1))
    return round(100 * (.3 * pf + .25 * wr + .2 * ret + .25 * dd))


def main():
    t0 = time.time()
    agora = time.time()
    bal = json.load(open(BAL, encoding="utf-8"))
    ant = {}
    if os.path.exists(EST):
        try: ant = json.load(open(EST, encoding="utf-8")).get("c", {})
        except Exception: ant = {}
    cand = [(a, c) for a, c in bal["contas"].items() if c["pnl"][3] > 0 and c["pnl"][2] > 0]
    cand.sort(key=lambda x: -x[1]["pnl"][2])
    cand = cand[:NCAND]
    ordem = sorted(cand, key=lambda x: ant.get(x[0], {}).get("t", 0))
    pend = [x for x in ordem if agora - ant.get(x[0], {}).get("t", 0) > VALID]
    res = {a: v for a, v in ant.items() if a in {x[0] for x in cand}}
    feitos = 0

    def tarefa(x):
        if time.time() - t0 > ORC: return None
        return x[0], stats(x[0], x[1], agora)
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(tarefa, pend):
            if r and r[1] is not None:
                res[r[0]] = r[1]; feitos += 1
    for a, c in cand:
        s = res.get(a)
        if s is not None:
            s["nota"] = nota(s, c["av"], c["pnl"][3])
            s["av"] = c["av"]; s["nome"] = c.get("nome"); s["pm"] = c["pnl"][2]; s["pa"] = c["pnl"][3]
    json.dump({"ts": agora, "c": res}, open(EST, "w", encoding="utf-8"), separators=(",", ":"))
    q = sum(1 for v in res.values() if v.get("nota"))
    print(f"carteiras: {len(cand)} candidatas, {feitos} atualizadas em {time.time() - t0:.0f}s, {q} qualificadas", file=sys.stderr)


if __name__ == "__main__":
    main()
