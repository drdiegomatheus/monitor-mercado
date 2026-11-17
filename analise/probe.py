import yfinance as yf, json
out={}
for t in ["M2ST34.SA","MSTR34.SA","MSTR.SA","MSTR","M2ST34","SPCX34.SA"]:
    try:
        d=yf.download(t,period="max",interval="1d",auto_adjust=False,progress=False)
        if hasattr(d.columns,"levels"): d.columns=d.columns.get_level_values(0)
        out[t]={"n":len(d),"ini":str(d.index[0].date()) if len(d) else None,"fim":str(d.index[-1].date()) if len(d) else None,"close0":float(d["Close"].iloc[0]) if len(d) else None}
    except Exception as e: out[t]={"erro":str(e)[:150]}
json.dump(out,open("analise/probe.json","w"),indent=1)
print(out)
