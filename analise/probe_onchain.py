import json, requests, time
H={"User-Agent":"Mozilla/5.0"}
out={}
def g(u,**k):
    r=requests.get(u,timeout=40,headers=H,**k); return r
# coinmetrics: metrics comunitarias 1d por ativo
r=g("https://community-api.coinmetrics.io/v4/catalog/assets?assets=btc,eth,sol,hype,uni,aave,pendle").json()
cm={}
for a in r["data"]:
    cm[a["asset"]]=sorted(m["metric"] for m in a.get("metrics",[]) if any(f["frequency"]=="1d" and f.get("community") for f in m["frequencies"]))
out["cm"]=cm
# teste de timeseries com metricas comunitarias
try:
    m=",".join(cm["btc"][:40])
    r=g("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",params={"assets":"btc","metrics":m,"frequency":"1d","page_size":2,"paging_from":"end"})
    out["cm_btc_ts"]=r.json() if r.status_code==200 else r.text[:300]
except Exception as e: out["cm_btc_ts"]=str(e)
# defillama: protocolos relevantes (so campos leves)
P=g("https://api.llama.fi/protocols").json()
out["llama_prot"]={}
for p in P:
    if p["slug"] in ("aave","uniswap","pendle","hyperliquid-perps","hyperliquid","lido","jito","jupiter","raydium") or p.get("gecko_id") in ("aave","uniswap","pendle","hyperliquid"):
        out["llama_prot"][p["slug"]]={k:p.get(k) for k in ("name","slug","category","chains","tvl","change_1d","change_7d","change_1m","mcap","gecko_id","symbol")}
for s in ("aave","uniswap","pendle","hyperliquid"):
    try:
        d=g(f"https://api.llama.fi/protocol/{s}").json()
        out["llama_"+s]={"keys":list(d.keys()),"currentChainTvls":d.get("currentChainTvls"),"tvl_last":d.get("tvl",[])[-2:] if isinstance(d.get("tvl"),list) else None,"mcap":d.get("mcap"),"tokenInUsd":str(d.get("tokensInUsd",[])[-1:])[:300]}
    except Exception as e: out["llama_"+s]=str(e)
for s in ("aave","uniswap","pendle","hyperliquid"):
    for dt in ("dailyFees","dailyRevenue","dailyHoldersRevenue"):
        try:
            d=g(f"https://api.llama.fi/summary/fees/{s}",params={"dataType":dt}).json()
            out[f"fee_{s}_{dt}"]={k:d.get(k) for k in ("total24h","total7d","total30d","totalAllTime","change_1d","change_7d","change_1m")}
        except Exception as e: out[f"fee_{s}_{dt}"]=str(e)
for s in ("uniswap","hyperliquid","pendle"):
    for kind in ("dexs","derivatives","aggregators"):
        try:
            d=g(f"https://api.llama.fi/summary/{kind}/{s}").json()
            if "total24h" in d: out[f"vol_{kind}_{s}"]={k:d.get(k) for k in ("total24h","total7d","total30d","totalAllTime")}
        except Exception as e: pass
for ch in ("Ethereum","Solana","Hyperliquid L1","Bitcoin"):
    try:
        d=g(f"https://api.llama.fi/overview/fees/{ch}",params={"excludeTotalDataChart":"true","excludeTotalDataChartBreakdown":"true"}).json()
        out["chainfees_"+ch]={k:d.get(k) for k in ("total24h","total7d","total30d","change_1d","change_7d")}
        d=g(f"https://api.llama.fi/overview/dexs/{ch}",params={"excludeTotalDataChart":"true","excludeTotalDataChartBreakdown":"true"}).json()
        out["chaindex_"+ch]={k:d.get(k) for k in ("total24h","total7d","total30d")}
    except Exception as e: out["chainfees_"+ch]=str(e)
for ch in ("Ethereum","Solana","Hyperliquid L1","Bitcoin"):
    try:
        d=g(f"https://api.llama.fi/v2/historicalChainTvl/{ch}").json(); out["tvl_hist_"+ch]=d[-3:]
    except Exception as e: out["tvl_hist_"+ch]=str(e)
