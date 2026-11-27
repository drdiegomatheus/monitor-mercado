#!/usr/bin/env python3
"""Universo amplo de ativos: B3 (top 200 por volume), S&P 500 + Nasdaq-100 e top 50 cripto.

Guarda só o fechamento diário de 5 anos (um arquivo compacto por mercado) e calcula os indicadores
(diário, semanal e mensal) a partir dele. Nada aqui roda a cada 5 minutos: é uma rotina diária.

Uso:
  python universo.py --listas    remonta as listas de ativos (rodar 1 vez por semana)
  python universo.py --diario    baixa os preços, atualiza os arquivos e recalcula os indicadores
  python universo.py --tudo      as duas coisas, na ordem
  python universo.py --auto      uso da rotina: lista nova 1x por semana (fim de semana), preços 1x por dia após o fechamento (22h UTC)

Arquivos (pasta universo/):
  listas.json             ativos de cada mercado, com setor, ticker no Yahoo e volume financeiro médio de 30 dias
  precos_<mercado>.csv.gz fechamentos diários (colunas = ativos, linhas = datas), 5 anos
  linhas.json             indicadores já calculados, que a página lê"""
import io
import re
import warnings
import json
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(RAIZ, "universo")
UA = {"User-Agent": "Mozilla/5.0"}
ANOS = 5
N_B3, N_CRIPTO = 200, 50
MERCADOS = ("brasil", "eua", "cripto")

# ---------- setores (nomes em português) ----------
GICS = {"Information Technology": "Tecnologia", "Health Care": "Saúde", "Financials": "Financeiro", "Consumer Discretionary": "Consumo cíclico",
        "Consumer Staples": "Consumo básico", "Industrials": "Industrial", "Communication Services": "Comunicação", "Energy": "Energia",
        "Utilities": "Utilidades", "Real Estate": "Imobiliário", "Materials": "Materiais"}
BRAPI = {"Finance": "Financeiro", "Energy Minerals": "Petróleo e energia", "Non-Energy Minerals": "Mineração e siderurgia", "Utilities": "Utilidades",
         "Retail Trade": "Varejo", "Consumer Non-Durables": "Consumo básico", "Consumer Durables": "Consumo cíclico", "Consumer Services": "Serviços ao consumidor",
         "Health Services": "Saúde", "Health Technology": "Saúde", "Process Industries": "Indústria de processos", "Producer Manufacturing": "Indústria",
         "Electronic Technology": "Tecnologia", "Technology Services": "Tecnologia", "Transportation": "Transporte e logística",
         "Commercial Services": "Serviços", "Communications": "Comunicação", "Distribution Services": "Distribuição", "Industrial Services": "Serviços industriais",
         "Miscellaneous": "Outros", "Finance (Other)": "Financeiro"}
SET_BR = {"Bancos": "Financeiro", "Seguros e serviços financeiros": "Financeiro", "Energia elétrica": "Utilidades", "Saneamento": "Utilidades",
          "Petróleo e gás": "Petróleo e energia", "Consumo não cíclico": "Consumo básico", "Bens industriais": "Indústria", "Serviços industriais": "Indústria",
          "Telecomunicações": "Comunicação", "Shoppings e imobiliário": "Imobiliário", "Serviços ao consumidor": "Consumo cíclico", "Indústria de processos": "Materiais",
          "Distribuição": "Varejo", "ETFs Ibovespa": "ETFs", "ETFs internacionais": "ETFs", "Petróleo e energia": "Petróleo e energia"}
