import json, requests, time
U = {
 "cm_assets": "https://community-api.coinmetrics.io/v4/catalog/assets?assets=btc,eth,sol,hype,uni,aave,pendle",
 "cm_metrics_btc": "https://community-api.coinmetrics.io/v4/catalog/asset-metrics?assets=btc",
 "cm_metrics_sol": "https://community-api.coinmetrics.io/v4/catalog/asset-metrics?assets=sol",
 "cm_metrics_uni": "https://community-api.coinmetrics.io/v4/catalog/asset-metrics?assets=uni",
 "cm_btc_ts": "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=AdrActCnt,CapMVRVCur,NVTAdj,TxCnt,HashRate,FeeTotUSD&frequency=1d&page_size=3&paging_from=end",
 "llama_protocols": "https://api.llama.fi/protocols",
 "llama_chains": "https://api.llama.fi/v2/chains",
 "llama_fees": "https://api.llama.fi/overview/fees?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true",
 "llama_dex": "https://api.llama.fi/overview/dexs?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true",
 "llama_stable": "https://stablecoins.llama.fi/stablecoinchains",
 "llama_aave": "https://api.llama.fi/protocol/aave",
 "llama_hl": "https://api.llama.fi/summary/fees/hyperliquid?dataType=dailyRevenue",
 "cg_markets": "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin,ethereum,solana,hyperliquid,uniswap,aave,pendle",
 "cg_coin": "https://api.coingecko.com/api/v3/coins/solana?localization=false&tickers=false&market_data=true&community_data=true&developer_data=true",
 "bc_hash": "https://api.blockchain.info/charts/hash-rate?timespan=30days&format=json",
 "bc_stats": "https://api.blockchain.info/stats",
 "mempool_diff": "https://mempool.space/api/v1/mining/hashrate/3m",
 "mempool_fees": "https://mempool.space/api/v1/fees/recommended",
 "mempool_ln": "https://mempool.space/api/v1/lightning/statistics/latest",
 "beacon": "https://beaconcha.in/api/v1/epoch/latest",
 "hl_meta": ("POST","https://api.hyperliquid.xyz/info",{"type":"metaAndAssetCtxs"}),
 "okx_fund": "https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP",
 "okx_oi": "https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP",
 "bybit_tick": "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT",
 "binance_fund": "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT",
 "fng": "https://api.alternative.me/fng/?limit=3",
 "sol_rpc": ("POST","https://api.mainnet-beta.solana.com",{"jsonrpc":"2.0","id":1,"method":"getEpochInfo"}),
 "sol_supply": ("POST","https://api.mainnet-beta.solana.com",{"jsonrpc":"2.0","id":1,"method":"getSupply"}),
 "sol_vote": ("POST","https://api.mainnet-beta.solana.com",{"jsonrpc":"2.0","id":1,"method":"getVoteAccounts"}),
 "eth_stake": "https://ultrasound.money/api/v2/fees/supply-over-time",
 "etherscan_supply": "https://api.etherscan.io/api?module=stats&action=ethsupply",
 "gh_sol": "https://api.github.com/repos/solana-labs/solana",
 "llama_treasury": "https://api.llama.fi/treasury/uniswap",
 "llama_emis": "https://api.llama.fi/emissions",
 "llama_raises": "https://api.llama.fi/raises",
 "llama_etf": "https://api.llama.fi/protocol/pendle",
 "cg_btc_hist": "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=30",
 "blockchair_btc": "https://api.blockchair.com/bitcoin/stats",
 "blockchair_eth": "https://api.blockchair.com/ethereum/stats",
}
out = {}
for k, u in U.items():
    try:
        if isinstance(u, tuple): r = requests.post(u[1], json=u[2], timeout=25)
        else: r = requests.get(u, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        out[k] = {"s": r.status_code, "n": len(r.content), "t": r.text[:700]}
    except Exception as e:
        out[k] = {"s": "ERR", "t": str(e)[:150]}
    time.sleep(0.5)
json.dump(out, open("analise/probe_onchain.json", "w"), ensure_ascii=False, indent=0)
