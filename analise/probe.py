import json, time, datetime as dt, urllib.request, yfinance as yf
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=25);return r.status,r.read().decode()[:1500]
    except Exception as e:
        b=""
        try: b=e.read().decode()[:300]
        except Exception: pass
        return "ERR "+str(e)[:80],b
out={"agora_utc":dt.datetime.utcnow().isoformat()}
for t in ["PETR4","MGLU3","NVDC34","M2ST34"]:
    out["brapi_"+t]=get(f"https://brapi.dev/api/quote/{t}")
out["hg"]=get("https://api.hgbrasil.com/finance/stock_price?symbol=petr4")
for t in ["PETR4.SA","NVDC34.SA","M2ST34.SA"]:
    try:
        d=yf.download(t,period="1d",interval="1m",progress=False)
        out["yahoo1m_"+t]={"n":len(d),"ultima_barra_utc":str(d.index[-1]) if len(d) else None,"close":float(d["Close"].iloc[-1]) if len(d) else None}
    except Exception as e: out["yahoo1m_"+t]=str(e)[:100]
json.dump(out,open("analise/probe.json","w"),indent=1,ensure_ascii=False)
print(out)