CRIPTO_SETOR = {"BTC": "Reserva de valor", "LTC": "Reserva de valor", "BCH": "Reserva de valor", "XMR": "Privacidade", "ZEC": "Privacidade",
                "ETH": "Camada 1", "SOL": "Camada 1", "BNB": "Camada 1", "ADA": "Camada 1", "AVAX": "Camada 1", "TRX": "Camada 1", "DOT": "Camada 1",
                "TON": "Camada 1", "NEAR": "Camada 1", "SUI": "Camada 1", "APT": "Camada 1", "ATOM": "Camada 1", "ICP": "Camada 1", "HBAR": "Camada 1",
                "ALGO": "Camada 1", "XLM": "Pagamentos", "XRP": "Pagamentos", "HYPE": "Derivativos e DeFi", "UNI": "DeFi", "AAVE": "DeFi", "LINK": "Infraestrutura",
                "ARB": "Camada 2", "OP": "Camada 2", "POL": "Camada 2", "MATIC": "Camada 2", "DOGE": "Meme", "SHIB": "Meme", "PEPE": "Meme", "BONK": "Meme",
                "WIF": "Meme", "TRUMP": "Meme", "FIL": "Infraestrutura", "RENDER": "IA e computação", "FET": "IA e computação", "TAO": "IA e computação",
                "INJ": "DeFi", "ENA": "DeFi", "PENDLE": "DeFi", "LDO": "DeFi", "MKR": "DeFi", "ONDO": "Ativos reais", "VET": "Infraestrutura", "ETC": "Camada 1",
                "LEO": "Exchange", "CRO": "Exchange", "OKB": "Exchange", "KAS": "Camada 1", "XDC": "Camada 1", "WLD": "IA e computação"}
EXCLUIR_CRIPTO = {"USDT", "USDC", "DAI", "USDE", "FDUSD", "TUSD", "USDS", "USDD", "PYUSD", "BUSD", "USD1", "USDG", "USDY", "BFUSD", "RLUSD",
                  "STETH", "WSTETH", "WBTC", "WETH", "WEETH", "WBETH", "CBBTC", "BSC-USD", "SUSDE", "SUSDS", "BUIDL", "USDTB", "USYC", "XAUT", "PAXG", "EURCV", "SOXLB", "NVDAB", "FIGR_HELOC", "EURC", "EURT"}


def _get(url, tentativas=3, timeout=40):
    for i in range(tentativas):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception as e:
            print("   falha", url[:80], e)
            time.sleep(3 * (i + 1))
    return None


def _json(url):
    b = _get(url)
    return json.loads(b) if b else None


# ---------- Yahoo ----------
def baixar_yahoo(tickers, periodo, lote=40):
    """fechamentos diários de vários tickers; devolve DataFrame (datas x tickers) e o volume financeiro médio de 30 dias"""
    import yfinance as yf
    import tempfile
    try: yf.set_tz_cache_location(tempfile.mkdtemp())
    except Exception: pass
    fech, adv = {}, {}
    tickers = sorted(set(tickers))
    for i in range(0, len(tickers), lote):
        L = tickers[i:i + lote]
        d = None
        for t in range(3):
            try:
                d = yf.download(L, period=periodo, interval="1d", auto_adjust=False, progress=False, group_by="ticker", threads=True)
                break
            except Exception as e:
                print("   lote", i, e); time.sleep(5 * (t + 1))
        if d is None or d.empty: continue
        for tk in L:
            try: s = d[tk] if len(L) > 1 else d
            except Exception: continue
            if isinstance(s.columns, pd.MultiIndex): s.columns = s.columns.get_level_values(0)
            s = s.dropna(subset=["Close"]) if "Close" in s else None
            if s is None or len(s) < 2: continue
            s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
            s = s[~s.index.duplicated(keep="last")]
            fech[tk] = s["Close"].astype(float)
            if "Volume" in s: adv[tk] = float((s["Close"] * s["Volume"]).tail(30).mean())
        print(f"   yahoo {min(i + lote, len(tickers))}/{len(tickers)}")
        time.sleep(1.5)
    return pd.DataFrame(fech).sort_index(), adv


