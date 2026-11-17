"""Aba Spread: relação entre ativos, para permutar do esticado para o descontado.
Todos os cálculos rodam no navegador a partir dos fechamentos embutidos na página."""
import json
import html as H
import datetime as dt
import os
import pandas as pd
import ui

CSS = """
.sp-base{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px}.sp-base button{padding:7px 12px!important;font-size:13px!important}
.sp-base button{border:1px solid var(--line);background:var(--card);color:var(--tx);border-radius:12px;padding:9px 16px;font-weight:800;font-size:14px;cursor:pointer;letter-spacing:-.01em}
.sp-base button small{display:block;color:var(--mu);font-weight:500;font-size:11px}
.sp-base button.on{background:var(--tx);color:var(--bg);border-color:var(--tx)}.sp-base button.on small{color:var(--bg);opacity:.7}
.sp-card{background:var(--card);border:1px solid var(--line);border-radius:18px;margin:0 0 18px;box-shadow:var(--shadow);overflow:hidden}
.sp-card h2{margin:0;padding:14px 18px 4px;font-size:17px;letter-spacing:-.02em}.sp-card .m{padding:0 18px 10px;color:var(--mu);font-size:12.5px}
.sp-t tr.sel td,.sp-t tr.sel td:first-child{background:color-mix(in srgb,var(--ac) 16%,var(--card))}
.sp-t tbody tr{cursor:pointer}
.sp-z{display:inline-block;min-width:50px;text-align:center;border-radius:8px;padding:2px 7px;font-weight:700}
.sp-sig{display:inline-block;border-radius:8px;padding:2px 9px;font-weight:700;font-size:12px}
.sp-sig.f{background:var(--os);color:#fff}.sp-sig.a{background:var(--grbg);color:var(--gr)}.sp-sig.n{background:var(--card2);color:var(--mu)}
.sp-sig.rd{background:var(--rdbg);color:var(--rd)}.sp-sig.rf{background:var(--ob);color:#fff}
.sp-sw{font-weight:700}.sp-sw small{color:var(--mu);font-weight:500;margin-left:4px}
.sp-det{padding:4px 18px 18px}
.sp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.sp-box{background:var(--card2);border-radius:14px;padding:12px 14px}.sp-box h3{margin:0 0 8px;font-size:13px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em}
.sp-in{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:4px 0 8px}
.sp-in input{width:92px;background:var(--card);border:1px solid var(--line);color:var(--tx);border-radius:10px;padding:7px 10px;font-size:14px;font-weight:700;outline:none}
.sp-in input:focus{border-color:var(--ac)}
.sp-line{display:flex;justify-content:space-between;padding:3px 0}.sp-line b{font-weight:700}
.sp-big{font-size:22px;font-weight:800;letter-spacing:-.02em;margin:2px 0 6px}
.sp-svg{display:block;max-width:100%;touch-action:pan-y}.sp-ch{position:relative}
.sp-tip{display:none;position:absolute;pointer-events:none;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:6px 9px;font-size:12px;line-height:1.35;box-shadow:0 4px 14px rgba(0,0,0,.18);z-index:5;white-space:nowrap}
.sp-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:6px;margin-top:8px}.sp-stats div{background:var(--card);border-radius:10px;padding:6px 9px}.sp-stats small{display:block;color:var(--mu);font-size:10.5px}.sp-stats b{font-size:13.5px}
.sp-wb{float:right;display:inline-flex;gap:4px}.sp-wb button{border:1px solid var(--line);background:var(--card);color:var(--tx);border-radius:999px;padding:1px 9px;font-size:11.5px;font-weight:600;cursor:pointer}.sp-wb button.on{background:var(--ac);color:#fff;border-color:var(--ac)}
.sp-hm td{text-align:center;padding:5px 3px;cursor:pointer;font-weight:700;font-size:10.5px}.sp-hm th{cursor:default;text-align:center;font-size:9.5px;padding:5px 2px;letter-spacing:0}.sp-hm td:first-child,.sp-hm th:first-child{padding-left:10px;font-size:11px}
.sp-grp{display:flex;flex-wrap:wrap;gap:6px;align-items:center;width:100%}.sp-grp>span{min-width:48px;font-size:12px;font-weight:700}
.sp-flt{display:flex;gap:6px;padding:0 18px 10px;flex-wrap:wrap}.sp-flt button{border:1px solid var(--line);background:var(--card);color:var(--tx);border-radius:999px;padding:4px 12px;font-weight:600;font-size:12px;cursor:pointer}.sp-flt button.on{background:var(--tx);color:var(--bg)}
.sp-hm td:first-child{text-align:left;font-weight:800}
.sp-al{display:inline-block;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:3px 9px;margin:4px 4px 0 0;font-size:12.5px;cursor:pointer;font-weight:600}
"""

