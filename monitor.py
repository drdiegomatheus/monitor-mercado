#!/usr/bin/env python3
"""Monitor de mercado: RSI, médias, RRG e pares. Gera um HTML (abre no celular).
Uso:  python monitor.py              (baixa do Yahoo Finance)
      python monitor.py --csv dados  (usa CSVs do TradingView em ./dados)
Edite só a seção CONFIG."""
import sys, glob, os, datetime as dt
import numpy as np, pandas as pd

# ================= CONFIG =================
ATIVOS = ["PETR4","VALE3","ITUB4","BBDC4","LREN3","EGIE3","SBSP3","WEGE3","ABEV3",
          "RADL3","VIVT3","SUZB3","MRVE3","TRIS3","DIRR3","M2ST34","BITH11"]
BENCH = "BOVA11"
CRIPTO = {"BTC-USD":"BTC", "SOL-USD":"SOL"}        # ticker Yahoo : nome
# Pares (A, B): spread = A - k*B e razão
PARES = [("TRIS3","MRVE3",1), ("DIRR3","TRIS3",1), ("M2ST34","BITH11",10)]
RSI_ROT = (65, 60)   # M2ST34: RSI semanal >= 65 favorece BITH11; volta quando <= 60
# ==========================================
SALVAR = "--salvar" in sys.argv   # grava dados/*.csv (usado pela coleta automática)

def rsi(c, n=14):
    d = c.diff(); up = d.clip(lower=0); dn = -d.clip(upper=0)
    au = up.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    return 100 - 100/(1 + au/ad)

def baixar_yahoo(tk, y):
    import yfinance as yf
    d = yf.download(y, period="3y", interval="1d", auto_adjust=False, progress=False)
    if d is None or d.empty: return None
    if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
    d = d.rename(columns=str.lower)[["open","high","low","close"]].dropna()
    d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
    return d

def ler_csv(pasta, tk):
    import re
    alvo = "(?:BTC|BTCUSDT)" if tk == "BTC" else tk
    pat = re.compile(r"^(?:[0-9a-f]{8}-)?(?:BMFBOVESPA|BINANCE)_%s_1D" % alvo)
    fs = [f for f in glob.glob(os.path.join(pasta, "*.csv")) if pat.match(os.path.basename(f))]
    if not fs: return None
    d = pd.read_csv(fs[0], usecols=["time","open","high","low","close"])
    d.index = pd.to_datetime(d.time, unit="s").dt.normalize(); d = d.drop(columns="time")
    return d[~d.index.duplicated(keep="last")].dropna()

