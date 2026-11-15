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
    import yfinance as yf, tempfile
    try: yf.set_tz_cache_location(tempfile.mkdtemp())
    except Exception: pass
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
        import time
        for t in lote:      # quem falhou no lote (ex.: "database is locked") é baixado de novo, um por vez
            x = CACHE.get((t, iv))
            if x is None or len(x) < 5:
                time.sleep(1)
                try: CACHE[(t, iv)] = limpa_yahoo(yf.download(t, period=per, interval=iv, auto_adjust=False, progress=False, threads=False), iv)
                except Exception as e: print("retry", t, iv, e)

def yahoo(tk, iv):
    if (tk, iv) in CACHE: return CACHE[(tk, iv)]
    import yfinance as yf
    d = yf.download(tk, period="5y" if iv == "1d" else "59d", interval=iv, auto_adjust=False, progress=False)
    return limpa_yahoo(d, iv)

def kraken(par, iv):
    url = f"https://api.kraken.com/0/public/OHLC?pair={par}&interval={ {'1d': 1440, '30m': 30, '15m': 15, '1h': 60, '4h': 240}.get(iv, 30) }"
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

def rotulo(nome, v=None):
    """nome exibido: '**' nas 2 melhores do setor (Brasil) e 'TICKER/BDR' nos EUA"""
    v = v or {}
    return ("** " if v.get("destaque") else "") + nome + (("/" + v["bdr"]) if v.get("bdr") else "")

def especificar(cfg):
    suf = cfg.get("sufixo", ""); A = cfg.get("ativos", {}); out = {}
    if isinstance(A, list): A = {t: {} for t in A}
    for t, v in A.items():
        if isinstance(v, str): v = {"grupo": v}
        v = dict(v); v.setdefault("yahoo", [t + suf]); out[t] = v
    return out

def carregar(cfg, pasta, offline):
    A = especificar(cfg); dados, d30, fonte, falhas = {}, {}, {}, []
    tempos = cfg.get("tempos", []); extra = {}
    if not offline:
        tks = [v["yahoo"][0] for v in A.values()] + [y[0] for y in cfg.get("benchmarks", {}).values()]
        prefetch(tks, "1d"); prefetch(tks, "30m")
        for tf in ("15m", "1h"):
            if tf in tempos or ("4h" in tempos and tf == "1h"): prefetch([v["yahoo"][0] for v in A.values()], tf)
    def um(nome, yts, kpar, bench=False):
        pre = "BENCH_" if bench else ""
        if offline: d, f, m = ler(pasta, pre+nome, "1D"), "csv", ler(pasta, pre+nome, "30m")
        else: d, f = baixar(yts, kpar, "1d"); m, _ = baixar(yts, kpar, "30m") if not bench else (None, "")
        if d is None or len(d) < 40: falhas.append(nome); return None, None, ""
        d = limpar(d); m = limpar(m) if m is not None and len(m) > 60 else None
        if tempos and not bench and not offline:
            for tf in ("15m", "1h"):
                if tf in tempos or ("4h" in tempos and tf == "1h"):
                    try:
                        x, _ = baixar(yts, kpar, tf)
                        if x is not None and len(x) > 40: extra[(nome, tf)] = limpar(x)
                    except Exception as e: print("tempo", nome, tf, e)
            if "4h" in tempos and (nome, "1h") in extra:
                extra[(nome, "4h")] = extra[(nome, "1h")].resample("4h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        if SALVAR and not offline:
            gravar(d, pasta, pre+nome, "1D")
            if m is not None: gravar(m, pasta, pre+nome, "30m")
            for (n_, tf), x in list(extra.items()):
                if n_ == nome and tf in tempos: gravar(x, pasta, nome, tf)
        return d, m, f
    for nome, v in A.items():
        d, m, f = um(nome, v["yahoo"], v.get("kraken"))
        if d is not None:
            dados[nome] = d; fonte[nome] = f
            if m is not None: d30[nome] = m
    if not offline:
        import time
        for nome in [x for x in falhas if x in A]:      # nova tentativa (erros passageiros do Yahoo)
            time.sleep(3); falhas.remove(nome); d, m, f = um(nome, A[nome]["yahoo"], A[nome].get("kraken"))
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
        h.append(f"<tr><td><b>{rotulo(k, A.get(k))}</b></td><td>{fmt(o['preco'])}</td><td>{pct(o['r7'])}</td><td>{pct(o['r30'])}</td><td>{pct(o['r90'])}</td><td>{pct(o['dd'])}</td><td class={cor}>{fmt(o['rsi_d'],1)}</td><td>{fmt(o['rsi_w'],1)}</td><td>{fmt(o['sma50'])}</td><td>{fmt(o['sma200'])}</td><td>{fmt(o['boll'])}</td><td>{fmt(o['atr'])}</td><td>{fmt(o['corr'])}</td></tr>")
        h.append(f"<tr><td colspan=13 class='l n'>{o['leitura']} · dado de {o['data']} · {o['n']} dias · {fonte.get(k,'')} · ref {bn}{(' · ' + A[k]['setor']) if A.get(k, {}).get('setor') else ''}{(' · BDR ' + A[k]['bdr']) if A.get(k, {}).get('bdr') else ''}</td></tr>")
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




def _fresco(pasta, chave, horas):
    """True se esta rotina rodou há menos de `horas` (guardado em _meta.json, pois o mtime muda a cada checkout do GitHub)"""
    try:
        t = json.load(open(os.path.join(pasta, "_meta.json")))[chave]
        return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(t)).total_seconds() < horas * 3600
    except Exception: return False

