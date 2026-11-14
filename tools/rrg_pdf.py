"""Gera o PDF de RRG (Brasil, EUA, Cripto) com comentário sob cada gráfico.
Uso: python tools/rrg_pdf.py [saida.pdf]"""
import sys, os, json, datetime as dt
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, RAIZ); os.chdir(RAIZ)
import monitor as m
import pandas as pd

QUADS = ["Leading", "Improving", "Weakening", "Lagging"]
SIGNIF = {"Leading": "força relativa acima do benchmark e ainda acelerando: são os líderes do momento",
          "Improving": "ainda abaixo do benchmark, mas melhorando: candidatos a virar líderes",
          "Weakening": "ainda acima do benchmark, mas perdendo ritmo: atenção, a liderança pode estar acabando",
          "Lagging": "abaixo do benchmark e piorando: fraqueza relativa, dinheiro saindo"}
TRANS = {("Leading", "Weakening"): "perdeu fôlego: segue acima do benchmark, mas desacelerou",
         ("Weakening", "Lagging"): "piorou: passou a ficar abaixo do benchmark",
         ("Lagging", "Improving"): "começou a reagir: ainda abaixo, mas já melhorando",
         ("Improving", "Leading"): "virou líder",
         ("Weakening", "Leading"): "retomou a força",
         ("Improving", "Lagging"): "a melhora não se sustentou",
         ("Leading", "Improving"): "caiu abaixo do benchmark, mas já tenta reagir",
         ("Leading", "Lagging"): "caiu de líder para fraco em poucas barras: perda forte de força relativa",
         ("Lagging", "Leading"): "saiu de fraco para líder em poucas barras: virada forte",
         ("Lagging", "Weakening"): "saltou para acima do benchmark, ainda sem aceleração"}

def carregar(cat):
    p = f"categorias/{cat}"; cfg = json.load(open(p + "/config.json", encoding="utf-8")); A = m.especificar(cfg); S = {}
    for k in A:
        d = m.ler(p + "/dados", k, "1D")
        if d is not None: S[k] = m.limpar(d)
    B = {b: m.limpar(d) for b in cfg.get("benchmarks", {}) if (d := m.ler(p + "/dados", "BENCH_" + b, "1D")) is not None}
    ordem = m.ordenar(cfg, p, list(S))
    return cfg, A, {k: S[k] for k in ordem}, B, ordem

def lista(v): return ", ".join(v)
def n1(x): return f"{x:.1f}".replace(".", ",")

def comentar(T, ordem, bench, modo, T_sem=None, T_dia=None):
    if T.empty: return ""
    rk = {n: i for i, n in enumerate(ordem)}; T = T.assign(r=T.ativo.map(rk)).sort_values("r")
    nome = "semanal" if modo == "w" else "diário"; n = len(T); P = []
    quad = {q: list(T[T.quad == q].ativo) for q in QUADS}
    cab = f"<b>O que está acontecendo ({nome}, contra {bench}).</b> "
    cab += " ".join(f"<b>{q}</b> ({len(quad[q])}): {lista(quad[q])}, {SIGNIF[q]}." for q in QUADS if quad[q])
    P.append(cab)
    mud = [(r.ativo, r.antes, r.quad) for r in T.itertuples() if r.antes != r.quad]
    if mud:
        P.append("<b>Mudanças nas últimas 4 barras.</b> " + "; ".join(f"{a}: {x} → {y} ({TRANS.get((x, y), 'mudou de quadrante')})" for a, x, y in mud) + ".")
    else:
        P.append("<b>Mudanças nas últimas 4 barras.</b> Ninguém mudou de quadrante: o cenário está estável.")
    if n >= 3:
        f = T.sort_values("x"); g = T.sort_values("y")
        P.append(f"<b>Destaques.</b> Mais forte contra o benchmark: {f.ativo.iloc[-1]} (RS-Ratio {n1(f.x.iloc[-1])}); mais fraco: {f.ativo.iloc[0]} ({n1(f.x.iloc[0])}). "
                 f"Maior aceleração: {g.ativo.iloc[-1]} (momento {n1(g.y.iloc[-1])}); maior perda de ritmo: {g.ativo.iloc[0]} ({n1(g.y.iloc[0])}). Acima de 100 = melhor que o benchmark / acelerando; abaixo de 100 = pior / desacelerando.")
    if modo == "d" and T_sem is not None and not T_sem.empty:
        sem = dict(zip(T_sem.ativo, T_sem.quad)); dia = dict(zip(T.ativo, T.quad)); forte = ("Leading", "Improving")
        g = {"a": [], "b": [], "c": [], "d": []}
        for a in T.ativo:
            if a not in sem: continue
            sf, df_ = sem[a] in ("Leading", "Weakening"), dia[a] in ("Leading", "Improving")
            if sem[a] in ("Leading", "Improving") and dia[a] in ("Leading", "Improving"): g["a"].append(a)
            elif sem[a] in ("Leading", "Improving") and dia[a] in ("Weakening", "Lagging"): g["b"].append(a)
            elif sem[a] in ("Weakening", "Lagging") and dia[a] in ("Leading", "Improving"): g["c"].append(a)
            else: g["d"].append(a)
        tx = []
        if g["a"]: tx.append(f"<b>Semanal e diário a favor</b> (tendência e timing alinhados): {lista(g['a'])}.")
        if g["b"]: tx.append(f"<b>Semanal bom, diário fraco</b> (recuo dentro de tendência favorável, ponto de observação): {lista(g['b'])}.")
        if g["c"]: tx.append(f"<b>Semanal fraco, diário reagindo</b> (repique dentro de tendência fraca; cautela, pode ser só alívio): {lista(g['c'])}.")
        if g["d"]: tx.append(f"<b>Semanal e diário fracos</b> (fraqueza alinhada): {lista(g['d'])}.")
        if tx: P.append("<b>Semanal × diário.</b> " + " ".join(tx))
    return "".join(f"<p>{x}</p>" for x in P)

