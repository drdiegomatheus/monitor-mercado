import yfinance as yf, json
out={}
for t in ["ANT","ANTH34.SA","ANTH34","ANT.US"]:
    for per,iv in (("5d","1d"),("1d","30m")):
        try:
            d=yf.download(t,period=per,interval=iv,auto_adjust=False,progress=False)
            out[f"{t}|{iv}"]={"n":len(d),"ult":str(d.index[-1]) if len(d) else None}
            if len(d) and iv=="1d": out[t+"|rows"]=d.tail(2).round(2).to_string()
        except Exception as e: out[f"{t}|{iv}"]={"erro":str(e)[:150]}
    try:
        i=yf.Ticker(t).fast_info; out[t+"|fast"]={"last":i.get("last_price"),"name":str(i.get("currency"))}
    except Exception as e: out[t+"|fast"]=str(e)[:100]
json.dump(out,open("analise/probe.json","w"),indent=1)
print(out)