def _marcar(pasta, chave):
    f = os.path.join(pasta, "_meta.json")
    try: meta = json.load(open(f))
    except Exception: meta = {}
    meta[chave] = dt.datetime.now(dt.timezone.utc).isoformat(); json.dump(meta, open(f, "w"))

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
        if os.path.exists(f) and not forcar and _fresco(pasta, "eventos", 20): continue
        out = {}
        for nome, v in especificar(cfg).items():
            try: d = _datas_yahoo(v["yahoo"][0])
            except Exception as e: print("evento", nome, e); d = None
            if d is not None: out[nome] = d.strftime("%Y-%m-%d")
            time.sleep(0.2)
        json.dump(out, open(f, "w"), indent=1); _marcar(pasta, "eventos"); print(os.path.basename(pasta), "eventos:", len(out))

def ler_eventos(pasta):
    """datas de resultado: estimada (4T do ano anterior +52 semanas, marcada com ~) < Yahoo (só se bater com a estimativa, ±45 dias) < manual"""
    def j(nome):
        f = os.path.join(pasta, nome)
        try: return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
        except Exception as e: print(nome, e); return {}
    est, yah, man = j("resultados_estimados.json"), j("eventos.json"), j("resultados_manual.json")
    ev = {k: "~" + v for k, v in est.items()}
    for k, v in yah.items():
        if k not in est: ev[k] = v
        else:
            try:
                if abs((pd.Timestamp(v) - pd.Timestamp(est[k])).days) <= 45: ev[k] = v
            except Exception: pass
    ev.update(man)
    return ev

def cor_dias(n):
    if n <= 3: return "background:#c62828;color:#fff"
    if n <= 7: return "background:#f4a261"
    if n <= 14: return "background:#fff3b0"
    return ""


# ---------- juros (EUA via FRED, Brasil via Tesouro Direto) ----------
TESOURO_DATASET = "df56aa42-484a-4a59-8184-7676580c81e3"
def tesouro_url():
    """acha o link atual do CSV pela API do portal (o link muda de vez em quando)"""
    import urllib.request
    try:
        j = json.load(urllib.request.urlopen(f"https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show?id={TESOURO_DATASET}", timeout=60))
        for r in j["result"]["resources"]:
            if r["url"].lower().endswith("precotaxatesourodireto.csv"): return r["url"]
    except Exception as e: print("tesouro api:", e)
    return f"https://www.tesourotransparente.gov.br/ckan/dataset/{TESOURO_DATASET}/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv"

