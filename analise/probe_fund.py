import yfinance as yf, json, time
cfg=lambda c: json.load(open(f"categorias/{c}/config.json",encoding="utf-8"))["ativos"]
T=[(n,n+".SA","B3") for n in cfg("brasil")]+[(n,n,"EUA") for n in cfg("eua")]
CH="trailingPE forwardPE priceToBook enterpriseToEbitda dividendYield payoutRatio returnOnEquity returnOnAssets profitMargins operatingMargins grossMargins revenueGrowth earningsGrowth totalDebt totalCash ebitda freeCashflow operatingCashflow debtToEquity currentRatio targetMeanPrice targetHighPrice targetLowPrice recommendationMean recommendationKey numberOfAnalystOpinions marketCap sector".split()
o={}
for n,y,g in T:
    try:
        t=yf.Ticker(y); i=t.info or {}
        r={"g":g,"campos":[k for k in CH if i.get(k) is not None]}
        try:
            q=t.quarterly_income_stmt; r["tri"]=0 if q is None else q.shape[1]
            r["tri_rows"]=[] if q is None else [x for x in ("Total Revenue","Net Income","Operating Income","EBITDA","Gross Profit") if x in q.index]
        except Exception as e: r["tri"]=-1
        try:
            a=t.income_stmt; r["anos"]=0 if a is None else a.shape[1]
            b=t.balance_sheet; r["bal"]=0 if b is None else b.shape[1]
            c=t.cashflow; r["cf"]=0 if c is None else c.shape[1]
        except Exception as e: r["anos"]=-1
        o[n]=r
    except Exception as e: o[n]={"g":g,"erro":str(e)[:60]}
    time.sleep(0.4)
json.dump(o,open("analise/probe_fund.json","w"),indent=1)
