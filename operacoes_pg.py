"""Aba Operações: feed das movimentações recentes das baleias da Hyperliquid."""
import json
import html as H
import os
import ui
import momento as M0
import baleias_pg as B

CSS = B.CSS + """
.op-r{display:grid;grid-template-columns:34px 1fr auto;gap:10px;padding:10px 4px;border-bottom:1px solid var(--line);align-items:center}
.op-r .ic2{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px}
.op-r .ic2.l{background:rgba(16,185,129,.16);color:var(--gr)}.op-r .ic2.s{background:rgba(239,68,68,.16);color:var(--rd)}
.op-r small{color:var(--mu)}.op-r .v{text-align:right;font-weight:700;white-space:nowrap}
.op-r a{color:var(--ac);text-decoration:none;font-weight:700}
.op-n{background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin:0 0 12px;font-size:13.5px}
.op-n.new{border-color:var(--ac)}
.op-new{background:var(--ac);color:#fff;border-radius:999px;font-size:10px;font-weight:800;padding:1px 7px;margin-left:6px}
@media(max-width:700px){.op-r{grid-template-columns:30px 1fr}.op-r .v{grid-column:2;text-align:left}}
"""


def dados(raiz):
    f = os.path.join(raiz, "categorias", "cripto", "baleias.json")
    if not os.path.exists(f): return None
    e = json.load(open(f, encoding="utf-8"))
    contas = e.get("contas", {})
    ev = []
    for x in e.get("eventos", [])[::-1]:
        c = contas.get(x["a"], {})
        ev.append({**x, "av": c.get("av"), "pm": (c.get("pnl") or [0, 0, 0, 0])[2], "pw": (c.get("pnl") or [0, 0, 0, 0])[1], "pt": (c.get("pnl") or [0, 0, 0, 0])[3]})
    return {"ts": e.get("ts"), "ev": ev, "mark": e.get("mark", {}), "cob": e.get("cobertura", {})}


