#!/usr/bin/env python3
"""Monitor cripto: RSI, médias móveis, Bollinger, ATR. Gera HTML (abre no celular).
Uso:  python monitor.py --salvar        (baixa preços, salva dados/*.csv e gera relatório)
      python monitor.py --csv dados     (usa os CSVs já salvos)
Para mudar os ativos, edite só a seção CONFIG."""
import sys, os, json, glob, datetime as dt, urllib.request
import numpy as np, pandas as pd

# ================= CONFIG =================
# nome : (tickers Yahoo em ordem de tentativa, par na Kraken como reserva)
ATIVOS = {
    "BTC":   (["BTC-USD"],                    "XBTUSD"),
    "ETH":   (["ETH-USD"],                    "ETHUSD"),
    "SOL":   (["SOL-USD"],                    "SOLUSD"),
    "HYPE":  (["HYPE32196-USD", "HYPE-USD"],  "HYPEUSD"),
    "UNI":   (["UNI7083-USD", "UNI-USD"],     "UNIUSD"),
    "AAVE":  (["AAVE-USD"],                   "AAVEUSD"),
    "PENDLE":(["PENDLE-USD"],                 "PENDLEUSD"),
}
# ==========================================
SALVAR = "--salvar" in sys.argv

def rsi(c, n=14):
    d = c.diff(); up = d.clip(lower=0); dn = -d.clip(upper=0)
    au = up.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    return 100 - 100/(1 + au/ad)

def yahoo(tk):
    import yfinance as yf
    d = yf.download(tk, period="5y", interval="1d", auto_adjust=False, progress=False)
    if d is None or d.empty: return None
    if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
    d = d.rename(columns=str.lower)[["open","high","low","close"]].dropna()
    d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
    return d

def kraken(par):
    url = f"https://api.kraken.com/0/public/OHLC?pair={par}&interval=1440"
    r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
    if r.get("error"): return None
    k = [v for kk, v in r["result"].items() if kk != "last"][0]
    d = pd.DataFrame(k, columns=["t","open","high","low","close","vwap","vol","n"]).astype(float)
    d.index = pd.to_datetime(d.t, unit="s").dt.normalize()
    return d[["open","high","low","close"]]

def ler_csv(pasta, nome):
    f = os.path.join(pasta, f"{nome}_1D.csv")
    if not os.path.exists(f): return None
    d = pd.read_csv(f); d.index = pd.to_datetime(d.time, unit="s").dt.normalize()
    return d[["open","high","low","close"]]

def carregar(csvdir):
    dados, falhas, fonte = {}, [], {}
    for nome, (yts, kpar) in ATIVOS.items():
        d = None
        if csvdir: d = ler_csv(csvdir, nome); fonte[nome] = "csv"
        else:
            for t in yts:
                try: d = yahoo(t)
                except Exception as e: print("yahoo", t, e)
                if d is not None and len(d) > 40: fonte[nome] = "Yahoo " + t; break
                d = None
            if d is None:
                try: d = kraken(kpar); fonte[nome] = "Kraken " + kpar
                except Exception as e: print("kraken", kpar, e)
        if d is None or len(d) < 40: falhas.append(nome); continue
        d = d[~d.index.duplicated(keep="last")].sort_index()
        dados[nome] = d
        if SALVAR and not csvdir:
            os.makedirs("dados", exist_ok=True)
            o = d.copy(); o.insert(0, "time", o.index.astype("datetime64[s]").astype("int64"))
            o.to_csv(f"dados/{nome}_1D.csv", index=False)
    return dados, falhas, fonte

def semanal(d): return d.resample("W-SUN").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()

