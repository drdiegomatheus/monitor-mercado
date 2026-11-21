"""Monitor de baleias da Hyperliquid: lista de carteiras grandes (leaderboard público) + posições de cada uma
(clearinghouseState), com preço de liquidação. Atualização incremental: cada rodada reconsulta as carteiras mais antigas
dentro de um orçamento de tempo e grava o estado em baleias.json (ramo `baleias` do repositório).
Entradas: BALEIAS_ESTADO (arquivo), BALEIAS_ORC (segundos), BALEIAS_MIN (conta mínima em US$)"""
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor

import requests

ESTADO = os.environ.get("BALEIAS_ESTADO", "baleias.json")
ORC = float(os.environ.get("BALEIAS_ORC", "230"))
MINIMO = float(os.environ.get("BALEIAS_MIN", "500000"))
MAXC = int(os.environ.get("BALEIAS_MAXC", "5000"))
TRABALHADORES = int(os.environ.get("BALEIAS_TRAB", "4"))
HIST_PASSO = 25 * 60          # snapshot do histórico a cada ~25 min
HIST_MAX = 340                # ≈ 6 dias
MOEDAS_HM = ["BTC", "ETH", "SOL", "HYPE", "XRP", "DOGE"]
INFO = "https://api.hyperliquid.xyz/info"
LB = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
UA = {"User-Agent": "Mozilla/5.0 (monitor-mercado)"}


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except Exception:
        return None


def info(corpo, tent=2):
    for i in range(tent):
        try:
            r = requests.post(INFO, json=corpo, timeout=30, headers=UA)
            if r.status_code == 200: return r.json()
            if r.status_code == 429:
                time.sleep(3 + 3 * i)
                continue
            return None
        except Exception:
            time.sleep(1)
    return None


def bonito(x):
    """passo 'redondo' (1, 2, 5 × 10^n) próximo de x"""
    import math
    if x <= 0: return 1
    e = 10 ** math.floor(math.log10(x))
    for m in (1, 2, 5, 10):
        if x <= m * e: return m * e


def posicoes(cs):
    out = []
    for ap in cs.get("assetPositions") or []:
        p = ap["position"]
        szi, ntl = num(p.get("szi")), num(p.get("positionValue"))
        if not szi or not ntl: continue
        out.append([p["coin"], szi, num(p.get("entryPx")), round(ntl), num(p.get("liquidationPx")), (p.get("leverage") or {}).get("value"),
                    round(num(p.get("unrealizedPnl")) or 0), (p.get("leverage") or {}).get("type", "cross")[:1]])
    return out


def diferencas(addr, nome, ant, novo, agora, mark, ev):
    """registra aberturas, fechamentos e variações grandes de posição entre duas consultas da mesma carteira"""
    a = {p[0]: p for p in ant}
    b = {p[0]: p for p in novo}
    for coin in set(a) | set(b):
        pa, pb = a.get(coin), b.get(coin)
        na, nb = (abs(pa[3]) if pa else 0), (abs(pb[3]) if pb else 0)
        lado = lambda p: "long" if p[1] > 0 else "short"
        acao = None
        if pa is None and nb >= 2e6: acao, p = "abriu", pb
        elif pb is None and na >= 2e6: acao, p = "fechou", pa
        elif pa and pb and lado(pa) != lado(pb) and max(na, nb) >= 2e6: acao, p = "virou", pb
        elif pa and pb and na and abs(nb - na) >= 2e6 and abs(nb / na - 1) >= 0.3:
            acao, p = ("aumentou" if nb > na else "reduziu"), pb
        if acao:
            ev.append({"t": agora, "a": addr, "n": nome, "c": coin, "ac": acao, "l": lado(p), "v": nb if acao != "fechou" else na, "d": round(nb - na), "px": mark.get(coin)})


