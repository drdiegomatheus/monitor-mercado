"""Opções dos EUA: posições em aberto e volume de calls e puts por vencimento e por strike (Yahoo).
Roda dentro da coleta de 5 em 5 minutos, mas só trabalha 3 vezes por pregão (horário de Nova York):
30 min depois da abertura (10:00), às 15:00 e depois do fechamento (16:20).
Guarda tudo em categorias/eua/dados/opcoes.json, já com as leituras prontas (barreiras, max pain, movimento precificado, viés)."""
import datetime as dt
import json
import os
import sys
import time
from zoneinfo import ZoneInfo

RAIZ = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.join(RAIZ, "categorias", "eua", "dados", "opcoes.json")
ET = ZoneInfo("America/New_York")
SLOTS = ["10:00", "15:00", "16:20"]
PADRAO = ["NVDA", "MSTR", "MU", "DELL", "AMD", "AVGO", "SPY", "QQQ"]
JANELAS = (7, 30, 0)          # dias até o vencimento; 0 = todos os vencimentos coletados
MAX_DIAS = 120
MAX_VENC = 16
ORC = float(os.environ.get("OPCOES_ORC", "150"))
HIST = 40


def ativos():
    try:
        c = json.load(open(os.path.join(RAIZ, "categorias", "eua", "config.json"), encoding="utf-8"))
        return c.get("opcoes") or PADRAO
    except Exception:
        return PADRAO


def ler():
    try: return json.load(open(ARQ, encoding="utf-8"))
    except Exception: return {"slots": {}, "ativos": {}}


