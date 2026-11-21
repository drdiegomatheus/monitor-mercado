"""Aba Baleias TradeFi: carteiras grandes da Hyperliquid em mercados HIP-3 (ações, índices, commodities). Sem ranking: o que manda é o lucro."""
import json
import html as H
import os
import ui
import momento as M0
import baleias_pg as B

CSS = B.CSS + """
.tf-n{color:var(--mu);font-size:12px}
.cw-pos{font-size:11.5px;white-space:normal;text-align:left!important;max-width:300px}
tr.clk{cursor:pointer}
"""


def dados(raiz):
    f = os.path.join(raiz, "categorias", "cripto", "tradefi.json")
    if not os.path.exists(f): return None
    e = json.load(open(f, encoding="utf-8"))
    acc = []
    agg, pos, mark, pnlc = {}, {}, {}, {}
    for a, c in e.get("c", {}).items():
        if not c.get("tf"): continue
        st = c.get("st") or {}
        ps = [p for p in c.get("p", []) if p[3] > 0]
        for p in ps:
            coin, szi, ent, ntl, liq = p[0], p[1], p[2], p[3], p[4]
            g = agg.setdefault(coin, [0, 0, 0, 0])
            i = 0 if szi > 0 else 1
            g[i] += ntl; g[2 + i] += 1
            if szi: mark[coin] = ntl / abs(szi)
            if liq: pos.setdefault(coin, []).append([round(liq, 4), ntl if szi > 0 else -ntl])
        for t in st.get("ativos", []):
            pnlc[t[0]] = pnlc.get(t[0], 0) + t[2]
        acc.append({"a": a, "n": c.get("nome"), "av": c.get("av") or c.get("av0") or 0, "pnl": st.get("pnl"), "no": st.get("n", 0), "nf": st.get("nf", 0), "w": st.get("w", 0), "vol": st.get("vol", 0),
                    "un": sum(p[6] for p in ps), "ex": sum(p[3] for p in ps), "at": st.get("ativos", []),
                    "pos": [[p[0], "long" if p[1] > 0 else "short", p[3], p[2], p[4], p[5], p[6]] for p in sorted(ps, key=lambda x: -x[3])[:6]], "lido": bool(st)})
    coins = sorted(agg, key=lambda k: -(agg[k][0] + agg[k][1]))[:14]
    for k in coins: pos[k] = sorted(pos.get(k, []), key=lambda x: -abs(x[1]))[:4000]
    acc.sort(key=lambda x: -(x["pnl"] if x["pnl"] is not None else -1e18))
    return {"ts": e.get("ts"), "acc": acc[:300], "n": len(acc), "coins": coins, "agg": {k: agg[k] for k in coins}, "pos": {k: pos[k] for k in coins}, "mark": {k: mark.get(k) for k in coins},
            "pnlc": pnlc, "nl": len(e.get("c", {})), "dexs": e.get("dexs", [])}


MAPA = B.JS[B.JS.index("function bandas()"):B.JS.index("function proxLiq()")]

