"""Aba Spread: relação entre ativos, para permutar do esticado para o descontado.
Todos os cálculos rodam no navegador a partir dos fechamentos embutidos na página."""
import json
import html as H
import datetime as dt
import os
import pandas as pd
import ui

CSS = """
.sp-base{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px}
.sp-base button{border:1px solid var(--line);background:var(--card);color:var(--tx);border-radius:12px;padding:9px 16px;font-weight:800;font-size:14px;cursor:pointer;letter-spacing:-.01em}
.sp-base button small{display:block;color:var(--mu);font-weight:500;font-size:11px}
.sp-base button.on{background:var(--tx);color:var(--bg);border-color:var(--tx)}.sp-base button.on small{color:var(--bg);opacity:.7}
.sp-card{background:var(--card);border:1px solid var(--line);border-radius:18px;margin:0 0 18px;box-shadow:var(--shadow);overflow:hidden}
.sp-card h2{margin:0;padding:14px 18px 4px;font-size:17px;letter-spacing:-.02em}.sp-card .m{padding:0 18px 10px;color:var(--mu);font-size:12.5px}
.sp-t tr.sel td,.sp-t tr.sel td:first-child{background:color-mix(in srgb,var(--ac) 16%,var(--card))}
.sp-t tbody tr{cursor:pointer}
.sp-z{display:inline-block;min-width:50px;text-align:center;border-radius:8px;padding:2px 7px;font-weight:700}
.sp-sig{display:inline-block;border-radius:8px;padding:2px 9px;font-weight:700;font-size:12px}
.sp-sig.f{background:var(--ob);color:#fff}.sp-sig.a{background:var(--rdbg);color:var(--rd)}.sp-sig.n{background:var(--card2);color:var(--mu)}
.sp-sig.fd{background:var(--os);color:#fff}.sp-sig.ad{background:var(--grbg);color:var(--gr)}
.sp-sw{font-weight:700}.sp-sw small{color:var(--mu);font-weight:500;margin-left:4px}
.sp-det{padding:4px 18px 18px}
.sp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.sp-box{background:var(--card2);border-radius:14px;padding:12px 14px}.sp-box h3{margin:0 0 8px;font-size:13px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em}
.sp-in{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:4px 0 8px}
.sp-in input{width:92px;background:var(--card);border:1px solid var(--line);color:var(--tx);border-radius:10px;padding:7px 10px;font-size:14px;font-weight:700;outline:none}
.sp-in input:focus{border-color:var(--ac)}
.sp-line{display:flex;justify-content:space-between;padding:3px 0}.sp-line b{font-weight:700}
.sp-big{font-size:22px;font-weight:800;letter-spacing:-.02em;margin:2px 0 6px}
.sp-svg{width:100%;height:auto;display:block}
.sp-hm td{text-align:center;padding:8px 6px;cursor:pointer;font-weight:700;font-size:12.5px}.sp-hm th{cursor:default;text-align:center}
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
function pair(xn,yn){var k=xn+'|'+yn;if(CACHE[k])return CACHE[k];var X=BY[xn],Y=BY[yn];var al=align(X.dt,X.dc,Y.dt,Y.dc);var n=al.t.length;if(n<30)return null;
 var r=al.x.map(function(v,i){return v/al.y[i]});var win=r.slice(-250),cur=r[n-1],c=0;win.forEach(function(v){if(v<=cur)c++});
 var am=align(X.mt,X.mc,Y.mt,Y.mc),rm=am.x.map(function(v,i){return v/am.y[i]});
 var o={x:xn,y:yn,al:al,r:r,n:n,ratio:cur,z20:zs(r,20,n-1),z60:n>=60?zs(r,60,n-1):null,perc:c/win.length*100,v1:cur/r[n-2]-1,v5:n>6?cur/r[n-6]-1:null,
  rsiR:rsi(r,14),rsiM:rm.length>20?rsi(rm,14):null,rsiX:rsi(al.x,14),rsiY:rsi(al.y,14),cor:corr(rets(al.x.slice(-61)),rets(al.y.slice(-61))),px:al.x[n-1],py:al.y[n-1]};
 CACHE[k]=o;return o}
function f2(v,n){return v===null||v===undefined||isNaN(v)?'–':v.toLocaleString('pt-BR',{minimumFractionDigits:n===undefined?2:n,maximumFractionDigits:n===undefined?2:n})}
function pc(v){return v===null||isNaN(v)?'–':'<span class="var '+(v>=0?'up':'dn')+'">'+f2(Math.abs(v*100))+'%</span>'}
function zc(z){if(z===null)return'–';var bg=Math.abs(z)>=2?(z>0?'var(--ob)':'var(--os)'):Math.abs(z)>=1?(z>0?'var(--rdbg)':'var(--grbg)'):'var(--card2)';var fg=Math.abs(z)>=2?'#fff':Math.abs(z)>=1?(z>0?'var(--rd)':'var(--gr)'):'var(--mu)';
 return'<span class="sp-z" style="background:'+bg+';color:'+fg+'">'+(z>0?'+':'')+f2(z)+'</span>'}
function rc(v){if(v===null)return'–';var c=v<=30?'os':v<40?'lo':v>=70?'ob':v>60?'hi':'';return'<span class="r '+c+'" style="'+(c?'':'background:var(--card2)')+'">'+f2(v,0)+'</span>'}
function sig(z20,z60){var z=Math.abs(z20),same=z60===null||Math.sign(z60)==Math.sign(z20);if(z>=2&&same)return z20>0?['f','Forte: sair do 1º']:['fd','Forte: sair do 2º'];
 if(z>=1)return z20>0?['a','Atenção: 1º esticado']:['ad','Atenção: 1º descontado'];return['n','Neutro']}
function swtxt(p){ // direção: z>0 vende X compra Y ; z<0 vende Y compra X
 var s,b,ps,pb;if(p.z20>=0){s=p.x;b=p.y;ps=p.px;pb=p.py}else{s=p.y;b=p.x;ps=p.py;pb=p.px}var w=swap(ps,pb);if(!w)return'–';
 return'<span class="sp-sw">'+w.a+' '+s+' → '+w.b+' '+b+'<small>sobra R$ '+f2(w.cash)+'</small></span>'}
var base=st('spbase');if(!BY[base])base=A[0].n;var sel=st('sppar');
function others(){return A.filter(function(x){return x.n!==base}).map(function(x){return pair(base,x.n)}).filter(Boolean)}
function renderBase(){document.getElementById('spb').innerHTML=A.map(function(x){return'<button data-n="'+x.n+'" class="'+(x.n==base?'on':'')+'">'+x.n+'<small>R$ '+f2(x.dc[x.dc.length-1])+'</small></button>'}).join('');
 document.querySelectorAll('#spb button').forEach(function(b){b.onclick=function(){base=b.dataset.n;st('spbase',base);sel=null;render()}})}
var sortK='abs',sortD=-1;
function renderTable(){var L=others();var key={abs:function(p){return Math.abs(p.z20)},z20:function(p){return p.z20},z60:function(p){return p.z60===null?-99:p.z60},perc:function(p){return p.perc},v5:function(p){return p.v5===null?-99:p.v5},rsiR:function(p){return p.rsiR===null?-1:p.rsiR},rsiM:function(p){return p.rsiM===null?-1:p.rsiM},cor:function(p){return p.cor}}[sortK];
 L.sort(function(a,b){return(key(a)-key(b))*sortD});
 if(!sel||!BY[sel]||sel==base)sel=L.length?L[0].y:null;
 var h='<div class=sc><table class=sp-t><thead><tr><th data-k=abs>'+base+' ÷ ativo</th><th>Situação</th><th>Troca sugerida</th><th data-k=ratio>Relação</th><th data-k=z20>z 20d</th><th data-k=z60>z 60d</th><th data-k=perc>Percentil</th><th>1d</th><th data-k=v5>5d</th><th data-k=rsiR>RSI relação D</th><th data-k=rsiM>RSI relação 30m</th><th>RSI '+base+'</th><th>RSI outro</th><th data-k=cor>Corr 60d</th></tr></thead><tbody>';
 L.forEach(function(p){var s=sig(p.z20,p.z60);h+='<tr data-y="'+p.y+'" class="'+(p.y==sel?'sel':'')+'"><td class=tk>'+p.x+' ÷ '+p.y+'</td><td><span class="sp-sig '+s[0]+'">'+s[1].replace('1º',p.x).replace('2º',p.y)+'</span></td><td>'+swtxt(p)+'</td><td>'+f2(p.ratio,4)+'</td><td>'+zc(p.z20)+'</td><td>'+zc(p.z60)+'</td><td>'+f2(p.perc,0)+'%</td><td>'+pc(p.v1)+'</td><td>'+pc(p.v5)+'</td><td>'+rc(p.rsiR)+'</td><td>'+rc(p.rsiM)+'</td><td>'+rc(p.rsiX)+'</td><td>'+rc(p.rsiY)+'</td><td>'+f2(p.cor)+'</td></tr>'});
 h+='</tbody></table></div>';document.getElementById('spt').innerHTML=h;
 document.querySelectorAll('#spt th[data-k]').forEach(function(t){t.onclick=function(){var k=t.dataset.k;if(k=='ratio')return;if(sortK==k)sortD=-sortD;else{sortK=k;sortD=-1}renderTable();renderDetail()}});
 document.querySelectorAll('#spt tbody tr').forEach(function(t){t.onclick=function(){sel=t.dataset.y;st('sppar',sel);renderTable();renderDetail()}})}
function svg(vals,lines,fmt,color){var W=340,Hh=190,pl=6,pr=62,pt=10,pb=18,mn=Math.min.apply(null,vals),mx=Math.max.apply(null,vals);lines.forEach(function(l){mn=Math.min(mn,l.v);mx=Math.max(mx,l.v)});
 var pad=(mx-mn)*.06||1;mn-=pad;mx+=pad;function X(i){return pl+(W-pl-pr)*i/(vals.length-1)}function Y(v){return pt+(Hh-pt-pb)*(1-(v-mn)/(mx-mn))}
 var o='<svg class=sp-svg viewBox="0 0 '+W+' '+Hh+'">';
 lines.forEach(function(l){o+='<line x1='+pl+' x2='+(W-pr)+' y1='+Y(l.v)+' y2='+Y(l.v)+' stroke="'+l.c+'" stroke-width=1 stroke-dasharray="'+(l.d||'')+'" opacity=.8 vector-effect="non-scaling-stroke"/><text x='+(W-pr+4)+' y='+(Y(l.v)+3)+' font-size=10 fill="'+l.c+'">'+l.t+'</text>'});
 var d='';vals.forEach(function(v,i){d+=(i?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)});
 o+='<path d="'+d+'" fill=none stroke="'+(color||'var(--ac)')+'" stroke-width=2 vector-effect="non-scaling-stroke"/>';
 o+='<circle cx='+X(vals.length-1)+' cy='+Y(vals[vals.length-1])+' r=3.5 fill="'+(color||'var(--ac)')+'"/><text x='+(W-pr+4)+' y='+(Y(vals[vals.length-1])-6)+' font-size=11 font-weight=700 fill="var(--tx)">'+fmt(vals[vals.length-1])+'</text></svg>';return o}
function hist(p,th){var r=p.r,n=p.n,ev=[],last=-9,i;for(i=20;i<n-5;i++){var z=zs(r,20,i);if(Math.abs(z)>=th&&i-last>=5){last=i;var ch=r[i+5]/r[i]-1;ev.push(z>0?-ch:ch)}}
 if(!ev.length)return null;var w=ev.filter(function(v){return v>0}).length,s=ev.slice().sort(function(a,b){return a-b});return{n:ev.length,win:w/ev.length,med:s[Math.floor(s.length/2)],worst:s[0],best:s[s.length-1]}}
function renderDetail(){var el=document.getElementById('spd');if(!sel||!BY[sel]){el.innerHTML='';return}var p=pair(base,sel);if(!p){el.innerHTML='';return}
 var up=p.z20>=0,S=up?p.x:p.y,B=up?p.y:p.x,pS=up?p.px:p.py,pB=up?p.py:p.px,w=swap(pS,pB)||{a:1,b:1};
 var key='sp_'+S+'_'+B,saved=st(key),a=w.a,b=w.b;if(saved){var q=saved.split(',');a=+q[0]||a;b=+q[1]||b}
 var qty=+(st('spq_'+S)||10000);
 var s=sig(p.z20,p.z60),n=p.n;
 var win=Math.min(120,n),rr=p.r.slice(-win),w60=p.r.slice(-Math.min(60,n)),m=mean(w60),sg=sd(w60);
 var lines=[{v:m,c:'#94a3b8',t:'méd 60d',d:''},{v:m+sg,c:'#f59e0b',t:'+1σ',d:'4 3'},{v:m-sg,c:'#f59e0b',t:'−1σ',d:'4 3'},{v:m+2*sg,c:'#ef4444',t:'+2σ',d:'4 3'},{v:m-2*sg,c:'#22c55e',t:'−2σ',d:'4 3'}];
 var h1=hist(p,1),h2=hist(p,2);
 function ht(h,t){return h?'<div class=sp-line><span>'+t+'</span><b>'+h.n+' casos · voltou a favor em '+f2(h.win*100,0)+'% · mediana '+f2(h.med*100)+'% · pior '+f2(h.worst*100)+'%</b></div>':'<div class=sp-line><span>'+t+'</span><b>sem casos</b></div>'}
 var o='<div class=sp-card><h2>'+p.x+' ÷ '+p.y+' <span class="sp-sig '+s[0]+'" style="margin-left:8px">'+s[1].replace('1º',p.x).replace('2º',p.y)+'</span></h2><div class=m>Relação hoje '+f2(p.ratio,4)+' ('+p.x+' vale '+f2(p.ratio,2)+' × '+p.y+') · z 20d '+f2(p.z20)+' · percentil '+f2(p.perc,0)+'% dos últimos '+Math.min(250,n)+' dias</div><div class=sp-det><div class=sp-grid>'
 +'<div class=sp-box><h3>Troca: sair de '+S+' para '+B+'</h3><div class=sp-in>Vender <input id=sa type=number min=1 value='+a+'> '+S+' por <input id=sb type=number min=1 value='+b+'> '+B+'</div>'
 +'<div id=spc></div><div class=sp-in>Tenho <input id=sq type=number min=0 value='+qty+' style="width:110px"> '+S+'</div><div id=spc2></div></div>'
 +'<div class=sp-box><h3>Relação '+p.x+' ÷ '+p.y+' (120 pregões)</h3>'+svg(rr,lines,function(v){return f2(v,3)})+'</div>'
 +'<div class=sp-box><h3 id=spdt></h3><div id=spdif></div></div>'
 +'<div class=sp-box><h3>No histórico deste par</h3><div class=mu style="font-size:12.5px;margin-bottom:6px">Quando a relação ficou esticada (z 20d), o que aconteceu nos 5 pregões seguintes a favor da troca (comprado em quem estava descontado)</div>'+ht(h1,'|z| ≥ 1')+ht(h2,'|z| ≥ 2')+'<div class=sp-line><span>RSI da relação D / 30m</span><b>'+f2(p.rsiR,0)+' / '+f2(p.rsiM,0)+'</b></div><div class=sp-line><span>Correlação 60d</span><b>'+f2(p.cor)+'</b></div></div>'
 +'</div></div></div>';el.innerHTML=o;
 function calc(){var na=+document.getElementById('sa').value,nb=+document.getElementById('sb').value,nq=+document.getElementById('sq').value;if(!(na>0&&nb>0))return;st(key,na+','+nb);st('spq_'+S,String(nq));
  var cash=na*pS-nb*pB,lotes=Math.floor(nq/na),tcash=lotes*cash,custo=lotes*(na*pS+nb*pB)*0.0003,pos=cash>=0;
  document.getElementById('spc').innerHTML='<div class=sp-line><span>Vende '+S+' (valor)</span><b>R$ '+f2(na*pS)+'</b></div><div class=sp-line><span>Recebe de '+B+' (valor)</span><b>R$ '+f2(nb*pB)+'</b></div>'
   +'<div class="sp-big '+(pos?'up':'dn')+'">'+(pos?'sobra':'falta')+' R$ '+f2(Math.abs(cash))+' por lote</div><div class=sp-line><span>Relação exata</span><b>1 '+S+' = '+f2(pS/pB,4)+' '+B+'</b></div>';
  document.getElementById('spc2').innerHTML='<div class=sp-line><span>Lotes completos</span><b>'+f2(lotes,0)+'</b></div><div class=sp-line><span>Compra '+B+'</span><b>'+f2(lotes*nb,0)+'</b></div><div class=sp-line><span>'+(pos?'Fica em caixa':'Precisa colocar')+'</span><b>R$ '+f2(Math.abs(tcash))+'</b></div><div class=sp-line><span>Custo B3 (0,03% × 2 pernas)</span><b>R$ '+f2(custo)+'</b></div>';
  var dif=[];for(var i=n-win;i<n;i++){dif.push(na*(up?p.al.x[i]:p.al.y[i])-nb*(up?p.al.y[i]:p.al.x[i]))}
  document.getElementById('spdt').textContent='Sobra em R$ por lote ('+na+' '+S+' − '+nb+' '+B+')';
  document.getElementById('spdif').innerHTML=svg(dif,[{v:mean(dif),c:'#94a3b8',t:'média',d:''}],function(v){return'R$ '+f2(v)},'#0891b2')}
 ['sa','sb','sq'].forEach(function(id){document.getElementById(id).oninput=calc});calc()}
function renderAlerts(){var out=[];for(var i=0;i<A.length;i++)for(var j=i+1;j<A.length;j++){var p=pair(A[i].n,A[j].n);if(!p)continue;if(Math.abs(p.z20)>=2&&(p.z60===null||Math.sign(p.z60)==Math.sign(p.z20)&&Math.abs(p.z60)>=1.5))out.push(p)}
 out.sort(function(a,b){return Math.abs(b.z20)-Math.abs(a.z20)});var el=document.getElementById('spa');
 if(!out.length){el.innerHTML='<div class=sp-card><div class=sp-det style="padding-top:14px"><b>Sem alertas agora</b><br><span class=mu>Nenhum par com z de 20d acima de 2 e z de 60d acima de 1,5 na mesma direção.</span></div></div>';return}
 el.innerHTML='<div class=alert><div>🔔</div><div><b>Pares esticados agora</b> (z 20d ≥ 2 e z 60d ≥ 1,5)<br>'+out.slice(0,8).map(function(p){var s=p.z20>0?p.x:p.y,b=p.z20>0?p.y:p.x;return'<span class=sp-al data-x="'+p.x+'" data-y="'+p.y+'">'+s+' → '+b+' · z '+f2(Math.abs(p.z20))+'</span>'}).join('')+'</div></div>';
 el.querySelectorAll('.sp-al').forEach(function(e){e.onclick=function(){base=e.dataset.x;sel=e.dataset.y;st('spbase',base);st('sppar',sel);render();window.scrollTo(0,0)}})}
function renderHeat(){var h='<div class=sc><table class=sp-hm><thead><tr><th></th>'+A.map(function(x){return'<th>'+x.n+'</th>'}).join('')+'</tr></thead><tbody>';
 A.forEach(function(r){h+='<tr><td>'+r.n+'</td>';A.forEach(function(c){if(r.n==c.n){h+='<td class=mu>–</td>';return}var p=pair(r.n,c.n);if(!p){h+='<td class=mu>–</td>';return}var z=p.z20,al=Math.min(Math.abs(z)/3,1);
  var bg=z>0?'rgba(220,38,38,'+(.1+.6*al)+')':'rgba(22,163,74,'+(.1+.6*al)+')';h+='<td data-x="'+r.n+'" data-y="'+c.n+'" style="background:'+bg+'">'+(z>0?'+':'')+f2(z,1)+'</td>'});h+='</tr>'});
 h+='</tbody></table></div>';document.getElementById('sph').innerHTML=h;
 document.querySelectorAll('#sph td[data-x]').forEach(function(t){t.onclick=function(){base=t.dataset.x;sel=t.dataset.y;st('spbase',base);st('sppar',sel);render();window.scrollTo(0,0)}})}
function render(){renderBase();renderTable();renderDetail()}
renderAlerts();render();renderHeat();
if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js').catch(function(){})}
})();
"""