def tecnico(d, btc):
    c = d.close; w = semanal(d)
    tr = pd.concat([d.high-d.low, (d.high-c.shift()).abs(), (d.low-c.shift()).abs()], axis=1).max(axis=1)
    o = dict(preco=c.iloc[-1], data=d.index[-1].date(), rsi_d=rsi(c).iloc[-1], n=len(c),
             rsi_w=rsi(w.close).iloc[-1] if len(w) > 15 else np.nan,
             atr=tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1])
    for n in (9, 21): o[f"ema{n}"] = c.ewm(span=n, adjust=False).mean().iloc[-1]
    for n in (50, 200): o[f"sma{n}"] = c.rolling(n).mean().iloc[-1] if len(c) >= n else np.nan
    m, s = c.rolling(20).mean().iloc[-1], c.rolling(20).std().iloc[-1]
    o["boll"] = (c.iloc[-1]-m)/(2*s) if s else np.nan
    for k, n in (("r7", 7), ("r30", 30), ("r90", 90)):
        o[k] = c.iloc[-1]/c.iloc[-1-n]-1 if len(c) > n+1 else np.nan
    o["dd"] = c.iloc[-1]/c.tail(365).max()-1
    if btc is not None:
        j = pd.concat([c.pct_change(), btc.pct_change()], axis=1, sort=True).dropna().tail(30)
        o["corr"] = j.iloc[:, 0].corr(j.iloc[:, 1]) if len(j) > 15 else np.nan
    else: o["corr"] = np.nan
    t = []
    r = o["rsi_d"]; t.append("sobrecomprado" if r >= 70 else "sobrevendido" if r <= 30 else "RSI neutro")
    if o["sma50"] == o["sma50"]: t.append("acima MM50" if o["preco"] > o["sma50"] else "abaixo MM50")
    if o["sma200"] == o["sma200"]: t.append("acima MM200" if o["preco"] > o["sma200"] else "abaixo MM200")
    t.append("MM9 acima MM21" if o["ema9"] > o["ema21"] else "MM9 abaixo MM21")
    o["leitura"] = " · ".join(t)
    return o

def fmt(v, n=2):
    if v != v: return "–"
    return f"{v:,.{n}f}" if abs(v) >= 1 else f"{v:.4f}"
def pct(v): return "–" if v != v else f"{v*100:+.1f}%"

def html(dados, falhas, fonte):
    agora = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    css = "body{font-family:system-ui;margin:12px;max-width:980px}table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}th,td{border-bottom:1px solid #ddd;padding:5px 6px;text-align:right}th:first-child,td:first-child,td.l{text-align:left}th{background:#f3f4f6}.ok{color:#0a7d33}.ruim{color:#b3261e}.n{color:#666;font-size:12px}.sc{overflow-x:auto}"
    btc = dados["BTC"].close if "BTC" in dados else None
    L = {k: tecnico(d, btc if k != "BTC" else None) for k, d in dados.items()}
    h = [f"<html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><style>{css}</style></head><body><h1>Monitor cripto · {agora}</h1>",
         "<p class=n>Preços em dólar, fechamento diário (UTC). Boll: −1 = banda inferior, +1 = superior. Corr = correlação diária com o BTC, 30 dias.</p>",
         "<div class=sc><table><tr><th>Ativo</th><th>Preço US$</th><th>7d</th><th>30d</th><th>90d</th><th>vs máx 12m</th><th>RSI D</th><th>RSI S</th><th>MM50</th><th>MM200</th><th>Boll</th><th>ATR</th><th>Corr BTC</th></tr>"]
    for k, o in L.items():
        cor = "ruim" if o["rsi_d"] >= 70 else "ok" if o["rsi_d"] <= 30 else ""
        h.append(f"<tr><td><b>{k}</b></td><td>{fmt(o['preco'])}</td><td>{pct(o['r7'])}</td><td>{pct(o['r30'])}</td><td>{pct(o['r90'])}</td><td>{pct(o['dd'])}</td><td class={cor}>{fmt(o['rsi_d'],1)}</td><td>{fmt(o['rsi_w'],1)}</td><td>{fmt(o['sma50'])}</td><td>{fmt(o['sma200'])}</td><td>{o['boll']:.2f}</td><td>{fmt(o['atr'])}</td><td>{o['corr']:.2f}</td></tr>")
        h.append(f"<tr><td colspan=13 class='l n'>{o['leitura']} · dado de {o['data']} · {o['n']} dias · {fonte.get(k,'')}</td></tr>")
    h.append("</table></div>")
    if falhas: h.append(f"<p class=ruim>Sem dados: {', '.join(falhas)}</p>")
    h.append("</body></html>"); return "".join(h)

if __name__ == "__main__":
    csvdir = sys.argv[sys.argv.index("--csv")+1] if "--csv" in sys.argv else None
    dados, falhas, fonte = carregar(csvdir)
    if not dados: sys.exit("Nenhum ativo carregado.")
    os.makedirs("relatorios", exist_ok=True)
    open("relatorios/ultimo.html", "w", encoding="utf-8").write(html(dados, falhas, fonte))
    print("Gerado relatorios/ultimo.html | sem dados:", falhas or "nenhum")
