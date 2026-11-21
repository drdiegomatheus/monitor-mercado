"""Coleta dados on-chain, DeFi, derivativos e desenvolvimento dos ativos de cripto (fontes gratuitas, sem chave).
Roda no máximo 1 vez por hora. Saída: categorias/cripto/onchain.json  (ONCHAIN_SAIDA muda o destino, para testes)"""
import json
import os
import sys
import time
import datetime as dt
import requests

RAIZ = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.environ.get("ONCHAIN_SAIDA") or os.path.join(RAIZ, "categorias", "cripto", "onchain.json")
VALIDADE = float(os.environ.get("ONCHAIN_VALIDADE", str(55 * 60)))
UA = {"User-Agent": "Mozilla/5.0 (monitor-mercado)"}
HOJE = int(time.time() // 86400)

# ativo: coingecko, coinmetrics, cadeia (llama), protocolo (llama), repositórios (github), símbolo na Hyperliquid/OKX
A = {
    "BTC": {"cg": "bitcoin", "cm": "btc", "chain": "Bitcoin", "prot": None, "gh": ["bitcoin/bitcoin"]},
    "ETH": {"cg": "ethereum", "cm": "eth", "chain": "Ethereum", "prot": None, "gh": ["ethereum/go-ethereum", "prysmaticlabs/prysm"]},
    "SOL": {"cg": "solana", "cm": "sol", "chain": "Solana", "prot": None, "gh": ["anza-xyz/agave"]},
    "HYPE": {"cg": "hyperliquid", "cm": "hype", "chain": "Hyperliquid L1", "prot": "hyperliquid", "gh": ["hyperliquid-dex/node"]},
    "UNI": {"cg": "uniswap", "cm": "uni", "chain": None, "prot": "uniswap", "gh": ["Uniswap/v4-core", "Uniswap/universal-router"]},
    "AAVE": {"cg": "aave", "cm": "aave", "chain": None, "prot": "aave", "gh": ["aave-dao/aave-v3-origin"]},
    "PENDLE": {"cg": "pendle", "cm": "pendle", "chain": None, "prot": "pendle", "gh": ["pendle-finance/pendle-core-v2-public"]},
}
CMM = ["AdrActCnt", "AdrBalCnt", "TxCnt", "TxTfrCnt", "CapMVRVCur", "CapMrktCurUSD", "FeeTotNtv", "FlowInExUSD", "FlowOutExUSD", "SplyExUSD", "SplyExNtv",
       "HashRate", "IssTotNtv", "IssTotUSD", "SplyCur", "BlkCnt", "volume_reported_spot_usd_1d"]


def J(url, metodo="GET", corpo=None, params=None, tent=2, tempo=40, cab=None):
    for i in range(tent):
        try:
            h = dict(UA)
            if cab: h.update(cab)
            r = requests.post(url, json=corpo, timeout=tempo, headers=h) if metodo == "POST" else requests.get(url, params=params, timeout=tempo, headers=h)
            if r.status_code == 200: return r.json()
            if r.status_code in (429, 503): time.sleep(4 + 4 * i)
            else: return None
        except Exception:
            time.sleep(1.5)
    return None


def num(x):
    try:
        v = float(x)
        return v if v == v and abs(v) != float("inf") else None
    except Exception:
        return None


def serie(pares, n=370, nd=0):
    """[(dia, valor)] -> {"d": [...], "v": [...]} com os últimos n pontos"""
    pares = [(d, num(v)) for d, v in pares if num(v) is not None][-n:]
    return {"d": [d for d, _ in pares], "v": [round(v, nd) if nd else int(round(v)) for _, v in pares]}


def dia(ts):
    return int(ts // 86400)


def cresc(s, jan=30):
    """variação % da média dos últimos `jan` dias contra a dos `jan` anteriores"""
    v = [x for x in (s or {}).get("v", []) if x is not None]
    if len(v) < jan * 2: return None
    a, b = sum(v[-jan:]) / jan, sum(v[-2 * jan:-jan]) / jan
    return (a / b - 1) * 100 if b else None


def mudanca(s, jan=30):
    v = [x for x in (s or {}).get("v", []) if x is not None]
    if len(v) <= jan or not v[-1 - jan]: return None
    return (v[-1] / v[-1 - jan] - 1) * 100


# ---------------------------------------------------------------- mercado geral
def mercado():
    m = {}
    f = J("https://api.alternative.me/fng/", params={"limit": 365})
    if f:
        d = f["data"]
        m["fng"] = {"v": num(d[0]["value"]), "c": d[0]["value_classification"], "h": [num(x["value"]) for x in reversed(d[:90])],
                    "d": [dia(int(x["timestamp"])) for x in reversed(d[:90])]}
    g = J("https://api.coingecko.com/api/v3/global")
    if g and g.get("data"):
        g = g["data"]
        m["dom_btc"] = num(g["market_cap_percentage"].get("btc"))
        m["dom_eth"] = num(g["market_cap_percentage"].get("eth"))
        m["mcap"] = num(g["total_market_cap"].get("usd"))
        m["vol"] = num(g["total_volume"].get("usd"))
        m["mcap_24h"] = num(g.get("market_cap_change_percentage_24h_usd"))
    return m


def coingecko():
    ids = ",".join(v["cg"] for v in A.values())
    r = J("https://api.coingecko.com/api/v3/coins/markets", params={"vs_currency": "usd", "ids": ids, "price_change_percentage": "24h,7d,30d,1y", "per_page": 50})
    out = {}
    for x in r or []:
        for k, v in A.items():
            if v["cg"] == x["id"]:
                out[k] = {c: x.get(c) for c in ("current_price", "market_cap", "fully_diluted_valuation", "total_volume", "circulating_supply", "total_supply", "max_supply",
                                                  "ath", "ath_change_percentage", "ath_date", "atl", "atl_change_percentage", "market_cap_rank", "market_cap_change_percentage_24h",
                                                  "price_change_percentage_24h_in_currency", "price_change_percentage_7d_in_currency", "price_change_percentage_30d_in_currency",
                                                  "price_change_percentage_1y_in_currency")}
    return out


# ---------------------------------------------------------------- Coin Metrics (comunidade)
def coinmetrics(a):
    ini = (dt.date.today() - dt.timedelta(days=400)).isoformat()
    cat = J("https://community-api.coinmetrics.io/v4/catalog/assets", params={"assets": a})
    ok = set()
    try:
        for m in cat["data"][0]["metrics"]:
            if any(f["frequency"] == "1d" and f.get("community") for f in m["frequencies"]): ok.add(m["metric"])
    except Exception:
        return None
    ms = [m for m in CMM if m in ok]
    if not ms: return None
    r = J("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics", params={"assets": a, "metrics": ",".join(ms), "frequency": "1d", "start_time": ini, "page_size": 1000}, tempo=60)
    if not r or not r.get("data"): return None
    out = {}
    for m in ms:
        out[m] = serie([(dia(dt.datetime.fromisoformat(x["time"][:19]).replace(tzinfo=dt.timezone.utc).timestamp()), x.get(m)) for x in r["data"]], 370, 4)
    return out


# ---------------------------------------------------------------- DefiLlama
def llama_prot(slug):
    d = J("https://api.llama.fi/protocol/" + slug, tempo=90)
    if not d: return None
    cur = d.get("currentChainTvls") or {}
    cadeias = sorted(((k, v) for k, v in cur.items() if "-" not in k and k not in ("borrowed", "staking", "pool2", "vesting", "offers")), key=lambda x: -x[1])[:6]
    tv = d.get("tvl") or []
    hk = d.get("hacks") or []
    rs = d.get("raises") or []
    return {"tvl": serie([(dia(x["date"]), x["totalLiquidityUSD"]) for x in tv]), "tvl_atual": num(sum(v for k, v in cur.items() if "-" not in k and k not in ("borrowed", "staking", "pool2", "vesting", "offers"))),
            "borrowed": num(cur.get("borrowed")), "staking": num(cur.get("staking")), "cadeias": cadeias, "categoria": d.get("category"),
            "hacks": len(hk), "hacks_usd": sum(num(h.get("amount")) or 0 for h in hk), "levantado_usd": sum((num(r.get("amount")) or 0) * 1e6 for r in rs),
            "audits": d.get("audits"), "github": d.get("github"), "mcap": num(d.get("mcap"))}


def llama_fees(slug, tipo="fees", dtp="dailyFees"):
    d = J(f"https://api.llama.fi/summary/{tipo}/{slug}", params={"dataType": dtp} if tipo == "fees" else None, tempo=60)
    if not d or "total24h" not in d: return None
    ch = d.get("totalDataChart") or []
    return {"h24": num(d.get("total24h")), "d7": num(d.get("total7d")), "d30": num(d.get("total30d")), "tot": num(d.get("totalAllTime")),
            "s": serie([(dia(x[0]), x[1]) for x in ch])}


def llama_chain(ch):
    o = {}
    d = J(f"https://api.llama.fi/v2/historicalChainTvl/{ch}", tempo=60)
    if d: o["tvl"] = serie([(dia(x["date"]), x["tvl"]) for x in d])
    for nome, tipo in (("fees", "fees"), ("dex", "dexs")):
        r = J(f"https://api.llama.fi/overview/{tipo}/{ch}", params={"excludeTotalDataChartBreakdown": "true"}, tempo=60)
        if r and "total24h" in r:
            o[nome] = {"h24": num(r.get("total24h")), "d7": num(r.get("total7d")), "d30": num(r.get("total30d")), "s": serie([(dia(x[0]), x[1]) for x in (r.get("totalDataChart") or [])])}
    st = J(f"https://stablecoins.llama.fi/stablecoincharts/{ch}", tempo=60)
    if st:
        try: o["stable"] = serie([(int(x["date"]) // 86400, x["totalCirculatingUSD"]["peggedUSD"]) for x in st])
        except Exception: pass
    return o


def llama_tesouro(slug):
    d = J("https://api.llama.fi/treasury/" + slug, tempo=60)
    if not d: return None
    cur = d.get("currentChainTvls") or {}
    return {"total": num(sum(v for k, v in cur.items() if "-" not in k)), "proprio": num(sum(v for k, v in cur.items() if k.endswith("-ownTokens")))}


# ---------------------------------------------------------------- derivativos
def hyperliquid():
    out = {}
    r = J("https://api.hyperliquid.xyz/info", "POST", {"type": "metaAndAssetCtxs"})
    ctx = {}
    if r:
        for i, u in enumerate(r[0]["universe"]): ctx[u["name"]] = r[1][i]
    ini = int((time.time() - 20 * 86400) * 1000)
    for k in A:
        c = ctx.get(k)
        if not c: continue
        mark = num(c.get("markPx")) or 0
        o = {"fund_h": num(c.get("funding")), "oi_usd": (num(c.get("openInterest")) or 0) * mark, "vol24": num(c.get("dayNtlVlm")), "premio": num(c.get("premium"))}
        h = J("https://api.hyperliquid.xyz/info", "POST", {"type": "fundingHistory", "coin": k, "startTime": ini})
        if h:
            por = {}
            for x in h: por.setdefault(dia(x["time"] / 1000), []).append(num(x["fundingRate"]) or 0)
            dias = sorted(por)
            o["fund_s"] = {"d": dias, "v": [round(sum(por[d]) / len(por[d]) * 24 * 365 * 100, 2) for d in dias]}      # % ao ano
        out[k] = o
        time.sleep(0.2)
    return out


def okx():
    out = {}
    for k in A:
        inst = f"{k}-USDT-SWAP"
        o = {}
        f = J("https://www.okx.com/api/v5/public/funding-rate", params={"instId": inst})
        if f and f.get("data"): o["fund_8h"] = num(f["data"][0].get("fundingRate"))
        fh = J("https://www.okx.com/api/v5/public/funding-rate-history", params={"instId": inst, "limit": 100})
        if fh and fh.get("data"):
            v = [num(x.get("realizedRate") or x.get("fundingRate")) for x in fh["data"]]
            v = [x for x in v if x is not None]
            if v:
                o["fund_7d"] = sum(v[:21]) / len(v[:21]) * 3 * 365 * 100
                o["fund_30d"] = sum(v[:90]) / len(v[:90]) * 3 * 365 * 100
        oi = J("https://www.okx.com/api/v5/public/open-interest", params={"instType": "SWAP", "instId": inst})
        if oi and oi.get("data"): o["oi_usd"] = num(oi["data"][0].get("oiUsd"))
        ls = J("https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio", params={"ccy": k, "period": "1D"})
        if ls and ls.get("data"): o["ls"] = num(ls["data"][0][1]); o["ls_s"] = {"d": [dia(int(x[0]) / 1000) for x in reversed(ls["data"][:60])], "v": [num(x[1]) for x in reversed(ls["data"][:60])]}
        hv = J("https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume", params={"ccy": k, "period": "1D"})
        if hv and hv.get("data"):
            d = list(reversed(hv["data"][:90]))
            o["oi_s"] = {"d": [dia(int(x[0]) / 1000) for x in d], "v": [int(num(x[1]) or 0) for x in d]}
            o["vol_s"] = {"d": [dia(int(x[0]) / 1000) for x in d], "v": [int(num(x[2]) or 0) for x in d]}
        out[k] = o
        time.sleep(0.25)
    return out


# ---------------------------------------------------------------- desenvolvimento
def github(repos):
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    cab = {"Authorization": "Bearer " + tok} if tok else None
    out = []
    for r in repos:
        d = J("https://api.github.com/repos/" + r, cab=cab)
        if not d: continue
        p = J(f"https://api.github.com/repos/{r}/stats/participation", cab=cab, tent=3)
        al = (p or {}).get("all") or []
        out.append({"repo": r, "stars": d.get("stargazers_count"), "forks": d.get("forks_count"), "issues": d.get("open_issues_count"), "push": (d.get("pushed_at") or "")[:10],
                    "c4": sum(al[-4:]) if al else None, "c52": sum(al) if al else None, "sem": al[-26:] if al else None})
    return out


# ---------------------------------------------------------------- específicos de cada rede
def tenta(f, *a):
    try: return f(*a)
    except Exception as e:
        print("  falha", f.__name__, str(e)[:80], file=sys.stderr)
        return None


def _bc():
    o = {}
    s = J("https://api.blockchain.info/stats")
    if s: o["bc"] = {k: s.get(k) for k in ("hash_rate", "n_tx", "minutes_between_blocks", "estimated_transaction_volume_usd", "miners_revenue_usd", "trade_volume_usd")}
    for ch in ("n-transactions", "n-unique-addresses", "miners-revenue", "transaction-fees-usd", "utxo-count", "avg-block-size", "mempool-size", "difficulty"):
        d = J(f"https://api.blockchain.info/charts/{ch}", params={"timespan": "1year", "format": "json", "sampled": "true"}, tempo=60)
        if d and d.get("values"):
            por = {}
            for x in d["values"]: por[dia(x["x"])] = x["y"]
            o["c_" + ch] = serie(sorted(por.items()), 370, 2)
    return o


def _chair():
    o = {}
    b = J("https://api.blockchair.com/bitcoin/stats")
    if b and b.get("data"):
        d = b["data"]
        o["chair"] = {k: d.get(k) for k in ("blocks", "transactions_24h", "difficulty", "mempool_transactions", "mempool_size", "mempool_total_fee_usd", "suggested_transaction_fee_per_byte_sat",
                                           "hashrate_24h", "nodes", "average_transaction_fee_usd_24h", "median_transaction_fee_usd_24h", "market_dominance_percentage", "blockchain_size", "inflation_usd_24h")}
        h = num(d.get("blocks"))
        if h: o["halving_blocos"] = 1050000 - h; o["halving_dias"] = (1050000 - h) / 144
    return o


def _mempool():
    o = {}
    da = J("https://mempool.space/api/v1/difficulty-adjustment")
    if da: o["dif"] = {k: da.get(k) for k in ("progressPercent", "difficultyChange", "remainingBlocks", "previousRetarget", "estimatedRetargetDate")}
    pl = J("https://mempool.space/api/v1/mining/pools/1w")
    if pl and pl.get("pools"):
        tot = sum(p["blockCount"] for p in pl["pools"]) or 1
        o["pools"] = [[p["name"], round(p["blockCount"] / tot * 100, 1)] for p in pl["pools"][:6]]
    hr = J("https://mempool.space/api/v1/mining/hashrate/1y", tempo=60)
    if hr and hr.get("hashrates"): o["hash_s"] = serie([(dia(x["timestamp"]), x["avgHashrate"] / 1e18) for x in hr["hashrates"]], 370, 1)      # EH/s
    f = J("https://mempool.space/api/v1/fees/recommended")
    if f: o["taxas"] = f
    return o


def _ln():
    o = {}
    ln = J("https://mempool.space/api/v1/lightning/statistics/latest")
    if ln and ln.get("latest"): o["ln"] = {k: ln["latest"].get(k) for k in ("channel_count", "node_count", "total_capacity", "med_capacity", "avg_fee_rate")}
    lh = J("https://mempool.space/api/v1/lightning/statistics/1y", tempo=60)
    if isinstance(lh, dict): lh = lh.get("history") or lh.get("data") or []
    if lh and isinstance(lh, list) and isinstance(lh[0], dict):
        o["ln_s"] = serie([(dia(dt.datetime.fromisoformat(x["added"][:10]).replace(tzinfo=dt.timezone.utc).timestamp()), x["total_capacity"] / 1e8) for x in lh], 370, 0)   # BTC
    return o


def btc_extra():
    o = {}
    for f in (_bc, _chair, _mempool, _ln):
        r = tenta(f)
        if r: o.update(r)
    return o


def eth_extra():
    o = {}
    sp = J("https://ultrasound.money/api/v2/fees/supply-parts")
    if sp:
        o["beacon_stake"] = (num(sp.get("beaconBalancesSum")) or 0) / 1e9      # gwei -> ETH
        o["deposits"] = (num(sp.get("beaconDepositsSum")) or 0) / 1e9
    so = J("https://ultrasound.money/api/v2/fees/supply-over-time", tempo=90)
    if so:
        for k in ("d30", "d7", "d90", "since_merge", "since_burn"):
            if k in so and so[k]:
                v = so[k]
                o["sup_" + k] = {"a": num(v[0]["supply"]), "b": num(v[-1]["supply"]), "ta": v[0]["timestamp"], "tb": v[-1]["timestamp"]}
        o["sup_chaves"] = [k for k in so if isinstance(so[k], list)]
    b = J("https://api.blockchair.com/ethereum/stats")
    if b and b.get("data"):
        d = b["data"]
        o["chair"] = {k: d.get(k) for k in ("blocks", "transactions_24h", "mempool_transactions", "mempool_median_gas_price", "average_transaction_fee_usd_24h", "median_transaction_fee_usd_24h", "nodes")}
    return o


def sol_extra():
    def rpc(m, p=None):
        r = J("https://api.mainnet-beta.solana.com", "POST", {"jsonrpc": "2.0", "id": 1, "method": m, "params": p or []}, tempo=60)
        return (r or {}).get("result")
    o = {}
    va = rpc("getVoteAccounts")
    if va:
        cur = va["current"]
        ss = sorted((x["activatedStake"] for x in cur), reverse=True)
        tot = sum(ss) or 1
        acc = 0
        n33 = n67 = 0
        for x in ss:
            acc += x
            n67 += 1
            if not n33 and acc > tot / 3: n33 = n67
            if acc > tot * 2 / 3: break
        com = [x["commission"] for x in cur if x["activatedStake"] > 0]
        o["val"] = {"ativos": len(cur), "inadimpl": len(va["delinquent"]), "stake": tot / 1e9, "nakamoto": n33, "super_maioria": n67,
                    "top10_pct": round(sum(ss[:10]) / tot * 100, 1), "comissao_media": round(sum(com) / len(com), 2) if com else None}
    ep = rpc("getEpochInfo")
    if ep: o["epoca"] = {k: ep.get(k) for k in ("epoch", "slotIndex", "slotsInEpoch", "transactionCount")}
    su = rpc("getSupply")
    if su: o["supply"] = {k: su["value"][k] / 1e9 for k in ("total", "circulating", "nonCirculating")}
    inf = rpc("getInflationRate")
    if inf: o["infl"] = inf
    pf = rpc("getRecentPerformanceSamples", [60])
    if pf:
        tx = sum(x["numNonVoteTransactions"] for x in pf)
        sec = sum(x["samplePeriodSecs"] for x in pf) or 1
        tt = sum(x["numTransactions"] for x in pf)
        o["tps"] = {"nao_voto": round(tx / sec, 0), "total": round(tt / sec, 0)}
    return o


def montar():
    out = {"ts": time.time(), "mercado": mercado(), "ativos": {}}
    cg = coingecko()
    der_h, der_o = hyperliquid(), okx()
    extra = {"BTC": btc_extra, "ETH": eth_extra, "SOL": sol_extra}
    for k, v in A.items():
        t0 = time.time()
        a = {"cg": cg.get(k), "cm": coinmetrics(v["cm"]), "hl": der_h.get(k), "okx": der_o.get(k), "dev": github(v["gh"])}
        if v["chain"]: a["chain"] = llama_chain(v["chain"])
        if v["prot"]:
            p = llama_prot(v["prot"])
            a["prot"] = p
            a["fees"] = llama_fees(v["prot"], "fees", "dailyFees")
            a["rev"] = llama_fees(v["prot"], "fees", "dailyRevenue")
            a["hold"] = llama_fees(v["prot"], "fees", "dailyHoldersRevenue")
            a["dex"] = llama_fees(v["prot"], "dexs")
            for slug in (v["prot"] + "-perps", v["prot"]):
                dv = llama_fees(slug, "derivatives")
                if dv: a["perp"] = dv; break
            a["tesouro"] = llama_tesouro(v["prot"])
        if k in extra:
            try: a["x"] = extra[k]()
            except Exception as e: a["x"] = {"erro": str(e)[:100]}
        if k == "ETH":
            li = llama_prot("lido")
            if li: a["lido"] = {"tvl": li["tvl_atual"]}
        out["ativos"][k] = a
        print(k, round(time.time() - t0, 1), "s", file=sys.stderr)
    return out


def main():
    if os.path.exists(SAIDA):
        try:
            if time.time() - json.load(open(SAIDA, encoding="utf-8")).get("ts", 0) < VALIDADE:
                print("onchain: dados recentes, nada a fazer")
                return
        except Exception:
            pass
    d = montar()
    ok = sum(1 for a in d["ativos"].values() if a.get("cg"))
    if ok < 3:
        print("onchain: coleta fraca, mantendo arquivo anterior")
        return
    json.dump(d, open(SAIDA, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False, default=str)
    print(f"onchain: salvo ({os.path.getsize(SAIDA) // 1024} KB)")


if __name__ == "__main__":
    main()
