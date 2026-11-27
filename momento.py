"""Aba Momento: tendência (MM200), RSI e notas descritivas por empresa, sem sinal de compra ou venda.
BDR e ação dos EUA ficam na mesma linha, com a técnica de cada um separada."""
import json
import html as H
import os
import numpy as np
import pandas as pd
import ui

CSS = """
.mo-bar{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;margin:0 0 12px}
.mo-bar button,.mo-bar select,.mo-bar input{border:1px solid var(--line);background:var(--card);color:var(--tx);border-radius:999px;padding:6px 13px;font-size:13px;font-weight:600}
.mo-bar button{cursor:pointer}.mo-bar button.on{background:var(--ac);color:#fff;border-color:var(--ac)}.mo-bar input{min-width:170px;font-weight:400}
.mo-t{width:100%;border-collapse:separate;border-spacing:0;background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.mo-t th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mu);text-align:left;padding:9px 10px;background:var(--card2);cursor:pointer;white-space:nowrap;user-select:none}
.mo-t td{text-align:left;padding:8px 10px;border-top:1px solid var(--line);font-size:13px;vertical-align:middle}
.mo-t tr.mr{cursor:pointer}.mo-t tr.mr:hover td{background:var(--card2)}
.mo-n b{font-size:14px}.mo-n small{display:block;color:var(--mu);font-size:11px}
.sf{display:inline-flex;align-items:center;gap:6px;font-weight:700;font-variant-numeric:tabular-nums}.sf i{width:12px;height:12px;border-radius:50%;display:inline-block;background:var(--mu);opacity:.4}
.sf.g i{background:#16a34a;opacity:1}.sf.r i{background:#dc2626;opacity:1}.sf.n i{background:#9ca3af;opacity:1}.sf.y i{background:#f59e0b;opacity:1}.rb{display:inline-block;margin-left:6px;padding:1px 7px;border:1px solid var(--line);border-radius:999px;font-size:10.5px;font-weight:600;color:var(--mu);white-space:nowrap}.sf small{color:var(--mu);font-weight:500;font-size:11px}
.mo-o{position:fixed;inset:0;background:rgba(5,8,15,.55);z-index:50;display:none;overflow:auto;padding:16px}
.mo-p{max-width:1000px;margin:0 auto;background:var(--bg);border:1px solid var(--line);border-radius:16px;padding:16px 18px}
.mo-p h2{margin:0 0 4px;font-size:20px}.mo-p .x{float:right;cursor:pointer;font-size:20px;color:var(--mu);border:0;background:none}
.mo-tabs{display:flex;gap:6px;margin:10px 0}.mo-tabs button{border:1px solid var(--line);background:var(--card);color:var(--tx);border-radius:999px;padding:5px 14px;font-weight:700;font-size:13px;cursor:pointer}.mo-tabs button.on{background:var(--tx);color:var(--bg)}
.mo-g{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin:10px 0}
.mo-k{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:7px 10px}.mo-k small{display:block;color:var(--mu);font-size:10.5px;font-weight:700;text-transform:uppercase}.mo-k b{font-size:15px}
.mo-c{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px 10px;margin:8px 0}.mo-c h4{margin:0 0 4px;font-size:12px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em}.mo-c canvas{width:100%;height:190px;display:block}
.mo-soon{background:var(--card);border:1px dashed var(--line);border-radius:12px;padding:20px;text-align:center;color:var(--mu)}
.mo-note{font-size:12px;color:var(--mu);margin:6px 0}
"""

