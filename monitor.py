#!/usr/bin/env python3
"""Monitor de mercado por categoria (categorias/<nome>/config.json).
Gera, para cada categoria: dados/*.csv e relatorio.html (RSI, médias, Bollinger, ATR, 30 min e RRG).
Uso:  python monitor.py --salvar            baixa tudo e gera os relatórios
      python monitor.py --csv                só recalcula a partir dos CSVs salvos
      python monitor.py --cat brasil         roda só uma categoria"""
import sys, os, json, glob, datetime as dt, urllib.request
import numpy as np, pandas as pd

SALVAR = "--salvar" in sys.argv
RAIZ = os.path.dirname(os.path.abspath(__file__))

# ---------- indicadores ----------
def rsi(c, n=14):
    d = c.diff(); up = d.clip(lower=0); dn = -d.clip(upper=0)
    au = up.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    return 100 - 100/(1 + au/ad)

def atr(d, n=14):
    c = d.close
    tr = pd.concat([d.high-d.low, (d.high-c.shift()).abs(), (d.low-c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean().iloc[-1]

def semanal(d, fim): return d.resample("W-" + fim).agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()

def tecnico(d, fim, ref):
    c = d.close; w = semanal(d, fim)
    o = dict(preco=c.iloc[-1], data=d.index[-1].date(), n=len(c), atr=atr(d),
             rsi_d=rsi(c).iloc[-1], rsi_w=rsi(w.close).iloc[-1] if len(w) > 15 else np.nan)
    for n in (9, 21): o[f"ema{n}"] = c.ewm(span=n, adjust=False).mean().iloc[-1]
    for n in (50, 200): o[f"sma{n}"] = c.rolling(n).mean().iloc[-1] if len(c) >= n else np.nan
    m, s = c.rolling(20).mean().iloc[-1], c.rolling(20).std().iloc[-1]
    o["boll"] = (c.iloc[-1]-m)/(2*s) if s else np.nan
    for k, n in (("r7", 7), ("r30", 30), ("r90", 90)):
        o[k] = c.iloc[-1]/c.iloc[-1-n]-1 if len(c) > n+1 else np.nan
    o["dd"] = c.iloc[-1]/c.tail(252).max()-1
    o["corr"] = np.nan
    if ref is not None:
        j = pd.concat([c.pct_change(), ref.pct_change()], axis=1, sort=True).dropna().tail(30)
        if len(j) > 15: o["corr"] = j.iloc[:, 0].corr(j.iloc[:, 1])
    t = ["sobrecomprado" if o["rsi_d"] >= 70 else "sobrevendido" if o["rsi_d"] <= 30 else "RSI neutro"]
    if o["sma50"] == o["sma50"]: t.append("acima MM50" if o["preco"] > o["sma50"] else "abaixo MM50")
    if o["sma200"] == o["sma200"]: t.append("acima MM200" if o["preco"] > o["sma200"] else "abaixo MM200")
    t.append("MM9 acima MM21" if o["ema9"] > o["ema21"] else "MM9 abaixo MM21")
    o["leitura"] = " · ".join(t); return o

def tec30(m):
    c = m.close; mm, sd = c.rolling(20).mean().iloc[-1], c.rolling(20).std().iloc[-1]
    return dict(preco=c.iloc[-1], t=m.index[-1], rsi=rsi(c).iloc[-1],
        e9=c.ewm(span=9, adjust=False).mean().iloc[-1], e21=c.ewm(span=21, adjust=False).mean().iloc[-1],
        s50=c.rolling(50).mean().iloc[-1], s200=c.rolling(200).mean().iloc[-1] if len(c) >= 200 else np.nan,
        boll=(c.iloc[-1]-mm)/(2*sd) if sd else np.nan, atr=atr(m),
        r1=c.iloc[-1]/c.iloc[-14]-1 if len(c) > 14 else np.nan)

# ---------- RRG ----------
def rrg(a, b, n, s, m):
    rs = (a/b).dropna()
    rsr = (100 + (rs/rs.rolling(n).mean() - 1)*100).ewm(span=s, adjust=False).mean()
    mom = 100 + (rsr/rsr.shift(m) - 1)*100
    return pd.DataFrame({"x": rsr, "y": mom}).dropna()

def quadrante(x, y):
    return ("Leading" if y >= 100 else "Weakening") if x >= 100 else ("Improving" if y >= 100 else "Lagging")

def tabela_rrg(series, bench, modo, fim):
    n, s, m = (20, 5, 5) if modo == "d" else (10, 3, 4)
    b = bench if modo == "d" else semanal(pd.DataFrame({"open": bench, "high": bench, "low": bench, "close": bench}), fim).close
    out = []
    for k, d in series.items():
        a = d.close if modo == "d" else semanal(d, fim).close
        r = rrg(a, b, n, s, m)
        if len(r) < 6: continue
        out.append(dict(ativo=k, x=r.x.iloc[-1], y=r.y.iloc[-1], quad=quadrante(r.x.iloc[-1], r.y.iloc[-1]),
                        antes=quadrante(r.x.iloc[-4], r.y.iloc[-4]), trilha=list(zip(r.x.iloc[-5:], r.y.iloc[-5:]))))
    return pd.DataFrame(out)

def svg_rrg(df):
    if df.empty: return ""
    xs = [p[0] for t in df.trilha for p in t]; ys = [p[1] for t in df.trilha for p in t]
    ext = lambda v: max(abs(min(v)-100), abs(max(v)-100), 1.5)*1.15
    ex, ey = ext(xs), ext(ys); W = H = 520
    X = lambda v: (v-100+ex)/(2*ex)*W; Y = lambda v: H-(v-100+ey)/(2*ey)*H
    s = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;max-width:560px;background:#fff;border:1px solid #ccc;border-radius:8px">',
         f'<rect x="{W/2}" y="0" width="{W/2}" height="{H/2}" fill="#e6f4ea"/><rect x="{W/2}" y="{H/2}" width="{W/2}" height="{H/2}" fill="#fff8e1"/>'
         f'<rect x="0" y="{H/2}" width="{W/2}" height="{H/2}" fill="#fdecea"/><rect x="0" y="0" width="{W/2}" height="{H/2}" fill="#e8f0fe"/>']
    for t, (px, py) in {"Leading": (W-70, 18), "Weakening": (W-85, H-8), "Lagging": (8, H-8), "Improving": (8, 18)}.items():
        s.append(f'<text x="{px}" y="{py}" font-size="12" fill="#666">{t}</text>')
    for _, r in df.iterrows():
        pts = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in r.trilha)
        s.append(f'<polyline points="{pts}" fill="none" stroke="#888" stroke-width="1.2"/>')
        s.append(f'<circle cx="{X(r.x):.1f}" cy="{Y(r.y):.1f}" r="4" fill="#1a56db"/><text x="{X(r.x)+6:.1f}" y="{Y(r.y)-4:.1f}" font-size="11">{r.ativo}</text>')
    s.append("</svg>"); return "".join(s)

# ---------- dados ----------
CACHE = {}

def limpa_yahoo(d, iv):
    if d is None or len(d) == 0: return None
    if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
    d = d.rename(columns=str.lower)
    if not set(["open","high","low","close"]) <= set(d.columns): return None
    d = d[["open","high","low","close"]].dropna()
    if d.empty: return None
    d.index = pd.to_datetime(d.index)
    d.index = (d.index.tz_convert("UTC") if d.index.tz is not None else d.index).tz_localize(None)
    if iv == "1d": d.index = d.index.normalize()
    return d

def prefetch(tickers, iv):
    """Baixa vários tickers numa só chamada (muito mais rápido que um por um)."""
    import yfinance as yf
    tickers = sorted(set(tickers))
    if not tickers: return
    per = "5y" if iv == "1d" else "59d"
    for i in range(0, len(tickers), 40):
        lote = tickers[i:i+40]
        try:
            d = yf.download(lote, period=per, interval=iv, auto_adjust=False, progress=False, group_by="ticker", threads=True)
        except Exception as e:
            print("lote", iv, e); continue
        for t in lote:
            try: sub = d[t] if len(lote) > 1 else d
            except Exception: continue
            CACHE[(t, iv)] = limpa_yahoo(sub.copy(), iv)

def yahoo(tk, iv):
    if (tk, iv) in CACHE: return CACHE[(tk, iv)]
    import yfinance as yf
    d = yf.download(tk, period="5y" if iv == "1d" else "59d", interval=iv, auto_adjust=False, progress=False)
    return limpa_yahoo(d, iv)

def kraken(par, iv):
    url = f"https://api.kraken.com/0/public/OHLC?pair={par}&interval={1440 if iv == '1d' else 30}"
    r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
    if r.get("error"): return None
    k = [v for kk, v in r["result"].items() if kk != "last"][0]
    d = pd.DataFrame(k, columns=["t","open","high","low","close","vwap","vol","n"]).astype(float)
    d.index = pd.to_datetime(d.t, unit="s")
    if iv == "1d": d.index = d.index.normalize()
    return d[["open","high","low","close"]]

def baixar(yts, kpar, iv):
    for t in yts:
        try: d = yahoo(t, iv)
        except Exception as e: print("yahoo", t, iv, e); d = None
        if d is not None and len(d) > 40: return d, "Yahoo " + t
    if kpar:
        try:
            d = kraken(kpar, iv)
            if d is not None and len(d) > 40: return d, "Kraken " + kpar
        except Exception as e: print("kraken", kpar, iv, e)
    return None, ""

def ler(pasta, nome, suf):
    f = os.path.join(pasta, f"{nome}_{suf}.csv")
    if not os.path.exists(f): return None
    d = pd.read_csv(f); d.index = pd.to_datetime(d.time, unit="s")
    if suf == "1D": d.index = d.index.normalize()
    return d[["open","high","low","close"]]

def gravar(d, pasta, nome, suf):
    os.makedirs(pasta, exist_ok=True)
    o = d.copy(); o.insert(0, "time", o.index.astype("datetime64[s]").astype("int64"))
    o.to_csv(os.path.join(pasta, f"{nome}_{suf}.csv"), index=False)

def limpar(d): return d[~d.index.duplicated(keep="last")].sort_index()

def especificar(cfg):
    suf = cfg.get("sufixo", ""); A = cfg.get("ativos", {}); out = {}
    if isinstance(A, list): A = {t: {} for t in A}
    for t, v in A.items():
        if isinstance(v, str): v = {"grupo": v}
        v = dict(v); v.setdefault("yahoo", [t + suf]); out[t] = v
    return out

def carregar(cfg, pasta, offline):
    A = especificar(cfg); dados, d30, fonte, falhas = {}, {}, {}, []
    if not offline:
        tks = [v["yahoo"][0] for v in A.values()] + [y[0] for y in cfg.get("benchmarks", {}).values()]
        prefetch(tks, "1d"); prefetch(tks, "30m")
    def um(nome, yts, kpar, bench=False):
        pre = "BENCH_" if bench else ""
        if offline: d, f, m = ler(pasta, pre+nome, "1D"), "csv", ler(pasta, pre+nome, "30m")
        else: d, f = baixar(yts, kpar, "1d"); m, _ = baixar(yts, kpar, "30m") if not bench else (None, "")
        if d is None or len(d) < 40: falhas.append(nome); return None, None, ""
        d = limpar(d); m = limpar(m) if m is not None and len(m) > 60 else None
        if SALVAR and not offline:
            gravar(d, pasta, pre+nome, "1D")
            if m is not None: gravar(m, pasta, pre+nome, "30m")
        return d, m, f
    for nome, v in A.items():
        d, m, f = um(nome, v["yahoo"], v.get("kraken"))
        if d is not None:
            dados[nome] = d; fonte[nome] = f
            if m is not None: d30[nome] = m
    bench = {}
    for nome, yts in cfg.get("benchmarks", {}).items():
        kp = yts[1] if len(yts) > 1 and nome == "BTC" else None
        d, _, f = um(nome, yts[:1] if kp else yts, kp, bench=True)
        if d is not None: bench[nome] = d
    return A, dados, d30, bench, fonte, falhas

# ---------- relatório ----------
def fmt(v, n=2):
    if v != v: return "–"
    return f"{v:,.{n}f}" if abs(v) >= 1 else f"{v:.4f}"
def pct(v): return "–" if v != v else f"{v*100:+.1f}%"
CSS = "body{font-family:system-ui;margin:12px;max-width:980px}table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}th,td{border-bottom:1px solid #ddd;padding:5px 6px;text-align:right}th:first-child,td:first-child,td.l{text-align:left}th{background:#f3f4f6}.ok{color:#0a7d33}.ruim{color:#b3261e}.n{color:#666;font-size:12px}.sc{overflow-x:auto}"

def relatorio(cfg, A, dados, d30, bench, fonte, falhas):
    agora = dt.datetime.now().strftime("%d/%m/%Y %H:%M"); fim = cfg.get("semana", "FRI")
    gb = cfg.get("grupo_benchmark", {}); pad = cfg.get("benchmark_padrao")
    def refde(k):
        b = gb.get(A[k].get("grupo", ""), pad) if A.get(k) else pad
        r = bench.get(b) if b in bench else dados.get(b)
        return (r.close if r is not None else None), b
    h = [f"<html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><style>{CSS}</style></head><body><h1>{cfg['nome']} · {agora}</h1>",
         "<p class=n>Fechamento diário. Boll: −1 = banda inferior, +1 = superior. Corr = correlação diária com o benchmark, 30 dias.</p>",
         f"<div class=sc><table><tr><th>Ativo</th><th>Preço {cfg['moeda']}</th><th>7d</th><th>30d</th><th>90d</th><th>vs máx 12m</th><th>RSI D</th><th>RSI S</th><th>MM50</th><th>MM200</th><th>Boll</th><th>ATR</th><th>Corr</th></tr>"]
    for k, d in dados.items():
        ref, bn = refde(k); o = tecnico(d, fim, None if bn == k else ref)
        cor = "ruim" if o["rsi_d"] >= 70 else "ok" if o["rsi_d"] <= 30 else ""
        h.append(f"<tr><td><b>{k}</b></td><td>{fmt(o['preco'])}</td><td>{pct(o['r7'])}</td><td>{pct(o['r30'])}</td><td>{pct(o['r90'])}</td><td>{pct(o['dd'])}</td><td class={cor}>{fmt(o['rsi_d'],1)}</td><td>{fmt(o['rsi_w'],1)}</td><td>{fmt(o['sma50'])}</td><td>{fmt(o['sma200'])}</td><td>{fmt(o['boll'])}</td><td>{fmt(o['atr'])}</td><td>{fmt(o['corr'])}</td></tr>")
        h.append(f"<tr><td colspan=13 class='l n'>{o['leitura']} · dado de {o['data']} · {o['n']} dias · {fonte.get(k,'')} · ref {bn}{(' · ' + A[k]['setor']) if A.get(k, {}).get('setor') else ''}{' · reserva' if A.get(k, {}).get('reserva') else ''}{(' · BDR ' + A[k]['bdr']) if A.get(k, {}).get('bdr') else ''}</td></tr>")
    h.append("</table></div>")
    if d30:
        h.append("<h2>30 minutos</h2><div class=sc><table><tr><th>Ativo</th><th>Preço</th><th>RSI 30m</th><th>MM9</th><th>MM21</th><th>MM50</th><th>MM200</th><th>Boll</th><th>ATR</th><th>Última candle (UTC)</th></tr>")
        for k, m in d30.items():
            o = tec30(m); cor = "ruim" if o["rsi"] >= 70 else "ok" if o["rsi"] <= 30 else ""
            h.append(f"<tr><td><b>{k}</b></td><td>{fmt(o['preco'])}</td><td class={cor}>{fmt(o['rsi'],1)}</td><td>{fmt(o['e9'])}</td><td>{fmt(o['e21'])}</td><td>{fmt(o['s50'])}</td><td>{fmt(o['s200'])}</td><td>{o['boll']:.2f}</td><td>{fmt(o['atr'])}</td><td>{o['t']:%d/%m %H:%M}</td></tr>")
        h.append("</table></div>")
    if cfg.get("rrg"):
        grupos = {}
        for k in dados:
            ref, bn = refde(k)
            if ref is not None and bn != k: grupos.setdefault(bn, {})[k] = dados[k]
        for bn, ser in grupos.items():
            ref = refde(next(iter(ser)))[0]
            for modo, nome in (("w", "semanal"), ("d", "diário")):
                T = tabela_rrg(ser, ref, modo, fim)
                if T.empty: continue
                h.append(f"<h2>RRG {nome} · referência {bn}</h2>" + svg_rrg(T) + "<div class=sc><table><tr><th>Ativo</th><th>Quadrante</th><th>Antes (4 barras)</th><th>RS-Ratio</th><th>Momentum</th></tr>")
                for _, r in T.sort_values("quad").iterrows():
                    h.append(f"<tr><td>{r.ativo}</td><td class=l>{r.quad}</td><td class=l>{r.antes}</td><td>{fmt(r.x)}</td><td>{fmt(r.y)}</td></tr>")
                h.append("</table></div>")
    if falhas: h.append(f"<p class=ruim>Sem dados: {', '.join(falhas)}</p>")
    if not dados: h.append("<p>Nenhum ativo configurado nesta categoria ainda.</p>")
    return "".join(h) + "</body></html>"



# ---------- eventos: datas de resultados ----------
def _datas_yahoo(tk):
    import yfinance as yf
    t = yf.Ticker(tk); hoje = pd.Timestamp.today().normalize(); cand = []
    try:
        cal = t.calendar
        v = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if v: cand += [pd.Timestamp(x) for x in (v if isinstance(v, (list, tuple)) else [v])]
    except Exception: pass
    if not cand:
        try:
            ed = t.get_earnings_dates(limit=8)
            if ed is not None and len(ed): cand += [pd.Timestamp(i).tz_localize(None) for i in ed.index]
        except Exception: pass
    fut = sorted(x.normalize() for x in cand if x.normalize() >= hoje - pd.Timedelta(days=1))
    return fut[0] if fut else None

def atualizar_eventos(forcar=False):
    import time
    base = os.path.join(RAIZ, "categorias")
    for cdir in sorted(glob.glob(os.path.join(base, "*", "config.json"))):
        pasta = os.path.dirname(cdir); cfg = json.load(open(cdir, encoding="utf-8"))
        if cfg.get("sem_eventos") or not cfg.get("ativos"): continue
        f = os.path.join(pasta, "eventos.json")
        if os.path.exists(f) and not forcar and time.time() - os.path.getmtime(f) < 20*3600: continue
        out = {}
        for nome, v in especificar(cfg).items():
            try: d = _datas_yahoo(v["yahoo"][0])
            except Exception as e: print("evento", nome, e); d = None
            if d is not None: out[nome] = d.strftime("%Y-%m-%d")
            time.sleep(0.2)
        json.dump(out, open(f, "w"), indent=1); print(os.path.basename(pasta), "eventos:", len(out))

def ler_eventos(pasta):
    ev = {}
    for nome in ("eventos.json", "resultados_manual.json"):   # o manual vence
        f = os.path.join(pasta, nome)
        if os.path.exists(f):
            try: ev.update(json.load(open(f, encoding="utf-8")))
            except Exception as e: print(nome, e)
    return ev

def cor_dias(n):
    if n <= 3: return "background:#c62828;color:#fff"
    if n <= 7: return "background:#f4a261"
    if n <= 14: return "background:#fff3b0"
    return ""

# ---------- painel resumo (todas as categorias) ----------
def cor_rsi(v):
    if v != v: return ""
    if v <= 30: return "background:#1b8a3a;color:#fff"
    if v <= 40: return "background:#cdeed6"
    if v >= 70: return "background:#c62828;color:#fff"
    if v >= 60: return "background:#f9d3d3"
    return ""

def cor_var(v):
    if v != v: return ""
    return "color:#0a7d33" if v > 0 else "color:#b3261e" if v < 0 else ""

def linha_painel(nome, d, fim, extra):
    c = d.close
    if len(c) < 20: return None
    w = semanal(d, fim)
    rd = rsi(c).iloc[-1]; rw = rsi(w.close).iloc[-1] if len(w) > 15 else np.nan
    dia = c.iloc[-1]/c.iloc[-2]-1
    sem = w.close.iloc[-1]/w.close.iloc[-2]-1 if len(w) > 1 else np.nan
    sig = []
    if rd <= 30: sig.append("sobrevenda D")
    if rd >= 70: sig.append("sobrecompra D")
    if rw == rw and rw <= 30: sig.append("sobrevenda S")
    if rw == rw and rw >= 70: sig.append("sobrecompra S")
    return dict(nome=nome, preco=c.iloc[-1], dia=dia, sem=sem, rd=rd, rw=rw, data=d.index[-1], sinal=" + ".join(sig), **extra)

def res_cell(r, com_res):
    if not com_res: return ""
    if not r.get("res"): return "<td class=n>–</td>"
    dd, n = r["res"]; return f"<td style='{cor_dias(n)}'>{dd:%d/%m} ({n}d)</td>"

def macro_html():
    f = os.path.join(RAIZ, "macro.json")
    if not os.path.exists(f): return ""
    hoje = pd.Timestamp.today().normalize(); L = []
    for e in json.load(open(f, encoding="utf-8")):
        d = pd.Timestamp(e["data"]); n = (d - hoje).days
        if n >= 0: L.append((d, n, e))
    if not L: return ""
    L.sort(key=lambda x: x[0])
    h = ["<h2>Calendário: juros, inflação e feriados <span class=n>· cores: ≤3 dias vermelho, ≤7 laranja, ≤14 amarelo</span></h2><div class=sc><table><tr><th>Data</th><th>Faltam</th><th>Região</th><th>Evento</th></tr>"]
    for d, n, e in L:
        h.append(f"<tr><td style='{cor_dias(n)}'>{d:%d/%m/%Y}</td><td style='{cor_dias(n)}'>{n}d</td><td class=l>{e['regiao']}</td><td class=l>{e['evento']}</td></tr>")
    h.append("</table></div><p class=n>Datas de resultados de empresas vêm do Yahoo (nos EUA são confiáveis; na B3 muitas vêm em branco). Para fixar uma data na B3, edite categorias/brasil/resultados_manual.json, por exemplo {\"PETR4\": \"2027-02-26\"}.</p>")
    return "".join(h)

def painel():
    import html as H
    base = os.path.join(RAIZ, "categorias"); secoes = []; total_s = total_c = 0
    for cdir in sorted(glob.glob(os.path.join(base, "*", "config.json"))):
        pasta = os.path.dirname(cdir); cfg = json.load(open(cdir, encoding="utf-8"))
        A = especificar(cfg); L = []; EV = ler_eventos(pasta)
        hoje = pd.Timestamp.today().normalize()
        for nome, v in A.items():
            d = ler(os.path.join(pasta, "dados"), nome, "1D")
            if d is None: continue
            r = linha_painel(nome, limpar(d), cfg.get("semana", "FRI"), dict(info=" · ".join(x for x in [v.get("setor", ""), ("BDR " + v["bdr"]) if v.get("bdr") else "", v.get("grupo", ""), "reserva" if v.get("reserva") else ""] if x), moeda=cfg.get("moeda", "")))
            if r:
                r["res"] = None
                if nome in EV:
                    try:
                        dd = pd.Timestamp(EV[nome]); n = (dd - hoje).days
                        if n >= 0: r["res"] = (dd, n)
                    except Exception: pass
                L.append(r)
        if L: secoes.append((cfg["nome"], L, not cfg.get("sem_eventos")))
    css = ("body{font-family:system-ui;margin:10px;max-width:1000px}h1{font-size:20px}h2{font-size:16px;margin:22px 0 4px}"
           "table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid #ddd;padding:5px 6px;text-align:right;white-space:nowrap}"
           "th{background:#f3f4f6;cursor:pointer;position:sticky;top:0}th:first-child,td:first-child,td.l{text-align:left}.n{color:#666;font-size:12px}.sc{overflow-x:auto}"
           ".leg span{display:inline-block;padding:2px 8px;margin:2px;border-radius:4px;font-size:12px}")
    h = [f"<html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Painel RSI</title><style>{css}</style></head><body>",
         f"<h1>Painel RSI · atualizado {dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))):%d/%m/%Y %H:%M} (Brasília)</h1>",
         "<div class=leg><span style='background:#1b8a3a;color:#fff'>RSI ≤ 30 sobrevenda</span><span style='background:#cdeed6'>30–40</span><span style='background:#f9d3d3'>60–70</span><span style='background:#c62828;color:#fff'>RSI ≥ 70 sobrecompra</span></div>",
         "<p class=n>D = candle diário, S = candle semanal (RSI de 14 períodos). Variação do dia = último preço contra o fechamento anterior; da semana = contra o fechamento da semana anterior. A candle do momento ainda está em andamento. Clique no título da coluna para ordenar.</p>"]
    for nome, L, com_res in secoes:
        ns = sum(1 for r in L if r["rd"] <= 30); nc = sum(1 for r in L if r["rd"] >= 70)
        h.append(f"<h2>{H.escape(nome)} <span class=n>· {len(L)} ativos · {ns} em sobrevenda diária · {nc} em sobrecompra diária</span></h2><div class=sc><table class=s><tr><th>Ativo</th><th>Preço</th><th>Dia</th><th>Semana</th><th>RSI D</th><th>RSI S</th><th>Sinal</th><th>Dado de</th>" + ("<th>Resultado</th>" if com_res else "") + "<th>Info</th></tr>")
        for r in sorted(L, key=lambda r: r["rd"]):
            h.append(f"<tr><td><b>{H.escape(r['nome'])}</b></td><td>{fmt(r['preco'])}</td><td style='{cor_var(r['dia'])}'>{pct(r['dia'])}</td><td style='{cor_var(r['sem'])}'>{pct(r['sem'])}</td>"
                     f"<td style='{cor_rsi(r['rd'])}'>{fmt(r['rd'],1)}</td><td style='{cor_rsi(r['rw'])}'>{fmt(r['rw'],1)}</td><td class=l>{r['sinal']}</td><td>{r['data']:%d/%m}</td>{res_cell(r, com_res)}<td class='l n'>{H.escape(r['info'])}</td></tr>")
        h.append("</table></div>")
    if not secoes: h.append("<p>Sem dados coletados ainda.</p>")
    h.append(macro_html())
    h.append("""<script>document.querySelectorAll('table.s').forEach(t=>{t.querySelectorAll('th').forEach((th,i)=>{th.onclick=()=>{const rows=[...t.rows].slice(1);const dir=th.dataset.d=th.dataset.d=='1'?-1:1;rows.sort((a,b)=>{const x=a.cells[i].innerText.replace('%','').replace(/,/g,''),y=b.cells[i].innerText.replace('%','').replace(/,/g,'');const nx=parseFloat(x),ny=parseFloat(y);return (isNaN(nx)||isNaN(ny)?x.localeCompare(y):nx-ny)*dir});rows.forEach(r=>t.appendChild(r))}})})</script></body></html>""")
    open(os.path.join(RAIZ, "painel.html"), "w", encoding="utf-8").write("".join(h))
    print("painel.html gerado:", sum(len(x[1]) for x in secoes), "ativos")

if __name__ == "__main__":
    if "--eventos" in sys.argv: atualizar_eventos("--forcar" in sys.argv); sys.exit(0)
    if "--painel" in sys.argv: painel(); sys.exit(0)
    offline = "--csv" in sys.argv
    so = sys.argv[sys.argv.index("--cat")+1] if "--cat" in sys.argv else None
    base = os.path.join(RAIZ, "categorias")
    for cdir in sorted(glob.glob(os.path.join(base, "*", "config.json"))):
        pasta_cat = os.path.dirname(cdir); nome = os.path.basename(pasta_cat)
        if so and so != nome: continue
        cfg = json.load(open(cdir, encoding="utf-8"))
        if not cfg.get("ativos"): print(nome, ": sem ativos, pulando"); continue
        A, dados, d30, bench, fonte, falhas = carregar(cfg, os.path.join(pasta_cat, "dados"), offline)
        if not dados: print(nome, ": nenhum dado", falhas); continue
        open(os.path.join(pasta_cat, "relatorio.html"), "w", encoding="utf-8").write(relatorio(cfg, A, dados, d30, bench, fonte, falhas))
        print(nome, "ok | sem dados:", falhas or "nenhum")
