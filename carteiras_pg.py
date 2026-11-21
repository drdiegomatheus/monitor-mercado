"""Aba Carteiras: ranking das carteiras vencedoras da Hyperliquid (taxa de acerto etc.) e como estão posicionadas."""
import json
import html as H
import os
import ui
import momento as M0
import baleias_pg as B

CSS = B.CSS + """
.cw-s{display:inline-block;min-width:34px;text-align:center;border-radius:8px;padding:2px 6px;font-weight:800;color:#fff}
.cw-pos{font-size:11.5px;color:var(--mu);white-space:normal;text-align:left;max-width:260px}
.cw-sel button{margin-right:4px}
"""


def dados(raiz):
    p = os.path.join(raiz, "categorias", "cripto")
    fb, fc = os.path.join(p, "baleias.json"), os.path.join(p, "carteiras.json")
    if not (os.path.exists(fb) and os.path.exists(fc)): return None
    b = json.load(open(fb, encoding="utf-8"))
    c = json.load(open(fc, encoding="utf-8"))
    contas = b["contas"]
    rk = []
    for a, s in c["c"].items():
        if not s.get("nota") or a not in contas: continue
        ct = contas[a]
        pos = sorted((x for x in ct["p"] if x[0] in B.MOEDAS), key=lambda x: -x[3])[:4]
        rk.append({"a": a, "n": s.get("nome"), "nota": s["nota"], "wr": s["wr"], "fl": s["fl"], "no": s["n"], "mg": s["mg"], "mp": s["mp"], "pnl": s["pnl"], "dd": s["dd"],
                   "pior": s["pior"], "lp": s.get("lp"), "at": s.get("ativos", []), "av": s["av"], "pa": s["pa"], "par": s.get("parcial"),
                   "pos": [[x[0], "long" if x[1] > 0 else "short", x[3], x[5], x[6]] for x in pos], "t": s["t"]})
    rk.sort(key=lambda r: -r["nota"])
    top = {r["a"] for r in rk[:60]}
    agg = {}
    for a, ct in contas.items():
        for p_ in ct["p"]:
            coin, szi, ntl = p_[0], p_[1], p_[3]
            if coin not in B.MOEDAS: continue
            g = agg.setdefault(coin, [0, 0, 0, 0, 0, 0])
            i = 0 if szi > 0 else 1
            if a in top: g[i] += ntl; g[4 + i] += 1
            else: g[2 + i] += ntl
    coins = [k for k in B.MOEDAS if k in agg]
    return {"ts": c["ts"], "rk": rk[:100], "nq": len(rk), "nc": len(c["c"]), "coins": coins, "agg": {k: agg[k] for k in coins}, "ntop": len(top), "mark": b.get("mark", {})}