LIB = r"""
function f1(v,d){return(v==null||v!==v)?'–':v.toLocaleString('pt-BR',{minimumFractionDigits:d==null?1:d,maximumFractionDigits:d==null?1:d})}
function sg(v,d){return v==null?'–':(v>=0?'+':'−')+f1(Math.abs(v),d)}
function sf(t){if(!t||t.sc==null)return'<span class="sf"><i></i>–</span>';var c=t.sc>=6.5?'g':(t.sc<=3.5?'r':'n');return'<span class="sf '+c+'"><i></i>'+f1(t.sc,1)+'<small>'+(c=='g'?'nota alta':c=='r'?'nota baixa':'nota média')+'</small></span>'}
var TRN={'Alta':['g','tendência de alta','acima das duas MM200'],'Correção':['y','tendência mista','acima da MM200 semanal, abaixo da diária'],'Repique':['y','tendência mista','acima da MM200 diária, abaixo da semanal'],'Baixa':['r','tendência de baixa','abaixo das duas MM200']};
function rsib(t){if(!t||t.rw==null)return'';return t.rw>=70?'<span class=rb title="RSI semanal acima de 70">RSI sem. '+f1(t.rw,0)+' ≥ 70</span>':t.rw<=30?'<span class=rb title="RSI semanal abaixo de 30">RSI sem. '+f1(t.rw,0)+' ≤ 30</span>':''}
function tf(t){if(!t||!TRN[t.rg])return'<span class="sf"><i></i>–</span>';var x=TRN[t.rg];return'<span class="sf '+x[0]+'" title="'+x[2]+'"><i></i><small>'+x[1]+'</small></span>'+rsib(t)}
function line(cv,series,opt){var dpr=window.devicePixelRatio||1,W=cv.clientWidth,H=cv.clientHeight;cv.width=W*dpr;cv.height=H*dpr;var g=cv.getContext('2d');g.scale(dpr,dpr);
 var all=[];series.forEach(function(s){s.v.forEach(function(x){if(x!=null)all.push(x)})});if(opt.lines)opt.lines.forEach(function(l){all.push(l.y)});
 var mn=Math.min.apply(null,all),mx=Math.max.apply(null,all);if(opt.min!=null)mn=opt.min;if(opt.max!=null)mx=opt.max;var pd=(mx-mn)*.06||1;if(opt.min==null)mn-=pd;if(opt.max==null)mx+=pd;
 var n=series[0].v.length,pl=8,pr=52,pt=8,pb=18,cs=getComputedStyle(document.body),mu=cs.getPropertyValue('--mu')||'#888',ln=cs.getPropertyValue('--line')||'#ddd';
 function X(i){return pl+(W-pl-pr)*i/(n-1)}function Y(v){return pt+(H-pt-pb)*(1-(v-mn)/(mx-mn))}
 g.font='10px system-ui';g.fillStyle=mu;g.strokeStyle=ln;g.lineWidth=1;
 for(var k=0;k<=4;k++){var v=mn+(mx-mn)*k/4,y=Y(v);g.beginPath();g.moveTo(pl,y);g.lineTo(W-pr,y);g.stroke();g.fillText(f1(v,opt.d==null?2:opt.d),W-pr+4,y+3)}
 if(opt.lines)opt.lines.forEach(function(l){var y=Y(l.y);g.setLineDash([4,3]);g.strokeStyle=l.c;g.beginPath();g.moveTo(pl,y);g.lineTo(W-pr,y);g.stroke();g.setLineDash([])});
 series.forEach(function(s){g.beginPath();g.strokeStyle=s.c;g.lineWidth=s.w||1.5;var st=false;s.v.forEach(function(x,i){if(x==null){st=false;return}if(!st){g.moveTo(X(i),Y(x));st=true}else g.lineTo(X(i),Y(x))});g.stroke()});
 g.fillStyle=mu;if(opt.dates){[0,Math.floor(n/2),n-1].forEach(function(i){var d=new Date(opt.dates[i]*864e5);g.textAlign=i==0?'left':i==n-1?'right':'center';g.fillText(d.toLocaleDateString('pt-BR',{month:'short',year:'2-digit'}),i==0?pl:i==n-1?W-pr:X(i),H-4)});g.textAlign='left'}
 var lg=0;series.forEach(function(s){if(s.l){g.fillStyle=s.c;g.fillText('● '+s.l,pl+lg,pt+8);lg+=s.l.length*6+22}})}

function bars(cv,labels,series,opt){var dpr=window.devicePixelRatio||1,W=cv.clientWidth,H=cv.clientHeight;cv.width=W*dpr;cv.height=H*dpr;var g=cv.getContext('2d');g.scale(dpr,dpr);
 var all=[0];series.forEach(function(s){s.v.forEach(function(x){if(x!=null)all.push(x)})});var mn=Math.min.apply(null,all),mx=Math.max.apply(null,all);if(mx==mn)mx=mn+1;
 var n=labels.length,pl=8,pr=56,pt=16,pb=18,cs=getComputedStyle(document.body),mu=cs.getPropertyValue('--mu')||'#888',ln=cs.getPropertyValue('--line')||'#ddd';
 function Y(v){return pt+(H-pt-pb)*(1-(v-mn)/(mx-mn))}g.font='10px system-ui';g.fillStyle=mu;g.strokeStyle=ln;
 for(var k=0;k<=3;k++){var v=mn+(mx-mn)*k/3,y=Y(v);g.beginPath();g.moveTo(pl,y);g.lineTo(W-pr,y);g.stroke();g.fillText((opt.f||f1)(v),W-pr+4,y+3)}
 var bw=(W-pl-pr)/n,m=series.length,w=bw*.8/m;
 series.forEach(function(s,j){g.fillStyle=s.c;s.v.forEach(function(x,i){if(x==null)return;var x0=pl+i*bw+bw*.1+j*w,y0=Y(0),y1=Y(x);g.fillRect(x0,Math.min(y0,y1),w,Math.abs(y1-y0)||1)})});
 g.fillStyle=mu;g.textAlign='center';labels.forEach(function(l,i){if(n<=8||i%2==n%2)g.fillText(l,pl+i*bw+bw/2,H-4)});g.textAlign='left';
 var lg=0;series.forEach(function(s){g.fillStyle=s.c;g.fillText('● '+s.l,pl+lg,10);lg+=s.l.length*6+22})}
function M(v){if(v==null)return'–';var a=Math.abs(v);return a>=1e9?f1(v/1e9,1)+' bi':a>=1e6?f1(v/1e6,0)+' mi':f1(v/1e3,0)+' mil'}
function B(v){return v==null?null:v/1e9}
"""

