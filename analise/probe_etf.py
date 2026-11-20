import yfinance as yf, json
T="SPXB11 SPXI11 IVVB11 NASD11 BIVB11 USTK11 WRLD11 TECK11 QQQQ11 SPYI11 ACWI11 XINA11 NDIV11 EURP11 BBSD11 BNDX11 GOLD11 ALUK11 USAL11 AMER11 NSDQ11 SPXR11 BRZP11 JPAN11 DIVO11".split()
o={}
for t in T:
    try:
        d=yf.download(t+".SA",period="1mo",interval="1d",auto_adjust=False,progress=False)
        if d is None or len(d)<3: o[t]=None; continue
        d.columns=d.columns.get_level_values(0)
        o[t]={"preco":round(float(d.Close.iloc[-1]),2),"vol_med_rs":round(float((d.Close*d.Volume).tail(20).mean())),"vol_med_cotas":round(float(d.Volume.tail(20).mean())),"n":len(d)}
    except Exception as e: o[t]=str(e)[:80]
json.dump(o,open("analise/probe_etf.json","w"),indent=1)