def carregar(csvdir):
    dados, falhas = {}, []
    nomes = [(a, a+".SA", a) for a in ATIVOS+[BENCH]] + [(n, y, n) for y, n in CRIPTO.items()]
    for tk, y, nome in nomes:
        try:
            d = ler_csv(csvdir, tk) if csvdir else baixar_yahoo(tk, y)
        except Exception as e:
            d = None; print("erro", tk, e)
        if d is None or len(d) < 40: falhas.append(tk)
        else:
            dados[nome] = d
            if SALVAR and not csvdir:
                os.makedirs("dados", exist_ok=True)
                o = d.copy(); o.insert(0, "time", (o.index.astype("int64") // 10**9) if str(o.index.dtype).endswith("[ns]") else (o.index.astype("datetime64[s]").astype("int64")))
                o.to_csv(f"dados/BMFBOVESPA_{tk}_1D.csv", index=False)
    return dados, falhas

def semanal(d): return d.resample("W-FRI").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()

def tecnico(d):
    c = d.close; w = semanal(d)
    tr = pd.concat([d.high-d.low, (d.high-c.shift()).abs(), (d.low-c.shift()).abs()], axis=1).max(axis=1)
    o = dict(preco=c.iloc[-1], data=d.index[-1].date(), rsi_d=rsi(c).iloc[-1],
             rsi_w=rsi(w.close).iloc[-1] if len(w) > 15 else np.nan,
             atr=tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1])
    for n in (9, 21): o[f"ema{n}"] = c.ewm(span=n, adjust=False).mean().iloc[-1]
    for n in (50, 200): o[f"sma{n}"] = c.rolling(n).mean().iloc[-1] if len(c) >= n else np.nan
    m, s = c.rolling(20).mean().iloc[-1], c.rolling(20).std().iloc[-1]
    o["boll"] = (c.iloc[-1]-m)/(2*s) if s else np.nan   # -1 banda inferior, +1 superior
    o["ret5"] = c.iloc[-1]/c.iloc[-6]-1 if len(c) > 6 else np.nan
    # leitura
    t = []
    r = o["rsi_d"]
    t.append("sobrecomprado" if r >= 70 else "sobrevendido" if r <= 30 else "RSI neutro")
    if o["sma50"] == o["sma50"]:
        t.append("acima MM50" if o["preco"] > o["sma50"] else "abaixo MM50")
    if o["sma200"] == o["sma200"]:
        t.append("acima MM200" if o["preco"] > o["sma200"] else "abaixo MM200")
    t.append("MM9 acima MM21" if o["ema9"] > o["ema21"] else "MM9 abaixo MM21")
    o["leitura"] = " · ".join(t)
    return o

def rrg(a, b, n, s, m):
    rs = (a/b).dropna()
    rsr = 100 + (rs/rs.rolling(n).mean() - 1)*100
    rsr = rsr.ewm(span=s, adjust=False).mean()
    mom = 100 + (rsr/rsr.shift(m) - 1)*100
    return pd.DataFrame({"x": rsr, "y": mom}).dropna()

def quadrante(x, y):
    return ("Leading" if y >= 100 else "Weakening") if x >= 100 else ("Improving" if y >= 100 else "Lagging")

def tabela_rrg(dados, modo):
    n, s, m = (20, 5, 5) if modo == "d" else (10, 3, 4)
    b = dados[BENCH].close if modo == "d" else semanal(dados[BENCH]).close
    out = []
    for k, d in dados.items():
        if k == BENCH: continue
        a = d.close if modo == "d" else semanal(d).close
        r = rrg(a, b, n, s, m)
        if len(r) < 6: continue
        x, y = r.x.iloc[-1], r.y.iloc[-1]
        x0, y0 = r.x.iloc[-4], r.y.iloc[-4]
        out.append(dict(ativo=k, x=x, y=y, quad=quadrante(x, y), antes=quadrante(x0, y0), trilha=list(zip(r.x.iloc[-5:], r.y.iloc[-5:]))))
    return pd.DataFrame(out)

def svg_rrg(df):
    if df.empty: return ""
    xs = [p[0] for t in df.trilha for p in t]; ys = [p[1] for t in df.trilha for p in t]
    ext = lambda v: max(abs(min(v)-100), abs(max(v)-100), 1.5)*1.15
    ex, ey = ext(xs), ext(ys); W = H = 520
    X = lambda v: (v-100+ex)/(2*ex)*W; Y = lambda v: H-(v-100+ey)/(2*ey)*H
    s = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;max-width:560px;background:#fff;border:1px solid #ccc;border-radius:8px">']
    s.append(f'<rect x="{W/2}" y="0" width="{W/2}" height="{H/2}" fill="#e6f4ea"/><rect x="{W/2}" y="{H/2}" width="{W/2}" height="{H/2}" fill="#fff8e1"/>'
             f'<rect x="0" y="{H/2}" width="{W/2}" height="{H/2}" fill="#fdecea"/><rect x="0" y="0" width="{W/2}" height="{H/2}" fill="#e8f0fe"/>')
    for t, (px, py) in {"Leading": (W-70, 18), "Weakening": (W-85, H-8), "Lagging": (8, H-8), "Improving": (8, 18)}.items():
        s.append(f'<text x="{px}" y="{py}" font-size="12" fill="#666">{t}</text>')
    for _, r in df.iterrows():
        pts = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in r.trilha)
        s.append(f'<polyline points="{pts}" fill="none" stroke="#888" stroke-width="1.2"/>')
        s.append(f'<circle cx="{X(r.x):.1f}" cy="{Y(r.y):.1f}" r="4" fill="#1a56db"/><text x="{X(r.x)+6:.1f}" y="{Y(r.y)-4:.1f}" font-size="11">{r.ativo}</text>')
    s.append("</svg>"); return "".join(s)

def pares(dados):
    L = []
    for a, b, k in PARES:
        if a not in dados or b not in dados: continue
        j = pd.concat([dados[a].close, dados[b].close], axis=1, keys=["a","b"], sort=True).dropna()
        if len(j) < 30: continue
        sp = j.a - k*j.b; rz = j.a/j.b
        z = (sp.iloc[-1]-sp.tail(60).mean())/sp.tail(60).std()
        L.append(dict(par=f"{a} − {k}×{b}", spread=sp.iloc[-1], min60=sp.tail(60).min(), max60=sp.tail(60).max(),
                      media60=sp.tail(60).mean(), z=z, razao=rz.iloc[-1], data=j.index[-1].date()))
    return pd.DataFrame(L)