def main():
    t0 = time.time()
    est = {}
    if os.path.exists(ESTADO):
        try: est = json.load(open(ESTADO, encoding="utf-8"))
        except Exception: est = {}
    contas = est.get("contas", {})
    ev = est.get("eventos", [])
    hist = est.get("hist", [])
    passos = est.get("passos", {})
    # ---- leaderboard
    try:
        lb = requests.get(LB, timeout=120, headers=UA).json()["leaderboardRows"]
    except Exception as e:
        print("leaderboard falhou:", e, file=sys.stderr)
        lb = None
    if lb:
        lb = [x for x in lb if (num(x["accountValue"]) or 0) >= MINIMO]
        lb.sort(key=lambda x: -float(x["accountValue"]))
        lb = lb[:MAXC]
        novas = {}
        for x in lb:
            a = x["ethAddress"]
            w = {k: v for k, v in x["windowPerformances"]}
            c = contas.get(a, {"t": 0, "p": []})
            c["av"] = round(float(x["accountValue"]))
            c["nome"] = x.get("displayName")
            c["pnl"] = [round(num(w.get(k, {}).get("pnl")) or 0) for k in ("day", "week", "month", "allTime")]
            c["roi"] = [round((num(w.get(k, {}).get("roi")) or 0) * 100, 1) for k in ("week", "month", "allTime")]
            novas[a] = c
        contas = novas
    # ---- preços e OI
    meta = info({"type": "metaAndAssetCtxs"})
    mark, oi = {}, {}
    if meta:
        for i, u in enumerate(meta[0]["universe"]):
            c = meta[1][i]
            mark[u["name"]] = num(c.get("markPx"))
            oi[u["name"]] = round((num(c.get("openInterest")) or 0) * (num(c.get("markPx")) or 0))
    # ---- consulta incremental das carteiras
    agora = int(time.time())
    fila = sorted(contas, key=lambda a: (contas[a]["t"] - (1800 if contas[a]["p"] else 0), -contas[a]["av"]))
    parar = threading.Event()
    cont = {"ok": 0, "429": 0}
    trava = threading.Lock()

    def consulta(a):
        if parar.is_set() or time.time() - t0 > ORC: return
        try:
            r = requests.post(INFO, json={"type": "clearinghouseState", "user": a}, timeout=25, headers=UA)
        except Exception:
            return
        if r.status_code == 429:
            with trava:
                cont["429"] += 1
                if cont["429"] >= 6: parar.set()
            time.sleep(4)
            return
        if r.status_code != 200: return
        cs = r.json()
        novo = posicoes(cs)
        c = contas[a]
        with trava:
            if c["t"]: diferencas(a, c.get("nome"), c["p"], novo, agora, mark, ev)
            c["p"], c["t"] = novo, int(time.time())
            c["av"] = round(num((cs.get("marginSummary") or {}).get("accountValue")) or c["av"])
            cont["ok"] += 1

    with ThreadPoolExecutor(TRABALHADORES) as ex:
        list(ex.map(consulta, fila))
    print(f"baleias: {len(contas)} contas, {cont['ok']} consultadas em {time.time() - t0:.0f}s, 429={cont['429']}", file=sys.stderr)
    # ---- agregados e histórico
    tot, hm = {}, {}
    for coin in {p[0] for c in contas.values() for p in c["p"]}:
        tot[coin] = [0, 0, 0, 0]
    for c in contas.values():
        for p in c["p"]:
            i = 0 if p[1] > 0 else 1
            tot[p[0]][i] += abs(p[3])
            tot[p[0]][2 + i] += 1
    if not hist or agora - hist[-1]["t"] >= HIST_PASSO:
        for coin in MOEDAS_HM:
            px = mark.get(coin)
            if not px: continue
            if coin not in passos: passos[coin] = bonito(px * 0.003)
            st = passos[coin]
            bins = {}
            for c in contas.values():
                for p in c["p"]:
                    if p[0] != coin or not p[4]: continue
                    b = int(p[4] // st)
                    k = bins.setdefault(b, [0, 0])
                    k[0 if p[1] > 0 else 1] += abs(p[3])
            hm[coin] = [[b, round(v[0] / 1e5) / 10, round(v[1] / 1e5) / 10] for b, v in sorted(bins.items()) if v[0] + v[1] >= 1e5]
        hist.append({"t": agora, "px": {c: mark.get(c) for c in MOEDAS_HM}, "tot": {c: [round(v[0] / 1e6, 2), round(v[1] / 1e6, 2)] for c, v in tot.items() if v[0] + v[1] >= 2e6}, "hm": hm})
        hist = hist[-HIST_MAX:]
    ev = [e for e in ev if agora - e["t"] < 3 * 86400][-400:]
    est = {"ts": agora, "contas": {a: c for a, c in contas.items()}, "mark": mark, "oi": oi, "eventos": ev, "hist": hist, "passos": passos,
           "cobertura": {"contas": len(contas), "consultadas": sum(1 for c in contas.values() if c["t"]), "minimo": MINIMO}}
    json.dump(est, open(ESTADO, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    print(f"baleias: estado salvo ({os.path.getsize(ESTADO) // 1024} KB), hist={len(hist)}, eventos={len(ev)}", file=sys.stderr)


if __name__ == "__main__":
    main()