def main(saida):
    paginas = []
    cfg, A, S, B, ordem = carregar("brasil")
    SEC = {"Financeiro (bancos, seguros)": ["Bancos", "Seguros e serviços financeiros"],
           "Petróleo, mineração, energia e saneamento": ["Petróleo e gás", "Mineração e siderurgia", "Energia elétrica", "Saneamento"],
           "Indústria e consumo": ["Bens industriais", "Consumo não cíclico", "Consumo cíclico"],
           "Construção, shoppings, saúde, tecnologia e telecom": ["Construção civil", "Shoppings e imobiliário", "Saúde", "Tecnologia", "Telecomunicações"]}
    gr = [(n, {k: v for k, v in S.items() if A[k].get("setor") in ss}) for n, ss in SEC.items()]
    gr = sorted([g for g in gr if g[1]], key=lambda g: min(ordem.index(k) for k in g[1]))   # grupos pelo ativo de maior valor
    paginas.append(("Brasil · referência BOVA11", "BOVA11", gr, B["BOVA11"].close, cfg["semana"], A))
    cfg, A, S, B, ordem = carregar("eua")
    for g, nome in (("nasdaq", "NASDAQ (QQQ)"), ("sp500", "S&P 500 (SPY)")):
        sub = {k: v for k, v in S.items() if A[k].get("grupo") == g}
        paginas.append((f"EUA · referência {nome}", nome, [("", sub)], B[cfg["grupo_benchmark"][g]].close, cfg["semana"], A))
    cfg, A, S, B, ordem = carregar("cripto")
    sub = {k: v for k, v in S.items() if k != "BTC"}
    paginas.append(("Cripto · referência BTC", "BTC", [("", sub)], (B["BTC"] if "BTC" in B else S["BTC"]).close, cfg["semana"], A))
    agora = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
    css = m.CSS + "body{max-width:none;font-size:12px}h1{margin:0 0 4px}h2{margin:8px 0 2px;font-size:14px}.par{display:flex;gap:12px}.par>div{flex:1;min-width:0}svg{width:56%!important;height:auto!important;display:block;margin:0 auto}.pg{break-before:page}.cm p{margin:4px 0;font-size:11px;line-height:1.35;text-align:left}"
    h = [f"<html><head><meta charset=utf-8><style>{css}</style></head><body><h1>RRG · {agora} (Brasília)</h1>"
         "<p class=n>O RRG mede força relativa contra o benchmark, não se o preço sobe ou cai: um ativo pode estar em Leading e cair, só que cai menos que o benchmark. Eixo horizontal = RS-Ratio (tendência da força relativa, 100 = igual ao benchmark); vertical = momento dessa força (acima de 100 = acelerando). "
         "Os quadrantes giram no sentido horário: Improving → Leading → Weakening → Lagging → Improving. Semanal mostra a tendência; diário, o timing. Rastro cinza = últimas barras. Ordem dos ativos: setores e empresas do maior para o menor valor de mercado.</p>"]
    for i, (tit, bn, grupos, ref, fim, A_) in enumerate(paginas):
        h.append(f"<h1{' class=pg' if i else ''}>{tit}</h1>")
        for j, (sub, ser) in enumerate(grupos):
            lab = {k: m.rotulo(k, A_[k]) for k in ser}; ser = {lab[k]: v for k, v in ser.items()}
            ordem_g = list(ser)
            Tw = m.tabela_rrg(ser, ref, "w", fim); Td = m.tabela_rrg(ser, ref, "d", fim)
            h.append("<div class=pg>" if j else "<div>")
            if sub: h.append(f"<h2>{sub}</h2>")
            cols = []
            for modo, T, nome in (("w", Tw, "semanal"), ("d", Td, "diário")):
                if T.empty: cols.append("<div></div>"); continue
                cols.append(f"<div><h2>RRG {nome}</h2>{m.svg_rrg(T)}<div class=cm>{comentar(T, ordem_g, bn, modo, T_sem=Tw)}</div></div>")
            h.append("<div class=par>" + "".join(cols) + "</div></div>")
    h.append("</body></html>")
    tmp = os.path.join(RAIZ, "_rrg_tmp.html"); open(tmp, "w", encoding="utf-8").write("".join(h))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1100, "height": 900}); pg.goto("file://" + tmp)
        pg.pdf(path=saida, format="A4", landscape=True, print_background=True, margin={"top": "8mm", "bottom": "8mm", "left": "8mm", "right": "8mm"}); b.close()
    os.remove(tmp); print("ok", saida)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "RRG.pdf"))