def rot_m2(dados):
    if "M2ST34" not in dados or "BITH11" not in dados: return ""
    r = rsi(semanal(dados["M2ST34"]).close).iloc[-1]; hi, lo = RSI_ROT
    aviso = " ATENÇÃO: histórico curto no Yahoo (%d pregões); RSI semanal pouco confiável, confira no TradingView/Alpha Vantage." % len(dados["M2ST34"]) if len(dados["M2ST34"]) < 300 else ""
    est = (f"RSI semanal do M2ST34 = {r:.1f}.{aviso} " +
           ("SINAL: favorece migrar para BITH11 (≥ %d); só voltar com RSI ≤ %d." % (hi, lo) if r >= hi else
            "Zona de transição: se já está no BITH11, mantém até RSI ≤ %d." % lo if r > lo else
            "Sem sinal de troca: fica no M2ST34 (abaixo de %d)." % hi))
    return est

def fmt(v, n=2): return "–" if v != v else f"{v:,.{n}f}"

def html(dados, falhas):
    agora = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    css = "body{font-family:system-ui;margin:12px;max-width:900px}table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}th,td{border-bottom:1px solid #ddd;padding:5px 6px;text-align:right}th:first-child,td:first-child,td.l{text-align:left}th{background:#f3f4f6}h2{margin-top:22px}.ok{color:#0a7d33}.ruim{color:#b3261e}.n{color:#666;font-size:12px}"
    h = [f"<html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><style>{css}</style></head><body>",
         f"<h1>Monitor {agora}</h1>"]
    h.append(f"<p>{rot_m2(dados)}</p>")
    P = pares(dados)
    if not P.empty:
        h.append("<h2>Pares (spread em R$, últimos 60 pregões)</h2><table><tr><th>Par</th><th>Spread</th><th>Mín</th><th>Média</th><th>Máx</th><th>z</th><th>Razão</th><th>Data</th></tr>")
        for _, r in P.iterrows():
            h.append(f"<tr><td>{r.par}</td><td>{fmt(r.spread)}</td><td>{fmt(r.min60)}</td><td>{fmt(r.media60)}</td><td>{fmt(r.max60)}</td><td>{fmt(r.z)}</td><td>{fmt(r.razao,3)}</td><td>{r.data}</td></tr>")
        h.append("</table>")
    for modo, nome in (("w","RRG semanal"),("d","RRG diário")):
        T = tabela_rrg(dados, modo)
        h.append(f"<h2>{nome} (vs {BENCH})</h2>"+svg_rrg(T))
        if not T.empty:
            h.append("<table><tr><th>Ativo</th><th>Quadrante</th><th>Antes (4 barras)</th><th>RS-Ratio</th><th>Momentum</th></tr>")
            for _, r in T.sort_values("quad").iterrows():
                h.append(f"<tr><td>{r.ativo}</td><td class=l>{r.quad}</td><td class=l>{r.antes}</td><td>{fmt(r.x)}</td><td>{fmt(r.y)}</td></tr>")
            h.append("</table>")
    h.append("<h2>Indicadores técnicos</h2><table><tr><th>Ativo</th><th>Preço</th><th>RSI D</th><th>RSI S</th><th>MM50</th><th>MM200</th><th>Boll</th><th>5d</th><th>ATR</th></tr>")
    L = {k: tecnico(d) for k, d in dados.items()}
    for k, o in L.items():
        cor = "ruim" if o["rsi_d"] >= 70 else "ok" if o["rsi_d"] <= 30 else ""
        h.append(f"<tr><td>{k}</td><td>{fmt(o['preco'])}</td><td class={cor}>{fmt(o['rsi_d'],1)}</td><td>{fmt(o['rsi_w'],1)}</td><td>{fmt(o['sma50'])}</td><td>{fmt(o['sma200'])}</td><td>{fmt(o['boll'])}</td><td>{fmt(o['ret5']*100,1)}%</td><td>{fmt(o['atr'])}</td></tr>")
        h.append(f"<tr><td colspan=9 class='l n'>{o['leitura']} (dado de {o['data']})</td></tr>")
    h.append("</table>")
    if falhas: h.append(f"<p class=n>Sem dados: {', '.join(falhas)}</p>")
    h.append("<p class=n>Boll: −1 = banda inferior, +1 = superior. Regra RSI→rotação M2ST34/BITH11 testada em backtest semanal.</p></body></html>")
    return "".join(h)

if __name__ == "__main__":
    csvdir = sys.argv[sys.argv.index("--csv")+1] if "--csv" in sys.argv else None
    dados, falhas = carregar(csvdir)
    if BENCH not in dados: sys.exit("Sem dados do benchmark (%s). Verifique a internet/yfinance." % BENCH)
    nome = f"relatorio_{dt.datetime.now():%Y-%m-%d_%H%M}.html"
    open(nome, "w", encoding="utf-8").write(html(dados, falhas))
    print("Gerado:", nome, "| sem dados:", falhas or "nenhum")