# ---------- listas ----------
def lista_eua():
    sp = pd.read_csv(io.BytesIO(_get("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv")))
    out = {}
    for _, r in sp.iterrows():
        out[str(r["Symbol"])] = {"nome": str(r["Security"]), "setor": GICS.get(r["GICS Sector"], r["GICS Sector"]), "indice": "S&P 500"}
    ICB = {"Technology": "Tecnologia", "Health Care": "Saúde", "Financials": "Financeiro", "Consumer Discretionary": "Consumo cíclico",
           "Consumer Staples": "Consumo básico", "Industrials": "Industrial", "Telecommunications": "Comunicação", "Energy": "Energia",
           "Utilities": "Utilidades", "Real Estate": "Imobiliário", "Basic Materials": "Materiais"}
    try:
        html = _get("https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies").decode("utf-8", "ignore")
        for t in pd.read_html(io.StringIO(html)):
            if "Ticker" in [str(c) for c in t.columns] and "Company" in [str(c) for c in t.columns]:
                ic = [c for c in t.columns if str(c).startswith("ICB Industry")][0]
                for _, r in t.iterrows():
                    tk = str(r["Ticker"]).strip()
                    if tk in out: out[tk]["indice"] = "S&P 500 e Nasdaq-100"
                    else: out[tk] = {"nome": str(r["Company"]), "setor": ICB.get(r[ic], r[ic]), "indice": "Nasdaq-100"}
                break
    except Exception as e:
        print("   nasdaq-100 indisponível:", e)
    return {tk: {**v, "yahoo": tk.replace(".", "-")} for tk, v in out.items()}


def lista_brasil():
    cfg = json.load(open(os.path.join(RAIZ, "categorias", "brasil", "config.json"), encoding="utf-8"))["ativos"]
    j = _json("https://brapi.dev/api/quote/list?sortBy=volume&sortOrder=desc&limit=400&type=stock")
    out = {}
    for s in (j or {}).get("stocks", []):
        tk = s["stock"]
        if not tk[-1].isdigit() or (re.match(r"^[A-Z]{4}3[1-9]$", tk) and tk not in cfg): continue   # fora BDRs
        setor = SET_BR.get((cfg.get(tk) or {}).get("setor") or BRAPI.get(s.get("sector"), s.get("sector") or "Outros"), None) or (cfg.get(tk) or {}).get("setor") or BRAPI.get(s.get("sector"), s.get("sector") or "Outros")
        out[tk] = {"nome": (s.get("name") or tk).title(), "setor": setor, "yahoo": tk + ".SA"}
    for tk, v in cfg.items():                       # os ativos que já acompanhamos entram sempre
        out.setdefault(tk, {"nome": tk, "setor": SET_BR.get((v or {}).get("setor", "Outros"), (v or {}).get("setor", "Outros")), "yahoo": tk + ".SA"})
    return out


def lista_cripto():
    """candidatos: 250 de maior volume em 24 h, só entre as 300 maiores por valor de mercado (tira moedas de volume inflado); sem stablecoins/wrapped"""
    j = _json("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=250&page=1")
    out = {}
    for c in j or []:
        s = c["symbol"].upper()
        rk = c.get("market_cap_rank") or 9999
        nome = (c.get("name") or "").lower()
        estavel = abs((c.get("current_price") or 0) - 1) < 0.03 and abs(c.get("price_change_percentage_24h") or 0) < 1
        if (s in EXCLUIR_CRIPTO or rk > 300 or estavel or "usd" in s.lower() or any(w in nome for w in ("wrapped", "staked", "bridged", "tether", "stable", "peg")) or
                c["id"].startswith(("wrapped", "staked", "bridged", "binance-peg")) or "_" in s or s in out): continue
        out[s] = {"nome": c["name"], "setor": CRIPTO_SETOR.get(s, "Outras"), "preco_ref": c["current_price"], "cg": c["id"]}
        if len(out) >= 80: break
    return out