st=g("https://stablecoins.llama.fi/stablecoinchains").json()
out["stable"]={s["name"]:s["totalCirculatingUSD"] for s in st if s["name"] in ("Ethereum","Solana","Hyperliquid L1","Bitcoin","Base","Arbitrum")}
# coingecko detalhado
cg={}
for i in ("bitcoin","ethereum","solana","hyperliquid","uniswap","aave","pendle"):
    try:
        d=g(f"https://api.coingecko.com/api/v3/coins/{i}",params={"localization":"false","tickers":"false","market_data":"true","community_data":"true","developer_data":"true"}).json()
        md=d.get("market_data",{})
        cg[i]={"md":{k:(md.get(k) if not isinstance(md.get(k),dict) else md[k].get("usd")) for k in ("market_cap","fully_diluted_valuation","total_volume","circulating_supply","total_supply","max_supply","ath","ath_change_percentage","atl","price_change_percentage_24h","price_change_percentage_7d","price_change_percentage_30d","price_change_percentage_1y","market_cap_rank")},
               "dev":d.get("developer_data"),"com":{k:d.get("community_data",{}).get(k) for k in ("twitter_followers","reddit_subscribers")},"cat":d.get("categories"),"genesis":d.get("genesis_date"),"hash":d.get("hashing_algorithm"),"sent":d.get("sentiment_votes_up_percentage")}
    except Exception as e: cg[i]=str(e)
    time.sleep(8)
out["cg"]=cg
# HL
r=requests.post("https://api.hyperliquid.xyz/info",json={"type":"metaAndAssetCtxs"},timeout=30).json()
u=r[0]["universe"];c=r[1]
out["hl"]={x["name"]:c[i] for i,x in enumerate(u) if x["name"] in ("BTC","ETH","SOL","HYPE","UNI","AAVE","PENDLE")}
# OKX funding/OI
ok={}
for s in ("BTC","ETH","SOL","HYPE","UNI","AAVE","PENDLE"):
    try:
        a=g("https://www.okx.com/api/v5/public/funding-rate",params={"instId":f"{s}-USDT-SWAP"}).json()
        b=g("https://www.okx.com/api/v5/public/open-interest",params={"instType":"SWAP","instId":f"{s}-USDT-SWAP"}).json()
        l=g("https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio",params={"ccy":s,"period":"1D"}).json()
        ok[s]={"f":a.get("data"),"oi":b.get("data"),"ls":(l.get("data") or [])[:2]}
    except Exception as e: ok[s]=str(e)
out["okx"]=ok
# BTC extras
out["bc_stats"]=g("https://api.blockchain.info/stats").json()
for ch in ("n-transactions","n-unique-addresses","miners-revenue","transaction-fees-usd","difficulty","mempool-size","estimated-transaction-volume-usd","utxo-count","avg-block-size"):
    try:
        d=g(f"https://api.blockchain.info/charts/{ch}",params={"timespan":"60days","format":"json"}).json(); out["bc_"+ch]=d["values"][-2:]
    except Exception as e: out["bc_"+ch]=str(e)
out["mempool_ln"]=g("https://mempool.space/api/v1/lightning/statistics/latest").json()
out["mempool_diffadj"]=g("https://mempool.space/api/v1/difficulty-adjustment").json()
out["mempool_pools"]=str(g("https://mempool.space/api/v1/mining/pools/1w").json())[:600]
out["blockchair_btc"]=g("https://api.blockchair.com/bitcoin/stats").json()["data"]
out["blockchair_eth"]=g("https://api.blockchair.com/ethereum/stats").json()["data"]
# ETH staking
try: out["eth_stake_keys"]=str(g("https://ultrasound.money/api/v2/fees/supply-parts").text[:600])
except Exception as e: out["eth_stake_keys"]=str(e)
for u in ("https://beaconcha.in/api/v1/ethstore/latest","https://api.llama.fi/protocol/lido","https://ultrasound.money/api/v2/fees/staking-ratio","https://eth-staking.rated.network/v0/eth/network/overview"):
    try: r=g(u); out["x_"+u[-30:]]={"s":r.status_code,"t":r.text[:400]}
    except Exception as e: out["x_"+u[-30:]]=str(e)
# SOL
def rpc(m,p=None):
    return requests.post("https://api.mainnet-beta.solana.com",json={"jsonrpc":"2.0","id":1,"method":m,"params":p or []},timeout=40).json().get("result")
va=rpc("getVoteAccounts"); cur=va["current"]
tot=sum(x["activatedStake"] for x in cur); ss=sorted((x["activatedStake"] for x in cur),reverse=True);acc=0;n33=0
for x in ss:
    acc+=x;n33+=1
    if acc>tot/3: break
out["sol"]={"validators":len(cur),"delinq":len(va["delinquent"]),"stake":tot,"nakamoto":n33,"epoch":rpc("getEpochInfo"),"supply":{k:v for k,v in rpc("getSupply")["value"].items() if k!="nonCirculatingAccounts"},"inflation":rpc("getInflationRate"),"perf":rpc("getRecentPerformanceSamples",[3])}
out["fng"]=g("https://api.alternative.me/fng/?limit=30").json()["data"][:2]
json.dump(out,open("analise/probe_onchain.json","w"),ensure_ascii=False,default=str)
