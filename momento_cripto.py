"""Aba Momento Cripto: semáforo de compra/venda por criptoativo.
Três visões: técnica (preço), on-chain/fundamentos (rede, DeFi, oferta, valuation, desenvolvimento) e derivativos/sentimento."""
import json
import html as H
import os
import ui
import momento as M0
from momento import _n, _clip, _banda, _ler, tecnica

CSS = M0.CSS + """
.mo-h{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:8px;margin:0 0 12px}
.mo-sec{margin:14px 0 2px;font-size:12px;color:var(--mu);text-transform:uppercase;letter-spacing:.06em;font-weight:800}
.tip{display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;margin-left:5px;border-radius:50%;background:var(--line);color:var(--mu);font-size:10px;font-weight:800;cursor:help;vertical-align:middle;text-transform:none;font-style:normal}.tip:hover{background:var(--ac);color:#fff}
#tipbox{position:fixed;z-index:99;max-width:300px;background:#111827;color:#f9fafb;border-radius:10px;padding:10px 12px;font-size:12px;line-height:1.45;box-shadow:0 8px 24px rgba(0,0,0,.35);display:none;pointer-events:none;white-space:pre-line}
.mo-k em{display:block;font-style:normal;color:var(--mu);font-size:10.5px;margin-top:1px}
"""

NOMES = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "HYPE": "Hyperliquid", "UNI": "Uniswap", "AAVE": "Aave", "PENDLE": "Pendle"}
TIPO = {"BTC": "Moeda / reserva de valor", "ETH": "Camada 1 / contratos inteligentes", "SOL": "Camada 1 / contratos inteligentes", "HYPE": "Camada 1 + exchange de perpétuos",
        "UNI": "DeFi / exchange descentralizada", "AAVE": "DeFi / empréstimos", "PENDLE": "DeFi / mercado de rendimento"}


# ----------------------------------------------------------------------------- formatação (pt-BR)
def br(v, d=1):
    if v is None: return "–"
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def usd(v, d=1):
    if v is None: return "–"
    a = abs(v)
    for lim, suf in ((1e12, " tri"), (1e9, " bi"), (1e6, " mi"), (1e3, " mil")):
        if a >= lim: return "US$ " + br(v / lim, d) + suf
    return "US$ " + br(v, 2)


def pc(v, d=1, sinal=False):
    if v is None: return "–"
    return (("+" if v > 0 else "−" if v < 0 else "") + br(abs(v), d) if sinal else br(v, d)) + "%"


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except Exception:
        return None


def cresc(s, jan=30):
    v = [x for x in (s or {}).get("v", []) if x is not None]
    if len(v) < jan * 2: return None
    a, b = sum(v[-jan:]) / jan, sum(v[-2 * jan:-jan]) / jan
    return (a / b - 1) * 100 if b else None


def mud(s, jan=30):
    v = [x for x in (s or {}).get("v", []) if x is not None]
    if len(v) <= jan or not v[-1 - jan]: return None
    return (v[-1] / v[-1 - jan] - 1) * 100