JS = M0.LIB + r"""
var SORT='nota',Q='';
function usd(v){return v==null?'–':'US$ '+M(v)}
function sh(a){return a.slice(0,6)+'…'+a.slice(-4)}
function nm(a,n){return '<a href="https://hypurrscan.io/address/'+a+'" target=_blank rel=noopener>'+(n?n:sh(a))+'</a>'}
function tp(t){return '<span class=tip data-tip="'+t.replace(/"/g,'&quot;')+'">i</span>'}
function cor(n){return n>=75?'#10b981':n>=55?'#84cc16':n>=40?'#f59e0b':'#ef4444'}
function pc(v,d){return f1(v*100,d==null?0:d)+'%'}
function posic(){var h='<div class=bl-sc><table class=bl-t><thead><tr><th>Ativo</th><th>Vencedoras: long</th><th>Vencedoras: short</th><th>Saldo vencedoras'+tp('Porcentagem do total das vencedoras que está comprada menos vendida. +100% = só long, −100% = só short.')+'</th><th>Saldo demais baleias</th><th>Leitura'+tp('Compara o que as carteiras de melhor histórico fazem com o resto das baleias. Se divergem, o sinal das vencedoras costuma ser o mais relevante; se concordam, a aposta está consensual.')+'</th></tr></thead><tbody>';
 D.coins.forEach(function(c){var g=D.agg[c],v=g[0]+g[1],o=g[2]+g[3],sv=v?(g[0]-g[1])/v:0,so=o?(g[2]-g[3])/o:0,l;
  if(v<1e6)l='poucas vencedoras posicionadas';else if(Math.abs(sv)<.15)l='vencedoras neutras';else l='vencedoras '+(sv>0?'compradas':'vendidas')+(Math.abs(so)>=.15&&(sv>0)!=(so>0)?' · <b>divergem</b> do resto':(Math.abs(so)>=.15?' · alinhadas com o resto':' · resto neutro'));
  h+='<tr><td><b>'+c+'</b></td><td class=lg>'+usd(g[0])+' <small>('+g[4]+')</small></td><td class=sh2>'+usd(g[1])+' <small>('+g[5]+')</small></td><td class='+(sv>=0?'lg':'sh2')+'>'+(sv>=0?'+':'')+pc(sv)+'</td><td class='+(so>=0?'lg':'sh2')+'>'+(o?(so>=0?'+':'')+pc(so):'–')+'</td><td style="text-align:left">'+l+'</td></tr>'});
 return h+'</tbody></table></div>'}
function tabela(){var R=D.rk.filter(function(r){return!Q||(r.a+(r.n||'')).toLowerCase().indexOf(Q)>=0}).slice();
 R.sort(function(a,b){return SORT=='nota'?b.nota-a.nota:SORT=='wr'?b.wr-a.wr:SORT=='fl'?b.fl-a.fl:b.pnl-a.pnl});
 var h='<div class=bl-f><input id=fq placeholder="Buscar carteira" size=20><span class=bl-sel>'+[['nota','Nota'],['wr','Acerto'],['fl','Fator de lucro'],['pnl','PnL 30d']].map(function(s){return'<button data-s='+s[0]+' class="'+(s[0]==SORT?'on':'')+'">'+s[1]+'</button>'}).join('')+'</span></div>';
 h+='<div class=bl-sc><table class=bl-t><thead><tr><th>Carteira</th><th>Nota'+tp('0 a 100. Combina fator de lucro (30%), taxa de acerto (25%), retorno sobre a conta (20%) e controle de queda (25%). Só entram carteiras com pelo menos 15 ordens fechadas em 30 dias, lucro no mês e lucro total positivo.')+'</th><th>Acerto'+tp('Porcentagem das ordens de fechamento que terminaram no lucro, já descontando as taxas. Sozinha engana: quem ganha pouco muitas vezes e perde muito de vez em quando também tem acerto alto. Veja junto com o fator de lucro.')+'</th><th>Fator de lucro'+tp('Soma dos ganhos dividida pela soma das perdas. Acima de 1 lucra; acima de 2 é muito bom. 99 = sem perdas no período.')+'</th><th>Ordens</th><th>Ganho médio</th><th>Perda média</th><th>PnL 30d</th><th>Queda máx.'+tp('Maior queda acumulada do resultado dentro dos 30 dias, do pico ao fundo. Quanto menor em relação ao lucro, mais consistente.')+'</th><th>Conta</th><th>Posição agora</th></tr></thead><tbody>';
 R.slice(0,60).forEach(function(r){var ps=r.pos.map(function(p){return'<span class='+(p.length&&p[1]=='long'?'lg':'sh2')+'>'+p[0]+' '+p[1]+' '+M(p[2])+' '+(p[3]?p[3]+'×':'')+'</span>'}).join(' · ')||'sem posição';
  h+='<tr><td>'+nm(r.a,r.n)+'</td><td><span class=cw-s style="background:'+cor(r.nota)+'">'+r.nota+'</span></td><td>'+pc(r.wr)+'</td><td>'+(r.fl>=99?'∞':f1(r.fl,2))+'</td><td>'+r.no+(r.par?'+':'')+'</td><td class=lg>'+usd(r.mg)+'</td><td class=sh2>−'+usd(r.mp)+'</td><td class=lg>+'+usd(r.pnl)+'</td><td>'+usd(r.dd)+'</td><td>'+usd(r.av)+'</td><td class=cw-pos>'+ps+'</td></tr>'});
 return h+'</tbody></table></div>'}
function draw(){var q=D.rk,tot=D.rk.slice(0,D.ntop),av=tot.length?tot.reduce(function(s,r){return s+r.wr},0)/tot.length:0,fl=tot.length?tot.reduce(function(s,r){return s+Math.min(r.fl,5)},0)/tot.length:0;
 var h='<div class=mo-h>'+
 '<div class=mo-k><small>Carteiras analisadas'+tp('Carteiras grandes com lucro no mês e no total, das quais lemos o histórico de ordens dos últimos 30 dias.')+'</small><b>'+D.nc+'</b><em>'+D.nq+' qualificadas</em></div>'+
 '<div class=mo-k><small>Grupo vencedor'+tp('As '+D.ntop+' carteiras com maior nota. É o grupo usado na comparação de posicionamento abaixo.')+'</small><b>'+D.ntop+'</b><em>maiores notas</em></div>'+
 '<div class=mo-k><small>Acerto médio do grupo</small><b>'+pc(av)+'</b><em>ordens no lucro</em></div>'+
 '<div class=mo-k><small>Fator de lucro médio</small><b>'+f1(fl,2)+'</b><em>ganhos ÷ perdas</em></div></div>';
 h+='<div class=bl-c><h3>Como as vencedoras estão posicionadas'+tp('Soma das posições abertas hoje pelas carteiras do grupo vencedor, ativo por ativo, comparada com as demais baleias. Mostra se quem vem acertando está comprado ou vendido.')+'</h3>'+posic()+'<div class=bl-n>Histórico recente não garante resultado futuro; carteiras que ganham muito costumam assumir muito risco, por isso a nota inclui a queda máxima.</div></div>';
 h+='<div class=bl-c><h3>Ranking das carteiras vencedoras · últimos 30 dias</h3>'+tabela()+'</div>';
 document.getElementById('cw').innerHTML=h;var fq=document.getElementById('fq');fq.value=Q;
 fq.oninput=function(){Q=fq.value.toLowerCase();var p=fq.selectionStart;draw();var z=document.getElementById('fq');z.focus();z.setSelectionRange(p,p)};
 document.querySelectorAll('[data-s]').forEach(function(b){b.onclick=function(){SORT=b.dataset.s;draw()}})}
var TB=document.createElement('div');TB.id='tipbox';document.body.appendChild(TB);
function tipShow(el){TB.textContent=el.dataset.tip;TB.style.display='block';var r=el.getBoundingClientRect(),w=TB.offsetWidth,h=TB.offsetHeight,x=Math.min(Math.max(8,r.left-8),innerWidth-w-8),y=r.bottom+8;if(y+h>innerHeight-8)y=Math.max(8,r.top-h-8);TB.style.left=x+'px';TB.style.top=y+'px'}
document.addEventListener('mouseover',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t)tipShow(t);else TB.style.display='none'});
document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t){if(TB.style.display=='block'&&TB.textContent==t.dataset.tip)TB.style.display='none';else tipShow(t)}else TB.style.display='none'});
draw();
"""


def pagina(arq, titulo, paginas, D):
    topo = ui.cabeca(titulo, paginas, arq) + f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>"
    if not D:
        return topo + "<p class=sub>O histórico de ordens das carteiras está sendo coletado. Volte em alguns minutos.</p></main></body></html>"
    return (topo + "<p class=sub>As grandes carteiras da Hyperliquid que mais acertam, com base nas ordens fechadas dos últimos 30 dias, e como estão posicionadas agora. Passe o mouse no <b>i</b> para ver o que cada item significa.</p><div id=cw></div></main><script>var D="
            + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";" + JS + "</script></body></html>")