def gravar(est):
    os.makedirs(os.path.dirname(ARQ), exist_ok=True)
    json.dump(est, open(ARQ, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)


def devidos(est, agora):
    """Leituras do dia que já passaram e ainda não foram feitas (até 3 h depois do horário)."""
    if agora.weekday() > 4: return []
    hoje = agora.strftime("%Y-%m-%d")
    feitos = est.get("slots", {}).get(hoje, [])
    out = []
    for s in SLOTS:
        h, m = map(int, s.split(":"))
        t = agora.replace(hour=h, minute=m, second=0, microsecond=0)
        if agora >= t and (agora - t).total_seconds() < 3 * 3600 and s not in feitos: out.append(s)
    return out


def _n(v):
    try:
        v = float(v)
        return 0.0 if v != v else v
    except Exception:
        return 0.0


def _mid(r):
    b, a, u = _n(r.get("bid")), _n(r.get("ask")), _n(r.get("lastPrice"))
    return round((b + a) / 2, 3) if b > 0 and a > 0 else round(u, 3)


def linhas_venc(calls, puts):
    """{strike: [oi_call, oi_put, vol_call, vol_put, preço_call, preço_put, iv_call, iv_put]}"""
    L = {}
    for i, rs in ((0, calls), (1, puts)):
        for r in rs:
            k = round(_n(r.get("strike")), 3)
            if k <= 0: continue
            x = L.setdefault(k, [0, 0, 0, 0, 0, 0, 0, 0])
            x[i] = _n(r.get("openInterest")); x[2 + i] = _n(r.get("volume"))
            x[4 + i] = _mid(r); x[6 + i] = _n(r.get("impliedVolatility"))
    return L


def max_pain(L):
    ks = sorted(L)
    if not ks or sum(L[k][0] + L[k][1] for k in ks) <= 0: return None
    best, bk = None, None
    for K in ks:
        p = sum(L[k][0] * max(0, K - k) + L[k][1] * max(0, k - K) for k in ks)
        if best is None or p < best: best, bk = p, K
    return bk


def resumo_venc(d, dte, L, spot):
    co = sum(v[0] for v in L.values()); po = sum(v[1] for v in L.values())
    cv = sum(v[2] for v in L.values()); pv = sum(v[3] for v in L.values())
    k0 = min(L, key=lambda k: abs(k - spot))
    v0 = L[k0]
    straddle = v0[4] + v0[5]
    iv = [x for x in (v0[6], v0[7]) if x > 0]
    return {"d": d, "n": dte, "co": int(co), "po": int(po), "cv": int(cv), "pv": int(pv),
            "iv": round(sum(iv) / len(iv) * 100, 1) if iv else None,
            "mv": round(straddle / spot * 100, 2) if v0[4] > 0 and v0[5] > 0 and spot else None,
            "mp": max_pain(L)}


def paredes(A, spot, lado):
    """Strike com mais posições: lado 'up' = calls acima do preço, 'dn' = puts abaixo."""
    if lado == "up": c = [(k, v[0]) for k, v in A.items() if spot < k <= spot * 1.3 and v[0] > 0]
    else: c = [(k, v[1]) for k, v in A.items() if spot * 0.7 <= k < spot and v[1] > 0]
    c.sort(key=lambda x: -x[1])
    out = []
    for k, oi in c:
        if all(abs(k - o["k"]) / spot >= 0.02 for o in out):
            out.append({"k": k, "oi": int(oi), "pct": round((k / spot - 1) * 100, 1)})
        if len(out) == 2: break
    return out


def analisar(spot, exps, janela):
    """exps: [{'d','n','L'(linhas),'r'(resumo)}]. Leitura de uma janela de vencimentos."""
    ex = [e for e in exps if janela == 0 or e["n"] <= janela] or exps[:1]
    if not ex: return None
    A = {}
    for e in ex:
        for k, v in e["L"].items():
            a = A.setdefault(k, [0, 0, 0, 0])
            a[0] += v[0]; a[1] += v[1]; a[2] += v[2]; a[3] += v[3]
    co = sum(a[0] for a in A.values()); po = sum(a[1] for a in A.values())
    cv = sum(a[2] for a in A.values()); pv = sum(a[3] for a in A.values())
    up, dn = paredes(A, spot, "up"), paredes(A, spot, "dn")
    carregado = max(ex, key=lambda e: e["r"]["co"] + e["r"]["po"])
    mp = carregado["r"]["mp"]
    alvo = ex[-1] if janela else (ex[min(len(ex) - 1, 5)])
    mv = alvo["r"]["mv"]
    an = {"pcoi": round(po / co, 2) if co else None, "pcv": round(pv / cv, 2) if cv > 100 else None,
          "co": int(co), "po": int(po), "cv": int(cv), "pv": int(pv),
          "up": up, "dn": dn,
          "mp": {"k": mp, "d": carregado["d"], "pct": round((mp / spot - 1) * 100, 1)} if mp else None,
          "mv": {"d": alvo["d"], "pct": mv, "lo": round(spot * (1 - mv / 100), 2), "hi": round(spot * (1 + mv / 100), 2)} if mv else None}
    sinais = []
    if an["pcv"] is not None: sinais.append(["fluxo", an["pcv"], 1 if an["pcv"] <= 0.6 else -1 if an["pcv"] >= 1.0 else 0])
    if an["pcoi"] is not None: sinais.append(["posicoes", an["pcoi"], 1 if an["pcoi"] <= 0.7 else -1 if an["pcoi"] >= 1.0 else 0])
    if an["mp"]: sinais.append(["maxpain", an["mp"]["pct"], 1 if an["mp"]["pct"] > 1.5 else -1 if an["mp"]["pct"] < -1.5 else 0])
    an["vies"] = {"s": sum(x[2] for x in sinais), "n": len(sinais), "sinais": sinais}
    # perfil por strike (±25% do preço), os 30 com mais posições, em ordem de strike
    P = [[k, int(a[0]), int(a[1]), int(a[2]), int(a[3])] for k, a in A.items() if spot * 0.75 <= k <= spot * 1.25 and a[0] + a[1] > 0]
    P.sort(key=lambda x: -(x[1] + x[2]))
    P = sorted(P[:30])
    return an, P


def coletar_ticker(tk, hoje, fonte):
    spot, vencs = fonte.spot(tk), fonte.vencimentos(tk)
    exps = []
    for d in vencs:
        n = (dt.date.fromisoformat(d) - hoje).days
        if n < 0 or n > MAX_DIAS: continue
        if len(exps) >= MAX_VENC: break
        try: calls, puts = fonte.cadeia(tk, d)
        except Exception as e:
            print(f"  {tk} {d}: falha {e}"); continue
        L = linhas_venc(calls, puts)
        if not L: continue
        exps.append({"d": d, "n": n, "L": L, "r": resumo_venc(d, n, L, spot)})
    if not exps: return None
    res = {"spot": round(spot, 2), "exp": [e["r"] for e in exps], "an": {}, "perfil": {}}
    for j in JANELAS:
        r = analisar(spot, exps, j)
        if r: res["an"][str(j)], res["perfil"][str(j)] = r
    return res


class Yahoo:
    def __init__(self):
        import yfinance as yf
        self.yf = yf; self.t = {}

    def _t(self, tk):
        if tk not in self.t: self.t[tk] = self.yf.Ticker(tk)
        return self.t[tk]

    def spot(self, tk):
        h = self._t(tk).history(period="5d")
        return float(h["Close"].dropna().iloc[-1])

    def ultimo_pregao(self, tk):
        h = self._t(tk).history(period="5d")
        return h.index[-1].date()

    def vencimentos(self, tk): return list(self._t(tk).options)

    def cadeia(self, tk, d):
        c = self._t(tk).option_chain(d)
        return c.calls.to_dict("records"), c.puts.to_dict("records")


def resumo_hist(ts, slot, r):
    a = r["an"].get("30") or next(iter(r["an"].values()))
    return {"ts": ts, "s": slot, "p": r["spot"], "pcoi": a["pcoi"], "pcv": a["pcv"],
            "up": a["up"][0]["k"] if a["up"] else None, "dn": a["dn"][0]["k"] if a["dn"] else None,
            "v": a["vies"]["s"], "nv": a["vies"]["n"]}


def main(forcar=False, fonte=None, agora=None):
    t0 = time.time()
    agora = agora or dt.datetime.now(ET)
    est = ler()
    dev = ["10:00"] if forcar else devidos(est, agora)
    if not dev:
        return
    hoje = agora.date()
    try:
        fonte = fonte or Yahoo()
        if not forcar and fonte.ultimo_pregao("SPY") != hoje:
            print("opções: mercado fechado hoje (feriado?); nada a coletar")
            est.setdefault("slots", {}).setdefault(hoje.isoformat(), []).extend(dev); gravar(est); return
    except Exception as e:
        print("opções: falha ao iniciar", e); return
    ok = 0
    ts = int(time.time())
    est.setdefault("ativos", {})
    for tk in ativos():
        if time.time() - t0 > ORC: print("opções: orçamento de tempo esgotado"); break
        try: r = coletar_ticker(tk, hoje, fonte)
        except Exception as e:
            print(f"  {tk}: falha {e}"); continue
        if not r: print(f"  {tk}: sem dados"); continue
        a = est["ativos"].get(tk) or {}
        hist = a.get("hist", [])
        hist.append(resumo_hist(ts, dev[-1], r))
        r["hist"] = hist[-HIST:]
        r["ts"] = ts
        est["ativos"][tk] = r
        ok += 1
        print(f"  {tk}: {len(r['exp'])} vencimentos")
    est["ts"] = ts
    tent = est.setdefault("tent", {})
    chave = hoje.isoformat() + "|" + dev[-1]
    if ok or tent.get(chave, 0) >= 2:
        est.setdefault("slots", {}).setdefault(hoje.isoformat(), []).extend(dev)
        # guarda só os últimos dias no controle
        est["slots"] = dict(sorted(est["slots"].items())[-10:]); est["tent"] = {}
    else:
        tent[chave] = tent.get(chave, 0) + 1
    if ok: gravar(est)
    else: gravar(est)
    print(f"opções: {ok} ativos gravados ({dev})")


if __name__ == "__main__":
    main(forcar="--forcar" in sys.argv)