JS = M0.LIB + r"""
var COIN=D.coins[0]||'',RNG=20,SORT='pnl',Q='',SO='todas',TB;
function usd(v){return v==null?'–':'US$ '+M(v)}
function fx(p){return p==null?'–':(p>=1000?f1(p,0):p>=10?f1(p,2):f1(p,4))}
function sh(a){return a.slice(0,6)+'…'+a.slice(-4)}
function nm(a,n){return '<a href="https://hypurrscan.io/address/'+a+'" target=_blank rel=noopener>'+(n?n:sh(a))+'</a>'}
function tp(t){return '<span class=tip data-tip="'+t.replace(/"/g,'&quot;')+'">i</span>'}
function sn(v){return '<span class='+(v>=0?'lg':'sh2')+'>'+(v>=0?'+':'−')+usd(Math.abs(v))+'</span>'}
function cn(c){return c.replace(/^[a-z]+:/,'')}
function agoraNet(c){var T=D.agg[c],t=T[0]+T[1],r=t?(T[0]-T[1])/t:0;return r>.2?'As baleias estão compradas em '+cn(c)+' ('+f1(r*100,0)+'% a mais no long).':r<-.2?'As baleias estão vendidas em '+cn(c)+' ('+f1(-r*100,0)+'% a mais no short).':'Posição equilibrada entre compradas e vendidas em '+cn(c)+'.'}
MAPAJS
function posTab(){var h='<div class=bl-sc><table class=bl-t><thead><tr><th>Ativo</th><th>Long</th><th>Short</th><th>Saldo'+tp('Long menos short das carteiras monitoradas. Positivo = viés de alta.')+'</th><th>Carteiras</th><th>Lucro realizado 30d'+tp('Soma do lucro realizado (já descontadas as taxas) das carteiras monitoradas neste ativo nos últimos 30 dias.')+'</th></tr></thead><tbody>';
 D.coins.forEach(function(c){var g=D.agg[c],net=g[0]-g[1];h+='<tr class=clk data-c="'+c+'"><td><b>'+cn(c)+'</b></td><td class=lg>'+usd(g[0])+' <small>('+g[2]+')</small></td><td class=sh2>'+usd(g[1])+' <small>('+g[3]+')</small></td><td>'+sn(net)+'</td><td>'+(g[2]+g[3])+'</td><td>'+(D.pnlc[c]!=null?sn(D.pnlc[c]):'–')+'</td></tr>'});return h+'</tbody></table></div>'}
function tabela(){var R=D.acc.filter(function(r){return(SO=='todas'||r.pos.some(function(p){return p[0]==SO}))&&(!Q||(r.a+(r.n||'')).toLowerCase().indexOf(Q)>=0)}).slice();
 R.sort(function(a,b){var x=SORT=='pnl'?(b.pnl==null?-1e18:b.pnl)-(a.pnl==null?-1e18:a.pnl):SORT=='un'?b.un-a.un:SORT=='av'?b.av-a.av:b.ex-a.ex;return x});
 var h='<div class=bl-f><select id=fs><option value=todas>Todos os ativos</option>'+D.coins.map(function(c){return'<option value="'+c+'">'+cn(c)+'</option>'}).join('')+'</select><input id=fq placeholder="Buscar carteira" size=20><span class=bl-sel>'+[['pnl','Lucro 30d'],['un','Lucro aberto'],['ex','Exposição'],['av','Conta']].map(function(s){return'<button data-s='+s[0]+' class="'+(s[0]==SORT?'on':'')+'">'+s[1]+'</button>'}).join('')+'</span></div>';
 h+='<div class=bl-sc><table class=bl-t><thead><tr><th>Carteira</th><th>Lucro realizado 30d'+tp('Lucro das ordens fechadas em TradeFi nos últimos 30 dias, já descontadas as taxas. É o critério principal desta aba. Não considera o lucro ainda aberto.')+'</th><th>Lucro aberto'+tp('Lucro ou prejuízo não realizado das posições TradeFi abertas agora.')+'</th><th>Ordens</th><th>Acerto</th><th>Exposição</th><th>Conta</th><th>Posições agora</th></tr></thead><tbody>';
 R.slice(0,80).forEach(function(r){var ps=r.pos.map(function(p){return'<span class='+(p[1]=='long'?'lg':'sh2')+'>'+cn(p[0])+' '+p[1]+' '+M(p[2])+(p[5]?' '+p[5]+'×':'')+'</span>'}).join(' · ')||'<span class=tf-n>sem posição</span>';
  h+='<tr><td>'+nm(r.a,r.n)+'</td><td>'+(r.pnl==null?'<span class=tf-n>lendo…</span>':sn(r.pnl))+'</td><td>'+(r.pos.length?sn(r.un):'–')+'</td><td>'+(r.no||0)+'</td><td>'+(r.nf?f1(r.w/r.nf*100,0)+'%':'–')+'</td><td>'+usd(r.ex)+'</td><td>'+usd(r.av)+'</td><td class=cw-pos>'+ps+'</td></tr>'});
 return h+'</tbody></table></div>'}
function head(){var L=0,S=0,N=D.acc.length;D.coins.forEach(function(c){L+=D.agg[c][0];S+=D.agg[c][1]});var pn=D.acc.reduce(function(s,r){return s+(r.pnl||0)},0);
 function k(t,v,s,tt){return'<div class=mo-k><small>'+t+(tt?tp(tt):'')+'</small><b>'+v+'</b>'+(s?'<em>'+s+'</em>':'')+'</div>'}
 return'<div class=mo-h>'+k('Carteiras TradeFi',N,D.nl+' lidas no total','Carteiras da Hyperliquid, entre as grandes que monitoramos, com posição ou ordens em mercados de ações, índices e commodities (mercados HIP-3, como xyz, io, km). As carteiras vão sendo descobertas aos poucos.')+k('Long total',usd(L),'comprado')+k('Short total',usd(S),'vendido')+k('Lucro 30d do grupo',sn(pn),'realizado, após taxas')+'</div>'}
function draw(){var h=head();
 h+='<div class=bl-c><h3>Posição por ativo'+tp('Soma das posições abertas das baleias em cada mercado TradeFi. Clique numa linha para ver o mapa de liquidação dela.')+'</h3>'+posTab()+'</div>';
 if(COIN){var rg=[10,20,30,50].map(function(r){return'<button data-r='+r+' class="'+(r==RNG?'on':'')+'">±'+r+'%</button>'}).join('');
  h+='<div class=bl-c><h3>Mapa de liquidação · '+cn(COIN)+' · preço '+fx(D.mark[COIN])+tp('Quanto dinheiro das baleias seria liquidado em cada faixa de preço. Barras vermelhas abaixo do preço = longs; verdes acima = shorts. As linhas mostram o acumulado a partir do preço atual. AGORA: '+agoraNet(COIN))+'<span class=bl-sel>'+rg+'</span></h3><canvas id=mapa class=m></canvas><div class=bl-n>Passe o mouse para ver quanto seria liquidado até cada preço. Só as carteiras monitoradas; mercados TradeFi funcionam só no horário do ativo de referência em parte dos casos.</div></div>'}
 h+='<div class=bl-c><h3>Carteiras, ordenadas por lucro'+tp('Sem nota nem ranking: a lista é ordenada pelo lucro realizado nos últimos 30 dias. Use os botões para ordenar por lucro aberto, exposição ou tamanho da conta.')+'</h3>'+tabela()+'</div>';
 h+='<div class=mo-note>Fonte: consulta pública de posições e de execuções da Hyperliquid (mercados HIP-3). Cobre carteiras acima de US$ 500 mil de saldo na conta principal; o lucro vem das execuções dos últimos 30 dias.</div>';
 document.getElementById('tf').innerHTML=h;
 document.querySelectorAll('tr.clk').forEach(function(t){t.onclick=function(){COIN=t.dataset.c;draw();document.getElementById('mapa').scrollIntoView({block:'center'})}});
 document.querySelectorAll('[data-r]').forEach(function(b){b.onclick=function(){RNG=+b.dataset.r;draw()}});
 document.querySelectorAll('[data-s]').forEach(function(b){b.onclick=function(){SORT=b.dataset.s;draw()}});
 var fs=document.getElementById('fs'),fq=document.getElementById('fq');fs.value=SO;fq.value=Q;fs.onchange=function(){SO=fs.value;draw()};
 fq.oninput=function(){Q=fq.value.toLowerCase();var p=fq.selectionStart;draw();var z=document.getElementById('fq');z.focus();z.setSelectionRange(p,p)};
 if(COIN){drawMapa();var cv=document.getElementById('mapa');cv.onmousemove=mapaTip;cv.onmouseleave=function(){TB.style.display='none'}}}
TB=document.createElement('div');TB.id='tipbox';document.body.appendChild(TB);
function tipShow(el){TB.textContent=el.dataset.tip;TB.style.display='block';var r=el.getBoundingClientRect(),w=TB.offsetWidth,h=TB.offsetHeight,x=Math.min(Math.max(8,r.left-8),innerWidth-w-8),y=r.bottom+8;if(y+h>innerHeight-8)y=Math.max(8,r.top-h-8);TB.style.left=x+'px';TB.style.top=y+'px'}
document.addEventListener('mouseover',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t)tipShow(t);else if(e.target.id!='mapa')TB.style.display='none'});
document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t){if(TB.style.display=='block'&&TB.textContent==t.dataset.tip)TB.style.display='none';else tipShow(t)}else if(!e.target.closest('tr.clk'))TB.style.display='none'});
window.addEventListener('resize',function(){if(COIN)drawMapa()});
draw();
""".replace("MAPAJS", MAPA)


def pagina(arq, titulo, paginas, D):
    topo = ui.cabeca(titulo, paginas, arq) + f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>"
    if not D or not D["acc"]:
        return topo + "<p class=sub>Estou procurando as baleias de TradeFi (ações, índices e commodities na Hyperliquid). Volte em alguns minutos.</p></main></body></html>"
    return (topo + "<p class=sub>Grandes carteiras da Hyperliquid operando ações, índices e commodities (TradeFi). Sem ranking: a ordem é o lucro realizado em 30 dias. Passe o mouse no <b>i</b> para ver o que cada item significa.</p><div id=tf></div></main><script>var D="
            + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";" + JS + "</script></body></html>")