def yahoo_cripto(L):
    """acha o ticker do Yahoo de cada cripto, conferindo o preço contra o da CoinGecko (evita moedas homônimas)"""
    import yfinance as yf
    cand = {s: [f"{s}-USD"] for s in L}
    d, _ = baixar_yahoo([c[0] for c in cand.values()], "5d")
    falta = []
    for s, v in L.items():
        tk = f"{s}-USD"
        ok = tk in d and abs(d[tk].dropna().iloc[-1] / v["preco_ref"] - 1) < 0.08 if tk in d and not d[tk].dropna().empty else False
        if ok: v["yahoo"] = tk
        else: falta.append(s)
    for s in falta:                                  # procura outro ticker (ex.: UNI7083-USD) pelo nome
        v = L[s]
        j = _json("https://query1.finance.yahoo.com/v1/finance/lookup?type=cryptocurrency&count=15&query=" + urllib.parse.quote(s))
        docs = (((j or {}).get("finance") or {}).get("result") or [{}])[0].get("documents", [])
        cs = [x["symbol"] for x in docs if x.get("symbol", "").endswith("-USD") and x.get("symbol", "").startswith(s)]
        if cs:
            dd, _ = baixar_yahoo(cs, "5d")
            for tk in cs:
                if tk in dd and not dd[tk].dropna().empty and abs(dd[tk].dropna().iloc[-1] / v["preco_ref"] - 1) < 0.08:
                    v["yahoo"] = tk; break
        if "yahoo" not in v: print("   cripto sem ticker confiável no Yahoo:", s)
    ok = {s: v for s, v in L.items() if "yahoo" in v}
    return dict(list(ok.items())[:N_CRIPTO])