def ma(v, n=7):
    out = []
    for i in range(len(v)):
        j = [x for x in v[max(0, i - n + 1):i + 1] if x is not None]
        out.append(sum(j) / len(j) if len(j) >= max(2, n // 2) else None)
    return out


def media(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


# ----------------------------------------------------------------------------- gráficos
CORES = ["#4f46e5", "#16a34a", "#f59e0b", "#dc2626"]


def grafico(titulo, series, janela=365, suave=0, d=None):
    """series: [(rótulo, {"d": [...], "v": [...]})] no mesmo eixo; valores escalados para mi/bi quando grandes"""
    series = [(l, s) for l, s in series if s and s.get("v")]
    if not series: return None
    ult = max(s["d"][-1] for _, s in series)
    ini = ult - janela + 1
    dias = list(range(max(ini, min(s["d"][0] for _, s in series)), ult + 1))
    vals = []
    for l, s in series:
        m = dict(zip(s["d"], s["v"]))
        v = [m.get(x) for x in dias]
        vals.append(ma(v, suave) if suave else v)
    mx = max((abs(x) for v in vals for x in v if x is not None), default=1)
    div, un = (1e9, " (bi)") if mx >= 1e9 else (1e6, " (mi)") if mx >= 1e6 else (1e3, " (mil)") if mx >= 1e5 else (1, "")
    if d is None: d = 2 if mx / div < 10 else 1 if mx / div < 100 else 0
    return {"t": titulo + un + (f" · média {suave}d" if suave else ""), "dd": dias, "d": d,
            "s": [{"l": l, "c": CORES[i % 4], "v": [None if x is None else round(x / div, 4) for x in v]} for i, ((l, _), v) in enumerate(zip(series, vals))]}


# ----------------------------------------------------------------------------- notas
def faixa(x, cortes, notas):
    return None if x is None else _banda(x, cortes, notas)


def fundamental(k, a, cg, m):
    """nota 0-10 de fundamentos on-chain + dados do detalhe. Cada bloco só entra se houver dado."""
    cm = a.get("cm") or {}
    ch = a.get("chain") or {}
    pr = a.get("prot") or {}
    x = a.get("x") or {}
    mc = num(cg.get("market_cap"))
    fdv = num(cg.get("fully_diluted_valuation"))
    circ, tot = num(cg.get("circulating_supply")), num(cg.get("total_supply"))
    fees = (a.get("fees") or ch.get("fees") or {})
    rev = a.get("rev") or {}
    hold = a.get("hold") or {}
    tvl_s = ch.get("tvl") or pr.get("tvl")
    dex = a.get("dex") or ch.get("dex") or {}
    crescimento = lambda x_: faixa(x_, (-30, -10, 0, 10, 30), (1.5, 3, 4.5, 6, 7.5, 9))
    sub = {}
    # ---- valuation
    v = []
    mvrv = (cm.get("CapMVRVCur") or {}).get("v") or []
    mvrv = mvrv[-1] if mvrv else None
    if mvrv is not None: v.append(faixa(mvrv, (0.8, 1, 1.5, 2.5, 3.5), (9.5, 8.5, 7, 5.5, 3.5, 1.5)))
    base = rev if (rev.get("d30") or 0) > 0 else fees
    ps = (mc / (base["d30"] * 365 / 30)) if mc and (base.get("d30") or 0) > 0 and k != "BTC" else None
    if ps is not None: v.append(faixa(ps, (10, 20, 40, 80, 200), (9, 7.5, 6, 4.5, 3, 1.5)))
    dil = fdv / mc if fdv and mc else None
    if dil is not None: v.append(faixa(dil, (1.05, 1.3, 2, 3), (8.5, 6.5, 4.5, 3, 2)))
    v = [i for i in v if i is not None]
    if v: sub["val"] = media(v)
    # ---- uso e crescimento
    g = []
    g_fees = cresc(base.get("s"))
    g_tvl = mud(tvl_s)
    g_act = cresc(cm.get("AdrActCnt"))
    g_tx = cresc(cm.get("TxCnt"))
    g_dex = cresc(dex.get("s"))
    for gg in (g_fees, g_tvl, g_act, g_tx, g_dex):
        if gg is not None: g.append(crescimento(gg))
    if g: sub["uso"] = media(g)
    # ---- captura de valor
    cap = None
    if hold.get("d30") is not None and a.get("prot"):
        h = hold["d30"] if hold["d30"] > 0 else 0.5 * (rev.get("d30") or 0)
        cap = h * 365 / 30 / mc * 100 if mc else None
        if cap is not None: sub["cap"] = faixa(cap, (0.5, 2, 5, 10), (2.5, 4.5, 6.5, 8, 9.5))
    elif k in ("ETH", "SOL") and fees.get("d30") and mc:
        cap = fees["d30"] * 365 / 30 / mc * 100
        sub["cap"] = faixa(cap, (1, 3, 6), (4, 5.5, 7, 8.5))
    # ---- oferta
    o = []
    emis = None
    if k == "BTC" and cm.get("IssTotNtv") and cm.get("SplyCur"):
        emis = (cm["IssTotNtv"]["v"][-1] * 365) / cm["SplyCur"]["v"][-1] * 100
    elif k == "ETH" and x.get("sup_d30"):
        s30 = x["sup_d30"]
        emis = (s30["b"] / s30["a"] - 1) * 365 / 30 * 100
    elif k == "SOL" and x.get("infl"):
        emis = x["infl"]["total"] * 100
    if emis is not None: o.append(faixa(emis, (0, 1, 2, 4, 8), (9.5, 8, 6.5, 5, 3.5, 2)))
    if dil is not None: o.append(faixa(dil, (1.05, 1.3, 2, 3), (8.5, 6.5, 4.5, 3, 2)))
    exm = mud(cm.get("SplyExNtv"))
    if exm is not None: o.append(faixa(exm, (-3, 0, 3), (8, 6.5, 5, 3.5)))
    o = [i for i in o if i is not None]
    if o: sub["oferta"] = media(o)
    # ---- segurança, descentralização e desenvolvimento
    s = []
    c4 = sum((d_.get("c4") or 0) for d_ in a.get("dev") or [])
    if k in ("BTC", "ETH", "SOL") and a.get("dev"): s.append(faixa(c4, (20, 60, 150), (4, 5.5, 7, 8.5)))
    if k == "BTC":
        if x.get("pools"): s.append(faixa(x["pools"][0][1], (30, 40), (8, 6.5, 5)))
        hs = mud(x.get("hash_s"))
        if hs is not None: s.append(faixa(hs, (-15, -5, 5), (3, 4.5, 6, 7.5)))
    if k == "SOL" and x.get("val"):
        s.append(faixa(x["val"]["nakamoto"], (8, 12, 20), (3, 4.5, 6, 7.5)))
        s.append(faixa(x["val"]["inadimpl"] / max(1, x["val"]["ativos"] + x["val"]["inadimpl"]) * 100, (2, 5), (7.5, 6, 4)))
    if k == "ETH" and x.get("beacon_stake") and tot:
        s.append(faixa(x["beacon_stake"] / tot * 100, (15, 25), (4.5, 6, 7.5)))
    if pr:
        h_ = pr.get("hacks") or 0
        s.append(8 if h_ == 0 else 6 if (pr.get("hacks_usd") or 0) < (pr.get("tvl_atual") or 1) * 0.002 else 4)
    s = [i for i in s if i is not None]
    if s: sub["seg"] = media(s)
    peso = {"val": 2, "uso": 2, "cap": 1.5, "oferta": 1.5, "seg": 1}
    tot_p = sum(peso[i] for i in sub)
    sc = sum(sub[i] * peso[i] for i in sub) / tot_p if tot_p else None
    why = {"val": [t for t in (f"MVRV {br(mvrv, 2)}" if mvrv is not None else None, f"preço/receita {br(ps, 1)}×" if ps is not None else None, f"diluição {br(dil, 2)}×" if dil is not None else None) if t],
           "uso": [t for t in (f"taxas {pc(g_fees, 0, True)}" if g_fees is not None else None, f"TVL {pc(g_tvl, 0, True)} em 30d" if g_tvl is not None else None, f"endereços {pc(g_act, 0, True)}" if g_act is not None else None,
                               f"transações {pc(g_tx, 0, True)}" if g_tx is not None else None, f"volume DEX {pc(g_dex, 0, True)}" if g_dex is not None else None) if t],
           "cap": [f"{pc(cap, 1)} ao ano do valor de mercado chega ao token"] if cap is not None else [],
           "oferta": [t for t in (f"emissão {pc(emis, 2)} ao ano" if emis is not None else None, f"diluição {br(dil, 2)}×" if dil is not None else None, f"oferta em exchanges {pc(exm, 1, True)} em 30d" if exm is not None else None) if t],
           "seg": [t for t in (f"{c4} commits em 4 semanas" if k in ("BTC", "ETH", "SOL") else None, f"maior pool com {x['pools'][0][1]}% dos blocos" if k == "BTC" and x.get("pools") else None,
                               f"Nakamoto {x['val']['nakamoto']}" if k == "SOL" and x.get("val") else None, f"{pr.get('hacks', 0)} hack(s) registrado(s)" if pr else None) if t]}
    return {"sc": _n(sc), "sub": {i: _n(j) for i, j in sub.items()}, "why": why, "mvrv": mvrv, "ps": ps, "emis": emis, "cap": cap, "dil": dil,
            "g": {"fees": g_fees, "tvl": g_tvl, "act": g_act, "tx": g_tx, "dex": g_dex}}


def sentimento(k, a, m, cg):
    hl, ok = a.get("hl") or {}, a.get("okx") or {}
    fs = (hl.get("fund_s") or {}).get("v") or []
    f_hl7 = media(fs[-7:]) if fs else None
    f_ok7 = ok.get("fund_7d")
    f7 = media([f_hl7, f_ok7])
    ls = ok.get("ls")
    fng = (m.get("fng") or {}).get("v")
    sub = {}
    if f7 is not None: sub["fund"] = faixa(f7, (-10, 0, 8, 15, 30), (9, 7.5, 6, 5, 3.5, 2))
    if fng is not None: sub["fng"] = faixa(fng, (16, 31, 46, 56, 71, 86), (9, 7.5, 6, 5, 4, 2.5, 1.5))
    if ls is not None: sub["ls"] = faixa(ls, (0.8, 1.2, 1.8, 2.5), (7.5, 6, 5, 4, 3))
    peso = {"fund": 2, "fng": 1.5, "ls": 1}
    t = sum(peso[i] for i in sub)
    sc = sum(sub[i] * peso[i] for i in sub) / t if t else None
    why = {"fund": [f"funding médio de {pc(f7, 1, True)} ao ano (Hyperliquid + OKX, 7d)"] if f7 is not None else [], "fng": [f"índice {br(fng, 0)}"] if fng is not None else [], "ls": [f"razão {br(ls, 2)}"] if ls is not None else []}
    return {"sc": _n(sc), "sub": {i: _n(j) for i, j in sub.items()}, "f7": f7, "why": why}


# ----------------------------------------------------------------------------- detalhe: KPIs e gráficos
def kp(lista, rot, val, sub=None, tip=None):
    if val is None or val == "–": return
    lista.append([rot, val, sub or "", tip or ""])


def ultimo(s):
    v = (s or {}).get("v") or []
    return v[-1] if v else None


def detalhe_onchain(k, a, cg, m, fu):
    cm = a.get("cm") or {}
    ch = a.get("chain") or {}
    pr = a.get("prot") or {}
    x = a.get("x") or {}
    G = []
    mc = num(cg.get("market_cap"))
    # mercado
    L = []
    kp(L, "Preço", "US$ " + br(num(cg.get("current_price")), 0 if (num(cg.get("current_price")) or 0) >= 1000 else 2 if (num(cg.get("current_price")) or 0) >= 1 else 4))
    kp(L, "Valor de mercado", usd(mc), f"#{cg.get('market_cap_rank')} do mercado" if cg.get("market_cap_rank") else "")
    fdv = num(cg.get("fully_diluted_valuation"))
    kp(L, "FDV (diluído)", usd(fdv), f"{br(fdv / mc, 2)}× o valor de mercado" if fdv and mc else "")
    kp(L, "Volume 24h", usd(num(cg.get("total_volume"))), f"{pc(num(cg['total_volume']) / mc * 100, 1)} do valor de mercado" if mc and cg.get("total_volume") else "")
    kp(L, "Variação 7d / 30d / 1a", " / ".join(pc(num(cg.get(c)), 0, True) for c in ("price_change_percentage_7d_in_currency", "price_change_percentage_30d_in_currency", "price_change_percentage_1y_in_currency")))
    kp(L, "Máxima histórica", usd(num(cg.get("ath"))), f"{pc(num(cg.get('ath_change_percentage')), 0, True)} desde a máxima")
    if k == "BTC": kp(L, "Dominância do BTC", pc(m.get("dom_btc")), "sobre o mercado cripto total")
    G.append(["Mercado", L])
    # valuation
    L = []
    kp(L, "MVRV (valor de mercado / valor realizado)", br(fu["mvrv"], 2) if fu["mvrv"] is not None else None, "abaixo de 1 = em média no prejuízo (zona de fundo); acima de 3 = euforia")
    kp(L, "Preço / receita anualizada", br(fu["ps"], 1) + "×" if fu["ps"] is not None else None, "valor de mercado ÷ receita (ou taxas) dos últimos 30d × 12")
    if pr.get("tvl_atual") and mc: kp(L, "Valor de mercado / TVL", br(mc / pr["tvl_atual"], 2) + "×")
    if ch.get("tvl") and mc: kp(L, "Valor de mercado / TVL da rede", br(mc / ultimo(ch["tvl"]), 1) + "×")
    G.append(["Valuation", L])
    # oferta
    L = []
    circ, tot, mx = num(cg.get("circulating_supply")), num(cg.get("total_supply")), num(cg.get("max_supply"))
    kp(L, "Oferta circulante", br(circ, 0), f"{pc(circ / mx * 100, 1)} do máximo ({br(mx, 0)})" if circ and mx else (f"{pc(circ / tot * 100, 1)} do total" if circ and tot else ""))
    if fu["emis"] is not None: kp(L, "Emissão / inflação anual", pc(fu["emis"], 2), "negativa = oferta encolhendo (queima maior que emissão)")
    if fu["dil"] is not None and fu["dil"] > 1.02: kp(L, "Diluição futura (FDV ÷ valor de mercado)", br(fu["dil"], 2) + "×", "tokens ainda a liberar")
    if cm.get("SplyExNtv"):
        e = ultimo(cm["SplyExNtv"])
        kp(L, "Oferta em exchanges", br(e, 0), f"{pc(mud(cm['SplyExNtv']), 1, True)} em 30d (queda = saindo das corretoras)")
    if cm.get("FlowInExUSD") and cm.get("FlowOutExUSD"):
        fi, fo = cm["FlowInExUSD"]["v"][-30:], cm["FlowOutExUSD"]["v"][-30:]
        net = sum(fi) - sum(fo)
        kp(L, "Fluxo líquido p/ exchanges (30d)", ("+" if net > 0 else "−") + usd(abs(net)), "positivo = entrando para vender; negativo = saindo para custódia")
    if k == "ETH" and x.get("beacon_stake"):
        kp(L, "ETH em staking", br(x["beacon_stake"], 0), f"{pc(x['beacon_stake'] / tot * 100, 1)} da oferta")
        if a.get("lido"): kp(L, "TVL da Lido (staking líquido)", usd(a["lido"]["tvl"]))
    if k == "SOL" and x.get("val"):
        kp(L, "SOL em staking", br(x["val"]["stake"], 0), f"{pc(x['val']['stake'] / x['supply']['total'] * 100, 1)} da oferta" if x.get("supply") else "")
    if k == "BTC" and x.get("halving_dias") is not None:
        kp(L, "Próximo halving", f"em ≈ {br(x['halving_dias'] / 365, 1)} anos", f"{br(x['halving_blocos'], 0)} blocos")
    G.append(["Oferta e emissão", L])
    # rede e uso
    L = []
    for nome, rot in (("AdrActCnt", "Endereços ativos / dia"), ("TxCnt", "Transações / dia"), ("TxTfrCnt", "Transferências / dia")):
        if cm.get(nome):
            kp(L, rot, br(ultimo(cm[nome]), 0), f"{pc(cresc(cm[nome]), 0, True)} (média 30d vs 30d anteriores)")
    kp(L, "Endereços com saldo", br(ultimo(cm.get("AdrBalCnt")), 0) if cm.get("AdrBalCnt") else None)
    if cm.get("FeeTotNtv"): kp(L, "Taxas pagas / dia (nativo)", br(ultimo(cm["FeeTotNtv"]), 1))
    if cm.get("HashRate") and ultimo(cm["HashRate"]): kp(L, "Hash rate", br(ultimo(cm["HashRate"]) / 1e9, 0) + " EH/s")
    if k == "BTC":
        if x.get("hash_s"): kp(L, "Hash rate (mempool.space)", br(ultimo(x["hash_s"]), 0) + " EH/s", f"{pc(mud(x['hash_s']), 1, True)} em 30d")
        d = x.get("dif") or {}
        if d: kp(L, "Próximo ajuste de dificuldade", pc(d.get("difficultyChange"), 1, True), f"em {d.get('remainingBlocks')} blocos; último {pc(d.get('previousRetarget'), 1, True)}")
        c_ = x.get("chair") or {}
        kp(L, "Mempool", br(num(c_.get("mempool_transactions")), 0) + " tx" if c_.get("mempool_transactions") is not None else None)
        kp(L, "Taxa média por transação", "US$ " + br(num(c_.get("average_transaction_fee_usd_24h")), 2) if c_.get("average_transaction_fee_usd_24h") is not None else None)
        kp(L, "Nós na rede", br(num(c_.get("nodes")), 0) if c_.get("nodes") else None)
        if x.get("c_utxo-count"): kp(L, "UTXOs", br(ultimo(x["c_utxo-count"]), 0))
        if x.get("c_miners-revenue"): kp(L, "Receita dos mineradores / dia", usd(ultimo(x["c_miners-revenue"])))
        if x.get("ln"): kp(L, "Lightning: capacidade", br(x["ln"]["total_capacity"] / 1e8, 0) + " BTC", f"{br(x['ln']['channel_count'], 0)} canais · {br(x['ln']['node_count'], 0)} nós")
    if k == "ETH" and x.get("chair"):
        c_ = x["chair"]
        kp(L, "Taxa média por transação", "US$ " + br(num(c_.get("average_transaction_fee_usd_24h")), 2) if c_.get("average_transaction_fee_usd_24h") is not None else None)
        kp(L, "Gás mediano (mempool)", br(num(c_.get("mempool_median_gas_price")) / 1e9, 2) + " gwei" if c_.get("mempool_median_gas_price") else None)
    if k == "SOL" and x.get("tps"): kp(L, "Transações por segundo", br(x["tps"]["total"], 0), f"{br(x['tps']['nao_voto'], 0)} sem contar votos")
    if k == "SOL" and x.get("epoca"): kp(L, "Transações acumuladas", br(x["epoca"]["transactionCount"] / 1e9, 0) + " bi", f"época {x['epoca']['epoch']}")
    G.append(["Rede e uso", L])
    # defi
    L = []
    if ch or pr:
        tv = ch.get("tvl") or pr.get("tvl")
        kp(L, "TVL (valor depositado)", usd(ultimo(tv)), f"{pc(mud(tv, 7), 1, True)} 7d · {pc(mud(tv, 30), 1, True)} 30d")
        for nome, rot in (("fees", "Taxas pagas pelos usuários"), ("rev", "Receita do protocolo"), ("hold", "Receita destinada aos detentores do token")):
            d = a.get(nome) or (ch.get("fees") if nome == "fees" else None)
            if d and d.get("h24") is not None:
                kp(L, rot + " (24h)", usd(d["h24"]), f"7d {usd(d.get('d7'))} · 30d {usd(d.get('d30'))}")
        dx = a.get("dex") or ch.get("dex")
        if dx and dx.get("h24") is not None: kp(L, "Volume em DEX (24h)", usd(dx["h24"]), f"30d {usd(dx.get('d30'))}")
        if a.get("perp"): kp(L, "Volume de perpétuos (24h)", usd(a["perp"]["h24"]), f"30d {usd(a['perp'].get('d30'))}")
        if ch.get("stable"): kp(L, "Stablecoins na rede", usd(ultimo(ch["stable"])), f"{pc(mud(ch['stable']), 1, True)} em 30d")
        if pr.get("borrowed"): kp(L, "Total emprestado", usd(pr["borrowed"]))
        if pr.get("staking"): kp(L, "Token em staking no protocolo", usd(pr["staking"]))
        if a.get("tesouro"): kp(L, "Tesouro do protocolo", usd(a["tesouro"]["total"]))
        if pr.get("cadeias"): kp(L, "TVL por rede", " · ".join(f"{n} {usd(v, 0)}" for n, v in pr["cadeias"][:4]))
        if pr: kp(L, "Hacks registrados", f"{pr['hacks']}", usd(pr["hacks_usd"]) + " perdidos" if pr["hacks"] else "nenhum")
        if pr.get("levantado_usd"): kp(L, "Capital levantado (VC)", usd(pr["levantado_usd"]))
    G.append(["DeFi e valor capturado", L])
    # segurança / dev
    L = []
    for d_ in a.get("dev") or []:
        kp(L, d_["repo"], f"{br(d_.get('c4'), 0)} commits em 4 sem.", f"{br(d_.get('c52'), 0)} em 52 sem · ★ {br(d_.get('stars'), 0)} · último push {d_.get('push')}")
    if k == "BTC" and x.get("pools"): kp(L, "Maiores pools (7d)", " · ".join(f"{n} {p}%" for n, p in x["pools"][:4]), "concentração de mineração")
    if k == "SOL" and x.get("val"):
        v = x["val"]
        kp(L, "Validadores ativos", br(v["ativos"], 0), f"{v['inadimpl']} inadimplentes")
        kp(L, "Coeficiente de Nakamoto", br(v["nakamoto"], 0), f"validadores necessários para travar 33% · {v['super_maioria']} para 67%")
        kp(L, "Top 10 validadores", pc(v["top10_pct"], 1), "do stake total")
        kp(L, "Comissão média dos validadores", pc(v["comissao_media"], 1))
    if k == "HYPE": kp(L, "Código", "nó parcialmente aberto", "dev. menos auditável por terceiros")
    G.append(["Segurança, descentralização e desenvolvimento", L])
    G = [[t, l] for t, l in G if l]
    # gráficos
    GR = []
    def add(g):
        if g: GR.append(g)
    add(grafico("MVRV", [("MVRV", cm.get("CapMVRVCur"))], d=2))
    add(grafico("Endereços ativos por dia", [("ativos", cm.get("AdrActCnt"))], suave=7))
    add(grafico("Transações por dia", [("tx", cm.get("TxCnt"))], suave=7))
    if k == "BTC":
        add(grafico("Hash rate (EH/s)", [("EH/s", x.get("hash_s"))], d=0))
        add(grafico("Receita dos mineradores (US$)", [("receita", x.get("c_miners-revenue"))], suave=7))
        add(grafico("Capacidade da rede Lightning (BTC)", [("BTC", x.get("ln_s"))], d=0))
    if ch.get("fees"): add(grafico("Taxas pagas na rede (US$)", [("taxas", ch["fees"].get("s"))], suave=7))
    if a.get("fees") and not ch: add(grafico("Taxas e receita do protocolo (US$)", [("taxas", a["fees"].get("s")), ("receita", (a.get("rev") or {}).get("s"))], suave=7))
    elif a.get("rev") and ch: add(grafico("Receita do protocolo (US$)", [("receita", a["rev"].get("s")), ("detentores", (a.get("hold") or {}).get("s"))], suave=7))
    add(grafico("TVL (US$)", [("TVL", ch.get("tvl") or pr.get("tvl"))]))
    add(grafico("Stablecoins na rede (US$)", [("stablecoins", ch.get("stable"))]))
    dx = a.get("dex") or ch.get("dex")
    add(grafico("Volume em DEX por dia (US$)", [("DEX", (dx or {}).get("s"))], suave=7))
    if a.get("perp"): add(grafico("Volume de perpétuos por dia (US$)", [("perpétuos", a["perp"].get("s"))], suave=7))
    add(grafico("Oferta em exchanges", [("exchanges", cm.get("SplyExNtv"))], d=0))
    if cm.get("FlowInExUSD") and cm.get("FlowOutExUSD"):
        fi, fo = cm["FlowInExUSD"], cm["FlowOutExUSD"]
        mo = dict(zip(fo["d"], fo["v"]))
        add(grafico("Fluxo líquido p/ exchanges (US$, entrada − saída)", [("líquido", {"d": fi["d"], "v": [v - mo.get(d_, v) for d_, v in zip(fi["d"], fi["v"])]})], suave=7))
    return G, GR


TIPS = {"fng": "Índice de 0 a 100 que resume o humor do mercado cripto (volatilidade, volume, redes sociais e dominância do BTC). Abaixo de 25 = medo extremo: vendedores exaustos, historicamente uma boa zona de acumulação. Acima de 75 = ganância extrema: mercado eufórico, risco maior de topo. Aqui é lido de forma contrária.", "fund": "Funding é a taxa que compradores e vendedores de contratos perpétuos (futuros sem vencimento) pagam uns aos outros para manter o preço do perpétuo colado ao preço à vista. Positivo = quem está comprado paga quem está vendido (otimismo e alavancagem na compra). Negativo = vendidos pagam comprados (pessimismo). Aparece anualizado para comparar: ≈ 10% ao ano é o normal. Muito acima disso indica compra esticada e risco de liquidações em cascata; negativo por muito tempo pode preceder um repique (short squeeze).", "fundh": "A Hyperliquid cobra o funding a cada hora. Este é o valor da última hora, em %. Para ter uma ideia: 0,0013% por hora equivale a ≈ 11% ao ano, o nível neutro de mercado. Valores negativos significam que os vendidos estão pagando.", "prem": "Diferença entre o preço do contrato perpétuo e o preço de referência (oráculo, ligado ao preço à vista). Positivo = perpétuo mais caro que o à vista: há mais demanda por compra alavancada, o que tende a elevar o funding. Negativo = perpétuo com desconto: mais gente querendo vender ou se proteger, pressão vendedora. Perto de zero = equilíbrio; variações de ±0,05% são ruído.", "oi": "Open interest é o valor total dos contratos de derivativos ainda abertos (posições que não foram zeradas). Sobe junto com o preço = dinheiro novo entrando na tendência de alta. Sobe com o preço caindo = vendidos acumulando (combustível para queda ou para um squeeze). Cai forte = liquidações e zeragem de posições. Comparado ao valor de mercado, mostra o nível de alavancagem do ativo.", "oi30": "Quanto o open interest (posições abertas) da OKX mudou em 30 dias. Queda junto com preço em baixa costuma indicar limpeza de alavancagem (capitulação), que muitas vezes antecede fundos. Alta junto com preço em alta indica alavancagem crescendo.", "ls": "Número de contas compradas dividido pelo de contas vendidas na OKX. Acima de 1 = mais contas compradas que vendidas. É um termômetro contrário: extremos de compra (acima de ≈ 2,5) mostram a multidão toda do mesmo lado, e o mercado costuma andar contra a maioria. Conta pessoas, não dinheiro: o varejo tende a ficar comprado.", "vol": "Volume financeiro negociado em contratos perpétuos nas últimas 24h, comparado ao volume à vista. Derivativos muito maiores que o à vista indicam um mercado dominado por especulação alavancada, com preços mais sujeitos a movimentos bruscos de liquidação."}


def detalhe_sent(k, a, m, cg, se):
    hl, ok = a.get("hl") or {}, a.get("okx") or {}
    mc = num(cg.get("market_cap"))
    L = []
    fng = m.get("fng") or {}
    PT = {"Extreme Fear": "Medo extremo", "Fear": "Medo", "Neutral": "Neutro", "Greed": "Ganância", "Extreme Greed": "Ganância extrema"}
    kp(L, "Medo e Ganância (mercado)", f"{br(fng.get('v'), 0)} · {PT.get(fng.get('c'), fng.get('c'))}" if fng else None, "índice contrário: medo extremo costuma ser zona de compra", TIPS["fng"])
    kp(L, "Funding anualizado (Hyperliquid, média 7d)", pc(media((hl.get("fund_s") or {}).get("v", [])[-7:]), 1, True), "positivo = comprados pagam vendidos", TIPS["fund"])
    kp(L, "Funding anualizado (OKX, 7d / 30d)", f"{pc(ok.get('fund_7d'), 1, True)} / {pc(ok.get('fund_30d'), 1, True)}" if ok.get("fund_7d") is not None else None, "referência neutra ≈ +10% ao ano", TIPS["fund"])
    kp(L, "Funding agora (Hyperliquid, por hora)", pc(hl["fund_h"] * 100, 4, True) if hl.get("fund_h") is not None else None, None, TIPS["fundh"])
    kp(L, "Prêmio do perpétuo vs. oráculo", pc(hl["premio"] * 100, 3, True) if hl.get("premio") is not None else None, "perpétuo acima (+) ou abaixo (−) do preço à vista", TIPS["prem"])
    oi = (hl.get("oi_usd") or 0) + (ok.get("oi_usd") or 0)
    kp(L, "Open interest (Hyperliquid + OKX)", usd(oi) if oi else None, f"{pc(oi / mc * 100, 1)} do valor de mercado" if oi and mc else "", TIPS["oi"])
    if ok.get("oi_s"): kp(L, "Open interest OKX: variação 30d", pc(mud(ok["oi_s"]), 1, True), None, TIPS["oi30"])
    kp(L, "Razão compra/venda de contas (OKX)", br(ok.get("ls"), 2) if ok.get("ls") else None, ">2 = muitos comprados (risco de aperto); <1 = maioria vendida", TIPS["ls"])
    kp(L, "Volume de derivativos 24h (Hyperliquid)", usd(hl.get("vol24")) if hl.get("vol24") else None, f"spot (mercado): {usd(num(cg.get('total_volume')))}", TIPS["vol"])
    GR = []
    def add(g):
        if g: GR.append(g)
    add(grafico("Medo e Ganância (90 dias)", [("índice", {"d": fng.get("d", []), "v": fng.get("h", [])})], janela=90, d=0))
    add(grafico("Funding anualizado % (Hyperliquid, 20 dias)", [("funding", hl.get("fund_s"))], janela=20, d=1))
    add(grafico("Open interest (US$, OKX)", [("OI", ok.get("oi_s"))], janela=90))
    add(grafico("Razão compra/venda de contas (OKX)", [("L/S", ok.get("ls_s"))], janela=60, d=2))
    return [["Derivativos e sentimento", L]], GR


# ----------------------------------------------------------------------------- caixinhas: o que o dado significa + o que está dizendo agora
def leit(sc):
    return "positiva (sinal de compra)" if sc >= 6.5 else "negativa (sinal de venda)" if sc <= 3.5 else "neutra"


def tem(*a):
    return all(x is not None for x in a)


FIXO = {
    "Valor de mercado": "Preço × oferta circulante: o tamanho do ativo. O ranking compara com todas as criptomoedas.",
    "FDV": "Fully Diluted Valuation: valor de mercado se TODOS os tokens (inclusive os ainda não liberados) já estivessem em circulação. Quanto maior que o valor de mercado, mais tokens ainda vão entrar no mercado (pressão vendedora futura).",
    "Volume 24h": "Valor negociado à vista em 24h. Dividido pelo valor de mercado, mede liquidez e interesse pelo ativo.",
    "Variação 7d": "Variação do preço em 7 dias, 30 dias e 1 ano.",
    "Máxima histórica": "Maior preço já negociado e quanto o preço atual está abaixo dele.",
    "Dominância do BTC": "Parcela do Bitcoin no valor total do mercado cripto. Subindo = capital fugindo para o ativo mais seguro (altcoins sofrem); caindo = rotação para altcoins.",
    "MVRV": "Razão entre o valor de mercado e o valor realizado (preço médio pelo qual cada moeda foi movida pela última vez, ou seja, o custo médio dos detentores). Abaixo de 1 a maioria está no prejuízo — historicamente zona de fundo. De 1 a 2,5 é normal. Acima de 3,5 é euforia.",
    "Preço / receita": "Quantos anos de receita o mercado está pagando: valor de mercado ÷ (receita dos últimos 30 dias × 12). Parecido com o P/L das ações: menor = mais barato.",
    "Valor de mercado / TVL": "Compara o valor do token com o dinheiro depositado (TVL). Abaixo de 1 o token vale menos que o capital depositado.",
    "Oferta circulante": "Moedas já em circulação e quanto isso representa do máximo (ou do total) que vai existir.",
    "Emissão": "Quantas moedas novas entram por ano, em % da oferta (inflação). Negativa = a queima supera a emissão e a oferta encolhe.",
    "Diluição futura": "Quanto o valor de mercado cresceria se todos os tokens ainda bloqueados entrassem em circulação.",
    "Oferta em exchanges": "Moedas guardadas em corretoras, prontas para venda. Caindo = investidores retirando para custódia própria (menos pressão de venda); subindo = movendo para vender.",
    "Fluxo líquido": "Entradas menos saídas de corretoras nos últimos 30 dias, em dólares.",
    "ETH em staking": "Moedas travadas para validar a rede. Mais staking = menos oferta disponível para venda e rede mais segura.",
    "SOL em staking": "Moedas travadas com validadores. Mais staking = menos oferta disponível para venda e rede mais segura.",
    "Próximo halving": "A cada ≈ 4 anos a emissão de novos BTC é cortada pela metade, reduzindo a oferta nova. Historicamente as altas fortes vieram nos meses seguintes.",
    "Endereços ativos": "Endereços que enviaram ou receberam algo no dia: aproximação do número de usuários ativos e do uso real da rede.",
    "Transações /": "Transações confirmadas por dia: demanda por espaço na rede.",
    "Transferências": "Transferências de valor por dia (exclui chamadas de contrato): uso como meio de pagamento e transferência.",
    "Endereços com saldo": "Endereços que guardam algum saldo: mede adoção e a base de detentores. Crescendo = mais gente entrando.",
    "Taxas pagas / dia": "Taxas pagas pelos usuários à rede, em moeda nativa: demanda por espaço de bloco.",
    "Hash rate": "Poder computacional dedicado à mineração. Quanto maior, mais caro atacar a rede e mais confiança dos mineradores.",
    "Próximo ajuste": "A cada 2.016 blocos a dificuldade se ajusta ao hash rate. Positivo = mineradores aumentaram a potência (rede mais segura); negativo = mineradores desligaram máquinas (estresse de rentabilidade).",
    "Mempool": "Fila de transações aguardando confirmação. Fila grande = demanda alta ou rede congestionada; vazia = demanda baixa.",
    "Taxa média": "Custo médio para fazer uma transação. Baixo = pouca demanda por espaço ou rede eficiente.",
    "Nós na rede": "Nós completos visíveis, que validam a rede por conta própria: quanto mais, mais descentralizada.",
    "UTXOs": "Saídas de transação ainda não gastas: cresce com a fragmentação de saldos e é usado para medir atividade.",
    "Receita dos mineradores": "Subsídio de bloco + taxas pagas aos mineradores por dia. Se cair abaixo do custo de operar, máquinas são desligadas (capitulação de mineradores).",
    "Lightning": "Rede de pagamentos em segunda camada do Bitcoin. Capacidade e canais medem a adoção para pagamentos rápidos.",
    "Gás mediano": "Preço por unidade de computação no Ethereum, em gwei. Baixo = rede barata ou pouca demanda.",
    "Transações por segundo": "Vazão atual da rede Solana, contando votos dos validadores ou não.",
    "TVL": "Total Value Locked: valor depositado nos contratos do protocolo ou da rede. Mede confiança e uso do capital. Atenção: em dólares, cai junto com o preço dos ativos depositados.",
    "Taxas pagas pelos usuários": "Total que os usuários pagam para usar o protocolo ou a rede (inclui a parte que vai para os provedores de liquidez).",
    "Receita do protocolo": "Parte das taxas que fica com o protocolo, e não com os provedores de liquidez. É o que pode sustentar o valor do token.",
    "Receita destinada": "Parte da receita que chega a quem segura o token (recompra, queima ou distribuição). É a captura de valor real pelo token.",
    "Volume em DEX": "Valor negociado em exchanges descentralizadas da rede ou protocolo.",
    "Volume de perpétuos": "Valor negociado em contratos perpétuos no protocolo.",
    "Stablecoins na rede": "Dólares digitais disponíveis na rede: combustível para compras e para o DeFi. Crescendo = entrada de capital.",
    "Total emprestado": "Valor emprestado pelo protocolo: demanda por crédito. Dividido pelo TVL, mostra a utilização.",
    "Token em staking": "Valor do token travado no próprio protocolo (reduz a oferta circulante).",
    "Tesouro": "Fundos pertencentes ao protocolo/DAO, usados para financiar desenvolvimento e incentivos.",
    "Hacks": "Histórico de ataques ao protocolo que causaram perdas.",
    "Coeficiente de Nakamoto": "Menor número de validadores que, juntos, controlam mais de 33% do stake e poderiam travar a rede. Maior = mais descentralizada.",
    "Top 10": "Parcela do stake total nas 10 maiores operadoras. Menor = stake mais distribuído.",
    "Validadores ativos": "Validadores participando do consenso; inadimplentes são os que estão offline.",
    "Comissão média": "Percentual que os validadores retêm das recompensas de quem delega.",
    "Maiores pools": "Pools de mineração que produziram mais blocos na última semana. Concentração alta = risco de censura ou de ataque de 51%.",
    "/": "Atividade de desenvolvimento: commits (alterações de código) nas últimas 4 e 52 semanas, estrelas e último push. Muitos commits = projeto mantido ativamente; poucos em contratos maduros é normal.",
}
FIXO_SUB = {
    "val": "Mede se o ativo está barato ou caro: MVRV (preço contra o custo médio dos detentores), preço/receita e diluição futura.",
    "uso": "Mede se o uso da rede ou protocolo está crescendo: taxas, TVL, endereços ativos, transações e volume (média de 30d contra os 30d anteriores).",
    "cap": "Mede quanto da receita chega a quem segura o token (recompra, queima, distribuição).",
    "oferta": "Mede a pressão de oferta: emissão de novas moedas, diluição futura e movimento de moedas para as corretoras.",
    "seg": "Mede descentralização, segurança e manutenção do código.",
}


def cresc_txt(g, o):
    if g is None: return None
    return (f"{o} em queda forte ({pc(g, 0, True)}): perda de uso" if g < -15 else f"{o} em queda ({pc(g, 0, True)})" if g < 0 else
            f"{o} estável ({pc(g, 0, True)})" if g < 10 else f"{o} crescendo ({pc(g, 0, True)}): uso aumentando")


def agora_oc(rot, k, a, cg, m, fu):
    cm, ch, pr, x = a.get("cm") or {}, a.get("chain") or {}, a.get("prot") or {}, a.get("x") or {}
    mc = num(cg.get("market_cap"))
    g = fu["g"]
    ult_ = lambda s: ultimo(s)
    if rot.startswith("FDV") or rot.startswith("Diluição"):
        d = fu["dil"]
        if d is None: return None
        return "praticamente tudo já circula: pouca diluição futura" if d <= 1.05 else f"diluição moderada: ainda faltam {pc((d - 1) * 100, 0)} em tokens a liberar" if d <= 1.5 else f"muitos tokens a liberar ({br(d, 2)}× o valor de mercado): pressão vendedora futura"
    if rot.startswith("Volume 24h"):
        v = num(cg.get("total_volume"))
        if not tem(v, mc): return None
        r = v / mc * 100
        return f"{pc(r, 1)} do valor de mercado girou no dia: " + ("pouco interesse" if r < 2 else "liquidez normal" if r < 6 else "interesse alto" if r < 15 else "giro muito alto, típico de pânico ou euforia")
    if rot.startswith("Variação"):
        v = num(cg.get("price_change_percentage_30d_in_currency"))
        if v is None: return None
        return (f"queda de {pc(abs(v), 0)} em 30 dias: ativo sob forte estresse e possivelmente sobrevendido" if v < -25 else f"queda de {pc(abs(v), 0)} em 30 dias: correção" if v < -8 else
                "preço lateral no mês" if v < 8 else f"alta de {pc(v, 0)} em 30 dias: tendência positiva" if v < 25 else f"alta forte de {pc(v, 0)} em 30 dias: pode estar esticado")
    if rot.startswith("Máxima"):
        v = num(cg.get("ath_change_percentage"))
        if v is None: return None
        return ("perto da máxima: sem desconto" if v > -10 else f"correção moderada ({pc(v, 0)} da máxima)" if v > -40 else f"queda profunda ({pc(v, 0)}): grande desconto, mas pode refletir deterioração" if v > -70 else f"queda extrema ({pc(v, 0)} da máxima)")
    if rot.startswith("Dominância"):
        d = m.get("dom_btc")
        return None if d is None else ("capital concentrado no BTC: altcoins costumam sofrer" if d > 60 else "dominância moderada a alta: BTC lidera" if d > 50 else "dominância baixa: apetite por altcoins")
    if rot.startswith("MVRV"):
        v = fu["mvrv"]
        if v is None: return None
        return (f"{br(v, 2)}: muito abaixo do custo médio, capitulação; historicamente zona de fundo" if v < 0.8 else f"{br(v, 2)}: abaixo do custo médio, a maioria dos detentores está no prejuízo" if v < 1 else
                f"{br(v, 2)}: pouco acima do custo médio, lucro pequeno, região de acumulação" if v < 1.5 else f"{br(v, 2)}: lucro moderado, mercado saudável" if v < 2.5 else f"{br(v, 2)}: lucros altos, atenção" if v < 3.5 else f"{br(v, 2)}: euforia, risco de topo")
    if rot.startswith("Preço / receita"):
        v = fu["ps"]
        return None if v is None else f"{br(v, 1)} anos de receita: " + ("barato" if v < 10 else "razoável" if v < 20 else "esticado" if v < 40 else "caro" if v < 80 else "muito caro")
    if rot.startswith("Valor de mercado / TVL"):
        t = pr.get("tvl_atual") or ultimo(ch.get("tvl"))
        if not tem(mc, t): return None
        r = mc / t
        return f"{br(r, 2)}×: " + ("token barato frente ao capital depositado" if r < 0.5 else "token abaixo do capital depositado" if r < 1 else "valor próximo ao capital depositado" if r < 3 else "token caro frente ao TVL, sustentado por expectativa e não pelo capital")
    if rot.startswith("Oferta circulante"):
        circ, mx, tot = num(cg.get("circulating_supply")), num(cg.get("max_supply")), num(cg.get("total_supply"))
        r = circ / (mx or tot) * 100 if circ and (mx or tot) else None
        return None if r is None else (f"{pc(r, 0)} já emitido: oferta quase toda em circulação, pouca diluição" if r > 95 else f"{pc(r, 0)} já emitido: ainda há tokens a entrar" if r > 70 else f"só {pc(r, 0)} emitido: muita oferta ainda por vir")
    if rot.startswith("Emissão"):
        e = fu["emis"]
        return None if e is None else (f"{pc(e, 2)}: oferta encolhendo (deflacionário)" if e < 0 else f"{pc(e, 2)}: emissão baixa" if e < 1.5 else f"{pc(e, 2)}: emissão moderada" if e < 4 else f"{pc(e, 2)}: emissão alta, diluição relevante para quem segura")
    if rot.startswith("Oferta em exchanges"):
        v = mud(cm.get("SplyExNtv"))
        return None if v is None else (f"{pc(v, 1, True)} em 30d: saindo das corretoras, sinal de acumulação" if v < -3 else f"{pc(v, 1, True)} em 30d: leve saída das corretoras" if v < 0 else f"{pc(v, 1, True)} em 30d: estável" if v < 3 else f"{pc(v, 1, True)} em 30d: mais oferta pronta para venda")
    if rot.startswith("Fluxo líquido"):
        fi, fo = (cm.get("FlowInExUSD") or {}).get("v"), (cm.get("FlowOutExUSD") or {}).get("v")
        if not (fi and fo): return None
        net = sum(fi[-30:]) - sum(fo[-30:])
        return "mais moedas entraram nas corretoras do que saíram: possível pressão de venda" if net > 0 else "saída líquida das corretoras: movimento de custódia/acumulação"
    if rot.endswith("em staking") and k in ("ETH", "SOL"):
        st = x.get("beacon_stake") if k == "ETH" else (x.get("val") or {}).get("stake")
        tot = num(cg.get("total_supply"))
        if not tem(st, tot): return None
        r = st / tot * 100
        return f"{pc(r, 0)} da oferta travada: " + ("alto, pouca oferta líquida" if r > 30 else "relevante" if r > 15 else "baixo")
    if rot.startswith("Próximo halving"):
        d = x.get("halving_dias")
        return None if d is None else f"faltam ≈ {br(d / 30, 0)} meses; o mercado costuma antecipar o evento, e o efeito histórico veio mais tarde"
    if rot.startswith("Endereços ativos"): return cresc_txt(g["act"], "uso")
    if rot.startswith("Transações /"): return cresc_txt(g["tx"], "transações")
    if rot.startswith("Transferências"): return cresc_txt(cresc(cm.get("TxTfrCnt")), "transferências")
    if rot.startswith("Endereços com saldo"):
        v = mud(cm.get("AdrBalCnt"))
        return None if v is None else f"{pc(v, 1, True)} em 30d: " + ("base de detentores crescendo" if v > 0.5 else "base estável" if v > -0.5 else "base de detentores encolhendo")
    if rot.startswith("Hash rate"):
        v = mud(x.get("hash_s"))
        return None if v is None else (f"{pc(v, 0, True)} em 30d: mineradores desligando máquinas (estresse)" if v < -5 else "estável" if v < 5 else f"{pc(v, 0, True)} em 30d: potência crescendo, rede mais segura")
    if rot.startswith("Próximo ajuste"):
        d = (x.get("dif") or {}).get("difficultyChange")
        return None if d is None else ("previsto subir: mineradores aumentaram a potência" if d > 2 else "previsto cair: mineradores saindo" if d < -2 else "ajuste pequeno: rede estável")
    if rot.startswith("Mempool"):
        n = num((x.get("chair") or {}).get("mempool_transactions"))
        return None if n is None else ("fila pequena: pouca demanda por espaço" if n < 20000 else "fila normal" if n < 80000 else "fila grande: demanda alta ou congestionamento")
    if rot.startswith("Receita dos mineradores"):
        s = x.get("c_miners-revenue")
        v = mud(s)
        return None if v is None else f"{pc(v, 0, True)} em 30d: " + ("receita caindo, pressiona mineradores menos eficientes" if v < -10 else "estável" if v < 10 else "receita subindo")
    if rot.startswith("TVL"):
        v = mud(ch.get("tvl") or pr.get("tvl"))
        return None if v is None else (f"{pc(v, 0, True)} em 30d: forte saída de capital (inclui queda de preço dos ativos)" if v < -20 else f"{pc(v, 0, True)} em 30d: capital saindo" if v < 0 else f"{pc(v, 0, True)} em 30d: estável" if v < 10 else f"{pc(v, 0, True)} em 30d: capital entrando")
    if rot.startswith("Taxas pagas pelos"): return cresc_txt(g["fees"], "taxas")
    if rot.startswith("Receita do protocolo"): return cresc_txt(cresc((a.get("rev") or {}).get("s")), "receita")
    if rot.startswith("Receita destinada"):
        c_ = fu["cap"]
        return None if c_ is None else ("quase nada chega ao token hoje" if c_ < 0.1 else f"equivale a {pc(c_, 1)} ao ano do valor de mercado: " + ("baixo" if c_ < 2 else "razoável" if c_ < 5 else "alto"))
    if rot.startswith("Volume em DEX"): return cresc_txt(g["dex"], "volume")
    if rot.startswith("Stablecoins"):
        v = mud(ch.get("stable"))
        return None if v is None else (f"{pc(v, 1, True)} em 30d: dólares saindo da rede" if v < -3 else f"{pc(v, 1, True)} em 30d: estável" if v < 3 else f"{pc(v, 1, True)} em 30d: entrada de capital")
    if rot.startswith("Total emprestado"):
        b, t = pr.get("borrowed"), pr.get("tvl_atual")
        return None if not tem(b, t) or not t else f"{pc(b / t * 100, 0)} do TVL está emprestado: " + ("utilização baixa" if b / t < .3 else "utilização saudável" if b / t < .6 else "utilização alta")
    if rot.startswith("Tesouro"):
        t = (a.get("tesouro") or {}).get("total")
        return None if not tem(t, mc) else f"equivale a {pc(t / mc * 100, 0)} do valor de mercado"
    if rot.startswith("Hacks"):
        return None if not pr else ("sem hacks registrados" if not pr.get("hacks") else f"{pr['hacks']} incidente(s), {usd(pr['hacks_usd'])} perdidos: " + ("pequeno frente ao TVL" if pr["hacks_usd"] < (pr.get("tvl_atual") or 1) * 0.002 else "relevante"))
    if rot.startswith("Coeficiente"):
        n = (x.get("val") or {}).get("nakamoto")
        return None if n is None else f"{n}: " + ("baixo, poucos validadores controlam a rede" if n < 10 else "mediano" if n < 20 else "bom nível de descentralização")
    if rot.startswith("Top 10"):
        v = (x.get("val") or {}).get("top10_pct")
        return None if v is None else ("stake bem distribuído" if v < 30 else "stake moderadamente concentrado" if v < 45 else "stake concentrado")
    if rot.startswith("Maiores pools"):
        p = (x.get("pools") or [[0, None]])[0][1]
        return None if p is None else ("mineração diversificada" if p < 30 else "concentração moderada" if p < 40 else "concentração alta")
    if "/" in rot:
        d_ = next((d for d in a.get("dev") or [] if d["repo"] == rot), None)
        if not d_ or d_.get("c4") is None: return None
        c4 = d_["c4"]
        return f"{c4} commits em 4 semanas: " + ("muito ativo" if c4 >= 150 else "ativo" if c4 >= 60 else "atividade moderada" if c4 >= 20 else "pouca atividade (comum em contratos maduros e já auditados)")
    return None


def agora_sent(rot, k, a, cg, m, se):
    hl, ok = a.get("hl") or {}, a.get("okx") or {}
    mc = num(cg.get("market_cap"))
    p30 = num(cg.get("price_change_percentage_30d_in_currency"))
    def fund_txt(f):
        return (f"{pc(f, 1, True)} ao ano: vendidos pagando muito, mercado pessimista e posicionado para baixo; favorece repique (short squeeze)" if f < -10 else f"{pc(f, 1, True)} ao ano: levemente negativo, leve pessimismo" if f < 0 else
                f"{pc(f, 1, True)} ao ano: nível normal, sem excesso" if f < 8 else f"{pc(f, 1, True)} ao ano: um pouco acima do normal, otimismo moderado" if f < 15 else
                f"{pc(f, 1, True)} ao ano: alto, compradores alavancados e risco de correção" if f < 30 else f"{pc(f, 1, True)} ao ano: muito alto, compra esticada e risco de liquidações")
    if rot.startswith("Medo e Ganância"):
        v = (m.get("fng") or {}).get("v")
        return None if v is None else (f"{br(v, 0)}: medo extremo, vendedores exaustos; historicamente favorece compra gradual" if v <= 25 else f"{br(v, 0)}: medo, mercado cauteloso" if v <= 45 else f"{br(v, 0)}: neutro" if v <= 55 else
                                       f"{br(v, 0)}: ganância, otimismo crescente" if v <= 75 else f"{br(v, 0)}: ganância extrema, mercado eufórico e risco de topo")
    if rot.startswith("Funding anualizado (Hyperliquid"):
        f = media(((hl.get("fund_s") or {}).get("v") or [])[-7:])
        return None if f is None else fund_txt(f)
    if rot.startswith("Funding anualizado (OKX"):
        f = ok.get("fund_7d")
        return None if f is None else "últimos 7 dias: " + fund_txt(f)
    if rot.startswith("Funding agora"):
        h = hl.get("fund_h")
        return None if h is None else fund_txt(h * 24 * 365 * 100)
    if rot.startswith("Prêmio"):
        p = (hl.get("premio") or 0) * 100 if hl.get("premio") is not None else None
        return None if p is None else (f"{pc(p, 3, True)}: perpétuo acima do à vista, demanda alavancada de compra" if p > 0.05 else f"{pc(p, 3, True)}: perpétuo com desconto, pressão vendedora ou busca por proteção" if p < -0.05 else f"{pc(p, 3, True)}: colado ao preço à vista, sem desequilíbrio relevante")
    if rot.startswith("Open interest (") or rot.startswith("Open interest OKX"):
        v = mud(ok.get("oi_s"))
        if v is None or p30 is None: return None
        cenario = ("alavancagem sendo zerada com o preço em queda: limpeza típica de capitulação, que costuma anteceder fundos" if p30 < 0 and v < 0 else
                   "preço caindo com posições abertas aumentando: vendidos acumulando, combustível para queda ou para um squeeze" if p30 < 0 else
                   "preço subindo com posições aumentando: dinheiro novo e alavancagem crescendo na alta" if v > 0 else "preço subindo com posições sendo fechadas: realização de lucros")
        return f"preço {pc(p30, 0, True)} e OI {pc(v, 0, True)} em 30d: {cenario}"
    if rot.startswith("Razão compra/venda"):
        v = ok.get("ls")
        return None if v is None else (f"{br(v, 2)}: multidão comprada, risco de aperto de compradores" if v > 2.5 else f"{br(v, 2)}: bem mais contas compradas que vendidas" if v > 1.8 else f"{br(v, 2)}: levemente comprado" if v > 1.2 else
                                       f"{br(v, 2)}: equilibrado" if v > 0.8 else f"{br(v, 2)}: maioria vendida, cenário contrário favorável a alta (short squeeze)")
    if rot.startswith("Volume de derivativos"):
        d, s = hl.get("vol24"), num(cg.get("total_volume"))
        return None if not tem(d, s) or not s else f"na Hyperliquid equivale a {pc(d / s * 100, 0)} do volume à vista global do ativo"
    return None


def decorar(G, f):
    for _, L in G:
        for it in L:
            fixo = it[3] or next((v for kx, v in FIXO.items() if it[0].startswith(kx) and kx != "/"), "") or (FIXO["/"] if "/" in it[0] and " " not in it[0] else "")
            ag = f(it[0])
            it[3] = fixo + (("\n\nAgora: " + ag) if ag and fixo else "")


def tips_sub(sub, why, fixo):
    out = {}
    for k_, v in sub.items():
        if k_ in why and v is not None:
            out[k_] = fixo[k_] + f"\n\nAgora: nota {br(v, 1)} de 10, leitura {leit(v)}. Pesaram: " + "; ".join(why[k_]) + "."
    return out


# ----------------------------------------------------------------------------- dados
def dados(raiz):
    cats = os.path.join(raiz, "categorias", "cripto")
    cfg = json.load(open(os.path.join(cats, "config.json"), encoding="utf-8"))
    f = os.path.join(cats, "onchain.json")
    oc = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    m = oc.get("mercado") or {}
    btc = _ler(raiz, "cripto", "BENCH_BTC")
    rows = []
    for n in cfg["ativos"]:
        c = _ler(raiz, "cripto", n)
        if c is None: continue
        r = {"i": len(rows), "n": n, "nome": NOMES.get(n, n), "s": TIPO.get(n, ""),
             "t1": tecnica(c, None if n == "BTC" else btc, "Cripto", "US$", "BTC", ano=365, fw="W-SUN", esc=(40, 30, 45), cap_rsi=40)}
        a = (oc.get("ativos") or {}).get(n)
        if a and a.get("cg"):
            cg = a["cg"]
            fu = fundamental(n, a, cg, m)
            G, GR = detalhe_onchain(n, a, cg, m, fu)
            fu["G"], fu["GR"] = G, GR
            decorar(G, lambda rot: agora_oc(rot, n, a, cg, m, fu))
            fu["tips"] = tips_sub(fu["sub"], fu["why"], FIXO_SUB)
            fu.pop("why", None)
            fu.pop("g", None)
            r["fu"] = fu
            se = sentimento(n, a, m, cg)
            G2, GR2 = detalhe_sent(n, a, m, cg, se)
            se["G"], se["GR"] = G2, GR2
            decorar(G2, lambda rot: agora_sent(rot, n, a, cg, m, se))
            se["tips"] = tips_sub(se["sub"], se["why"], {"fund": TIPS["fund"], "fng": TIPS["fng"], "ls": TIPS["ls"]})
            se.pop("why", None)
            r["se"] = se
        rows.append(r)
    mk = {}
    if m:
        mk = {"fng": (m.get("fng") or {}).get("v"), "fngc": (m.get("fng") or {}).get("c"), "dom": m.get("dom_btc"), "mcap": m.get("mcap"), "vol": m.get("vol"), "mc24": m.get("mcap_24h")}
    return {"rows": rows, "mk": mk, "ts": oc.get("ts")}


JS = M0.LIB + r"""
var R=D.rows,TAB='tec',CUR=null,SORT='ger';
function ger(r){var P=[[r.t1&&r.t1.sc,.4],[r.fu&&r.fu.sc,.4],[r.se&&r.se.sc,.2]],a=0,w=0;P.forEach(function(p){if(p[0]!=null){a+=p[0]*p[1];w+=p[1]}});return w?a/w:null}
R.forEach(function(r){r.ger=ger(r)});
var PT={'Extreme Fear':'Medo extremo','Fear':'Medo','Neutral':'Neutro','Greed':'Ganância','Extreme Greed':'Ganância extrema'};
function mk(){var m=D.mk,h='';if(!m||m.fng==null)return'';
 function c(t,v,s){return'<div class=mo-k><small>'+t+'</small><b>'+v+'</b>'+(s?'<em>'+s+'</em>':'')+'</div>'}
 h+=c('Medo e Ganância',f1(m.fng,0)+' · '+(PT[m.fngc]||m.fngc),'contrário: medo extremo = compra');h+=c('Dominância BTC',f1(m.dom,1)+'%');h+=c('Valor total do mercado','US$ '+M(m.mcap),sg(m.mc24,1)+'% em 24h');h+=c('Volume 24h','US$ '+M(m.vol));
 return'<div class=mo-h>'+h+'</div>'}
function build(){var L=R.slice().sort(function(a,b){return (b.ger==null?-1:b.ger)-(a.ger==null?-1:a.ger)});
 var h=mk()+'<table class=mo-t><thead><tr><th>Ativo</th><th>Técnica</th><th>On-chain</th><th>Derivativos e sentimento</th><th>Geral ▾</th></tr></thead><tbody>';
 L.forEach(function(r){h+='<tr class=mr data-i="'+r.i+'"><td class=mo-n><b>'+r.n+' <span class=mu style="font-weight:500">· '+r.nome+'</span></b><small>'+r.s+'</small></td><td>'+sf(r.t1)+'</td><td>'+(r.fu?sf(r.fu):'<span class=mu>–</span>')+'</td><td>'+(r.se?sf(r.se):'<span class=mu>–</span>')+'</td><td>'+sf({sc:r.ger})+'</td></tr>'});
 document.getElementById('mo').innerHTML=h+'</tbody></table>'}
document.addEventListener('click',function(e){var t=e.target;
 if(t.closest&&t.closest('.mo-p')&&t.classList.contains('x')||t.id=='mo-o'){document.getElementById('mo-o').style.display='none';return}
 var tr=t.closest&&t.closest('tr.mr');if(tr&&!t.closest('.mo-o')){CUR=R.filter(function(r){return r.i==tr.dataset.i})[0];TAB='tec';document.getElementById('mo-o').style.display='block';drawD()}});
var SUBN={val:'Valuation',uso:'Uso e crescimento',cap:'Captura de valor',oferta:'Oferta e emissão',seg:'Segurança e desenvolvimento',fund:'Funding',fng:'Medo e Ganância',ls:'Compra/venda'};
var SUBT={fund:"Funding é a taxa que compradores e vendedores de contratos perpétuos (futuros sem vencimento) pagam uns aos outros para manter o preço do perpétuo colado ao preço à vista. Positivo = quem está comprado paga quem está vendido (otimismo e alavancagem na compra). Negativo = vendidos pagam comprados (pessimismo). Aparece anualizado para comparar: ≈ 10% ao ano é o normal. Muito acima disso indica compra esticada e risco de liquidações em cascata; negativo por muito tempo pode preceder um repique (short squeeze).",fng:"Índice de 0 a 100 que resume o humor do mercado cripto (volatilidade, volume, redes sociais e dominância do BTC). Abaixo de 25 = medo extremo: vendedores exaustos, historicamente uma boa zona de acumulação. Acima de 75 = ganância extrema: mercado eufórico, risco maior de topo. Aqui é lido de forma contrária.",ls:"Número de contas compradas dividido pelo de contas vendidas na OKX. Acima de 1 = mais contas compradas que vendidas. É um termômetro contrário: extremos de compra (acima de ≈ 2,5) mostram a multidão toda do mesmo lado, e o mercado costuma andar contra a maioria. Conta pessoas, não dinheiro: o varejo tende a ficar comprado."};
function subs(o){return'<div class=mo-g>'+Object.keys(o.sub).map(function(k){return'<div class=mo-k><small>'+SUBN[k]+(((o.tips&&o.tips[k])||SUBT[k])?'<span class=tip data-tip="'+((o.tips&&o.tips[k])||SUBT[k]).replace(/"/g,'&quot;')+'">i</span>':'')+'</small><b>'+sf({sc:o.sub[k]})+'</b></div>'}).join('')+'</div>'}
function groups(G){return G.map(function(g){return'<div class=mo-sec>'+g[0]+'</div><div class=mo-g style="grid-template-columns:repeat(auto-fill,minmax(210px,1fr))">'+g[1].map(function(k){return'<div class=mo-k><small>'+k[0]+(k[3]?'<span class=tip data-tip="'+k[3].replace(/"/g,'&quot;')+'">i</span>':'')+'</small><b style="font-size:14px">'+k[1]+'</b>'+(k[2]?'<em>'+k[2]+'</em>':'')+'</div>'}).join('')+'</div>'}).join('')}
function chartsH(GR){return GR.map(function(g,i){return'<div class=mo-c><h4>'+g.t+'</h4><canvas data-gi="'+i+'"></canvas></div>'}).join('')}
function drawCharts(GR){document.querySelectorAll('canvas[data-gi]').forEach(function(cv){var g=GR[+cv.dataset.gi];line(cv,g.s,{dates:g.dd,d:g.d})})}
function drawD(){var r=CUR,t1=r.t1,h='<button class=x>✕</button><h2>'+r.n+' <span class=mu style="font-weight:500">· '+r.nome+'</span></h2><div class=mo-note>'+r.s+'</div>';
 var tt=[['tec','Técnica'],['fun','On-chain'],['der','Derivativos e sentimento']];
 h+='<div class=mo-tabs>'+tt.map(function(k){return'<button data-tab='+k[0]+' class="'+(TAB==k[0]?'on':'')+'">'+k[1]+'</button>'}).join('')+'</div>';
 var GR=null;
 if(TAB=='tec'){
  h+='<div>'+sf(t1)+' <span class=mu>Regime: <b>'+t1.rg+'</b></span> · <span class=mu>preço US$ '+f1(t1.p,t1.p<10?4:2)+'</span></div>';
  h+='<div class=mo-g>'+[['RSI diário',f1(t1.rd,0)],['RSI semanal',f1(t1.rw,0)],['vs MM200 diária',sg(t1.d2,1)+'%'],['vs MM200 semanal',sg(t1.w2,1)+'%'],['vs máx. 12 meses',sg(t1.h52,1)+'%'],['vs máx. histórica (5 anos)',sg(t1.h5,1)+'%'],['vs mín. 12 meses',sg(t1.l52,1)+'%'],['1 mês',sg(t1.r1,1)+'%'],['3 meses',sg(t1.r3,1)+'%'],['6 meses',sg(t1.r6,1)+'%'],['12 meses',sg(t1.r12,1)+'%'],['Força 6m vs BTC',t1.rs==null?'–':sg(t1.rs,1)+' pp']].map(function(x){return'<div class=mo-k><small>'+x[0]+'</small><b>'+x[1]+'</b></div>'}).join('')+'</div>';
  h+='<div class=mo-c><h4>Preço diário (≈ 1 ano) com MM 50 e MM 200</h4><canvas id=c1></canvas></div><div class=mo-c><h4>Preço semanal com MM 200 semanal</h4><canvas id=c2></canvas></div><div class=mo-c><h4>RSI diário e semanal</h4><canvas id=c3></canvas></div>';
  h+='<div class=mo-note>Nota técnica: RSI semanal, RSI diário, distância da MM 200 diária e queda desde a máxima de 12 meses, com escalas adaptadas à volatilidade de cripto. Em regime de baixa a nota fica no máximo neutra, salvo RSI semanal abaixo de 40 (capitulação em cripto). Cripto negocia 7 dias por semana: semana = domingo a sábado. Pesos iniciais, sem backtest.</div>'}
 else if(TAB=='fun'){var f=r.fu;if(!f)h+='<div class=mo-soon>Dados on-chain ainda não coletados.</div>';else{
  h+='<div>'+sf(f)+' <span class=mu>nota on-chain / fundamentos (0–10)</span></div>'+subs(f)+groups(f.G)+chartsH(f.GR);GR=f.GR;
  h+='<div class=mo-note>Nota = média ponderada de valuation (peso 2: MVRV, preço/receita, diluição), uso e crescimento (2: taxas, TVL, endereços, transações, volume — 30d contra 30d anteriores), captura de valor (1,5: receita que chega a quem segura o token), oferta (1,5: emissão, diluição, saída de exchanges) e segurança/desenvolvimento (1). Só entram os blocos que têm dado para o ativo. Fontes: Coin Metrics (comunidade), DefiLlama, CoinGecko, mempool.space, blockchain.info, Blockchair, Solana RPC, ultrasound.money, GitHub. Atualização a cada ≈ 1 hora.</div>'}}
 else{var s=r.se;if(!s)h+='<div class=mo-soon>Dados de derivativos ainda não coletados.</div>';else{
  h+='<div>'+sf(s)+' <span class=mu>nota de derivativos e sentimento (0–10), contrária: euforia e funding alto = venda</span></div>'+subs(s)+groups(s.G)+chartsH(s.GR);GR=s.GR;
  h+='<div class=mo-note>Nota = funding anualizado (peso 2; até ≈ 8% ao ano é normal, acima de 30% indica mercado esticado de comprados), Medo e Ganância (1,5) e razão compra/venda de contas na OKX (1). Fontes: Hyperliquid, OKX, alternative.me.</div>'}}
 var p=document.getElementById('mo-p');p.innerHTML=h;
 p.querySelectorAll('[data-tab]').forEach(function(b){b.onclick=function(){TAB=b.dataset.tab;drawD()}});
 if(TAB=='tec'){var c=t1.ch;
  line(document.getElementById('c1'),[{v:c.d,c:'#4f46e5',w:1.6,l:'preço'},{v:c.m50,c:'#f59e0b',l:'MM50'},{v:c.m200,c:'#dc2626',l:'MM200'}],{dates:c.dd});
  line(document.getElementById('c2'),[{v:c.w,c:'#4f46e5',w:1.6,l:'preço'},{v:c.w200,c:'#dc2626',l:'MM200 semanal'}],{dates:c.wd});
  line(document.getElementById('c3'),[{v:c.rwd,c:'#4f46e5',l:'RSI diário'},{v:c.rww,c:'#16a34a',l:'RSI semanal'}],{min:0,max:100,d:0,lines:[{y:30,c:'#16a34a'},{y:70,c:'#dc2626'}]})}
 else if(GR)drawCharts(GR)}
window.addEventListener('resize',function(){if(document.getElementById('mo-o').style.display=='block')drawD()});
var TB=document.createElement('div');TB.id='tipbox';document.body.appendChild(TB);
function tipShow(el){TB.textContent=el.dataset.tip;TB.style.display='block';var r=el.getBoundingClientRect(),w=TB.offsetWidth,h=TB.offsetHeight,x=Math.min(Math.max(8,r.left-8),innerWidth-w-8),y=r.bottom+8;if(y+h>innerHeight-8)y=Math.max(8,r.top-h-8);TB.style.left=x+'px';TB.style.top=y+'px'}
document.addEventListener('mouseover',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t)tipShow(t);else TB.style.display='none'});
document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t){if(TB.style.display=='block'&&TB.textContent==t.dataset.tip)TB.style.display='none';else tipShow(t)}else TB.style.display='none'});
build();
"""


def pagina(arq, titulo, paginas, D):
    h = [ui.cabeca(titulo, paginas, arq), f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>",
         "<p class=sub>Semáforo por criptoativo: verde = momento de compra, vermelho = venda, cinza = neutro. Técnica (preço), on-chain e fundamentos (rede, DeFi, oferta, valuation, desenvolvimento) e derivativos e sentimento. Clique em uma linha para ver todos os dados e gráficos.</p>",
         "<div id=mo></div><div class=mo-o id=mo-o><div class=mo-p id=mo-p></div></div>",
         "</main><script>var D=" + json.dumps(D, separators=(",", ":"), ensure_ascii=False, default=str) + ";" + JS + "</script></body></html>"]
    return "".join(h)
