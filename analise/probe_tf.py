import json, requests, time
I="https://api.hyperliquid.xyz/info"; UA={"User-Agent":"Mozilla/5.0"}
def P(b):
    try:
        r=requests.post(I,json=b,timeout=30,headers=UA); return r.status_code, (r.json() if r.status_code==200 else r.text[:200])
    except Exception as e: return 0,str(e)
out={}
s,d=P({"type":"perpDexs"}); out["dexs"]=[ (x or {}).get("name") for x in d] if s==200 else d
out["dexs_raw"]=d[:4] if s==200 else None
c=json.load(open("carteiras.json"))["c"]
tf=[a for a,v in c.items() if any(":" in t[0] for t in v.get("ativos",[]))][:8]
out["tf_addrs"]=tf
out["pos"]={}
for a in tf[:6]:
    for dx in [x for x in out["dexs"] if x][:6]:
        s,d=P({"type":"clearinghouseState","user":a,"dex":dx})
        if s==200 and d.get("assetPositions"):
            out["pos"][a+"|"+dx]={"av":d.get("marginSummary"),"pos":d["assetPositions"][:3]}
s,d=P({"type":"metaAndAssetCtxs","dex":"xyz"})
out["meta_xyz"]=[ (d[0]["universe"][:5], d[1][:2]) ] if s==200 else d
s,d=P({"type":"allPerpMetas"}); out["allmeta_ok"]=s; out["allmeta_len"]=len(d) if s==200 else d
json.dump(out,open("analise/probe_tf.json","w"),indent=1,ensure_ascii=False)