def fred_serie(codigo):
    d = pd.read_csv(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={codigo}")
    d.columns = ["data", "v"]; d["v"] = pd.to_numeric(d.v, errors="coerce")
    d = d.dropna(); d.index = pd.to_datetime(d.data).dt.normalize()
    return d.v[d.index >= pd.Timestamp.today().normalize() - pd.Timedelta(days=900)]

def tesouro_curvas(ler_csv=None):
    """devolve {'pre': DataFrame(index=data, colunas=anos), 'real': ...} com taxa interpolada por vértice"""
    d = (ler_csv or (lambda: pd.read_csv(tesouro_url(), sep=";", decimal=",", encoding="latin-1")))()
    d.columns = [c.strip() for c in d.columns]
    d["base"] = pd.to_datetime(d["Data Base"], dayfirst=True); d["venc"] = pd.to_datetime(d["Data Vencimento"], dayfirst=True)
    d = d[d.base >= pd.Timestamp.today().normalize() - pd.Timedelta(days=900)].copy()
    d["anos"] = (d.venc - d.base).dt.days / 365.25
    d["taxa"] = pd.to_numeric(d["Taxa Compra Manha"], errors="coerce")
    d = d.dropna(subset=["taxa"]); d = d[d.anos > 0.5]
    tipo = d["Tipo Titulo"].str.lower()
    fam = {"pre": d[tipo.str.contains("prefixado")], "real": d[tipo.str.contains("ipca")]}
    out = {}
    for nome, f in fam.items():
        linhas = {}
        for dia, g in f.groupby("base"):
            g = g.sort_values("anos"); x, y = g.anos.values, g.taxa.values
            if len(x) < 2: continue
            linhas[dia] = {a: float(np.interp(a, x, y)) for a in (2, 5, 10, 20, 30) if x[0] - 0.5 <= a <= x[-1] + 1.5}
        out[nome] = pd.DataFrame.from_dict(linhas, orient="index").sort_index()
    return out


def di_curva(n_dias=120, existentes=None):
    """taxa de ajuste do DI1 (B3) interpolada em 2, 5, 10, 20, 30 anos, por data. Só baixa datas novas."""
    from pyield import di1
    datas = [pd.Timestamp(x) for x in di1.datas_disponiveis().to_list()][-n_dias:]
    feitas = set(existentes.index) if existentes is not None else set()
    linhas = {}
    for dia in datas:
        if dia in feitas: continue
        vs = [dia + pd.DateOffset(years=a) for a in (2, 5, 10, 20, 30)]
        try:
            t = di1.interpolar_taxas(datas_referencia=dia.date(), datas_vencimento=[v.date() for v in vs], extrapolar=False).to_list()
        except Exception as e:
            print("DI", dia.date(), e); continue
        linhas[dia] = {a: (x * 100 if x is not None and x == x else np.nan) for a, x in zip((2, 5, 10, 20, 30), t)}
    return pd.DataFrame.from_dict(linhas, orient="index").sort_index()

def coletar_juros(cfg, pasta):
    pasta = os.path.join(pasta, "dados"); ok, falhas = [], []
    curvas = None; cache = {}
    for nome, v in cfg["ativos"].items():
        try:
            if "fred" in v: s_ = fred_serie(v["fred"])
            elif "di" in v:
                if "DI" not in cache:
                    ant = {a: ler(pasta, n, "1D") for a, n in [(vv["di"], n) for n, vv in cfg["ativos"].items() if "di" in vv]}
                    base = next((x for x in ant.values() if x is not None), None)
                    cache["DI"] = (di_curva(existentes=base), ant)
                novo, ant = cache["DI"]; a = v["di"]
                s_ = novo[a].dropna() if a in novo.columns else pd.Series(dtype=float)
                velho = ant.get(a)
                if velho is not None: s_ = pd.concat([velho.close, s_]); s_ = s_[~s_.index.duplicated(keep="last")].sort_index()
            else:
                if curvas is None: curvas = tesouro_curvas()
                fam, anos = v["tesouro"]; s_ = curvas[fam][anos].dropna()
            if len(s_) < 20: raise ValueError("poucos dados")
            df = pd.DataFrame({"open": s_, "high": s_, "low": s_, "close": s_}); df.index = pd.to_datetime(df.index)
            gravar(limpar(df), pasta, nome, "1D"); ok.append(nome)
        except Exception as e:
            falhas.append(nome); print("juros", nome, "erro:", e)
    return ok, falhas

def bp(v): return "–" if v != v else f"{v:+.1f} bp"


# ---------- valor de mercado e ordem por setor ----------
def atualizar_mercado(forcar=False):
    import time, yfinance as yf
    base = os.path.join(RAIZ, "categorias")
    for cdir in sorted(glob.glob(os.path.join(base, "*", "config.json"))):
        pasta = os.path.dirname(cdir); cfg = json.load(open(cdir, encoding="utf-8"))
        if not cfg.get("valor_mercado"): continue
        f = os.path.join(pasta, "mercado.json")
        if os.path.exists(f) and not forcar and _fresco(pasta, "mercado", 20): continue
        out = {}
        for nome, v in especificar(cfg).items():
            cap = None
            for tk in v["yahoo"]:
                try:
                    t = yf.Ticker(tk)
                    try: cap = t.fast_info.get("market_cap")
                    except Exception: cap = None
                    if not cap: cap = t.info.get("marketCap")
                except Exception as e: print("mercado", nome, e)
                if cap: break
            if cap: out[nome] = float(cap)
            time.sleep(0.2)
        json.dump(out, open(f, "w"), indent=1); _marcar(pasta, "mercado"); print(os.path.basename(pasta), "valor de mercado:", len(out))

def ordenar(cfg, pasta, nomes):
    """setores do maior para o menor (pelo maior valor de mercado de cada um); dentro do setor, do maior para o menor"""
    A = especificar(cfg); nomes = list(nomes); idx = {n: i for i, n in enumerate(A)}
    cap = {}
    for arq in ("mercado_reserva.json", "mercado.json"):       # o valor real vence a reserva
        f = os.path.join(pasta, arq)
        if os.path.exists(f):
            try: cap.update({k: float(v) for k, v in json.load(open(f)).items()})
            except Exception: pass
    setor = lambda n: A.get(n, {}).get("setor") or A.get(n, {}).get("grupo") or ""
    c = lambda n: cap.get(n, -1.0)
    if not any(c(n) > 0 for n in nomes):                      # sem valor de mercado: mantém a ordem do config.json
        ordem_setor = {}
        for n in sorted(nomes, key=lambda n: idx.get(n, 9999)): ordem_setor.setdefault(setor(n), len(ordem_setor))
        return sorted(nomes, key=lambda n: (ordem_setor[setor(n)], idx.get(n, 9999)))
    topo = {}
    for n in nomes: topo[setor(n)] = max(topo.get(setor(n), -1.0), c(n))
    return sorted(nomes, key=lambda n: (-topo[setor(n)], setor(n), -c(n), idx.get(n, 9999)))

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

def rsi_mensal(c):
    try: mm = c.resample("ME").last().dropna()
    except Exception: mm = c.resample("M").last().dropna()
    return (rsi(mm).iloc[-1] if len(mm) > 15 else np.nan), len(mm)

def linha_painel(nome, d, fim, extra, juros=False):
    c = d.close
    if len(c) < 20: return None
    w = semanal(d, fim)
    rd = rsi(c).iloc[-1]; rw = rsi(w.close).iloc[-1] if len(w) > 15 else np.nan
    rm, nm = (np.nan, 0) if juros else rsi_mensal(c)
    if juros:
        dia = (c.iloc[-1]-c.iloc[-2])*100
        sem = (w.close.iloc[-1]-w.close.iloc[-2])*100 if len(w) > 1 else np.nan
    else:
        dia = c.iloc[-1]/c.iloc[-2]-1
        sem = w.close.iloc[-1]/w.close.iloc[-2]-1 if len(w) > 1 else np.nan
    sig = []
    if rd <= 30: sig.append("sobrevenda D")
    if rd >= 70: sig.append("sobrecompra D")
    if rw == rw and rw <= 30: sig.append("sobrevenda S")
    if rw == rw and rw >= 70: sig.append("sobrecompra S")
    if rm == rm and rm <= 30: sig.append("sobrevenda M")
    if rm == rm and rm >= 70: sig.append("sobrecompra M")
    return dict(nome=nome, preco=c.iloc[-1], dia=dia, sem=sem, rd=rd, rw=rw, rm=rm, nm=nm, data=d.index[-1], sinal=" + ".join(sig), **extra)

def res_cell(r, com_res):
    if not com_res: return ""
    if not r.get("res"): return "<td class=n>–</td>"
    dd, n, est = r["res"]; return f"<td style='{cor_dias(n)}'>{'~' if est else ''}{dd:%d/%m} ({n}d)</td>"

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
    h.append("</table></div><p class=n>Datas de resultados: nos EUA vêm do Yahoo. Na B3, as marcadas com ~ são estimativas (data do 4T do ano anterior mais 52 semanas), até a empresa publicar o calendário oficial. Para fixar uma data na B3, edite categorias/brasil/resultados_manual.json, por exemplo {\"PETR4\": \"2027-02-26\"}.</p>")
    return "".join(h)

SO_PAINEL = sys.argv[sys.argv.index("--so")+1] if "--so" in sys.argv else None

def calc_ext(d):
    """d: barras de 5 min com prepost, indice em horario de Nova York. Retorna (preco, variacao%, fase, datahora) ou None."""
    d = d.dropna(subset=["Close"]) if "Close" in d.columns else d
    if d is None or len(d) < 2: return None
    idx = d.index; hm = idx.hour * 60 + idx.minute
    reg = (hm >= 570) & (hm < 960)
    if not reg.any(): return None
    ult = idx[-1]; h = ult.hour * 60 + ult.minute
    if 570 <= h < 960: return None
    if h >= 960:
        ref = d.loc[reg & (idx.normalize() == ult.normalize()), "Close"]
        fase = "Pós"
    else:
        ref = d.loc[reg & (idx.normalize() < ult.normalize()), "Close"]
        fase = "Pré"
    if len(ref) == 0: return None
    ref = float(ref.iloc[-1]); p = float(d["Close"].iloc[-1])
    return p, (p / ref - 1) * 100, fase, ult.tz_convert("America/Sao_Paulo").strftime("%d/%m %H:%M")

def atualizar_ext():
    """Preço pré/pós-mercado (EUA) das ações e ETFs americanos; grava ext.json"""
    import yfinance as yf
    tks = {}
    for cat in ("eua", "setores", "macro", "commodities"):
        f = os.path.join(RAIZ, "categorias", cat, "config.json")
        if not os.path.exists(f): continue
        for nome, v in especificar(json.load(open(f, encoding="utf-8"))).items():
            y = v["yahoo"][0]
            if not any(c in y for c in "^=.-"): tks[y] = 1
    out = {}; L = sorted(tks)
    for i in range(0, len(L), 40):
        lote = L[i:i+40]
        try: d = yf.download(lote, period="5d", interval="5m", prepost=True, auto_adjust=False, progress=False, group_by="ticker", threads=False)
        except Exception as e: print("ext lote", e); continue
        for t in lote:
            try:
                sub = d[t].dropna(how="all")
                if sub.index.tz is None: sub.index = sub.index.tz_localize("UTC")
                sub.index = sub.index.tz_convert("America/New_York")
                r = calc_ext(sub)
                if r: out[t] = dict(preco=r[0], var=r[1], fase=r[2], hora=r[3])
            except Exception as e: print("ext", t, e)
    json.dump(out, open(os.path.join(RAIZ, "ext.json"), "w"))
    print("ext.json:", len(out), "de", len(L))

def ext_cell(r):
    e = r.get("ext")
    if not e: return "<td>–</td>"
    return f"<td style='{cor_var(e['var'])}' title='{e['fase']}-mercado, {e['hora']} (Brasília)'>{fmt(e['preco'])} ({e['var']:+.2f}%) <span class=n>{e['fase']} {e['hora'][-5:]}</span></td>"

def rsi_est(c, n=14):
    """Estado do RSI de Wilder para recalcular ao vivo: [fech_ant, ganho_ant, perda_ant, fech, ganho, perda] (barra atual em andamento ou fechada)"""
    d = c.diff(); up = d.clip(lower=0); dn = -d.clip(upper=0)
    ag = up.ewm(alpha=1/n, adjust=False, min_periods=n).mean(); al = dn.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    if len(c) < n + 3 or ag.iloc[-2] != ag.iloc[-2]: return None
    return [float(f"{x:.8g}") for x in (c.iloc[-2], ag.iloc[-2], al.iloc[-2], c.iloc[-1], ag.iloc[-1], al.iloc[-1])]

def mensal_serie(c):
    try: return c.resample("ME").last().dropna()
    except Exception: return c.resample("M").last().dropna()

TF_SEG = {"15m": 900, "30m": 1800, "1h": 3600, "4h": 14400}

def painel():
    import html as H
    base = os.path.join(RAIZ, "categorias"); secoes = []; total_s = total_c = 0
    f_e = os.path.join(RAIZ, "ext.json"); EXT = json.load(open(f_e)) if os.path.exists(f_e) else {}
    for cdir in sorted(glob.glob(os.path.join(base, "*", "config.json"))):
        pasta = os.path.dirname(cdir); cfg = json.load(open(cdir, encoding="utf-8"))
        if SO_PAINEL and os.path.basename(pasta) != SO_PAINEL: continue
        A = especificar(cfg); L = []; EV = ler_eventos(pasta)
        hoje = pd.Timestamp.today().normalize()
        for nome, v in A.items():
            d = ler(os.path.join(pasta, "dados"), nome, "1D")
            if d is None: continue
            r = linha_painel(nome, limpar(d), cfg.get("semana", "FRI"), dict(info=" · ".join(x for x in [v.get("grupo", "")] if x), rot=rotulo(nome, v), moeda=cfg.get("moeda", "")), juros=cfg.get("tipo") == "juros")
            if r:
                r["tf"] = {}; r["rs"] = {}; r["mes"] = float("nan")
                dd = limpar(d); cc = dd.close; fim = cfg.get("semana", "FRI"); ww = semanal(dd, fim); lab = lambda ix: int(ix.strftime("%Y%m%d"))
                try:
                    if cfg.get("tipo") != "juros":
                        e = rsi_est(cc)
                        if e: r["rs"]["D"] = (e, "d", lab(cc.index[-1]))
                        e = rsi_est(ww.close)
                        if e: r["rs"]["S"] = (e, "d", lab(ww.index[-1]))
                        mm = mensal_serie(cc); e = rsi_est(mm)
                        if len(mm) > 1: r["mes"] = float(mm.iloc[-1] / mm.iloc[-2] - 1)
                        if e: r["rs"]["M"] = (e, "d", lab(mm.index[-1]))
                        cb = os.path.basename(pasta); y0 = A[nome]["yahoo"][0]
                        src = "cr" if cb == "cripto" else "us" if (cb == "eua" or (cb in ("setores", "macro") and not any(ch in y0 for ch in "^=.-"))) else None
                        if src and len(cc) > 2 and len(ww) > 1:
                            r["lv"] = dict(src=src, sym=nome if cb in ("cripto", "eua") else y0, tz="utc" if src == "cr" else "et",
                                           pd=[float(cc.iloc[-2]), float(cc.iloc[-1])], pw=[float(ww.close.iloc[-2]), float(ww.close.iloc[-1])],
                                           ld=lab(cc.index[-1]), lw=lab(ww.index[-1]), pc=float(cc.iloc[-1]))
                except Exception as ex: print("live", nome, ex)
                for tf in cfg.get("tempos", []):
                    x = ler(os.path.join(pasta, "dados"), nome, tf)
                    if x is not None and len(x) > 30:
                        xc = limpar(x).close; r["tf"][tf] = rsi(xc).iloc[-1]
                        try:
                            e = rsi_est(xc)
                            if e: r["rs"][tf] = (e, "i", int(pd.Timestamp(xc.index[-1]).tz_localize("UTC").timestamp()) + TF_SEG.get(tf, 900))
                        except Exception as ex: print("live tf", nome, tf, ex)
                r["juros"] = cfg.get("tipo") == "juros"
                r["ext"] = EXT.get(A[nome]["yahoo"][0])
                r["res"] = None
                if nome in EV:
                    try:
                        dd = pd.Timestamp(EV[nome].lstrip("~")); n = (dd - hoje).days
                        if n >= 0: r["res"] = (dd, n, EV[nome].startswith("~"))
                    except Exception: pass
                L.append(r)
        if L:
            pos = {n: i for i, n in enumerate(ordenar(cfg, pasta, [r["nome"] for r in L]))}
            for r in L: r["ord"] = pos[r["nome"]]; r["setor"] = A[r["nome"]].get("setor") or A[r["nome"]].get("grupo") or ""
            secoes.append((cfg["nome"], L, not cfg.get("sem_eventos"), cfg.get("tempos", []), cfg.get("tipo") == "juros", os.path.basename(pasta)))
    import ui
    PAGINAS = [("painel.html", "Todos", None), ("painel_cripto.html", "Cripto", ["cripto"]), ("painel_brasil.html", "Brasil", ["brasil"]),
               ("painel_eua.html", "EUA", ["eua"]), ("painel_outros.html", "Dados gerais", ["setores", "commodities", "macro", "juros"]),
               ("painel_oscilacoes.html", "Oscilações", "oscilacoes"), ("painel_graficos.html", "Gráficos", "graficos")]
    f_m = os.path.join(RAIZ, "macro.json")
    macro_ev = json.load(open(f_m, encoding="utf-8")) if os.path.exists(f_m) else []
    f_l = os.path.join(RAIZ, "live.json")
    ui.LIVE = json.load(open(f_l)) if os.path.exists(f_l) else {}
    for arq, titulo, chaves in PAGINAS:
        if chaves == "oscilacoes":
            if not SO_PAINEL: open(os.path.join(RAIZ, arq), "w", encoding="utf-8").write(ui.oscilacoes(arq, titulo, PAGINAS, secoes))
            continue
        if chaves == "graficos":
            if not SO_PAINEL: open(os.path.join(RAIZ, arq), "w", encoding="utf-8").write(ui.graficos(arq, titulo, PAGINAS))
            continue
        if SO_PAINEL and SO_PAINEL not in (chaves or []): continue
        sel = [x for x in secoes if chaves is None or x[5] in chaves]
        if chaves: sel.sort(key=lambda x: chaves.index(x[5]))
        com_cal = chaves is None or "juros" in chaves
        open(os.path.join(RAIZ, arq), "w", encoding="utf-8").write(ui.pagina(arq, titulo, sel, PAGINAS, macro_ev, com_cal))
    if not SO_PAINEL:
        open(os.path.join(RAIZ, "index.html"), "w", encoding="utf-8").write(ui.inicio(PAGINAS, secoes, macro_ev))
    print("paineis gerados:", sum(len(x[1]) for x in secoes), "ativos")

if __name__ == "__main__":
    if "--mercado" in sys.argv: atualizar_mercado("--forcar" in sys.argv); sys.exit(0)
    if "--eventos" in sys.argv: atualizar_eventos("--forcar" in sys.argv); sys.exit(0)
    if "--faltando" in sys.argv:
        for cdir in sorted(glob.glob(os.path.join(RAIZ, "categorias", "*", "config.json"))):
            pasta = os.path.dirname(cdir); cfg = json.load(open(cdir, encoding="utf-8"))
            if cfg.get("tipo") == "juros": continue
            if any(not os.path.exists(os.path.join(pasta, "dados", f"{n}_1D.csv")) for n in especificar(cfg)): print(os.path.basename(pasta))
        sys.exit(0)
    if "--ext" in sys.argv: atualizar_ext(); sys.exit(0)
    if "--painel" in sys.argv: painel(); sys.exit(0)
    offline = "--csv" in sys.argv
    so = sys.argv[sys.argv.index("--cat")+1] if "--cat" in sys.argv else None
    base = os.path.join(RAIZ, "categorias")
    for cdir in sorted(glob.glob(os.path.join(base, "*", "config.json"))):
        pasta_cat = os.path.dirname(cdir); nome = os.path.basename(pasta_cat)
        if so and so != nome: continue
        cfg = json.load(open(cdir, encoding="utf-8"))
        if not cfg.get("ativos"): print(nome, ": sem ativos, pulando"); continue
        if cfg.get("tipo") == "juros":
            ok, f = coletar_juros(cfg, pasta_cat); print(nome, "ok:", ok, "| falhas:", f or "nenhuma"); continue
        A, dados, d30, bench, fonte, falhas = carregar(cfg, os.path.join(pasta_cat, "dados"), offline)
        if not dados: print(nome, ": nenhum dado", falhas); continue
        open(os.path.join(pasta_cat, "relatorio.html"), "w", encoding="utf-8").write(relatorio(cfg, A, dados, d30, bench, fonte, falhas))
        print(nome, "ok | sem dados:", falhas or "nenhum")