JS = r"""
(function(){
var A=SPDATA.a,BY={};A.forEach(function(x){BY[x.n]=x});
var LOTS=[1,2,3,4,5,6,8,10,12,15,20,25,30,40,50,100];
function st(k,v){try{if(v===undefined)return localStorage.getItem(k);localStorage.setItem(k,v)}catch(e){return null}}
function mean(a){var s=0;for(var i=0;i<a.length;i++)s+=a[i];return s/a.length}
function sd(a){var m=mean(a),s=0;for(var i=0;i<a.length;i++)s+=(a[i]-m)*(a[i]-m);return Math.sqrt(s/(a.length-1))}
function rsi(c,p){if(c.length<p+2)return null;var g=0,l=0,i,d;for(i=1;i<=p;i++){d=c[i]-c[i-1];g+=Math.max(d,0);l+=Math.max(-d,0)}g/=p;l/=p;
 for(i=p+1;i<c.length;i++){d=c[i]-c[i-1];g=(g*(p-1)+Math.max(d,0))/p;l=(l*(p-1)+Math.max(-d,0))/p}return l==0?100:100-100/(1+g/l)}
function align(xt,xc,yt,yc){if(!xt||!yt)return{t:[],x:[],y:[]};var m={},i;for(i=0;i<yt.length;i++)m[yt[i]]=yc[i];var t=[],x=[],y=[];
 for(i=0;i<xt.length;i++){var v=m[xt[i]];if(v!==undefined){t.push(xt[i]);x.push(xc[i]);y.push(v)}}return{t:t,x:x,y:y}}
function zs(r,w,i){var s=r.slice(i-w+1,i+1);var sdv=sd(s);return sdv>0?(r[i]-mean(s))/sdv:0}
function corr(a,b){var n=Math.min(a.length,b.length);a=a.slice(-n);b=b.slice(-n);var ma=mean(a),mb=mean(b),s=0,sa=0,sb=0;for(var i=0;i<n;i++){s+=(a[i]-ma)*(b[i]-mb);sa+=(a[i]-ma)*(a[i]-ma);sb+=(b[i]-mb)*(b[i]-mb)}return s/Math.sqrt(sa*sb)}
function rets(c){var o=[];for(var i=1;i<c.length;i++)o.push(c[i]/c[i-1]-1);return o}
function swap(pS,pB){var best=null;for(var i=0;i<LOTS.length;i++){var a=LOTS[i],b=Math.floor(a*pS/pB);if(b<1)continue;var cash=a*pS-b*pB,pct=cash/(a*pS),c={a:a,b:b,cash:cash,pct:pct};if(pct<=0.01)return c;if(!best||pct<best.pct)best=c}return best}
var CACHE={};
function pair(xn,yn,full){var k=xn+'|'+yn;if(CACHE[k]){var c0=CACHE[k];if(full&&!c0.full){var am0=align(BY[xn].mt,BY[xn].mc,BY[yn].mt,BY[yn].mc);c0.rsiM=am0.x.length>20?rsi(am0.x.map(function(v,i){return v/am0.y[i]}),14):null;c0.full=1}return c0}var X=BY[xn],Y=BY[yn];var al=align(X.dt,X.dc,Y.dt,Y.dc);var n=al.t.length;if(n<30)return null;
 var r=al.x.map(function(v,i){return v/al.y[i]});var win=r.slice(-250),cur=r[n-1],c=0;win.forEach(function(v){if(v<=cur)c++});
 var o={x:xn,y:yn,al:al,r:r,n:n,ratio:cur,z20:zs(r,20,n-1),z60:n>=60?zs(r,60,n-1):null,perc:c/win.length*100,v1:cur/r[n-2]-1,v5:n>6?cur/r[n-6]-1:null,
  rsiR:rsi(r,14),rsiM:null,rsiX:rsi(al.x,14),rsiY:rsi(al.y,14),cor:corr(rets(al.x.slice(-61)),rets(al.y.slice(-61))),px:al.x[n-1],py:al.y[n-1]};
 CACHE[k]=o;if(full)return pair(xn,yn,true);return o}
function f2(v,n){return v===null||v===undefined||isNaN(v)?'–':v.toLocaleString('pt-BR',{minimumFractionDigits:n===undefined?2:n,maximumFractionDigits:n===undefined?2:n})}
function pc(v){return v===null||isNaN(v)?'–':'<span class="var '+(v>=0?'up':'dn')+'">'+f2(Math.abs(v*100))+'%</span>'}
function zc(z){if(z===null)return'–';var a=Math.abs(z),pos=z>0,bg=a>=2?(pos?'var(--os)':'var(--ob)'):a>=1?(pos?'var(--grbg)':'var(--rdbg)'):'var(--card2)';var fg=a>=2?'#fff':a>=1?(pos?'var(--gr)':'var(--rd)'):'var(--mu)';return'<span class="sp-z" style="background:'+bg+';color:'+fg+'">'+(z>0?'+':'')+f2(z)+'</span>'}
function rc(v){if(v===null)return'–';var c=v<=30?'os':v<40?'lo':v>=70?'ob':v>60?'hi':'';return'<span class="r '+c+'" style="'+(c?'':'background:var(--card2)')+'">'+f2(v,0)+'</span>'}
function sig(z20,z60){var z=Math.abs(z20),same=z60===null||Math.sign(z60)==Math.sign(z20);if(z20>=2&&same)return['f','Bom para sair'];if(z20>=1)return['a','Esticado: considerar sair'];if(z20<=-2&&same)return['rf','Evite: está barato'];if(z20<=-1)return['rd','Barato: melhor esperar'];return['n','Neutro']}
function swtxt(p){var w=swap(p.px,p.py);if(!w)return'–';return'<span class="sp-sw">'+w.a+' '+p.x+' → '+w.b+' '+p.y+'<small>sobra R$ '+f2(w.cash)+'</small></span>'}
var base=st('spbase');if(!BY[base])base=A[0].n;var sel=st('sppar');
var flt=st('spflt')||'Todos';function others(){return A.filter(function(x){return x.n!==base&&(flt=='Todos'||x.g==flt)}).map(function(x){return pair(base,x.n,true)}).filter(Boolean)}
function renderBase(){var gs=[];A.forEach(function(x){if(gs.indexOf(x.g)<0)gs.push(x.g)});
 document.getElementById('spb').innerHTML=gs.map(function(g){return'<div class=sp-grp><span class=mu>'+g+'</span>'+A.filter(function(x){return x.g==g}).map(function(x){return'<button data-n="'+x.n+'" class="'+(x.n==base?'on':'')+'">'+x.n+'<small>R$ '+f2(x.dc[x.dc.length-1])+'</small></button>'}).join('')+'</div>'}).join('');
 document.querySelectorAll('#spb button').forEach(function(b){b.onclick=function(){base=b.dataset.n;st('spbase',base);sel=null;render()}});
 document.getElementById('spf').innerHTML=['Todos'].concat(gs).map(function(g){return'<button data-g="'+g+'" class="'+(g==flt?'on':'')+'">'+g+'</button>'}).join('');
 document.querySelectorAll('#spf button').forEach(function(b){b.onclick=function(){flt=b.dataset.g;st('spflt',flt);sel=null;render()}})}
var sortK='z20',sortD=-1;
function renderTable(){var L=others();var key={abs:function(p){return Math.abs(p.z20)},z20:function(p){return p.z20},z60:function(p){return p.z60===null?-99:p.z60},perc:function(p){return p.perc},v5:function(p){return p.v5===null?-99:p.v5},rsiR:function(p){return p.rsiR===null?-1:p.rsiR},rsiM:function(p){return p.rsiM===null?-1:p.rsiM},cor:function(p){return p.cor}}[sortK];
 L.sort(function(a,b){return(key(a)-key(b))*sortD});
 if(!sel||!BY[sel]||sel==base)sel=L.length?L[0].y:null;
 var h='<div class=sc><table class=sp-t><thead><tr><th data-k=abs>Sair de '+base+' para</th><th>Situação</th><th>Troca sugerida</th><th data-k=ratio>Relação</th><th data-k=z20>z 20d</th><th data-k=z60>z 60d</th><th data-k=perc>Percentil</th><th>1d</th><th data-k=v5>5d</th><th data-k=rsiR>RSI relação D</th><th data-k=rsiM>RSI relação 30m</th><th>RSI '+base+'</th><th>RSI outro</th><th data-k=cor>Corr 60d</th></tr></thead><tbody>';
 L.forEach(function(p){var s=sig(p.z20,p.z60);h+='<tr data-y="'+p.y+'" class="'+(p.y==sel?'sel':'')+'"><td class=tk>'+p.y+'</td><td><span class="sp-sig '+s[0]+'">'+s[1]+'</span></td><td>'+swtxt(p)+'</td><td>'+f2(p.ratio,4)+'</td><td>'+zc(p.z20)+'</td><td>'+zc(p.z60)+'</td><td>'+f2(p.perc,0)+'%</td><td>'+pc(p.v1)+'</td><td>'+pc(p.v5)+'</td><td>'+rc(p.rsiR)+'</td><td>'+rc(p.rsiM)+'</td><td>'+rc(p.rsiX)+'</td><td>'+rc(p.rsiY)+'</td><td>'+f2(p.cor)+'</td></tr>'});
 h+='</tbody></table></div>';document.getElementById('spt').innerHTML=h;
 document.querySelectorAll('#spt th[data-k]').forEach(function(t){t.onclick=function(){var k=t.dataset.k;if(k=='ratio')return;if(sortK==k)sortD=-sortD;else{sortK=k;sortD=-1}renderTable();renderDetail()}});
 document.querySelectorAll('#spt tbody tr').forEach(function(t){t.onclick=function(){sel=t.dataset.y;st('sppar',sel);renderTable();renderDetail()}})}
var WIN=+(st('spwin')||120),CTX=null;
function dstr(d){var t=new Date(d*86400000);return('0'+t.getUTCDate()).slice(-2)+'/'+('0'+(t.getUTCMonth()+1)).slice(-2)+'/'+String(t.getUTCFullYear()).slice(-2)}
function winBar(n){var o=[120,180,250,500,0].filter(function(w){return w==0||w<n});return'<span class=sp-wb>'+o.map(function(w){return'<button data-w='+w+' class="'+((WIN==w||(WIN>=n&&w==0))?'on':'')+'">'+(w==250?'1 ano':w==500?'2 anos':w?w+'d':'Tudo')+'</button>'}).join('')+'</span>'}
function chart(id,vals,dts,fmt,color,sig,rel){var el=document.getElementById(id);if(!el||!vals.length)return;
 var N=vals.length,W=Math.max(el.clientWidth,280),Hh=240,pl=8,pr=88,pt=14,pb=22,col=color||'var(--ac)';
 var m=mean(vals),sg=sd(vals),mn=Infinity,mx=-Infinity,imn=0,imx=0,cur=vals[N-1],i;
 for(i=0;i<N;i++){if(vals[i]<mn){mn=vals[i];imn=i}if(vals[i]>mx){mx=vals[i];imx=i}}
 var pad=(mx-mn)*.12||1,lo=mn-pad,hi=mx+pad;
 function X(i){return pl+(W-pl-pr)*i/Math.max(N-1,1)}function Y(v){return pt+(Hh-pt-pb)*(1-(v-lo)/(hi-lo))}
 var lines=[{v:m,c:'#64748b',t:'méd',d:'',w:1.4}];
 if(sig){[[1,'#f59e0b'],[-1,'#f59e0b'],[2,'#ef4444'],[-2,'#22c55e']].forEach(function(q){var v=m+q[0]*sg;if(v>lo&&v<hi)lines.push({v:v,c:q[1],t:(q[0]>0?'+':'−')+Math.abs(q[0])+'σ',d:'4 3',w:1})})}
 var o='<svg class=sp-svg width='+W+' height='+Hh+' viewBox="0 0 '+W+' '+Hh+'">';
 for(i=0;i<=3;i++){var gv=lo+(hi-lo)*i/3;if(Math.abs(Y(gv)-Y(m))<13||Math.abs(Y(gv)-Y(cur))<13)continue;o+='<line x1='+pl+' x2='+(W-pr)+' y1='+Y(gv)+' y2='+Y(gv)+' stroke="var(--line)" stroke-width=1 opacity=.5 /><text x='+(W-pr+5)+' y='+(Y(gv)+3)+' font-size=9.5 fill="var(--mu)">'+fmt(gv)+'</text>'}
 var tk=[0,Math.floor((N-1)/2),N-1];tk.forEach(function(j,k){o+='<text x='+X(j)+' y='+(Hh-6)+' font-size=9.5 fill="var(--mu)" text-anchor="'+(k==0?'start':k==2?'end':'middle')+'">'+dstr(dts[j])+'</text>'});
 lines.forEach(function(l){o+='<line x1='+pl+' x2='+(W-pr)+' y1='+Y(l.v)+' y2='+Y(l.v)+' stroke="'+l.c+'" stroke-width='+l.w+' stroke-dasharray="'+l.d+'"/>'+(l.t=='méd'?'<text x='+(W-pr+5)+' y='+(Y(l.v)+3)+' font-size=10 font-weight=700 fill="'+l.c+'" paint-order=stroke stroke="var(--card2)" stroke-width=3>méd '+fmt(l.v)+'</text>':'<text x='+(W-pr-3)+' y='+(Y(l.v)-3)+' font-size=9 text-anchor="end" fill="'+l.c+'">'+l.t+'</text>')});
 var d='';vals.forEach(function(v,i){d+=(i?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)});
 o+='<path d="'+d+'L'+X(N-1)+' '+Y(lo)+'L'+X(0)+' '+Y(lo)+'Z" fill="'+col+'" opacity=.07 /><path d="'+d+'" fill=none stroke="'+col+'" stroke-width=2 stroke-linejoin=round />';
 function mk(j,v,up,c){var tx=X(j),an=tx>W-pr-70?'end':tx<pl+70?'start':'middle';return'<circle cx='+tx+' cy='+Y(v)+' r=3.2 fill="'+c+'"/><text x='+tx+' y='+(Y(v)+(up?-8:15))+' font-size=10 font-weight=700 text-anchor="'+an+'" fill="'+c+'" paint-order=stroke stroke="var(--card2)" stroke-width=3>'+fmt(v)+' · '+dstr(dts[j])+'</text>'}
 if(imx!=N-1)o+=mk(imx,mx,true,'#ef4444');if(imn!=N-1)o+=mk(imn,mn,false,'#22c55e');
 o+='<circle cx='+X(N-1)+' cy='+Y(cur)+' r=4.5 fill="'+col+'" stroke="var(--card2)" stroke-width=2 /><text x='+(W-pr+5)+' y='+(Y(cur)+(Math.abs(Y(cur)-Y(m))<14?(cur>=m?-8:16):4))+' font-size=11.5 font-weight=800 fill="var(--tx)">'+fmt(cur)+'</text>';
 o+='<line id='+id+'vl x1=0 x2=0 y1='+pt+' y2='+(Hh-pb)+' stroke="var(--mu)" stroke-width=1 stroke-dasharray="3 3" style="display:none" /><circle id='+id+'dot r=4.5 fill="'+col+'" stroke="var(--tx)" stroke-width=1.5 style="display:none" /><rect id='+id+'hit x='+pl+' y=0 width='+(W-pl-pr)+' height='+Hh+' fill=transparent style="cursor:crosshair" /></svg><div class=sp-tip id='+id+'tip></div>';
 var cnt=0;vals.forEach(function(v){if(v<=cur)cnt++});var pc2=cnt/N*100;
 function dv(v){return rel?(v/m-1)*100:v-m}function dtx(v){var x=dv(v);return(x>=0?'+':'−')+(rel?f2(Math.abs(x),1)+'%':'R$ '+f2(Math.abs(x)))}
 o+='<div class=sp-stats><div><small>Hoje</small><b>'+fmt(cur)+'</b></div><div><small>Média</small><b>'+fmt(m)+'</b></div><div><small>Máx · '+dstr(dts[imx])+'</small><b>'+fmt(mx)+'</b></div><div><small>Mín · '+dstr(dts[imn])+'</small><b>'+fmt(mn)+'</b></div><div><small>Hoje vs média</small><b>'+dtx(cur)+(sg>0?' · z '+f2((cur-m)/sg,1):'')+'</b></div><div><small>Percentil no período</small><b>'+f2(pc2,0)+'%</b></div></div>';
 el.innerHTML=o;
 var hit=document.getElementById(id+'hit'),vl=document.getElementById(id+'vl'),dot=document.getElementById(id+'dot'),tip=document.getElementById(id+'tip');
 function mv(ev){var r=hit.getBoundingClientRect(),cx=(ev.touches?ev.touches[0].clientX:ev.clientX)-r.left,j=Math.round(cx/r.width*(N-1));j=Math.max(0,Math.min(N-1,j));var v=vals[j],px=X(j);
  vl.setAttribute('x1',px);vl.setAttribute('x2',px);vl.style.display='';dot.setAttribute('cx',px);dot.setAttribute('cy',Y(v));dot.style.display='';
  var z=sg>0?(v-m)/sg:0;tip.innerHTML='<b>'+dstr(dts[j])+'</b><br>'+fmt(v)+'<br><span style="color:'+(v>=m?'var(--gr)':'var(--rd)')+'">'+dtx(v)+' vs média</span>'+(sg>0?'<br>z '+f2(z,1):'');
  tip.style.display='block';var tw=tip.offsetWidth,left=px+12;if(left+tw>W-4)left=px-tw-12;tip.style.left=left+'px';tip.style.top=Math.max(2,Math.min(Y(v)-30,Hh-70))+'px';if(ev.cancelable&&ev.touches)ev.preventDefault()}
 function lv(){vl.style.display='none';dot.style.display='none';tip.style.display='none'}
 hit.addEventListener('mousemove',mv);hit.addEventListener('mouseleave',lv);hit.addEventListener('touchstart',mv,{passive:false});hit.addEventListener('touchmove',mv,{passive:false});hit.addEventListener('touchend',lv)}
function drawCharts(){if(!CTX)return;var p=CTX.p,n=p.n,w=(!WIN||WIN>=n)?n:WIN,i0=n-w,dts=p.al.t.slice(i0);
 chart('spch1',p.r.slice(i0),dts,function(v){return f2(v,3)},null,true,true);
 if(CTX.na){var dif=[];for(var i=i0;i<n;i++)dif.push(CTX.na*p.al.x[i]-CTX.nb*p.al.y[i]);chart('spch2',dif,dts,function(v){return'R$ '+f2(v)},'#0891b2',false,false)}
 document.querySelectorAll('.sp-wb').forEach(function(b){b.innerHTML=winBar(n).replace(/^<span class=sp-wb>|<\/span>$/g,'')});
 document.querySelectorAll('.sp-wb button').forEach(function(b){b.onclick=function(){WIN=+b.dataset.w;st('spwin',String(WIN));drawCharts()}})}
window.addEventListener('resize',function(){drawCharts()});
function hist(p,th){var r=p.r,n=p.n,ev=[],last=-9,i;for(i=20;i<n-5;i++){var z=zs(r,20,i);if(z>=th&&i-last>=5){last=i;ev.push(-(r[i+5]/r[i]-1))}}
 if(!ev.length)return null;var w=ev.filter(function(v){return v>0}).length,s=ev.slice().sort(function(a,b){return a-b});return{n:ev.length,win:w/ev.length,med:s[Math.floor(s.length/2)],worst:s[0],best:s[s.length-1]}}
function renderDetail(){var el=document.getElementById('spd');if(!sel||!BY[sel]){el.innerHTML='';return}var p=pair(base,sel,true);if(!p){el.innerHTML='';return}
 var up=true,S=p.x,B=p.y,pS=p.px,pB=p.py,w=swap(pS,pB)||{a:1,b:1};
 var key='sp_'+S+'_'+B,saved=st(key),a=w.a,b=w.b;if(saved){var q=saved.split(',');a=+q[0]||a;b=+q[1]||b}
 var qty=+(st('spq_'+S)||10000);
 var s=sig(p.z20,p.z60),n=p.n;
 CTX={p:p,na:0,nb:0};
 var h1=hist(p,1),h2=hist(p,2);
 function ht(h,t){return h?'<div class=sp-line><span>'+t+'</span><b>'+h.n+' casos · compensou em '+f2(h.win*100,0)+'% · mediana '+f2(h.med*100)+'% · pior '+f2(h.worst*100)+'%</b></div>':'<div class=sp-line><span>'+t+'</span><b>sem casos</b></div>'}
 var o='<div class=sp-card><h2>'+p.x+' ÷ '+p.y+' <span class="sp-sig '+s[0]+'" style="margin-left:8px">'+s[1]+'</span></h2><div class=m>Relação hoje '+f2(p.ratio,4)+' ('+p.x+' vale '+f2(p.ratio,2)+' × '+p.y+') · z 20d '+f2(p.z20)+' · percentil '+f2(p.perc,0)+'% dos últimos '+Math.min(250,n)+' dias</div><div class=sp-det><div class=sp-grid>'
 +'<div class=sp-box><h3>Troca: sair de '+S+' para '+B+'</h3><div class=sp-in>Vender <input id=sa type=number min=1 value='+a+'> '+S+' por <input id=sb type=number min=1 value='+b+'> '+B+'</div>'
 +'<div id=spc></div><div class=sp-in>Tenho <input id=sq type=number min=0 value='+qty+' style="width:110px"> '+S+'</div><div id=spc2></div></div>'
 +'<div class=sp-box style="grid-column:1/-1"><h3>Relação '+p.x+' ÷ '+p.y+' <span class=sp-wb></span></h3><div id=spch1 class=sp-ch></div></div>'
 +'<div class=sp-box style="grid-column:1/-1"><h3><span id=spdt></span> <span class=sp-wb></span></h3><div id=spch2 class=sp-ch></div></div>'
 +'<div class=sp-box><h3>No histórico deste par</h3><div class=mu style="font-size:12.5px;margin-bottom:6px">Quando '+S+' ficou esticado contra '+B+' (z 20d), em quantos casos a relação caiu nos 5 pregões seguintes, ou seja, sair compensou</div>'+ht(h1,'|z| ≥ 1')+ht(h2,'|z| ≥ 2')+'<div class=sp-line><span>RSI da relação D / 30m</span><b>'+f2(p.rsiR,0)+' / '+f2(p.rsiM,0)+'</b></div><div class=sp-line><span>Correlação 60d</span><b>'+f2(p.cor)+'</b></div></div>'
 +'</div></div></div>';el.innerHTML=o;
 function calc(){var na=+document.getElementById('sa').value,nb=+document.getElementById('sb').value,nq=+document.getElementById('sq').value;if(!(na>0&&nb>0))return;st(key,na+','+nb);st('spq_'+S,String(nq));
  var cash=na*pS-nb*pB,lotes=Math.floor(nq/na),tcash=lotes*cash,custo=lotes*(na*pS+nb*pB)*0.0003,pos=cash>=0;
  document.getElementById('spc').innerHTML='<div class=sp-line><span>Vende '+S+' (valor)</span><b>R$ '+f2(na*pS)+'</b></div><div class=sp-line><span>Recebe de '+B+' (valor)</span><b>R$ '+f2(nb*pB)+'</b></div>'
   +'<div class="sp-big '+(pos?'up':'dn')+'">'+(pos?'sobra':'falta')+' R$ '+f2(Math.abs(cash))+' por lote</div><div class=sp-line><span>Relação exata</span><b>1 '+S+' = '+f2(pS/pB,4)+' '+B+'</b></div>';
  document.getElementById('spc2').innerHTML='<div class=sp-line><span>Lotes completos</span><b>'+f2(lotes,0)+'</b></div><div class=sp-line><span>Compra '+B+'</span><b>'+f2(lotes*nb,0)+'</b></div><div class=sp-line><span>'+(pos?'Fica em caixa':'Precisa colocar')+'</span><b>R$ '+f2(Math.abs(tcash))+'</b></div><div class=sp-line><span>Custo B3 (0,03% × 2 pernas)</span><b>R$ '+f2(custo)+'</b></div>';
  CTX.na=na;CTX.nb=nb;document.getElementById('spdt').textContent='Sobra em R$ por lote ('+na+' '+S+' − '+nb+' '+B+')';drawCharts()}
 ['sa','sb','sq'].forEach(function(id){document.getElementById(id).oninput=calc});calc()}
function renderHeat(){var h='<div class=sc><table class=sp-hm><thead><tr><th></th>'+A.map(function(x){return'<th>'+x.n+'</th>'}).join('')+'</tr></thead><tbody>';
 A.forEach(function(r){h+='<tr><td>'+r.n+'</td>';A.forEach(function(c){if(r.n==c.n){h+='<td class=mu>–</td>';return}var p=pair(r.n,c.n);if(!p){h+='<td class=mu>–</td>';return}var z=p.z20,al=Math.min(Math.abs(z)/3,1);
  var bg=z>0?'rgba(22,163,74,'+(.1+.6*al)+')':'rgba(220,38,38,'+(.1+.6*al)+')';h+='<td data-x="'+r.n+'" data-y="'+c.n+'" style="background:'+bg+'">'+(z>0?'+':'')+f2(z,1)+'</td>'});h+='</tr>'});
 h+='</tbody></table></div>';document.getElementById('sph').innerHTML=h;
 document.querySelectorAll('#sph td[data-x]').forEach(function(t){t.onclick=function(){base=t.dataset.x;sel=t.dataset.y;st('spbase',base);st('sppar',sel);render();window.scrollTo(0,0)}})}
function render(){renderBase();renderTable();renderDetail()}
render();renderHeat();
if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js').catch(function(){})}
})();
"""


