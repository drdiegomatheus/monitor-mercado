"""Coleta fundamentos e dados de analistas (Yahoo) de forma incremental: a cada rodada atualiza alguns ativos,
os mais antigos primeiro; cada ativo é atualizado no máximo 1 vez por dia. Saída: categorias/<cat>/fundamentos.json"""
import json
import os
import sys
import time
import datetime as dt
import yfinance as yf

RAIZ = os.path.dirname(os.path.abspath(__file__))
ORC = float(os.environ.get("FUND_ORCAMENTO", "110"))       # segundos por rodada
VALIDADE = 20 * 3600
RETENTAR = 6 * 3600
CH = ("trailingPE forwardPE priceToBook enterpriseToEbitda dividendYield payoutRatio returnOnEquity returnOnAssets profitMargins operatingMargins "
      "grossMargins revenueGrowth earningsGrowth totalDebt totalCash ebitda freeCashflow operatingCashflow debtToEquity currentRatio "
      "targetMeanPrice targetHighPrice targetLowPrice recommendationMean recommendationKey numberOfAnalystOpinions marketCap sector").split()
LIN = {"rev": ["Total Revenue", "Operating Revenue"], "bruto": ["Gross Profit"], "op": ["Operating Income"], "liq": ["Net Income", "Net Income Common Stockholders"],
       "ebitda": ["EBITDA", "Normalized EBITDA"], "div": ["Total Debt"], "cx": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"],
       "pl": ["Stockholders Equity", "Common Stock Equity"], "fco": ["Operating Cash Flow"], "fcl": ["Free Cash Flow"]}


def ycod(cat, n):
    return n + ".SA" if cat == "brasil" else n.replace(".", "-")


def serie(df, nomes, n):
    """últimos n períodos (do mais antigo ao mais novo) de uma linha da demonstração"""
    if df is None or df.empty: return None
    for nm in nomes:
        if nm in df.index:
            s = df.loc[nm].dropna().sort_index().tail(n)
            return [[str(i.date()), float(v)] for i, v in s.items()]
    return None


def coletar(cat, n):
    t = yf.Ticker(ycod(cat, n))
    r = {"ts": time.time()}
    info = t.info or {}
    r["info"] = {k: info[k] for k in CH if info.get(k) is not None}
    if len(r["info"]) < 5:
        r["vazio"] = True
        return r
    for nome, attr, n_ in (("q", "quarterly_income_stmt", 8), ("a", "income_stmt", 5)):
        try: df = getattr(t, attr)
        except Exception: df = None
        r[nome] = {k: serie(df, LIN[k], n_) for k in ("rev", "bruto", "op", "liq", "ebitda")}
    for nome, attr, n_ in (("qb", "quarterly_balance_sheet", 8), ("ab", "balance_sheet", 5)):
        try: df = getattr(t, attr)
        except Exception: df = None
        r[nome] = {k: serie(df, LIN[k], n_) for k in ("div", "cx", "pl")}
    try: df = t.cashflow
    except Exception: df = None
    r["af"] = {k: serie(df, LIN[k], 5) for k in ("fco", "fcl")}
    try:
        e = t.get_earnings_dates(limit=12)
        ev = []
        if e is not None and not e.empty:
            for i, row in e.sort_index().iterrows():
                ev.append({"d": str(i.date()), "est": None if row.get("EPS Estimate") != row.get("EPS Estimate") else float(row["EPS Estimate"]),
                           "rep": None if row.get("Reported EPS") != row.get("Reported EPS") else float(row["Reported EPS"]),
                           "sur": None if row.get("Surprise(%)") != row.get("Surprise(%)") else float(row["Surprise(%)"])})
        r["res"] = ev
    except Exception:
        r["res"] = []
    return r


def main():
    t0 = time.time()
    fila = []
    arq = {}
    for cat in ("brasil", "eua"):
        f = os.path.join(RAIZ, "categorias", cat, "fundamentos.json")
        arq[cat] = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
        cfg = json.load(open(os.path.join(RAIZ, "categorias", cat, "config.json"), encoding="utf-8"))["ativos"]
        for n, v in cfg.items():
            if cat == "brasil" and "ETF" in ((v or {}).get("setor", "")): continue
            a = arq[cat].get(n)
            idade = time.time() - a["ts"] if a else 1e12
            lim = RETENTAR if a and a.get("vazio") else VALIDADE
            if idade >= lim: fila.append((idade, cat, n))
    fila.sort(reverse=True)
    feitos = 0
    for _, cat, n in fila:
        if time.time() - t0 > ORC: break
        try:
            arq[cat][n] = coletar(cat, n)
        except Exception as e:
            arq[cat][n] = {"ts": time.time(), "vazio": True, "erro": str(e)[:80]}
        feitos += 1
        time.sleep(0.3)
    for cat in arq:
        f = os.path.join(RAIZ, "categorias", cat, "fundamentos.json")
        json.dump(arq[cat], open(f, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"fundamentos: {feitos} atualizados, {max(0, len(fila) - feitos)} pendentes")


if __name__ == "__main__":
    main()