def montar_listas():
    os.makedirs(PASTA, exist_ok=True)
    print("EUA..."); eua = lista_eua()
    print("Brasil..."); br = lista_brasil()
    print("Cripto..."); cr = yahoo_cripto(lista_cripto())
    L = {"brasil": br, "eua": eua, "cripto": cr}
    # brasil: mantém os 300 mais líquidos (brapi) como candidatos; o corte final em 200 é feito pelo volume de 30 dias do Yahoo
    json.dump(L, open(os.path.join(PASTA, "listas.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("listas:", {k: len(v) for k, v in L.items()})
    return L


# ---------- preços ----------
def _arq(m): return os.path.join(PASTA, f"precos_{m}.csv.gz")


def atualizar_precos(L):
    """baixa 5 anos para o que é novo e só o último mês para o resto; guarda tudo comprimido"""
    for m in MERCADOS:
        yt = {v["yahoo"]: t for t, v in L[m].items()}
        antigo = pd.read_csv(_arq(m), index_col=0, parse_dates=True) if os.path.exists(_arq(m)) else pd.DataFrame()
        novos = [y for y in yt if y not in antigo.columns]
        velhos = [y for y in yt if y in antigo.columns]
        print(m, "| novos:", len(novos), "| a atualizar:", len(velhos))
        partes, adv = [], {}
        if novos:
            d, a = baixar_yahoo(novos, f"{ANOS}y"); partes.append(d); adv.update(a)
        if velhos:
            d, a = baixar_yahoo(velhos, "3mo"); adv.update(a)
            base = antigo[[c for c in velhos if c in antigo.columns]]
            d = d.combine_first(base) if not base.empty else d   # o novo vale mais; o antigo preenche o que faltar
            d.update(d)                                          # (sem efeito, mantém o índice ordenado)
            partes.append(d.reindex(base.index.union(d.index)))
        todo = pd.concat(partes, axis=1) if partes else antigo
        todo = todo.loc[:, ~todo.columns.duplicated()].sort_index()
        todo = todo[todo.index >= todo.index.max() - pd.Timedelta(days=365 * ANOS + 10)]
        todo = todo.dropna(axis=1, how="all")
        todo.to_csv(_arq(m), compression="gzip", float_format="%.8g")
        for y, t in yt.items():
            if y in adv: L[m][t]["adv"] = adv[y]
    return L


# ---------- indicadores ----------
def _rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _n(x, nd=1):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def indicadores(c, mercado):
    """c: fechamentos diários (Series com índice de datas). Semanal e mensal saem do próprio diário."""
    c = c.dropna()
    if len(c) < 60: return None
    p, hoje = c.iloc[-1], c.index[-1]
    cripto = mercado == "cripto"
    w = c.resample("W-SUN" if cripto else "W-FRI").last().dropna()
    mo = c.resample("ME").last().dropna()
    def atras(dias):
        x = c[c.index <= hoje - pd.Timedelta(days=dias)]
        return (p / x.iloc[-1] - 1) * 100 if len(x) else None
    m200, w200 = c.rolling(200).mean().iloc[-1], w.rolling(200).mean().iloc[-1] if len(w) >= 200 else np.nan
    d2 = (p / m200 - 1) * 100 if np.isfinite(m200) else None
    w2 = (p / w200 - 1) * 100 if np.isfinite(w200) else None
    ab_d, ab_w = d2 is not None and d2 > 0, w2 is not None and w2 > 0
    if d2 is None and w2 is None: tend = ""
    else: tend = "alta" if ab_d and (ab_w or w2 is None) else "baixa" if (not ab_d) and (not ab_w) and d2 is not None else "mista"
    ano = 365 if cripto else 252
    return {"p": float(f"{p:.6g}"), "dt": str(hoje.date()), "d1": _n((p / c.iloc[-2] - 1) * 100, 2), "w1": _n(atras(7), 2), "m1": _n(atras(30), 2),
            "rd": _n(_rsi(c).iloc[-1], 0), "rw": _n(_rsi(w).iloc[-1], 0) if len(w) > 15 else None, "rm": _n(_rsi(mo).iloc[-1], 0) if len(mo) > 15 else None,
            "d200": _n(d2), "w200": _n(w2), "t": tend, "h52": _n((p / c.tail(ano).max() - 1) * 100)}


def calcular(L):
    linhas = []
    for m in MERCADOS:
        if not os.path.exists(_arq(m)): continue
        P = pd.read_csv(_arq(m), index_col=0, parse_dates=True)
        rank = sorted((t for t, v in L[m].items() if v.get("adv")), key=lambda t: -L[m][t]["adv"])
        pos = {t: i + 1 for i, t in enumerate(rank)}
        corte = N_B3 if m == "brasil" else None
        for t, v in L[m].items():
            if v["yahoo"] not in P.columns: continue
            if m == "brasil" and pos.get(t, 9999) > N_B3: continue      # só as 200 mais negociadas
            ind = indicadores(P[v["yahoo"]], m)
            if not ind: continue
            linhas.append({"m": m, "t": t, "n": v["nome"], "s": v["setor"], "adv": _n(v.get("adv"), 0), "r": pos.get(t), **{k if k != "t" else "tr": x for k, x in ind.items()}})
    json.dump({"gerado": pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC"), "linhas": linhas}, open(os.path.join(PASTA, "linhas.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print("indicadores:", {m: sum(1 for x in linhas if x["m"] == m) for m in MERCADOS})
    return linhas


def ler_listas():
    return json.load(open(os.path.join(PASTA, "listas.json"), encoding="utf-8"))


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--listas" in a or "--tudo" in a: L = montar_listas()
    if "--diario" in a or "--tudo" in a:
        L = ler_listas()
        L = atualizar_precos(L)
        json.dump(L, open(os.path.join(PASTA, "listas.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        calcular(L)
    if "--auto" in a:        # chamada pela rotina da plataforma: decide sozinho o que precisa rodar
        agora = pd.Timestamp.now("UTC")
        fl, fn = os.path.join(PASTA, "listas.json"), os.path.join(PASTA, "linhas.json")
        velha = (not os.path.exists(fl)) or (agora.timestamp() - os.path.getmtime(fl) > 7 * 86400 and agora.weekday() >= 5)
        feito_hoje = os.path.exists(fn) and json.load(open(fn, encoding="utf-8")).get("gerado", "")[:10] == str(agora.date())
        apos_fechamento = agora.hour >= 22 or not os.path.exists(fn)
        if velha: L = montar_listas()
        if velha or (apos_fechamento and not feito_hoje):
            L = ler_listas()
            L = atualizar_precos(L)
            json.dump(L, open(fl, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            calcular(L)
        else: print("universo: nada a fazer agora")
    elif not a: print(__doc__)