def dados(raiz):
    """Fechamentos diários e de 30 min: ações da B3 (categoria brasil) e BDRs/ETF (categoria pares)."""
    cats = os.path.join(raiz, "categorias")
    cfg = json.load(open(os.path.join(cats, "pares", "config.json"), encoding="utf-8"))
    lista = [(n, "Ações", "", "brasil") for n in cfg.get("spread_acoes", [])]
    lista += [(n, a.get("grupo", "BDR"), a.get("setor", ""), "pares") for n, a in cfg["ativos"].items()]
    lista += [(n, "ETF", "", "brasil") for n in cfg.get("spread_etfs", [])]
    out = []
    for n, g, setor, cat in lista:
        f1 = os.path.join(cats, cat, "dados", f"{n}_1D.csv")
        if not os.path.exists(f1): continue
        d = pd.read_csv(f1).dropna().tail(520)
        if len(d) < 30: continue
        item = {"n": n, "g": g, "s": setor, "dt": [int(t) // 86400 for t in d["time"]], "dc": [round(float(x), 4) for x in d["close"]]}
        f3 = os.path.join(cats, cat, "dados", f"{n}_30m.csv")
        if os.path.exists(f3):
            m = pd.read_csv(f3).dropna().tail(700)
            item["mt"] = [int(t) for t in m["time"]]; item["mc"] = [round(float(x), 3) for x in m["close"]]
        out.append(item)
    return out


def pagina(arq, titulo, paginas, ativos):
    agora = dt.datetime.now(ui.BRT)
    h = [ui.cabeca(titulo, paginas, arq), f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>",
         f"<p class=sub>Clique no ativo que você tem em carteira e veja, para cada outro ativo, se é um bom momento de sair dele: quanto a relação está esticada, o RSI da relação e quanto sobra em R$ na troca. Atualizado em {agora:%d/%m/%Y às %H:%M} (Brasília). B3 com ~15 min de atraso.</p>"]
    if len(ativos) < 2:
        h.append("<p class=mu>Preciso de pelo menos 2 ativos com histórico coletado.</p></main></body></html>")
        return "".join(h)
    h.append("<div class=sp-base id=spb></div><div class=sp-card><h2>Relação com os outros ativos</h2><div class=m>Clique numa linha para abrir os detalhes e a conta da troca. Clique no título de uma coluna para ordenar. Verde (z positivo) = o ativo que você tem está caro em relação ao outro, bom momento para sair dele. Vermelho = está barato, melhor esperar.</div><div class=sp-flt id=spf></div><div id=spt></div></div>")
    h.append("<div id=spd></div><div class=sp-card><h2>Mapa de todos contra todos (z 20d)</h2><div class=m>Linha = ativo que você tem; coluna = para onde iria. Verde: a linha está esticada contra a coluna (bom para sair). Vermelho: está barata. Clique numa célula para abrir.</div><div id=sph></div></div>")
    h.append("<details><summary>Como ler</summary><p><b>Relação</b> = preço do ativo da esquerda ÷ preço do outro. <b>z 20d / 60d</b> = quantos desvios-padrão a relação de hoje está acima (+, bom para sair do ativo da esquerda) ou abaixo (−) da média dos últimos 20 / 60 pregões; acima de +2 ou abaixo de −2 é raro. "
             "<b>Percentil</b> = em que posição a relação está nos últimos 250 pregões. <b>RSI da relação</b> = RSI de 14 períodos calculado sobre a própria relação (diário e 30 min). "
             "<b>Troca sugerida</b>: sai do ativo que você tem e vai para o outro; mostra a menor proporção em que a sobra em caixa é de até 1% do valor vendido (você pode editar as quantidades). "
             "Correlação baixa não impede a troca, mas quer dizer que a relação não tem âncora e pode se afastar mais antes de voltar. O histórico do par mostra como foi no passado, em amostra pequena.</p></details>")
    h.append("</main><script>var SPDATA=" + json.dumps({"a": ativos}, separators=(",", ":")) + ";" + JS + "</script></body></html>")
    return "".join(h)
