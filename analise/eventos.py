"""Reação de preço em resultados (after-market, dia seguinte, +5 pregões)."""
import json, sys
import pandas as pd, yfinance as yf

EVENTOS = ["2025-05-28", "2025-08-27", "2025-11-19", "2026-02-25", "2026-05-20", "2026-08-26"]
ATIVOS = {"NVDA": "NVDA", "QQQ": "QQQ", "NQ=F": "NQ=F", "^NDX": "^NDX"}
out = {}
for nome, tk in ATIVOS.items():
    try:
        d = yf.download(tk, period="2y", interval="1d", auto_adjust=False, progress=False)
        d.columns = [c[0] if isinstance(c, tuple) else c for c in d.columns]
        h = yf.download(tk, period="730d", interval="1h", prepost=True, auto_adjust=False, progress=False)
        h.columns = [c[0] if isinstance(c, tuple) else c for c in h.columns]
        h.index = h.index.tz_convert("America/New_York")
    except Exception as e:
        out[nome] = {"erro": str(e)}; continue
    d.index = pd.to_datetime(d.index).tz_localize(None)
    res = []
    for ev in EVENTOS:
        t0 = pd.Timestamp(ev)
        if t0 not in d.index: res.append({"data": ev, "erro": "sem dia"}); continue
        i = d.index.get_loc(t0)
        c0 = float(d.Close.iloc[i]); r = {"data": ev, "fech": round(c0, 2)}
        if i + 1 < len(d):
            r["abre_d1"] = round(float(d.Open.iloc[i+1]) / c0 * 100 - 100, 2)
            r["fech_d1"] = round(float(d.Close.iloc[i+1]) / c0 * 100 - 100, 2)
            r["max_d1"] = round(float(d.High.iloc[i+1]) / c0 * 100 - 100, 2)
            r["min_d1"] = round(float(d.Low.iloc[i+1]) / c0 * 100 - 100, 2)
        if i + 5 < len(d): r["fech_d5"] = round(float(d.Close.iloc[i+5]) / c0 * 100 - 100, 2)
        if i + 5 < len(d): r["pior_5d"] = round(float(d.Low.iloc[i+1:i+6].min()) / c0 * 100 - 100, 2); r["melhor_5d"] = round(float(d.High.iloc[i+1:i+6].max()) / c0 * 100 - 100, 2)
        # after-market do dia do resultado (barras horárias 16:00-20:00 ET)
        try:
            dia = h[h.index.date == t0.date()]
            pos = dia[(dia.index.hour >= 16)]
            reg = dia[(dia.index.hour < 16) & ((dia.index.hour > 9) | (dia.index.minute >= 30))]
            ref = float(reg.Close.iloc[-1]) if len(reg) else c0
            r["ref_regular"] = round(ref, 2)
            r["ah_barras"] = {str(ix.strftime("%H:%M")): round(float(v) / ref * 100 - 100, 2) for ix, v in pos.Close.items() if pd.notna(v)}
            if len(pos): r["ah_ultima"] = round(float(pos.Close.dropna().iloc[-1]) / ref * 100 - 100, 2)
        except Exception as e:
            r["ah_erro"] = str(e)
        res.append(r)
    out[nome] = res
json.dump(out, open("analise/eventos.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out)[:3000])