JS = LIB + r"""
var R=D.rows,SORT={k:'ger',d:-1},FG='',FS='',FQ='',FSIG='';
function ger(r){var v=[];['t1','t2'].forEach(function(k){if(r[k]&&r[k].sc!=null)v.push(r[k].sc)});var t=v.length?v.reduce(function(a,b){return a+b},0)/v.length:null;var P=[[t,.4],[r.fu&&r.fu.sc,.4],[r.an&&r.an.sc,.2]],a=0,w=0;P.forEach(function(p){if(p[0]!=null){a+=p[0]*p[1];w+=p[1]}});return w?a/w:null}
R.forEach(function(r){r.ger=ger(r)});
var SET=Array.from(new Set(R.map(function(r){return r.s}).filter(Boolean))).sort();
var TO={'Alta':3,'Correção':2,'Repique':2,'Baixa':1};
function val(r,k){if(k=='n')return r.n;if(k=='ger')return r.ger;if(k=='t1')return r.t1&&TO[r.t1.rg];if(k=='t2')return r.t2&&TO[r.t2.rg];if(k=='fu')return r.fu&&r.fu.sc;if(k=='an')return r.an&&r.an.sc;return null}
function build(){
 var bar='<div class=mo-bar><input id=q placeholder="buscar ativo…" value="'+FQ+'"><button data-g="" class="'+(FG==''?'on':'')+'">Todos</button><button data-g=B3 class="'+(FG=='B3'?'on':'')+'">B3</button><button data-g=EUA class="'+(FG=='EUA'?'on':'')+'">EUA + BDR</button><select id=st><option value="">Todos os setores</option>'+SET.map(function(s){return'<option'+(FS==s?' selected':'')+'>'+s+'</option>'}).join('')+'</select><button data-sg=g class="'+(FSIG=='g'?'on':'')+'">● Nota alta</button><button data-sg=r class="'+(FSIG=='r'?'on':'')+'">● Nota baixa</button></div>';
 var L=R.filter(function(r){if(FG&&r.g!=FG)return false;if(FS&&r.s!=FS)return false;if(FQ&&(r.n+' '+(r.b||'')).toUpperCase().indexOf(FQ.toUpperCase())<0)return false;if(FSIG){var x=r.ger;if(x==null)return false;if(FSIG=='g'&&x<6.5)return false;if(FSIG=='r'&&x>3.5)return false}return true});
 L.sort(function(a,b){var x=val(a,SORT.k),y=val(b,SORT.k);if(x==null)return 1;if(y==null)return-1;return x<y?-SORT.d:x>y?SORT.d:0});
 var h=bar+'<table class=mo-t><thead><tr><th data-k=n>Empresa</th><th data-k=t1>Tendência (B3 / EUA)</th><th data-k=t2>Tendência BDR</th><th data-k=fu>Fundamental</th><th data-k=an>Analistas externos</th><th data-k=ger>Nota geral ▾</th></tr></thead><tbody>';
 L.forEach(function(r){h+='<tr class=mr data-i="'+r.i+'"><td class=mo-n><b>'+r.n+(r.b?' <span class=mu style="font-weight:500">· '+r.b+'</span>':'')+'</b><small>'+(r.s||'')+'</small></td><td>'+tf(r.t1)+'</td><td>'+(r.t2?tf(r.t2):'<span class=mu>–</span>')+'</td><td>'+(r.fu?sf(r.fu):'<span class=mu>–</span>')+'</td><td>'+(r.an?sf(r.an):'<span class=mu>–</span>')+'</td><td>'+sf({sc:r.ger})+'</td></tr>'});
 h+='</tbody></table>';document.getElementById('mo').innerHTML=h}
document.addEventListener('click',function(e){var t=e.target;
 if(t.dataset&&t.dataset.g!==undefined&&t.closest('.mo-bar')){FG=t.dataset.g;build();return}
 if(t.dataset&&t.dataset.sg){FSIG=FSIG==t.dataset.sg?'':t.dataset.sg;build();return}
 var th=t.closest('th[data-k]');if(th){var k=th.dataset.k;SORT=SORT.k==k?{k:k,d:-SORT.d}:{k:k,d:k=='n'?1:-1};build();return}
 var tr=t.closest('tr.mr');if(tr){openD(+tr.dataset.i);return}
 if(t.closest('.x')||t.id=='mo-o'){document.getElementById('mo-o').style.display='none'}});
document.addEventListener('input',function(e){if(e.target.id=='q'){FQ=e.target.value;var p=e.target.selectionStart;build();var q=document.getElementById('q');q.focus();q.setSelectionRange(p,p)}});
document.addEventListener('change',function(e){if(e.target.id=='st'){FS=e.target.value;build()}});
var CUR=null,TAB='tec',LST=0;
function openD(i){CUR=R.filter(function(r){return r.i==i})[0];LST=0;TAB='tec';document.getElementById('mo-o').style.display='block';drawD()}
function qlab(a){return a.map(function(x){var d=x[0].split('-');return d[1]+'/'+d[0].slice(2)})}
function tr(a,s){return a?a.map(function(x){return x[1]}):[]}
function dt(d){if(!d)return'–';var p=d.split('-');return p[2]+'/'+p[1]+'/'+p[0]}
function dias(d){var n=Math.round((new Date(d)-new Date(new Date().toISOString().slice(0,10)))/864e5);return n==0?'hoje':n>0?'em '+n+' dias':'há '+(-n)+' dias'}
var RK={strong_buy:'Compra forte',buy:'Compra',hold:'Neutro',underperform:'Abaixo do mercado',sell:'Venda',strong_sell:'Venda forte'};
var FONTE_AN='Dados de analistas externos (terceiros), compilados pelo Yahoo Finance. Não são opinião nem recomendação desta plataforma.';
var SUB={val:'Valuation',cres:'Crescimento',rent:'Rentabilidade',saude:'Saúde financeira',div:'Dividendos'};
function subs(fu){return'<div class=mo-g>'+Object.keys(SUB).map(function(k){var v=fu.sub[k];return'<div class=mo-k><small>'+SUB[k]+'</small><b>'+sf({sc:v})+'</b></div>'}).join('')+'</div>'}
function pct(v){return v==null?'–':f1(v,1)+'%'}
function fundH(r){var fu=r.fu;if(!fu)return'<div class=mo-soon>Sem dados fundamentalistas para este ativo (ETFs não têm).</div>';
 var k=fu.k,rs=fu.rs,h='<div>'+sf(fu)+' <span class=mu>nota fundamentalista (0–10)</span></div>'+subs(fu);
 h+='<div class=mo-c><h4>Resultados</h4><div class=mo-g>';
 h+='<div class=mo-k><small>Próximo resultado</small><b>'+(rs.prox?dt(rs.prox.d)+' <span class=mu style="font-weight:500;font-size:12px">'+dias(rs.prox.d)+'</span>':'–')+'</b></div>';
 h+='<div class=mo-k><small>Último resultado</small><b>'+(rs.ult?dt(rs.ult.d)+' <span class=mu style="font-weight:500;font-size:12px">'+dias(rs.ult.d)+'</span>':'–')+'</b></div>';
 var u=rs.ult,lab='–';if(u&&u.sur!=null)lab=u.sur>=3?'🟢 Superou':u.sur<=-3?'🔴 Abaixo':'⚪ Em linha';
 h+='<div class=mo-k><small>Como foi (lucro/ação)</small><b>'+lab+'</b></div>';
 h+='<div class=mo-k><small>LPA reportado × esperado</small><b>'+(u&&u.rep!=null?f1(u.rep,2)+' × '+(u.est!=null?f1(u.est,2):'–'):'–')+'</b></div>';
 h+='<div class=mo-k><small>Surpresa</small><b>'+(u&&u.sur!=null?sg(u.sur,1)+'%':'–')+'</b></div>';
 h+='<div class=mo-k><small>Receita vs 4 tri. antes</small><b>'+(rs.rev!=null?sg(rs.rev,1)+'%':'–')+'</b></div>';
 h+='<div class=mo-k><small>Lucro líq. vs 4 tri. antes</small><b>'+(rs.liq!=null?sg(rs.liq,1)+'%':'–')+'</b></div>';
 h+='<div class=mo-k><small>Margem líq. (tri. / ano ant.)</small><b>'+(rs.mg!=null?f1(rs.mg,1)+'%':'–')+' / '+(rs.mg0!=null?f1(rs.mg0,1)+'%':'–')+'</b></div></div>';
 if(rs.per)h+='<div class=mo-note>Último balanço no histórico: trimestre de '+dt(rs.per)+'. Datas e LPA esperado vêm do Yahoo e podem variar um pouco.</div>';h+='</div>';
 h+='<div class=mo-g>'+[['P/L',f1(k.pl,1)],['P/L projetado',f1(k.plf,1)],['P/VP',f1(k.pvp,2)],['EV/EBITDA',f1(k.eve,1)],['Dividend yield',pct(k.dy)],['Payout',pct(k.po)],['ROE',pct(k.roe)],['Margem líquida',pct(k.ml)],['Margem operacional',pct(k.mo)],['Cresc. receita (a/a)',k.cr==null?'–':sg(k.cr,1)+'%'],['Cresc. lucro (a/a)',k.cl==null?'–':sg(k.cl,1)+'%'],['Dív. líq./EBITDA',f1(k.nd,1)],['Liquidez corrente',f1(k.lc,2)],['Fluxo de caixa livre',M(k.fcl)],['Valor de mercado',M(k.mc)]].map(function(x){return'<div class=mo-k><small>'+x[0]+'</small><b>'+x[1]+'</b></div>'}).join('')+'</div>';
 h+='<div class=mo-c><h4>Receita e lucro líquido por trimestre (bi)</h4><canvas id=f1></canvas></div><div class=mo-c><h4>Margens por trimestre (%)</h4><canvas id=f2></canvas></div><div class=mo-c><h4>Dívida × caixa (bi)</h4><canvas id=f3></canvas></div><div class=mo-c><h4>Caixa operacional e livre por ano (bi)</h4><canvas id=f4></canvas></div>';
 h+='<div class=mo-note>Nota fundamentalista = média ponderada de valuation (peso 2), crescimento (2), rentabilidade (2), saúde financeira (2) e dividendos (1), por faixas absolutas fixas (ex.: P/L até 12 = barato; dív. líq./EBITDA até 1 = confortável). Bancos/seguradoras usam ROE, P/VP e ROA em vez de dívida/EBITDA. Valores em moeda do ativo (R$ ou US$).</div>';return h}
function anaH(r){var a=r.an;if(!a)return'<div class=mo-soon>Sem cobertura de analistas disponível.</div>';
 var h='<div class=mo-note><b>'+FONTE_AN+'</b></div><div>'+sf(a)+' <span class=mu>consenso dos analistas externos: '+(RK[a.rk]||a.rk||'–')+' · '+a.n+' analista'+(a.n==1?'':'s')+'</span></div><div class=mo-g>';
 h+=[['Consenso externo (1=compra forte … 5=venda)',a.rm==null?'–':f1(a.rm,2)],['Analistas',a.n],['Preço-alvo médio (externo)',a.alvo==null?'–':f1(a.alvo,2)],['Alvo máximo',a.max==null?'–':f1(a.max,2)],['Alvo mínimo',a.min==null?'–':f1(a.min,2)],['Potencial até o alvo',a.up==null?'–':sg(a.up,1)+'%']].map(function(x){return'<div class=mo-k><small>'+x[0]+'</small><b>'+x[1]+'</b></div>'}).join('')+'</div>';
 var cu=r.g=='B3'?'R$':'US$';
 h+='<div class=mo-note>Preço-alvo em '+cu+' (ativo de referência '+(r.g=='B3'?r.n:r.n+' nos EUA')+'; preço atual '+cu+' '+f1(a.p,2)+').';
 if(r.t2&&a.alvo!=null&&r.t1&&r.t1.p&&r.t2.p){var ratio=r.t2.p/r.t1.p;h+=' Equivalente no BDR '+r.b+': alvo R$ '+f1(a.alvo*ratio,2)+' (preço R$ '+f1(r.t2.p,2)+') — o potencial % é o mesmo, pois o BDR acompanha a ação; a diferença real fica no câmbio.'}
 h+='</div>';
 var rs=r.fu&&r.fu.rs;if(rs&&rs.ult)h+='<div class=mo-note>Último resultado: '+dt(rs.ult.d)+(rs.ult.sur!=null?' · surpresa de lucro '+sg(rs.ult.sur,1)+'%':'')+(rs.prox?' · próximo '+dt(rs.prox.d):'')+'</div>';
 h+='<div class=mo-note>Fonte: Yahoo Finance (consenso de analistas de terceiros). Nota de analistas = 50% consenso (1→10 … 5→0) + 50% potencial até o preço-alvo (±20% ≈ nota 10/0). Com menos de 3 analistas a nota é puxada para o neutro.</div>';return h}
function drawD(){var r=CUR,lst=LST==0?r.t1:r.t2,tabs='';
 var tt=['tec','fun','ana'],tn={tec:'Técnica',fun:'Fundamental',ana:'Analistas'};
 var h='<button class=x>✕</button><h2>'+r.n+(r.b?' <span class=mu style="font-weight:500">· '+r.b+'</span>':'')+'</h2><div class=mo-note>'+(r.s||'')+'</div>';
 h+='<div class=mo-tabs>'+tt.map(function(k){return'<button data-tab='+k+' class="'+(TAB==k?'on':'')+'">'+tn[k]+'</button>'}).join('')+'</div>';
 if(TAB=='tec'){
  if(r.t2)h+='<div class=mo-tabs>'+[r.t1,r.t2].map(function(t,i){return'<button data-l='+i+' class="'+(LST==i?'on':'')+'">'+t.lb+' · '+t.cu+'</button>'}).join('')+'</div>';
  h+='<div>'+tf(lst)+' <span class=mu>Regime: <b>'+lst.rg+'</b></span> · <span class=mu>nota técnica '+f1(lst.sc,1)+'</span> · <span class=mu>preço '+lst.cu+' '+f1(lst.p,2)+'</span></div>';
  h+='<div class=mo-g>'+[['RSI diário',f1(lst.rd,0)],['RSI semanal',f1(lst.rw,0)],['vs MM200 diária',sg(lst.d2,1)+'%'],['vs MM200 semanal',sg(lst.w2,1)+'%'],['vs máx. 52 sem.',sg(lst.h52,1)+'%'],['vs máx. 5 anos',sg(lst.h5,1)+'%'],['vs mín. 52 sem.',sg(lst.l52,1)+'%'],['1 mês',sg(lst.r1,1)+'%'],['3 meses',sg(lst.r3,1)+'%'],['6 meses',sg(lst.r6,1)+'%'],['12 meses',sg(lst.r12,1)+'%'],['Força 6m vs '+lst.ix,sg(lst.rs,1)+' pp']].map(function(x){return'<div class=mo-k><small>'+x[0]+'</small><b>'+x[1]+'</b></div>'}).join('')+'</div>';
  h+='<div class=mo-c><h4>Preço diário (≈ 1 ano) com MM 50 e MM 200</h4><canvas id=c1></canvas></div><div class=mo-c><h4>Preço semanal (5 anos) com MM 200 semanal</h4><canvas id=c2></canvas></div><div class=mo-c><h4>RSI diário e semanal</h4><canvas id=c3></canvas></div>';
  h+='<div class=mo-note>Cor = tendência pela MM200: verde = preço acima das MM200 diária e semanal; amarelo = entre elas; vermelho = abaixo das duas. Nota técnica (0–10): média de RSI semanal, RSI diário, distância da MM 200 diária e queda desde a máxima de 52 semanas; em regime de baixa ela fica no máximo em 6,4, salvo RSI semanal abaixo de 30. Pesos iniciais, ainda sem backtest.</div><div class=mo-note>Legenda: RSI acima de 70 costuma ser lido no mercado como região de sobrecompra, e abaixo de 30 como sobrevenda. O indicador não prevê preço.</div>'}
 else if(TAB=='fun')h+=fundH(r);else h+=anaH(r);
 var p=document.getElementById('mo-p');p.innerHTML=h;
 p.querySelectorAll('[data-tab]').forEach(function(b){b.onclick=function(){TAB=b.dataset.tab;drawD()}});
 p.querySelectorAll('[data-l]').forEach(function(b){b.onclick=function(){LST=+b.dataset.l;drawD()}});
 if(TAB=='fun'&&r.fu){var fu=r.fu,q=fu.q||{},ql=q.rev?qlab(q.rev):[];
  if(document.getElementById('f1')){bars(document.getElementById('f1'),ql,[{v:tr(q.rev).map(B),c:'#4f46e5',l:'Receita'},{v:tr(q.liq).map(B),c:'#16a34a',l:'Lucro líq.'}],{f:function(v){return f1(v,1)}});
  var mg=function(a,b){return a&&b?a.map(function(x,i){return b[i]&&x[1]!=null&&b[i][1]?x[1]/b[i][1]*100:null}):[]};
  bars(document.getElementById('f2'),ql,[{v:mg(q.liq,q.rev),c:'#16a34a',l:'Líquida'},{v:mg(q.op,q.rev),c:'#f59e0b',l:'Operacional'},{v:mg(q.bruto,q.rev),c:'#4f46e5',l:'Bruta'}],{f:function(v){return f1(v,0)}});
  var qb=fu.qb||{};bars(document.getElementById('f3'),qb.div?qlab(qb.div):[],[{v:tr(qb.div).map(B),c:'#dc2626',l:'Dívida'},{v:tr(qb.cx).map(B),c:'#16a34a',l:'Caixa'}],{f:function(v){return f1(v,1)}});
  var af=fu.af||{};bars(document.getElementById('f4'),af.fco?af.fco.map(function(x){return x[0].slice(0,4)}):[],[{v:tr(af.fco).map(B),c:'#4f46e5',l:'Operacional'},{v:tr(af.fcl).map(B),c:'#16a34a',l:'Livre'}],{f:function(v){return f1(v,1)}})}}
 if(TAB=='tec'){var c=lst.ch;
  line(document.getElementById('c1'),[{v:c.d,c:'#4f46e5',w:1.6,l:'preço'},{v:c.m50,c:'#f59e0b',l:'MM50'},{v:c.m200,c:'#dc2626',l:'MM200'}],{dates:c.dd});
  line(document.getElementById('c2'),[{v:c.w,c:'#4f46e5',w:1.6,l:'preço'},{v:c.w200,c:'#dc2626',l:'MM200 semanal'}],{dates:c.wd});
  line(document.getElementById('c3'),[{v:c.rwd,c:'#4f46e5',l:'RSI diário'},{v:c.rww,c:'#16a34a',l:'RSI semanal'}],{min:0,max:100,d:0,lines:[{y:30,c:'#16a34a'},{y:70,c:'#dc2626'}]})}}
window.addEventListener('resize',function(){if(document.getElementById('mo-o').style.display=='block')drawD()});
build();
"""