def dados(raiz):
    """Lê os fechamentos dos ativos da categoria 'pares' (diário e 30 min)."""
    pasta = os.path.join(raiz, "categorias", "pares")
    cfg = json.load(open(os.path.join(pasta, "config.json"), encoding="utf-8"))
    out = []
    for n, a in cfg["ativos"].items():
        f1 = os.path.join(pasta, "dados", f"{n}_1D.csv")
        if not os.path.exists(f1): continue
        d = pd.read_csv(f1).dropna().tail(520)
        if len(d) < 30: continue
        item = {"n": n, "s": a.get("setor", ""), "dt": [int(t) // 86400 for t in d["time"]], "dc": [round(float(x), 4) for x in d["close"]]}
        f3 = os.path.join(pasta, "dados", f"{n}_30m.csv")
        if os.path.exists(f3):
            m = pd.read_csv(f3).dropna().tail(900)
            item["mt"] = [int(t) for t in m["time"]]; item["mc"] = [round(float(x), 4) for x in m["close"]]
        out.append(item)
    return out


def pagina(arq, titulo, paginas, ativos):
    agora = dt.datetime.now(ui.BRT)
    h = [ui.cabeca(titulo, paginas, arq), f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>",
         f"<p class=sub>Escolha o ativo de partida e veja a relação com cada um dos outros: quanto está esticada, o RSI da relação e quanto sobra em R$ na troca. Atualizado em {agora:%d/%m/%Y às %H:%M} (Brasília). B3 com ~15 min de atraso.</p>"]
    if len(ativos) < 2:
        h.append("<p class=mu>Preciso de pelo menos 2 ativos com histórico coletado.</p></main></body></html>")
        return "".join(h)
    h.append("<div id=spa></div><div class=sp-base id=spb></div><div class=sp-card><h2>Relação com os outros ativos</h2><div class=m>Clique numa linha para abrir os detalhes e a conta da troca. Clique no título de uma coluna para ordenar. z positivo = o ativo da esquerda está caro em relação ao da direita.</div><div id=spt></div></div>")
    h.append("<div id=spd></div><div class=sp-card><h2>Mapa de todos contra todos (z 20d)</h2><div class=m>Vermelho: o ativo da linha está esticado contra o da coluna. Verde: está descontado. Clique numa célula para abrir.</div><div id=sph></div></div>")
    h.append("<details><summary>Como ler</summary><p><b>Relação</b> = preço do ativo da esquerda ÷ preço do outro. <b>z 20d / 60d</b> = quantos desvios-padrão a relação de hoje está acima (+) ou abaixo (−) da média dos últimos 20 / 60 pregões; acima de +2 ou abaixo de −2 é raro. "
             "<b>Percentil</b> = em que posição a relação está nos últimos 250 pregões. <b>RSI da relação</b> = RSI de 14 períodos calculado sobre a própria relação (diário e 30 min). "
             "<b>Troca sugerida</b>: sai do ativo esticado e vai para o descontado; mostra a menor proporção em que a sobra em caixa é de até 1% do valor vendido (você pode editar as quantidades). "
             "Correlação baixa não impede a troca, mas quer dizer que a relação não tem âncora e pode se afastar mais antes de voltar. O histórico do par mostra como foi no passado, em amostra pequena.</p></details>")
    h.append("</main><script>var SPDATA=" + json.dumps({"a": ativos}, separators=(",", ":")) + ";" + JS + "</script></body></html>")
    return "".join(h)
