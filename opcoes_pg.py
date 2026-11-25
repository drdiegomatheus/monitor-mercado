"""Aba Opções: onde estão as posições de calls e puts (por vencimento e por strike), as barreiras de alta e de queda,
o max pain, o movimento que as opções precificam e o que o mercado de opções está sinalizando."""
import json
import html as H
import os
import ui
import momento as M0
import baleias_pg as B

CSS = B.CSS + """
.op-r{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;margin:0 0 12px}
.op-k{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px 12px}
.op-k small{display:block;color:var(--mu);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.op-k b{display:block;font-size:20px;margin:2px 0}.op-k em{display:block;font-style:normal;color:var(--mu);font-size:12px}
.op-k.dn{border-color:#ef444466}.op-k.dn b{color:var(--rd)}.op-k.up{border-color:#10b98166}.op-k.up b{color:var(--gr)}
.op-v{border-radius:16px;padding:14px 16px;margin:0 0 14px;border:1px solid var(--line);background:var(--card)}
.op-v h2{margin:0 0 6px;font-size:18px}.op-v.alta{border-color:#10b981}.op-v.baixa{border-color:#ef4444}
.op-v ul{margin:8px 0 0;padding-left:18px;font-size:13px}.op-v li{margin:3px 0}
.op-v .tag{display:inline-block;border-radius:999px;padding:2px 10px;font-weight:800;font-size:13px;color:#fff;margin-left:6px;vertical-align:middle}
.op-ler{font-size:14px;line-height:1.5;margin:6px 0}
"""