def _rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _ler(raiz, cat, nome):
    f = os.path.join(raiz, "categorias", cat, "dados", f"{nome}_1D.csv")
    if not os.path.exists(f): return None
    d = pd.read_csv(f)
    if len(d) < 60: return None
    d.index = pd.DatetimeIndex(pd.to_datetime(d["time"], unit="s")).normalize()
    return d["close"][~d.index.duplicated(keep="last")].dropna()


def _n(x, nd=1):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def _clip(x, a=-1, b=1): return max(a, min(b, x))


def tecnica(c, idx, rotulo, moeda, idx_nome, ano=252, fw="W-FRI", esc=(25, 15, 35), cap_rsi=30):
    """indicadores técnicos de uma série diária de fechamentos"""
    w = c.resample(fw).last().dropna()
    s200, s50 = c.rolling(200).mean(), c.rolling(50).mean()
    w200 = w.rolling(200).mean()
    rd, rw = _rsi(c), _rsi(w)
    p = c.iloc[-1]
    d2 = (p / s200.iloc[-1] - 1) * 100 if np.isfinite(s200.iloc[-1]) else None
    w2 = (p / w200.iloc[-1] - 1) * 100 if len(w200) and np.isfinite(w200.iloc[-1]) else None
    h52 = (p / c.tail(ano).max() - 1) * 100
    h5 = (p / c.max() - 1) * 100
    l52 = (p / c.tail(ano).min() - 1) * 100
    def ret(n): return (p / c.iloc[-1 - n] - 1) * 100 if len(c) > n else None
    rs = None
    mt = ano // 2
    if idx is not None and len(idx) > mt and len(c) > mt:
        ri = (idx.iloc[-1] / idx.iloc[-1 - mt] - 1) * 100
        rs = ret(mt) - ri if ret(mt) is not None else None
    ab_d = d2 is not None and d2 > 0
    ab_w = w2 is not None and w2 > 0
    rg = "Alta" if ab_d and ab_w else "Correção" if ab_w and not ab_d else "Repique" if ab_d and not ab_w else "Baixa"
    if d2 is None and w2 is None: rg = "–"
    sc = None
    xs = []
    if np.isfinite(rw.iloc[-1]): xs.append((_clip((50 - rw.iloc[-1]) / 20), 2))
    if np.isfinite(rd.iloc[-1]): xs.append((_clip((50 - rd.iloc[-1]) / 20), 1.5))
    if d2 is not None: xs.append((_clip(-d2 / esc[0]), 1.5))
    xs.append((_clip((-h52 - esc[1]) / esc[2]), 1))
    if len(xs) >= 3:
        sc = 5 + 5 * sum(x * k for x, k in xs) / sum(k for _, k in xs)
        if rg == "Baixa" and sc > 6.4 and not (np.isfinite(rw.iloc[-1]) and rw.iloc[-1] < cap_rsi): sc = 6.4   # baixa confirmada: no máximo neutro, salvo capitulação (RSI semanal < 30)
        sc = max(0, min(10, sc))
    nd = 2 if p >= 10 else 4
    nt = max(250, ano)
    dc = c.tail(nt)
    wc = w.tail(260)
    ch = {"d": [round(x, nd) for x in dc], "m50": [_n(x, nd) for x in s50.tail(nt)], "m200": [_n(x, nd) for x in s200.tail(nt)],
          "dd": [int(t.timestamp() // 86400) for t in dc.index],
          "w": [round(x, nd) for x in wc], "w200": [_n(x, nd) for x in w200.tail(260)], "wd": [int(t.timestamp() // 86400) for t in wc.index],
          "rwd": [_n(x, 1) for x in rd.tail(nt)], "rww": [_n(x, 1) for x in rw.reindex(dc.index, method="ffill")]}
    return {"lb": rotulo, "cu": moeda, "p": _n(p, nd), "sc": _n(sc), "rg": rg, "rd": _n(rd.iloc[-1], 0), "rw": _n(rw.iloc[-1], 0),
            "d2": _n(d2), "w2": _n(w2), "h52": _n(h52), "h5": _n(h5), "l52": _n(l52), "r1": _n(ret(ano // 12)), "r3": _n(ret(ano // 4)), "r6": _n(ret(ano // 2)),
            "r12": _n(ret(ano)), "rs": _n(rs), "ix": idx_nome, "ch": ch}


def _banda(x, cortes, notas):
    """nota por faixa: cortes crescentes, len(notas) = len(cortes)+1"""
    for c, n in zip(cortes, notas):
        if x < c: return n
    return notas[-1]


def _fin(info, setor):
    s = (info.get("sector") or "") + " " + (setor or "")
    return any(k in s for k in ("Financial", "Banco", "Seguro", "financeir"))


def _yoy(serie, k=4):
    if not serie or len(serie) <= k: return None
    a, b = serie[-1][1], serie[-1 - k][1]
    return (a / abs(b) - 1) * 100 if b else None


def fundamental(f, setor, preco):
    """nota 0-10 (10 = fundamentos atraentes) e dados para o detalhe"""
    if not f or f.get("vazio"): return None
    i = f["info"]
    fin = _fin(i, setor)
    sub = {}
    # valuation
    v = []
    pl = i.get("trailingPE") if (i.get("trailingPE") or 0) > 0 else i.get("forwardPE")
    if pl and pl > 0: v.append(_banda(pl, (8, 12, 18, 25, 40), (9, 7.5, 6, 4.5, 3, 1.5)))
    elif i.get("trailingPE") is not None or i.get("forwardPE") is not None: v.append(2)
    if i.get("priceToBook"): v.append(_banda(i["priceToBook"], (1, 2, 4), (8, 6, 4, 2)))
    if i.get("enterpriseToEbitda") and not fin and i["enterpriseToEbitda"] > 0: v.append(_banda(i["enterpriseToEbitda"], (5, 8, 12, 20), (9, 7, 5.5, 4, 2)))
    if v: sub["val"] = sum(v) / len(v)
    # crescimento
    g = []
    for k in ("revenueGrowth", "earningsGrowth"):
        if i.get(k) is not None: g.append(_banda(i[k] * 100, (-10, 0, 5, 15, 30), (1.5, 3.5, 5, 7, 8.5, 9.5)))
    if g: sub["cres"] = sum(g) / len(g)
    # rentabilidade
    r = []
    if i.get("returnOnEquity") is not None: r.append(_banda(i["returnOnEquity"] * 100, (5, 10, 15, 25), (2, 4, 6, 8, 9)))
    if i.get("profitMargins") is not None: r.append(_banda(i["profitMargins"] * 100, (0, 5, 10, 20), (1, 3.5, 5.5, 7.5, 9)))
    if r: sub["rent"] = sum(r) / len(r)
    # saúde financeira
    h = []
    if not fin:
        if i.get("totalDebt") is not None and i.get("totalCash") is not None and (i.get("ebitda") or 0) > 0:
            h.append(_banda((i["totalDebt"] - i["totalCash"]) / i["ebitda"], (0, 1, 2, 3, 4), (10, 8.5, 7, 5, 3, 1.5)))
        elif i.get("totalDebt") is not None and i.get("totalCash") is not None and i["totalCash"] >= i["totalDebt"]: h.append(9)
        if i.get("currentRatio"): h.append(_banda(i["currentRatio"], (1, 1.5), (3, 6, 8)))
        if i.get("freeCashflow") is not None: h.append(7.5 if i["freeCashflow"] > 0 else 3)
    else:
        if i.get("returnOnAssets") is not None: h.append(_banda(i["returnOnAssets"] * 100, (0.5, 1, 1.5), (3, 5, 7, 8.5)))
    if h: sub["saude"] = sum(h) / len(h)
    # dividendos
    if i.get("dividendYield") is not None:
        dy = i["dividendYield"] if i["dividendYield"] > 0.5 else i["dividendYield"] * 100     # o Yahoo varia entre fração e %
        d = _banda(dy, (0.5, 2, 4, 6), (4, 5, 6, 7.5, 9))
        if (i.get("payoutRatio") or 0) > 1: d -= 2
        sub["div"] = max(0, d)
    peso = {"val": 2, "cres": 2, "rent": 2, "saude": 2, "div": 1}
    tot = sum(peso[k] for k in sub)
    sc = sum(sub[k] * peso[k] for k in sub) / tot if tot else None
    q = f.get("q") or {}
    ref = (f.get("res") or [])
    hoje = pd.Timestamp.now().strftime("%Y-%m-%d")
    ult = next((e for e in reversed(ref) if e["d"] <= hoje and (e.get("rep") is not None or e.get("sur") is not None)), None)
    prox = next((e for e in ref if e["d"] > hoje), None)
    liq, rev = q.get("liq"), q.get("rev")
    mg = (liq[-1][1] / rev[-1][1] * 100) if liq and rev and rev[-1][1] else None
    mg0 = (liq[-5][1] / rev[-5][1] * 100) if liq and rev and len(liq) >= 5 and len(rev) >= 5 and rev[-5][1] else None
    ndebt = None
    if i.get("totalDebt") is not None and i.get("totalCash") is not None and (i.get("ebitda") or 0) > 0: ndebt = (i["totalDebt"] - i["totalCash"]) / i["ebitda"]
    k = {"pl": i.get("trailingPE"), "plf": i.get("forwardPE"), "pvp": i.get("priceToBook"), "eve": i.get("enterpriseToEbitda"),
         "dy": (None if i.get("dividendYield") is None else (i["dividendYield"] if i["dividendYield"] > 0.5 else i["dividendYield"] * 100)),
         "po": None if i.get("payoutRatio") is None else i["payoutRatio"] * 100, "roe": None if i.get("returnOnEquity") is None else i["returnOnEquity"] * 100,
         "ml": None if i.get("profitMargins") is None else i["profitMargins"] * 100, "mo": None if i.get("operatingMargins") is None else i["operatingMargins"] * 100,
         "cr": None if i.get("revenueGrowth") is None else i["revenueGrowth"] * 100, "cl": None if i.get("earningsGrowth") is None else i["earningsGrowth"] * 100,
         "nd": ndebt, "lc": i.get("currentRatio"), "fcl": i.get("freeCashflow"), "mc": i.get("marketCap")}
    k = {a: (None if b is None else round(float(b), 2)) for a, b in k.items()}
    sub = {a: _n(b) for a, b in sub.items()}
    return {"sc": _n(sc), "sub": sub, "k": k, "q": q, "a": f.get("a"), "qb": f.get("qb"), "af": f.get("af"),
            "rs": {"ult": ult, "prox": prox, "rev": _n(_yoy(rev)), "liq": _n(_yoy(liq)), "mg": _n(mg), "mg0": _n(mg0), "per": rev[-1][0] if rev else None}}


def analistas(f, preco):
    if not f or f.get("vazio"): return None
    i = f["info"]
    rm, alvo, nn = i.get("recommendationMean"), i.get("targetMeanPrice"), i.get("numberOfAnalystOpinions") or 0
    if rm is None and alvo is None: return None
    xs = []
    if rm is not None: xs.append(_clip(10 - (rm - 1) * 2.5, 0, 10))
    up = (alvo / preco - 1) * 100 if alvo and preco else None
    if up is not None: xs.append(_clip(5 + up / 4, 0, 10))
    sc = sum(xs) / len(xs)
    if nn < 3: sc = 5 + (sc - 5) * 0.5          # poucos analistas: nota puxada para o neutro
    return {"sc": _n(sc), "rm": rm, "rk": i.get("recommendationKey"), "n": nn, "alvo": _n(alvo, 2), "max": _n(i.get("targetHighPrice"), 2),
            "min": _n(i.get("targetLowPrice"), 2), "up": _n(up), "p": _n(preco, 2)}


def dados(raiz):
    cats = os.path.join(raiz, "categorias")
    cfg = {c: json.load(open(os.path.join(cats, c, "config.json"), encoding="utf-8")) for c in ("brasil", "eua", "pares")}
    IX = {"BOVA11": _ler(raiz, "brasil", "BENCH_BOVA11"), "Nasdaq": _ler(raiz, "eua", "BENCH_NASDAQ"), "S&P 500": _ler(raiz, "eua", "BENCH_SP500")}
    FU = {}
    for cat in ("brasil", "eua"):
        f = os.path.join(cats, cat, "fundamentos.json")
        FU[cat] = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    rows = []
    for n, v in cfg["brasil"]["ativos"].items():
        c = _ler(raiz, "brasil", n)
        if c is None: continue
        r = {"i": len(rows), "n": n, "g": "B3", "s": (v or {}).get("setor", ""), "t1": tecnica(c, IX["BOVA11"], "B3", "R$", "BOVA11")}
        fu = fundamental(FU["brasil"].get(n), r["s"], r["t1"]["p"])
        if fu: r["fu"] = fu
        an = analistas(FU["brasil"].get(n), r["t1"]["p"])
        if an: r["an"] = an
        rows.append(r)
    for n, v in cfg["eua"]["ativos"].items():
        c = _ler(raiz, "eua", n)
        if c is None: continue
        ixn = "Nasdaq" if v.get("grupo") == "nasdaq" else "S&P 500"
        r = {"i": len(rows), "n": n, "g": "EUA", "s": v.get("setor", ""), "t1": tecnica(c, IX[ixn], "EUA", "US$", ixn)}
        fu = fundamental(FU["eua"].get(n), r["s"], r["t1"]["p"])
        if fu: r["fu"] = fu
        an = analistas(FU["eua"].get(n), r["t1"]["p"])
        if an: r["an"] = an
        b = v.get("bdr")
        if b:
            cb = _ler(raiz, "pares", b)
            if cb is not None:
                r["b"] = b
                r["t2"] = tecnica(cb, IX[ixn], "BDR", "R$", ixn)
        rows.append(r)
    return {"rows": rows}


def pagina(arq, titulo, paginas, D):
    h = [ui.cabeca(titulo, paginas, arq), f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>",
         "<p class=sub>Tendência por empresa pela MM200: verde = acima das MM200 diária e semanal, amarelo = entre elas, vermelho = abaixo das duas. O selo de RSI aparece quando o RSI semanal está acima de 70 ou abaixo de 30 (costuma ser lido como sobrecompra e sobrevenda; o indicador não prevê preço). As notas de 0 a 10 resumem os dados e não são recomendação de compra ou venda. Clique em uma linha para ver os detalhes e gráficos.</p>",
         "<div id=mo></div><div class=mo-o id=mo-o><div class=mo-p id=mo-p></div></div>",
         "</main><script>var D=" + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";" + JS + "</script></body></html>"]
    return "".join(h)
