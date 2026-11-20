import json, os, time, urllib.request, urllib.parse, glob
TK = os.environ["BRAPI_TOKEN"]
def get(path, **q):
    q["token"] = TK
    u = "https://brapi.dev/api/" + path + "?" + urllib.parse.urlencode(q)
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30)
        return r.status, json.loads(r.read().decode())
    except Exception as e:
        b = ""
        try: b = e.read().decode()[:300]
        except Exception: pass
        return "ERR " + str(e)[:60], b
ativos = {}
for cat in ("brasil", "pares"):
    c = json.load(open(f"categorias/{cat}/config.json", encoding="utf-8"))
    for n in c["ativos"]: ativos[n] = cat
out = {"total": len(ativos), "cobertos": {}, "faltando": {}, "campos": {}, "exemplos": {}}
for i, (n, cat) in enumerate(ativos.items()):
    st, d = get("quote/" + n)
    ok = st == 200 and isinstance(d, dict) and d.get("results")
    if ok:
        r = d["results"][0]
        out["cobertos"][n] = {"preco": r.get("regularMarketPrice"), "hora": r.get("regularMarketTime"), "vol": r.get("regularMarketVolume"), "cap": r.get("marketCap"), "ant": r.get("regularMarketPreviousClose")}
        if i < 3 or n in ("NVDC34", "M2ST34", "IVVB11", "PETR4"): out["exemplos"][n] = r
        for k in r: out["campos"][k] = out["campos"].get(k, 0) + 1
    else:
        out["faltando"][n] = [str(st), str(d)[:160]]
    time.sleep(0.4)
# endpoints extras num ativo B3 e num BDR
for n in ("PETR4", "NVDC34"):
    for nome, q in (("fundamental", {"fundamental": "true"}), ("dividends", {"dividends": "true"}), ("hist_1d_1mo", {"range": "1mo", "interval": "1d"}), ("hist_30m", {"range": "5d", "interval": "30m"}), ("modules", {"modules": "summaryProfile"})):
        st, d = get("quote/" + n, **q)
        txt = json.dumps(d)[:600] if st == 200 else str(d)[:200]
        out.setdefault("extras", {})[f"{n}|{nome}"] = [str(st), txt]
        time.sleep(0.4)
st, d = get("available", search="NVDC")
out["available_NVDC"] = [str(st), json.dumps(d)[:300]]
json.dump(out, open("analise/probe.json", "w"), indent=1, ensure_ascii=False)
print(len(out["cobertos"]), "cobertos;", len(out["faltando"]), "faltando")