JS = M0.LIB + r"""
function N(v){if(v==null)return'–';var a=Math.abs(v);return a>=1e6?f1(v/1e6,1)+' mi':a>=1e3?f1(v/1e3,a>=1e5?0:1)+' mil':f1(v,0)}
var TK=Object.keys(D.ativos),AT=TK[0],JN='30',MET='oi';
var NOMEJ={'7':'Até 7 dias','30':'Até 30 dias','0':'Todos os vencimentos'};
function us(v){return v==null?'–':'US$ '+f1(v,(v%1==0||v>=1000)?0:2)}
function pc(v){return v==null?'–':(v>=0?'+':'−')+f1(Math.abs(v),1)+'%'}
function dd(s){var p=s.split('-');return p[2]+'/'+p[1]}
function hr(ts){return new Date(ts*1000).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}
function tp(t){return '<span class=tip data-tip="'+t.replace(/"/g,'&quot;')+'">i</span>'}
function K(c,t,v,s,tt){return '<div class="op-k '+(c||'')+'"><small>'+t+(tt?tp(tt):'')+'</small><b>'+v+'</b><em>'+(s||'')+'</em></div>'}
function vies(an){var s=an.vies.s,n=an.vies.n;
 if(!n)return{t:'sem dados suficientes',c:'#9ca3af',k:''};
 if(s>=2)return{t:'ALTA',c:'#10b981',k:'alta'};if(s==1)return{t:'leve ALTA',c:'#65a30d',k:'alta'};
 if(s==0)return{t:'NEUTRO',c:'#9ca3af',k:''};if(s==-1)return{t:'leve BAIXA',c:'#f59e0b',k:'baixa'};return{t:'BAIXA',c:'#ef4444',k:'baixa'}}
function sinal(x,an){var n=x[0],v=x[1],p=x[2],ic=p>0?'▲':p<0?'▼':'●',cl=p>0?'lg':p<0?'sh2':'';
 if(n=='fluxo')return '<span class='+cl+'>'+ic+'</span> Fluxo de hoje (put/call do volume = '+f1(v,2)+'): '+(p>0?'mais calls que puts sendo negociadas, aposta em alta.':p<0?'mais puts que calls sendo negociadas, proteção ou aposta em queda.':'equilibrado entre calls e puts.');
 if(n=='posicoes')return '<span class='+cl+'>'+ic+'</span> Posições abertas (put/call = '+f1(v,2)+'): '+(p>0?'bem mais calls que puts em aberto.':p<0?'puts em aberto igualam ou superam as calls.':'equilíbrio entre calls e puts.');
 return '<span class='+cl+'>'+ic+'</span> Max pain '+pc(v)+' em relação ao preço: '+(p>0?'o preço tende a ser puxado para cima perto do vencimento.':p<0?'o preço tende a ser puxado para baixo perto do vencimento.':'praticamente no preço atual, sem puxão claro.')}
function resumo(a,an){var up=an.up[0],dn=an.dn[0],mp=an.mp,mv=an.mv,h='<div class=op-r>';
 h+=K('','Preço agora',us(a.spot),'leitura de '+hr(a.ts));
 h+=K('dn','🔻 Barreira de queda',dn?us(dn.k):'–',dn?pc(dn.pct)+' · '+N(dn.oi)+' puts em aberto':'sem puts relevantes abaixo','Strike abaixo do preço com mais puts em aberto no período. Costuma funcionar como suporte; se for perdido, a queda pode acelerar.');
 h+=K('up','🔺 Barreira de alta',up?us(up.k):'–',up?pc(up.pct)+' · '+N(up.oi)+' calls em aberto':'sem calls relevantes acima','Strike acima do preço com mais calls em aberto no período. Costuma funcionar como resistência perto do vencimento; se for rompido, a alta pode ganhar força.');
 h+=K('','🧲 Max pain',mp?us(mp.k):'–',mp?'venc. '+dd(mp.d)+' · '+pc(mp.pct):'','Preço em que mais opções expiram sem valor (menor perda para quem vendeu). Perto do vencimento o preço tende a gravitar para ele. Calculado no vencimento mais carregado do período.');
 h+=K('','Movimento precificado',mv?'±'+f1(mv.pct,1)+'%':'–',mv?us(mv.lo)+' a '+us(mv.hi)+' até '+dd(mv.d):'','Preço da opção de compra e da de venda no preço atual (straddle) dividido pelo preço do ativo. É a variação que o mercado considera provável até o vencimento, para cima ou para baixo.');
 h+=K('','Put/Call',an.pcoi==null?'–':f1(an.pcoi,2),'posições · fluxo '+(an.pcv==null?'–':f1(an.pcv,2)),'Puts divididas por calls. Abaixo de 0,7 indica mais apostas em alta; acima de 1,0, mais proteção ou apostas em queda. Posições = contratos em aberto; fluxo = contratos negociados hoje.');
 return h+'</div>'}
function leitura(a,an){var v=vies(an),up=an.up[0],dn=an.dn[0],h='<div class="op-v '+v.k+'"><h2>O que as opções sinalizam para '+AT+'<span class=tag style="background:'+v.c+'">'+v.t+'</span></h2>';
 var t='Com o preço em '+us(a.spot)+', ';
 if(dn&&up)t+='a <b>barreira de queda</b> está em <b>'+us(dn.k)+'</b> ('+pc(dn.pct)+') e a <b>barreira de alta</b> em <b>'+us(up.k)+'</b> ('+pc(up.pct)+'). '+(Math.abs(dn.pct)<up.pct*0.6?'O preço está mais perto do suporte que da resistência: há mais espaço para subir do que para cair antes de encontrar uma barreira.':up.pct<Math.abs(dn.pct)*0.6?'O preço está mais perto da resistência que do suporte: a alta encontra barreira antes de a queda encontrar a dela.':'As duas barreiras estão a distâncias parecidas: faixa de lado entre elas.');
 else if(dn)t+='a barreira de queda está em <b>'+us(dn.k)+'</b> ('+pc(dn.pct)+').';
 else if(up)t+='a barreira de alta está em <b>'+us(up.k)+'</b> ('+pc(up.pct)+').';
 if(an.mv)t+=' O mercado precifica movimento de ±'+f1(an.mv.pct,1)+'% até '+dd(an.mv.d)+' ('+us(an.mv.lo)+' a '+us(an.mv.hi)+').';
 h+='<div class=op-ler>'+t+'</div><ul>'+an.vies.sinais.map(function(x){return '<li>'+sinal(x,an)+'</li>'}).join('')+'</ul>';
 h+='<div class=bl-n>Como ler: o viés soma os sinais acima (fluxo, posições e max pain). Isto mostra onde as opções estão concentradas, não é previsão. Calls grandes podem ser cobertura ou venda coberta, e nem toda posição é direcional.</div></div>';
 return h}
function dados(){return D.ativos[AT]}
function janelaEx(a){var l=JN=='0'?99999:+JN,r=a.exp.filter(function(e){return e.n<=l});return r.length?r:a.exp.slice(0,1)}
function graf1(a){var ex=janelaEx(a),cv=document.getElementById('c1');
 var c=ex.map(function(e){return MET=='oi'?e.co:e.cv}),p=ex.map(function(e){return MET=='oi'?e.po:e.pv});
 bars(cv,ex.map(function(e){return dd(e.d)}),[{l:'Calls',c:'#3b82f6',v:c},{l:'Puts',c:'#ef4444',v:p}],{f:function(v){return N(v)}})}
function graf2(a){var P=a.perfil[JN],cv=document.getElementById('c2');if(!P||!P.length)return;
 var dpr=window.devicePixelRatio||1,W=cv.clientWidth,H=cv.clientHeight;cv.width=W*dpr;cv.height=H*dpr;var g=cv.getContext('2d');g.scale(dpr,dpr);
 var cs=getComputedStyle(document.body),mu=cs.getPropertyValue('--mu')||'#888',ln=cs.getPropertyValue('--line')||'#ddd';
 var mx=1;P.forEach(function(r){mx=Math.max(mx,r[1],r[2])});var n=P.length,pl=8,pr=56,pt=14,pb=20,bw=(W-pl-pr)/n,w=bw*.4;
 function Y(v){return pt+(H-pt-pb)*(1-v/mx)}g.font='10px system-ui';
 for(var k=0;k<=3;k++){var v=mx*k/3,y=Y(v);g.strokeStyle=ln;g.beginPath();g.moveTo(pl,y);g.lineTo(W-pr,y);g.stroke();g.fillStyle=mu;g.fillText(N(v),W-pr+4,y+3)}
 var an=a.an[JN],bu=an.up[0]?an.up[0].k:null,bd=an.dn[0]?an.dn[0].k:null;
 P.forEach(function(r,i){var x0=pl+i*bw+bw*.08;g.fillStyle=(r[0]==bu)?'#1d4ed8':'#3b82f6';g.fillRect(x0,Y(r[1]),w,Y(0)-Y(r[1]));g.fillStyle=(r[0]==bd)?'#b91c1c':'#ef4444';g.fillRect(x0+w,Y(r[2]),w,Y(0)-Y(r[2]));
  if(n<=14||i%2==0){g.fillStyle=mu;g.textAlign='center';g.fillText(f1(r[0],r[0]%1?1:0),x0+w,H-5);g.textAlign='left'}});
 var xs=null;for(var i=0;i<n;i++){if(P[i][0]>=a.spot){xs=i==0?0:i-1+(a.spot-P[i-1][0])/(P[i][0]-P[i-1][0]);break}}if(xs==null)xs=n-1;
 var X=pl+xs*bw+bw*.08+w;g.setLineDash([4,3]);g.strokeStyle='#f59e0b';g.lineWidth=1.5;g.beginPath();g.moveTo(X,pt);g.lineTo(X,Y(0));g.stroke();g.setLineDash([]);g.fillStyle='#f59e0b';g.fillText('preço '+f1(a.spot,2),Math.min(X+4,W-pr-70),pt+2);
 g.fillStyle='#3b82f6';g.fillText('● Calls',pl,pt+2);g.fillStyle='#ef4444';g.fillText('● Puts',pl+50,pt+2)}
function tabEx(a){var h='<div class=bl-sc><table class=bl-t><thead><tr><th>Vencimento</th><th>Dias</th><th>Calls (posições)</th><th>Puts (posições)</th><th>Put/Call</th><th>Calls (volume)</th><th>Puts (volume)</th><th>Vol. implícita'+tp('Volatilidade que a opção no preço atual embute, ao ano. Quanto maior, mais movimento o mercado espera.')+'</th><th>Movimento ±</th><th>Max pain</th></tr></thead><tbody>';
 a.exp.forEach(function(e){h+='<tr><td><b>'+dd(e.d)+'</b></td><td>'+e.n+'</td><td class=lg>'+N(e.co)+'</td><td class=sh2>'+N(e.po)+'</td><td>'+(e.co?f1(e.po/e.co,2):'–')+'</td><td>'+N(e.cv)+'</td><td>'+N(e.pv)+'</td><td>'+(e.iv==null?'–':f1(e.iv,0)+'%')+'</td><td>'+(e.mv==null?'–':'±'+f1(e.mv,1)+'%')+'</td><td>'+(e.mp?us(e.mp):'–')+'</td></tr>'});
 return h+'</tbody></table></div>'}
function tabHist(a){var H=(a.hist||[]).slice(-10).reverse(),NS={'10:00':'30 min após abrir','15:00':'15h ET','16:20':'pós-fechamento'};
 var h='<div class=bl-sc><table class=bl-t><thead><tr><th>Leitura (Brasília)</th><th>Momento</th><th>Preço</th><th>Put/Call posições</th><th>Put/Call fluxo</th><th>Barreira de queda</th><th>Barreira de alta</th><th>Viés</th></tr></thead><tbody>';
 H.forEach(function(r){var v=vies({vies:{s:r.v,n:r.nv}});h+='<tr><td>'+hr(r.ts)+'</td><td>'+(NS[r.s]||r.s)+'</td><td>'+us(r.p)+'</td><td>'+(r.pcoi==null?'–':f1(r.pcoi,2))+'</td><td>'+(r.pcv==null?'–':f1(r.pcv,2))+'</td><td>'+us(r.dn)+'</td><td>'+us(r.up)+'</td><td><b style="color:'+v.c+'">'+v.t+'</b></td></tr>'});
 return h+'</tbody></table></div>'}
function draw(){var a=dados(),an=a.an[JN];
 var h='<div class=bl-top>'+TK.map(function(t){return '<button data-t='+t+' class="'+(t==AT?'on':'')+'">'+t+'</button>'}).join('')+'</div>';
 h+='<div class=bl-f><span class=bl-sel style="margin-left:0">'+['7','30','0'].map(function(j){return '<button data-j='+j+' class="'+(j==JN?'on':'')+'">'+NOMEJ[j]+'</button>'}).join('')+'</span></div>';
 if(!an){document.getElementById('op').innerHTML=h+'<p class=sub>Sem vencimentos nessa janela.</p>';bind();return}
 h+=resumo(a,an)+leitura(a,an);
 h+='<div class=bl-c><h3>Calls e puts por vencimento'+tp('Contratos de calls (azul) e puts (vermelho) em cada vencimento. Posições = contratos em aberto; volume = negociados no dia. Vencimentos com muita posição são onde o mercado concentra as apostas.')+'<span class=bl-sel>'+[['oi','Posições'],['vol','Volume']].map(function(s){return '<button data-m='+s[0]+' class="'+(s[0]==MET?'on':'')+'">'+s[1]+'</button>'}).join('')+'</span></h3><canvas id=c1></canvas></div>';
 h+='<div class=bl-c><h3>Posições por strike'+tp('Onde estão as posições em aberto, somando os vencimentos da janela escolhida. Barra azul escura = barreira de alta; vermelha escura = barreira de queda; linha laranja = preço atual.')+'</h3><canvas id=c2></canvas></div>';
 h+='<div class=bl-c><h3>Todos os vencimentos</h3>'+tabEx(a)+'</div>';
 h+='<div class=bl-c><h3>Leituras anteriores'+tp('Cada leitura é feita 3 vezes por pregão: 30 minutos depois da abertura, às 15h (Nova York) e depois do fechamento. Serve para ver se as barreiras e o viés mudaram ao longo do dia e dos dias.')+'</h3>'+tabHist(a)+'</div>';
 h+='<div class=mo-note>Fonte: cadeias de opções do Yahoo Finance (ações e ETFs dos EUA), atualizadas 3 vezes por pregão. As posições em aberto só são atualizadas pela bolsa uma vez por dia, então o que muda durante o dia é principalmente o volume e o preço.</div>';
 document.getElementById('op').innerHTML=h;bind();graf1(a);graf2(a)}
function bind(){document.querySelectorAll('[data-t]').forEach(function(b){b.onclick=function(){AT=b.dataset.t;draw()}});
 document.querySelectorAll('[data-j]').forEach(function(b){b.onclick=function(){JN=b.dataset.j;draw()}});
 document.querySelectorAll('[data-m]').forEach(function(b){b.onclick=function(){MET=b.dataset.m;draw()}})}
var TB=document.createElement('div');TB.id='tipbox';document.body.appendChild(TB);
function tipShow(el){TB.textContent=el.dataset.tip;TB.style.display='block';var r=el.getBoundingClientRect(),w=TB.offsetWidth,h=TB.offsetHeight,x=Math.min(Math.max(8,r.left-8),innerWidth-w-8),y=r.bottom+8;if(y+h>innerHeight-8)y=Math.max(8,r.top-h-8);TB.style.left=x+'px';TB.style.top=y+'px'}
document.addEventListener('mouseover',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t)tipShow(t);else TB.style.display='none'});
document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t){if(TB.style.display=='block'&&TB.textContent==t.dataset.tip)TB.style.display='none';else tipShow(t)}else TB.style.display='none'});
window.addEventListener('resize',function(){var a=dados();if(a&&a.an[JN]){graf1(a);graf2(a)}});
draw();
"""


def dados(raiz):
    f = os.path.join(raiz, "categorias", "eua", "dados", "opcoes.json")
    if not os.path.exists(f): return None
    try: d = json.load(open(f, encoding="utf-8"))
    except Exception: return None
    if not d.get("ativos"): return None
    return {"ts": d.get("ts"), "ativos": d["ativos"]}


def pagina(arq, titulo, paginas, D):
    topo = ui.cabeca(titulo, paginas, arq) + f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>"
    if not D:
        return topo + ("<p class=sub>A primeira leitura das opções ainda não foi feita. Elas são lidas 3 vezes por pregão (30 min depois da abertura, às 15h e depois do fechamento, "
                       "horário de Nova York). Volte depois da próxima leitura.</p></main></body></html>")
    return (topo + "<p class=sub>Onde o mercado de opções concentra as apostas: barreiras de alta e de queda, max pain e o movimento que está precificado. "
            "Lido 3 vezes por pregão. Passe o mouse no <b>i</b> para ver o que cada item significa.</p><div id=op></div></main><script>var D="
            + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";" + JS + "</script></body></html>")