JS = M0.LIB + r"""
var FC='todas',FL='todos',FA='todas',MIN=2e6,Q='';
function usd(v){return v==null?'–':'US$ '+M(v)}
function fx(p){return p==null?'–':(p>=1000?f1(p,0):p>=10?f1(p,2):f1(p,4))}
function sh(a){return a.slice(0,6)+'…'+a.slice(-4)}
function nm(a,n){return '<a href="https://hypurrscan.io/address/'+a+'" target=_blank rel=noopener>'+(n?n:sh(a))+'</a>'}
function ago(t){var s=Math.round(Date.now()/1000-t);return s<90?'agora':s<5400?Math.round(s/60)+' min':s<172800?Math.round(s/3600)+' h':Math.round(s/86400)+' d'}
function tp(t){return '<span class=tip data-tip="'+t.replace(/"/g,'&quot;')+'">i</span>'}
var A={abriu:'abriu',fechou:'fechou',aumentou:'aumentou',reduziu:'reduziu',virou:'inverteu'};
function lista(){return D.ev.filter(function(e){var v=Math.abs(e.d);return v>=MIN&&(FC=='todas'||e.c==FC)&&(FL=='todos'||e.l==FL)&&(FA=='todas'||e.ac==FA)&&(!Q||((e.a+(e.n||'')).toLowerCase().indexOf(Q)>=0))})}
function resumo(L){var h=Date.now()/1000-3600,r=L.filter(function(e){return e.t>=h}),lg=0,sh_=0;r.forEach(function(e){var v=e.ac=='fechou'||e.ac=='reduziu'?-1:1,s=e.l=='long'?1:-1;if(v*s>0)lg+=Math.abs(e.d);else sh_+=Math.abs(e.d)});
 var t=r.length?(lg>sh_*1.5?'Na última hora o fluxo das baleias é de COMPRA: mais exposição comprada sendo aberta ou short sendo fechado ('+usd(lg)+' contra '+usd(sh_)+').':sh_>lg*1.5?'Na última hora o fluxo das baleias é de VENDA: mais exposição vendida sendo aberta ou long sendo fechado ('+usd(sh_)+' contra '+usd(lg)+').':'Na última hora o fluxo está dividido entre compra ('+usd(lg)+') e venda ('+usd(sh_)+').'):'Nenhuma movimentação grande na última hora.';
 return{n:r.length,t:t,lg:lg,sh:sh_}}
function draw(){var L=lista(),R=resumo(L),coins={};D.ev.forEach(function(e){coins[e.c]=1});
 var h='<div class="op-n'+(R.n?' new':'')+'"><b>Última hora:</b> '+R.n+' movimentações · '+R.t+tp('Soma do valor das movimentações da última hora, separando o que aumenta a exposição comprada (abrir long, fechar short) do que aumenta a exposição vendida (abrir short, fechar long). É um termômetro do fluxo das baleias neste momento.')+'</div>';
 h+='<div class=bl-f><select id=fa><option value=todas>Todas as ações</option><option value=abriu>Abriu</option><option value=fechou>Fechou</option><option value=aumentou>Aumentou</option><option value=reduziu>Reduziu</option><option value=virou>Inverteu</option></select>';
 h+='<select id=fc><option value=todas>Todos os ativos</option>'+Object.keys(coins).sort().map(function(c){return'<option>'+c+'</option>'}).join('')+'</select>';
 h+='<select id=fl><option value=todos>Long e short</option><option value=long>Só long</option><option value=short>Só short</option></select>';
 h+='<select id=fm><option value=2000000>≥ US$ 2 mi</option><option value=5000000>≥ US$ 5 mi</option><option value=10000000>≥ US$ 10 mi</option><option value=25000000>≥ US$ 25 mi</option></select><input id=fq placeholder="Buscar carteira" size=18></div>';
 h+='<div class=bl-c><h3>Operações recentes das baleias'+tp('Movimentações detectadas entre duas leituras da mesma carteira (a cada poucos minutos). Abriu/fechou = posição nova ou encerrada; aumentou/reduziu = variação de pelo menos 30% e US$ 2 milhões; inverteu = trocou de lado. O horário é o da detecção. O PnL 30d ao lado mostra se a carteira vem acertando.')+'</h3>';
 if(!L.length)h+='<div class=bl-n>Nada com esses filtros. As movimentações aparecem quando uma carteira é lida duas vezes e a posição mudou.</div>';
 L.slice(0,120).forEach(function(e){var up=e.l=='long';
  h+='<div class=op-r><div class="ic2 '+(up?'l':'s')+'">'+(up?'▲':'▼')+'</div><div>'+nm(e.a,e.n)+' '+A[e.ac]+' <b>'+e.c+' '+e.l+'</b> de '+usd(Math.abs(e.d))+(e.ac=='abriu'||e.ac=='fechou'?'':' (agora '+usd(e.v)+')')+'<br><small>há '+ago(e.t)+(e.px?' · preço '+fx(e.px):'')+' · conta '+usd(e.av)+'</small></div>'
  +'<div class=v><span class='+(e.pm>=0?'lg':'sh2')+'>'+(e.pm>=0?'+':'−')+usd(Math.abs(e.pm))+'</span><br><small>PnL 30d</small></div></div>'});
 h+='</div>';document.getElementById('op').innerHTML=h;
 var fa=document.getElementById('fa'),fc=document.getElementById('fc'),fl=document.getElementById('fl'),fm=document.getElementById('fm'),fq=document.getElementById('fq');fa.value=FA;fc.value=FC;fl.value=FL;fm.value=MIN;fq.value=Q;
 fa.onchange=function(){FA=fa.value;draw()};fc.onchange=function(){FC=fc.value;draw()};fl.onchange=function(){FL=fl.value;draw()};fm.onchange=function(){MIN=+fm.value;draw()};
 fq.oninput=function(){Q=fq.value.toLowerCase();var p=fq.selectionStart;draw();var q=document.getElementById('fq');q.focus();q.setSelectionRange(p,p)}}
var TB=document.createElement('div');TB.id='tipbox';document.body.appendChild(TB);
function tipShow(el){TB.textContent=el.dataset.tip;TB.style.display='block';var r=el.getBoundingClientRect(),w=TB.offsetWidth,h=TB.offsetHeight,x=Math.min(Math.max(8,r.left-8),innerWidth-w-8),y=r.bottom+8;if(y+h>innerHeight-8)y=Math.max(8,r.top-h-8);TB.style.left=x+'px';TB.style.top=y+'px'}
document.addEventListener('mouseover',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t)tipShow(t);else TB.style.display='none'});
document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t){if(TB.style.display=='block'&&TB.textContent==t.dataset.tip)TB.style.display='none';else tipShow(t)}else TB.style.display='none'});
draw();
"""


def pagina(arq, titulo, paginas, D):
    topo = ui.cabeca(titulo, paginas, arq) + f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>"
    if not D:
        return topo + "<p class=sub>Os dados ainda estão sendo coletados. Volte em alguns minutos.</p></main></body></html>"
    return (topo + "<p class=sub>O que as grandes carteiras da Hyperliquid abriram, fecharam ou mudaram nas últimas horas. Passe o mouse no <b>i</b> para ver o que cada item significa.</p><div id=op></div></main><script>var D="
            + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";" + JS + "</script></body></html>")
