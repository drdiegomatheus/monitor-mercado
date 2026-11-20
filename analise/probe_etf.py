import yfinance as yf, json
T="NASD11 QQQI11 QQQQ11 BQYL39 BQQQ39 QQQM39 QQQQ39 NDXB11 BNDQ39 NASD11 TQQQ39 SQQQ39 QQQQ34 EQQQ39".split()
o={}
for t in T:
    try:
        d=yf.download(t+".SA",period="1mo",interval="1d",auto_adjust=False,progress=False)
        if d is None or len(d)<3: o[t]=None; continue
        d.columns=d.columns.get_level_values(0)
        o[t]={"preco":round(float(d.Close.iloc[-1]),2),"vol_med_rs":round(float((d.Close*d.Volume).tail(20).mean())),"vol_med_cotas":round(float(d.Volume.tail(20).mean())),"dias_c_volume":int((d.Volume>0).sum())}
    except Exception as e: o[t]=str(e)[:80]
json.dump(o,open("analise/probe_etf.json","w"),indent=1)
