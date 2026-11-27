"""Visual do painel (páginas HTML). Recebe os dados prontos de monitor.py e devolve HTML."""
import html as H
import json
import datetime as dt
import pandas as pd

BRT = dt.timezone(dt.timedelta(hours=-3))
LIVE = {}

CSS = """
:root{--bg:#f4f6fa;--card:#fff;--card2:#eef1f7;--line:#e2e7f0;--tx:#0f1729;--mu:#6b7690;--ac:#4f46e5;--gr:#16a34a;--rd:#dc2626;
--grbg:rgba(22,163,74,.14);--rdbg:rgba(220,38,38,.12);--os:#16a34a;--ob:#dc2626;--shadow:0 1px 2px rgba(15,23,41,.06),0 4px 14px rgba(15,23,41,.04)}
@media (prefers-color-scheme:dark){:root{--bg:#0a0e16;--card:#121826;--card2:#1a2234;--line:#222d42;--tx:#e8eefb;--mu:#8793ab;--ac:#8b8cf8;--gr:#34d399;--rd:#f87171;
--grbg:rgba(52,211,153,.14);--rdbg:rgba(248,113,113,.14);--os:#10b981;--ob:#ef4444;--shadow:none}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Inter","Segoe UI",system-ui,sans-serif;font-variant-numeric:tabular-nums}
.top{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:14px;padding:10px 16px;background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--line);padding-top:max(10px,env(safe-area-inset-top))}
.brand{display:flex;align-items:center;gap:8px;font-weight:800;letter-spacing:-.02em;font-size:16px;color:var(--tx);text-decoration:none}
.logo{width:26px;height:26px;border-radius:8px;background:linear-gradient(135deg,#4f46e5,#06b6d4);display:grid;place-items:center;color:#fff;font-size:13px}
nav{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;flex:1}nav::-webkit-scrollbar{display:none}
nav a{padding:6px 12px;border-radius:999px;color:var(--mu);text-decoration:none;font-weight:600;font-size:13px;white-space:nowrap}
nav a:hover{color:var(--tx);background:var(--card2)}nav a.at{background:var(--tx);color:var(--bg)}
.stamp{display:flex;align-items:center;gap:7px;color:var(--mu);font-size:12px;white-space:nowrap}
.dot{width:8px;height:8px;border-radius:50%;background:var(--gr);animation:p 2s infinite}
@keyframes p{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--gr) 60%,transparent)}70%{box-shadow:0 0 0 7px transparent}100%{box-shadow:0 0 0 0 transparent}}
main{max-width:1180px;margin:0 auto;padding:18px 16px 60px}
h1{font-size:26px;letter-spacing:-.03em;margin:6px 0 2px}.sub{color:var(--mu);margin:0 0 16px}
.alert{display:flex;gap:10px;align-items:flex-start;background:var(--rdbg);border:1px solid color-mix(in srgb,var(--rd) 40%,transparent);border-radius:14px;padding:12px 14px;margin:0 0 16px}
.alert b{color:var(--rd)}.alert .it{display:inline-block;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:2px 8px;margin:4px 4px 0 0;font-size:12.5px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin:0 0 18px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;box-shadow:var(--shadow)}
.kpi .l{color:var(--mu);font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em}
.kpi .v{font-size:30px;font-weight:800;letter-spacing:-.03em;margin:2px 0 6px}
.chips{display:flex;flex-wrap:wrap;gap:5px}.chip{background:var(--card2);border-radius:8px;padding:3px 8px;font-size:12px;font-weight:600}
.chip i{font-style:normal;color:var(--mu);font-weight:500;margin-left:4px}
.mv{display:flex;justify-content:space-between;padding:4px 0;font-weight:600}.mv span:last-child{font-weight:700}
.up{color:var(--gr)}.dn{color:var(--rd)}.mu{color:var(--mu)}
.bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 14px}
.bar input{flex:1;min-width:180px;background:var(--card);border:1px solid var(--line);color:var(--tx);border-radius:12px;padding:10px 14px;font-size:14px;outline:none}
.bar input:focus{border-color:var(--ac)}
.seg{display:flex;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:3px}
.seg button{border:0;background:none;color:var(--mu);font-weight:600;font-size:13px;padding:6px 12px;border-radius:9px;cursor:pointer}
.seg button.on{background:var(--tx);color:var(--bg)}
.sec{background:var(--card);border:1px solid var(--line);border-radius:18px;margin:0 0 18px;box-shadow:var(--shadow);overflow:hidden}
.sh{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;padding:14px 18px 10px}
.sh h2{margin:0;font-size:17px;letter-spacing:-.02em}.sh .m{color:var(--mu);font-size:12.5px}
.pill{font-size:11.5px;font-weight:700;padding:2px 8px;border-radius:999px}
.pill.g{background:var(--grbg);color:var(--gr)}.pill.r{background:var(--rdbg);color:var(--rd)}
.sc{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:13.5px}
th{background:var(--card);color:var(--mu);font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;text-align:right;padding:8px 10px;border-bottom:1px solid var(--line);cursor:pointer;white-space:nowrap;user-select:none}
th:first-child,td:first-child{text-align:left;position:sticky;left:0;background:var(--card);z-index:2;padding-left:18px}
th.so::after{content:" ▲";font-size:9px}th.so.d::after{content:" ▼"}
td{text-align:right;padding:8px 10px;border-bottom:1px solid color-mix(in srgb,var(--line) 55%,transparent);white-space:nowrap}
tr:hover td,tr:hover td:first-child{background:var(--card2)}
td.tk{font-weight:700}
tr.band td{background:var(--card2);color:var(--mu);font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;padding:6px 18px;text-align:left;position:static}
.r{display:inline-block;min-width:42px;text-align:center;border-radius:8px;padding:2px 7px;font-weight:700}
.r.os{background:var(--os);color:#fff}.r.lo{background:var(--grbg);color:var(--gr)}.r.hi{background:var(--rdbg);color:var(--rd)}.r.ob{background:var(--ob);color:#fff}
.var{font-weight:600}.var.up::before{content:"▲ ";font-size:9px}.var.dn::before{content:"▼ ";font-size:9px}
.tag{display:inline-block;font-size:11px;font-weight:600;border-radius:6px;padding:1px 6px;margin-left:3px}
.tag.os{background:var(--grbg);color:var(--gr)}.tag.ob{background:var(--rdbg);color:var(--rd)}
.ext small{color:var(--mu);margin-left:6px;font-size:11px}
.dia{display:inline-block;border-radius:8px;padding:2px 8px;font-weight:700;font-size:12px}
.dia.d3{background:var(--rd);color:#fff}.dia.d7{background:#f59e0b;color:#1b1200}.dia.d14{background:rgba(250,204,21,.28)}.dia.d0{color:var(--mu);font-weight:500}
.cal{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px;padding:4px 18px 18px}
.ev{display:flex;gap:12px;align-items:center;background:var(--card2);border-radius:12px;padding:10px 12px}
.ev .dt{min-width:46px;text-align:center;font-weight:800;font-size:19px;line-height:1.05}.ev .dt small{display:block;font-size:11px;color:var(--mu);font-weight:600;text-transform:uppercase}
.ev .tx{flex:1;font-weight:600}.ev .tx small{display:block;color:var(--mu);font-weight:500}
details{margin:0 0 18px;color:var(--mu);font-size:13px}summary{cursor:pointer;font-weight:600}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:6px 0 20px}
a.tile{display:block;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:18px 20px;color:var(--tx);text-decoration:none;box-shadow:var(--shadow);transition:transform .15s,border-color .15s}
a.tile:hover{transform:translateY(-2px);border-color:var(--ac)}
a.tile .tt{font-size:20px;font-weight:800;letter-spacing:-.02em;display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
a.tile .tt span{color:var(--mu);font-weight:400}
a.tile .ln{color:var(--mu);font-size:13px;margin-top:3px}
a.tile.big{background:linear-gradient(135deg,#4f46e5,#0891b2);color:#fff;border:0}a.tile.big .ln,a.tile.big .tt span{color:#dbeafe}
.lvb{font-size:11px;font-weight:700;border-radius:999px;padding:2px 8px;background:var(--card2);color:var(--mu)}.lvb.on{background:var(--grbg);color:var(--gr)}
@keyframes fu{from{background:var(--grbg)}to{background:transparent}}@keyframes fd{from{background:var(--rdbg)}to{background:transparent}}
td.fu{animation:fu 1s}td.fd{animation:fd 1s}
.tvw{height:70vh;min-height:420px;background:var(--card);border:1px solid var(--line);border-radius:18px;overflow:hidden;margin:0 0 16px}
.tvt{margin:0 0 14px;border-radius:12px;overflow:hidden}
.sy{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}.sy button{border:1px solid var(--line);background:var(--card);color:var(--tx);border-radius:999px;padding:5px 12px;font-weight:600;font-size:12.5px;cursor:pointer}.sy button.on{background:var(--tx);color:var(--bg)}
.osc{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;padding:4px 18px 18px}.osc .kpi{box-shadow:none;background:var(--card2);border:0}
.foot{color:var(--mu);font-size:12px;margin:0 0 18px}
@media (max-width:700px){.kpis{grid-template-columns:1fr 1fr;gap:8px}.kpi{padding:11px 12px}.kpi .v{font-size:24px}.kpi .l{font-size:10.5px}h1{font-size:22px}.tx2{display:none}main{padding:14px 10px 50px}th,td{padding:7px 8px}td:first-child,th:first-child{padding-left:12px}}
.ic,.ng,.sbt{display:none}
@media (min-width:900px){
html{--sw:212px}html.col{--sw:62px}
body{padding-left:var(--sw);transition:padding .15s}
.top{position:fixed;left:0;top:0;bottom:0;width:var(--sw);z-index:30;flex-direction:column;align-items:stretch;gap:4px;padding:14px 10px;border-right:1px solid var(--line);border-bottom:0;background:var(--card);overflow-y:auto;overflow-x:hidden;backdrop-filter:none;transition:width .15s}
.brand{padding:2px 6px 10px;white-space:nowrap}
.sbt{display:flex;align-items:center;justify-content:center;width:100%;margin:0 0 6px;border:1px solid var(--line);background:var(--card2);color:var(--mu);border-radius:10px;padding:5px;cursor:pointer;font-size:14px;line-height:1}
.sbt:hover{color:var(--tx)}
nav{flex-direction:column;overflow:visible;flex:1;gap:2px}
nav a{display:flex;align-items:center;gap:11px;border-radius:10px;padding:8px 10px;font-size:13.5px}
nav a.at{background:var(--tx);color:var(--bg)}
.bdg{background:#ef4444;color:#fff;border-radius:999px;font-size:10px;font-weight:800;padding:1px 6px;margin-left:auto}html.col .bdg{display:none}.ic{display:inline-grid;place-items:center;width:22px;height:22px;flex:none;font-style:normal;font-weight:800;font-size:13px}
.ng{display:block;margin:12px 10px 3px;font-size:10.5px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--mu);opacity:.8;white-space:nowrap}
.stamp{flex-direction:column;align-items:flex-start;gap:3px;padding:10px 8px 0;border-top:1px solid var(--line);font-size:11.5px;white-space:normal}
.stamp .tx2{display:block}
html.col .t,html.col .brand .bn,html.col .ng,html.col .stamp span:not(.dot):not(.lvb),html.col .stamp .tx2{display:none}
html.col .stamp{align-items:center}
html.col nav a{justify-content:center;padding:8px 0}
html.col .brand{justify-content:center;padding-left:0;padding-right:0}
main{max-width:1280px}
}
@media print{.top,.bar{display:none}}
"""

JS = """
(function(){
var SS=window.sessionStorage,g=function(k){try{return SS.getItem(k)}catch(e){return null}},s=function(k,v){try{SS.setItem(k,v)}catch(e){}};
var q=document.getElementById('q'),chips=document.querySelectorAll('.seg button'),mode=g('mode')||'all';
function aplica(){var t=(q?q.value:'').toLowerCase().trim();
 document.querySelectorAll('tr[data-t]').forEach(function(r){var ok=(!t||r.dataset.t.indexOf(t)>-1)&&(mode=='all'||(mode=='os'&&r.dataset.os=='1')||(mode=='ob'&&r.dataset.ob=='1'));r.style.display=ok?'':'none'});
 document.querySelectorAll('tr.band').forEach(function(b){var n=b.nextElementSibling,v=false;while(n&&!n.classList.contains('band')){if(n.style.display!='none')v=true;n=n.nextElementSibling}b.style.display=v?'':'none'});
 chips.forEach(function(c){c.classList.toggle('on',c.dataset.m==mode)});s('mode',mode);if(q)s('q',q.value)}
if(q){q.value=g('q')||'';q.addEventListener('input',aplica)}
chips.forEach(function(c){c.onclick=function(){mode=c.dataset.m;aplica()}});
document.querySelectorAll('table.s').forEach(function(t){t.querySelectorAll('th').forEach(function(th,i){th.onclick=function(){
 var d=th.classList.contains('so')&&!th.classList.contains('d');t.querySelectorAll('th').forEach(function(x){x.classList.remove('so','d')});th.classList.add('so');if(d)th.classList.add('d');
 var dir=d?-1:1,rows=[].slice.call(t.querySelectorAll('tr[data-t]'));t.querySelectorAll('tr.band').forEach(function(b){b.remove()});
 rows.sort(function(a,b){var x=a.cells[i],y=b.cells[i],vx=x.dataset.v,vy=y.dataset.v;
  if(vx===''||vx===undefined)return 1;if(vy===''||vy===undefined)return -1;return(parseFloat(vx)-parseFloat(vy))*dir});
 rows.forEach(function(r){t.tBodies[0].appendChild(r)})}})});
aplica();
var y=g('y');if(y){window.scrollTo(0,parseInt(y))}
var fim=Date.now()+300000,cd=document.getElementById('cd');
setInterval(function(){var r=Math.max(0,Math.round((fim-Date.now())/1000));if(cd)cd.textContent=Math.floor(r/60)+':'+('0'+(r%60)).slice(-2);
 if(r<=0){s('y',window.scrollY);location.reload()}},1000);

var LV=window.LVCFG||{},rows={},last={},dirty={},lastKr={},open_=0;
document.querySelectorAll('tr[data-lv]').forEach(function(r){try{var c=JSON.parse(r.dataset.lv);r._c=c;(rows[c.sym]=rows[c.sym]||[]).push(r)}catch(e){}});
function fnum(v){return v.toLocaleString('pt-BR',{minimumFractionDigits:v>=1?2:4,maximumFractionDigits:v>=1?2:4})}
function vtxt(v){return(v>=0?'+':'')+(v*100).toFixed(2).replace('.',',')+'%'}
function setVar(td,v){if(!td)return;var sp=td.querySelector('.var');if(!sp){td.innerHTML='<span class=var></span>';sp=td.firstChild}
 sp.className='var '+(v>0?'up':v<0?'dn':'mu');sp.textContent=vtxt(v);td.dataset.v=v}
function flash(td,up){if(!td)return;td.classList.remove('fu','fd');void td.offsetWidth;td.classList.add(up?'fu':'fd')}
function etNow(){var o={};new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false,weekday:'short'}).formatToParts(new Date()).forEach(function(p){o[p.type]=p.value});
 var m=(parseInt(o.hour)%24)*60+parseInt(o.minute);return{d:parseInt(o.year+o.month+o.day),reg:o.weekday!='Sat'&&o.weekday!='Sun'&&m>=570&&m<960}}
function utcD(){return parseInt(new Date().toISOString().slice(0,10).replace(/-/g,''))}
function apply(r,p){var c=r._c,et=etNow(),today=c.tz=='et'?et.d:utcD(),reg=c.tz=='utc'||et.reg;
 if(!reg){var ex=r.querySelector('td.ex');if(ex){var v=p/c.pc-1;ex.className='ext ex';ex.innerHTML=fnum(p)+' <span class="var '+(v>0?'up':v<0?'dn':'mu')+'">'+vtxt(v)+'</span><small>ao vivo</small>';ex.dataset.v=v;flash(ex,v>=0)}return}
 var px=r.querySelector('td.px');if(px){var old=parseFloat(px.dataset.v);px.textContent=fnum(p);px.dataset.v=p;if(old!==p)flash(px,p>=old)}
 setVar(r.querySelector('td.vd'),p/(c.ld>=today?c.pd[0]:c.pd[1])-1);
 setVar(r.querySelector('td.vw'),p/(c.lw>=today?c.pw[0]:c.pw[1])-1);
 var now=Date.now()/1000;
 r.querySelectorAll('td.rc').forEach(function(td){var a=JSON.parse(td.dataset.rs),k=td.dataset.k,e=parseFloat(td.dataset.e),inp=k=='d'?e>=today:now<e,pc=inp?a[0]:a[3],ag=inp?a[1]:a[4],al=inp?a[2]:a[5],d=p-pc;
  ag=ag*13/14+Math.max(d,0)/14;al=al*13/14+Math.max(-d,0)/14;var v=al==0?100:100-100/(1+ag/al);
  var cl=v<=30?'os':v<=40?'lo':v>=70?'ob':v>=60?'hi':'';td.dataset.v=v.toFixed(2);td.innerHTML='<span class="r '+cl+'">'+Math.round(v)+(td.dataset.star?'*':'')+'</span>'})}
function tick(k,p,src){if(!(p>0)||!rows[k])return;if(src=='kr')lastKr[k]=Date.now();else if(src=='bn'&&Date.now()-(lastKr[k]||0)<20000)return;last[k]=p;dirty[k]=1}
setInterval(function(){for(var k in dirty){delete dirty[k];(rows[k]||[]).forEach(function(r){apply(r,last[k])})}},1000);
window.__tick=tick;
var bad=document.getElementById('lv');
function st(d){open_+=d;if(bad){bad.textContent=open_>0?'● ao vivo':'5 min';bad.className='lvb'+(open_>0?' on':'')}}
function sock(url,onopen,onmsg){var w;function go(){try{w=new WebSocket(url)}catch(e){return}var up=false;
 w.onopen=function(){up=true;st(1);onopen(w)};w.onmessage=function(m){try{onmsg(JSON.parse(m.data))}catch(e){}};
 w.onclose=function(){if(up)st(-1);setTimeout(go,8000)};w.onerror=function(){try{w.close()}catch(e){}}}go()}
var cr=[],us=[];document.querySelectorAll('tr[data-lv]').forEach(function(r){var c=r._c;if(c.src=='cr'&&cr.indexOf(c.sym)<0)cr.push(c.sym);if(c.src=='us'&&us.indexOf(c.sym)<0)us.push(c.sym)});
if(cr.length){
 sock('wss://ws.kraken.com/v2',function(w){w.send(JSON.stringify({method:'subscribe',params:{channel:'ticker',symbol:cr.map(function(k){return k+'/USD'})}}))},
  function(j){if(j.channel=='ticker'&&j.data)j.data.forEach(function(d){tick(d.symbol.split('/')[0].replace('XBT','BTC'),d.last,'kr')})});
 sock('wss://stream.binance.com:9443/stream?streams='+cr.map(function(k){return k.toLowerCase()+'usdt@miniTicker'}).join('/'),function(){},
  function(j){var d=j.data;if(d&&d.s)tick(d.s.replace('USDT',''),parseFloat(d.c),'bn')})}
if(us.length&&LV.fh){us=us.slice(0,50);
 sock('wss://ws.finnhub.io?token='+LV.fh,function(w){us.forEach(function(k){w.send(JSON.stringify({type:'subscribe',symbol:k}))})},
  function(j){if(j.type=='trade'&&j.data)j.data.forEach(function(t){tick(t.s,t.p,'fh')})})}
if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js').catch(function(){})}
})();
"""


def num(v, n=2):
    if v is None or v != v: return "–"
    s = f"{v:,.{n}f}" if abs(v) >= 1 else f"{v:.4f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pc(v, juros=False):
    if v != v: return "–"
    if juros: return f"{v:+.1f} bp".replace(".", ",")
    return f"{v*100:+.2f}%".replace(".", ",")


def var(v, juros=False, cls=""):
    if v != v: return f"<td class='{cls}' data-v=''>–</td>"
    c = "up" if v > 0 else "dn" if v < 0 else "mu"
    return f"<td class='{cls}' data-v='{v:.6f}'><span class='var {c}'>{pc(v, juros)}</span></td>"


def rsi_td(v, star=False, rs=None):
    live = f" class=rc data-rs='{json.dumps(rs[0])}' data-k={rs[1]} data-e={rs[2]}{' data-star=1' if star else ''}" if rs else ""
    if v != v: return f"<td{live} data-v=''><span class=mu>–</span></td>"
    c = "os" if v <= 30 else "lo" if v <= 40 else "ob" if v >= 70 else "hi" if v >= 60 else ""
    return f"<td{live} data-v='{v:.2f}'><span class='r {c}'>{v:.0f}{'*' if star else ''}</span></td>"


def dias_badge(n):
    return "d3" if n <= 3 else "d7" if n <= 7 else "d14" if n <= 14 else "d0"


def ext_td(r):
    e = r.get("ext")
    if not e: return "<td data-v='' class='mu ex'>–</td>"
    c = "up" if e["var"] > 0 else "dn" if e["var"] < 0 else "mu"
    return (f"<td class='ext ex' data-v='{e['var']:.4f}' title='{e['fase']}-mercado, {e['hora']} (Brasília)'>"
            f"{num(e['preco'])} <span class='var {c}'>{e['var']:+.2f}%</span><small>{e['fase']} {e['hora'][-5:]}</small></td>")


def tags(sinal):
    if not sinal: return ""
    out = []
    for p in sinal.split(" + "):
        c = "os" if "sobrevenda" in p else "ob"
        out.append(f"<span class='tag {c}'>{'↓' if c == 'os' else '↑'} {p.split()[-1]}</span>")
    return "".join(out)


def agrega(sel):
    """KPIs: sobrevenda, sobrecompra e maiores movimentos (ignora juros)."""
    L = [r for x in sel if not x[4] for r in x[1]]
    os_ = sorted([r for r in L if r["rd"] <= 30], key=lambda r: r["rd"])
    ob = sorted([r for r in L if r["rd"] >= 70], key=lambda r: -r["rd"])
    mv = sorted([r for r in L if r["dia"] == r["dia"]], key=lambda r: r["dia"])
    return L, os_, ob, mv


def limpo(r): return H.escape(r["rot"].replace("** ", ""))


def kpis(sel):
    L, os_, ob, mv = agrega(sel)
    def chips(rs, lim=9):
        if not rs: return "<span class=mu>nenhum agora</span>"
        return ("<div class=chips>" + "".join(f"<span class=chip>{limpo(r)}<i>{r['rd']:.0f}</i></span>" for r in rs[:lim])
                + (f"<span class=chip><i>+{len(rs)-lim}</i></span>" if len(rs) > lim else "") + "</div>")
    cards = [f"<div class=kpi><div class=l>Sobrevenda · RSI diário ≤ 30</div><div class='v up'>{len(os_)}</div>{chips(os_)}</div>",
             f"<div class=kpi><div class=l>Sobrecompra · RSI diário ≥ 70</div><div class='v dn'>{len(ob)}</div>{chips(ob)}</div>",
             f"<div class=kpi><div class=l>Maiores altas · dia</div>{top5(L, 'dia', True)}</div>",
             f"<div class=kpi><div class=l>Maiores quedas · dia</div>{top5(L, 'dia', False)}</div>"]
    return "<div class=kpis>" + "".join(cards) + "</div>"


def top5(L, chave, alta, n=5):
    rs = sorted([r for r in L if r.get(chave) is not None and r.get(chave) == r.get(chave)], key=lambda r: r[chave], reverse=alta)
    rs = [r for r in rs if (r[chave] > 0) == alta][:n]
    return "".join(f"<div class=mv><span>{limpo(r)}</span><span class='{'up' if alta else 'dn'}'>{pc(r[chave])}</span></div>" for r in rs) or "<span class=mu>–</span>"


def oscilacoes(arq, titulo, paginas, secoes):
    h = [cabeca(titulo, paginas, arq), f"<h1>{titulo}</h1><p class=sub>Maiores altas e quedas por período · atualizado em {dt.datetime.now(BRT):%d/%m/%Y às %H:%M} (Brasília)</p>"]
    for grupo, chave in (("Brasil", "brasil"), ("EUA", "eua"), ("Cripto", "cripto")):
        L = [r for x in secoes if x[5] == chave and not x[4] for r in x[1]]
        if not L: continue
        h.append(f"<section class=sec><div class=sh><h2>{grupo}</h2><span class=m>{len(L)} ativos</span></div><div class=osc>")
        for per, k, leg in (("Dia", "dia", "último preço contra o fechamento anterior"), ("Semana", "sem", "contra o fechamento da semana anterior"), ("Mês", "mes", "contra o fechamento do mês anterior")):
            h.append(f"<div class=kpi><div class=l>{per} <span class=mu style='text-transform:none;letter-spacing:0;font-weight:500'>· {leg}</span></div>"
                     f"<div class='l up' style='margin-top:10px'>▲ Maiores altas</div>{top5(L, k, True)}"
                     f"<div class='l dn' style='margin-top:14px'>▼ Maiores quedas</div>{top5(L, k, False)}</div>")
        h.append("</div></section>")
    h.append(f"</main><script>{JS}</script></body></html>")
    return "".join(h)


def secao(nome, L, com_res, tempos, e_juros):
    tem_ext = any(r.get("ext") for r in L)
    ns = sum(1 for r in L if r["rd"] <= 30); nc = sum(1 for r in L if r["rd"] >= 70)
    h = [f"<section class=sec><div class=sh><h2>{H.escape(nome)}</h2><span class=m>{len(L)} ativos</span>"
         + (f"<span class='pill g'>{ns} em sobrevenda</span>" if ns else "") + (f"<span class='pill r'>{nc} em sobrecompra</span>" if nc else "")
         + "</div><div class=sc><table class=s><thead><tr><th>Ativo</th><th>Preço</th>" + ("<th>Fora do pregão</th>" if tem_ext else "")
         + "<th>Dia</th><th>Semana</th>" + "".join(f"<th>RSI {t.upper() if t.endswith('h') else t}</th>" for t in tempos)
         + "<th>RSI D</th><th>RSI S</th>" + ("" if e_juros else "<th>RSI M</th>") + "<th>Sinal</th>" + ("<th>Resultado</th>" if com_res else "") + "<th>Dado de</th></tr></thead><tbody>"]
    ant = None; ncol = 8 + (1 if tem_ext else 0) + len(tempos) + (0 if e_juros else 1) + (1 if com_res else 0)
    for r in sorted(L, key=lambda r: r["ord"]):
        if r["setor"] and r["setor"] != ant:
            h.append(f"<tr class=band><td colspan={ncol}>{H.escape(r['setor'])}</td></tr>")
        ant = r["setor"]
        j = bool(r.get("juros"))
        os_ = "1" if r["rd"] <= 30 else "0"; ob = "1" if r["rd"] >= 70 else "0"
        busca = f"{r['rot']} {r['nome']} {r['setor']} {r.get('info', '')}".lower()
        star = r["rm"] == r["rm"] and r["nm"] < 30
        lv = f" data-lv='{json.dumps(r['lv'], separators=(',', ':'))}'" if r.get("lv") else ""
        row = [f"<tr data-t='{H.escape(busca, quote=True)}' data-os={os_} data-ob={ob}{lv}><td class=tk data-v='{r['ord']}' title='{H.escape(r.get('info', ''), quote=True)}'>{H.escape(r['rot'])}</td>",
               f"<td class=px data-v='{r['preco']:.6f}'>{num(r['preco']) + ('%' if j else '')}</td>"]
        if tem_ext: row.append(ext_td(r))
        row += [var(r["dia"], j, "vd"), var(r["sem"], j, "vw")]
        rs = r.get("rs") or {}
        row += [rsi_td(r["tf"].get(t, float("nan")), rs=rs.get(t)) for t in tempos]
        row += [rsi_td(r["rd"], rs=rs.get("D")), rsi_td(r["rw"], rs=rs.get("S"))]
        if not e_juros: row.append(rsi_td(r["rm"], star, rs.get("M")))
        row.append(f"<td data-v='' style='text-align:left'>{tags(r['sinal'])}</td>")
        if com_res:
            if r.get("res"):
                dd, n, est = r["res"]
                row.append(f"<td data-v='{n}'><span class='dia {dias_badge(n)}'>{'~' if est else ''}{dd:%d/%m} · {n}d</span></td>")
            else: row.append("<td data-v='' class=mu>–</td>")
        row.append(f"<td class=mu data-v='{r['data']:%Y%m%d}'>{r['data']:%d/%m}</td></tr>")
        h.append("".join(row))
    h.append("</tbody></table></div></section>")
    return "".join(h)


def calendario(eventos):
    hoje = pd.Timestamp.today().normalize(); L = []
    for e in eventos:
        d = pd.Timestamp(e["data"]); n = (d - hoje).days
        if n >= 0: L.append((d, n, e))
    if not L: return ""
    L.sort(key=lambda x: x[0])
    meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    h = ["<section class=sec><div class=sh><h2>Calendário</h2><span class=m>juros, inflação e feriados · vermelho ≤ 3 dias, laranja ≤ 7, amarelo ≤ 14</span></div><div class=cal>"]
    for d, n, e in L:
        h.append(f"<div class=ev><div class=dt>{d.day:02d}<small>{meses[d.month-1]}</small></div><div class=tx>{H.escape(e['evento'])}<small>{H.escape(e['regiao'])} · {d:%d/%m/%Y}</small></div>"
                 f"<span class='dia {dias_badge(n)}'>{'hoje' if n == 0 else f'{n}d'}</span></div>")
    h.append("</div></section><p class=foot>Datas de resultados: nos EUA vêm do Yahoo. Na B3, as marcadas com ~ são estimativas (data do 4T do ano anterior mais 52 semanas) até a empresa publicar o calendário oficial. Para fixar uma data na B3, edite categorias/brasil/resultados_manual.json.</p>")
    return "".join(h)


def alerta(sel, eventos, com_eventos=True):
    prox = []
    for x in sel:
        for r in x[1]:
            if r.get("res") and r["res"][1] <= 7:
                prox.append((r["res"][1], f"Resultado {r['nome']} · {'~' if r['res'][2] else ''}{r['res'][0]:%d/%m}"))
    if com_eventos:
        for e in eventos:
            n = (pd.Timestamp(e["data"]) - pd.Timestamp.today().normalize()).days
            if 0 <= n <= 7: prox.append((n, f"{e['evento']} · {pd.Timestamp(e['data']):%d/%m}"))
    if not prox: return ""
    prox.sort()
    return ("<div class=alert><div>🔔</div><div><b>Atenção, próximos 7 dias</b><br>" +
            "".join(f"<span class=it>{'hoje' if n == 0 else f'em {n}d'} · {H.escape(t)}</span>" for n, t in prox) + "</div></div>")


def _novas_ops():
    try:
        import os, time
        f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "categorias", "cripto", "baleias.json")
        e = json.load(open(f, encoding="utf-8"))
        lim = time.time() - 3600
        return sum(1 for x in e.get("eventos", []) if x["t"] >= lim and abs(x["d"]) >= 5e6)
    except Exception:
        return 0


def cabeca(titulo, paginas, atual):
    agora = dt.datetime.now(BRT)
    n_ops = _novas_ops()
    ICO = {"Todos": "☰", "Cotações": "≣", "Cripto": "₿", "Brasil": "R$", "EUA": "$", "Opções": "◔", "Dados gerais": "◍", "Oscilações": "↕", "Spread": "⇄", "Mapa": "▦", "Trades": "⇆", "Momento": "◐", "Momento Cripto": "₿", "Baleias": "🐋", "Operações": "⚡", "Carteiras": "🏆", "Baleias TradeFi": "🏛", "Gráficos": "▤"}
    GRP = {"Oscilações": "Análises", "Momento Cripto": "Cripto", "Baleias": "Cripto", "Operações": "Cripto", "Carteiras": "Cripto", "Baleias TradeFi": "Cripto", "Gráficos": "Outros"}
    vistos = set()
    nav = ""
    for a, t, _ in paginas:
        g = GRP.get(t)
        if g and g not in vistos:
            vistos.add(g)
            nav += f"<div class=ng>{g}</div>"
        bd = f"<span class=bdg title='Movimentações de baleias acima de US$ 5 mi na última hora'>{n_ops}</span>" if (t == "Operações" and n_ops) else ""
        nav += f"<a class='{'at' if a == atual else ''}' href='{a}' title='{t}'><i class=ic>{ICO.get(t, '•')}</i><span class=t>{t}</span>{bd}</a>"
    return (f"<!doctype html><html lang=pt-br><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            f"<title>{titulo} · Monitor</title><meta http-equiv=refresh content=330><meta name=theme-color content='#0a0e16'>"
            "<link rel=manifest href=manifest.webmanifest><link rel=icon href=icon.svg type='image/svg+xml'><link rel=apple-touch-icon href=apple-touch-icon.png>"
            "<meta name=apple-mobile-web-app-capable content=yes><meta name=mobile-web-app-capable content=yes><meta name=apple-mobile-web-app-title content=Monitor>"
            "<script>try{if(localStorage.sbcol=='1')document.documentElement.classList.add('col')}catch(e){}</script>"
            f"<style>{CSS}</style></head><body><header class=top><a class=brand href=index.html><span class=logo>◢</span><span class=bn>Monitor</span></a>"
            "<button class=sbt type=button title='Recolher ou expandir o menu' onclick=\"var c=document.documentElement.classList.toggle('col');try{localStorage.sbcol=c?'1':'0'}catch(e){}\">☰</button><nav>"
            f"<a class='{'at' if atual == 'index.html' else ''}' href=index.html title='Início'><i class=ic>⌂</i><span class=t>Início</span></a>{nav}</nav>"
            f"<div class=stamp><span class=dot></span><span>{agora:%H:%M}</span><span id=lv class=lvb title='Tempo real'>5 min</span><span class=tx2>· próxima em <b id=cd>5:00</b></span></div></header><main>")


def pagina(arq, titulo, sel, paginas, eventos, com_cal):
    h = [cabeca(titulo, paginas, arq), f"<h1>{H.escape(titulo)}</h1><p class=sub>Atualizado em {dt.datetime.now(BRT):%d/%m/%Y às %H:%M} (Brasília) · recarrega sozinho a cada 5 minutos</p>",
         alerta(sel, eventos, com_cal), kpis(sel) if sel else "",
         "<div class=bar><input id=q type=search placeholder='Buscar ativo ou setor…' autocomplete=off><div class=seg>"
         "<button data-m=all>Todos</button><button data-m=os>Sobrevenda</button><button data-m=ob>Sobrecompra</button></div></div>"]
    for nome, L, com_res, tempos, e_juros, _ in sel:
        h.append(secao(nome, L, com_res, tempos, e_juros))
    if not sel: h.append("<p class=mu>Sem dados coletados ainda.</p>")
    if com_cal: h.append(calendario(eventos))
    h.append("<details><summary>Como ler</summary><p>RSI de 14 períodos: <b>D</b> diário, <b>S</b> semanal, <b>M</b> mensal (30 dias); nas criptos também 15 min, 30 min, 1H e 4H. "
             "Verde forte = sobrevenda (RSI ≤ 30), verde claro = 30–40, vermelho claro = 60–70, vermelho forte = sobrecompra (≥ 70). "
             "* no RSI mensal = menos de 30 meses de histórico. Dia = último preço contra o fechamento anterior; Semana = contra o fechamento da semana anterior. "
             "A candle do momento ainda está em andamento. ** antes do nome (Brasil) = as 2 melhores do setor. Clique no título de uma coluna para ordenar.</p></details>")
    h.append(f"</main><script>window.LVCFG={{fh:{json.dumps(LIVE.get('finnhub', ''))}}};{JS}</script></body></html>")
    return "".join(h)


def inicio(paginas, secoes, eventos):
    h = [cabeca("Início", paginas, "index.html"), "<h1>Monitor de mercado</h1><p class=sub>RSI, variações e calendário · atualizado a cada 5 minutos</p>",
         alerta(secoes, eventos), "<div class=tiles>"]
    for arq, titulo, chaves in paginas:
        if chaves == "oscilacoes":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>Maiores altas e quedas: dia, semana e mês</div><div class=ln>Brasil, EUA e cripto</div></a>")
            continue
        if chaves == "spread":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>Relação entre ativos para permutar</div><div class=ln>Esticado x descontado, com a sobra em R$</div></a>")
            continue
        if chaves == "opcoes":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>Barreiras de alta e de queda nas opções</div><div class=ln>Max pain, movimento precificado e viés</div></a>")
            continue
        if chaves == "mapa":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>Mapa de calor das ações da B3 e dos BDRs</div><div class=ln>Quadrados por valor de mercado, cor pela variação</div></a>")
            continue
        if chaves == "momento":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>Semáforo de compra e venda por empresa</div><div class=ln>MM 200, RSI, máximas; detalhes ao clicar</div></a>")
            continue
        if chaves == "momento_cripto":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>Semáforo de compra e venda por criptoativo</div><div class=ln>Técnica, on-chain, derivativos e sentimento</div></a>")
            continue
        if chaves == "baleias":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>Grandes carteiras da Hyperliquid em tempo real</div><div class=ln>Mapa de liquidação, heatmap, posições e movimentações</div></a>")
            continue
        if chaves == "operacoes":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>O que as baleias abriram e fecharam agora</div><div class=ln>Feed com filtros e fluxo da última hora</div></a>")
            continue
        if chaves == "carteiras":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>Carteiras vencedoras da Hyperliquid</div><div class=ln>Taxa de acerto, fator de lucro e posição atual</div></a>")
            continue
        if chaves == "tradefi":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>Baleias de ações, índices e commodities</div><div class=ln>Ordenadas por lucro, com mapa de liquidação</div></a>")
            continue
        if chaves == "trades":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>Day trade e swing curto: trocar um ativo por outro</div><div class=ln>Confluência de indicadores, nota de 0 a 10 em estrelas</div></a>")
            continue
        if chaves == "graficos":
            h.append(f"<a class=tile href='{arq}'><div class=tt>{titulo}<span>→</span></div><div class=ln>TradingView: gráficos interativos com RSI</div><div class=ln>Cripto, B3, EUA, dólar, ouro e petróleo</div></a>")
            continue
        sel = [x for x in secoes if chaves is None or x[5] in chaves]
        L, os_, ob, mv = agrega(sel)
        big = " big" if chaves is None else ""
        top = f"{limpo(mv[-1])} {pc(mv[-1]['dia'])}" if mv else "–"
        bot = f"{limpo(mv[0])} {pc(mv[0]['dia'])}" if mv else "–"
        h.append(f"<a class='tile{big}' href='{arq}'><div class=tt>{titulo}<span>→</span></div>"
                 f"<div class=ln>{len(L)} ativos · {len(os_)} em sobrevenda · {len(ob)} em sobrecompra</div>"
                 f"<div class=ln>Maior alta: {top}</div><div class=ln>Maior queda: {bot}</div></a>")
    h.append(f"</div></main><script>{JS}</script></body></html>")
    return "".join(h)


SIMBOLOS = [("Cripto", [("BTC", "BINANCE:BTCUSDT"), ("ETH", "BINANCE:ETHUSDT"), ("SOL", "BINANCE:SOLUSDT"), ("AAVE", "BINANCE:AAVEUSDT"), ("UNI", "BINANCE:UNIUSDT"), ("PENDLE", "BINANCE:PENDLEUSDT")]),
            ("Brasil", [("IBOV", "BMFBOVESPA:IBOV"), ("PETR4", "BMFBOVESPA:PETR4"), ("VALE3", "BMFBOVESPA:VALE3"), ("ITUB4", "BMFBOVESPA:ITUB4"), ("BBAS3", "BMFBOVESPA:BBAS3"), ("MGLU3", "BMFBOVESPA:MGLU3"), ("MRVE3", "BMFBOVESPA:MRVE3"), ("ANTH34", "BMFBOVESPA:ANTH34")]),
            ("EUA", [("S&P 500", "AMEX:SPY"), ("Nasdaq", "NASDAQ:QQQ"), ("NVDA", "NASDAQ:NVDA"), ("AMD", "NASDAQ:AMD"), ("MSFT", "NASDAQ:MSFT"), ("AMZN", "NASDAQ:AMZN"), ("ANT", "NASDAQ:ANT"), ("EWZ", "AMEX:EWZ")]),
            ("Outros", [("Dólar/Real", "FX_IDC:USDBRL"), ("DXY", "TVC:DXY"), ("Ouro", "TVC:GOLD"), ("Brent", "TVC:UKOIL"), ("US 10 anos", "TVC:US10Y")])]

GJS = """
(function(){
var dark=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches,SS=window.localStorage;
function get(k){try{return SS.getItem(k)}catch(e){return null}}function put(k,v){try{SS.setItem(k,v)}catch(e){}}
function chart(sym){put('gsym',sym);var w=document.getElementById('tvc');w.innerHTML='';var c=document.createElement('div');c.className='tradingview-widget-container';c.style.cssText='height:100%;width:100%';
 var d=document.createElement('div');d.className='tradingview-widget-container__widget';d.style.cssText='height:100%;width:100%';c.appendChild(d);
 var s=document.createElement('script');s.src='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';s.async=true;
 s.text=JSON.stringify({autosize:true,symbol:sym,interval:'60',timezone:'America/Sao_Paulo',theme:dark?'dark':'light',style:'1',locale:'br',allow_symbol_change:true,withdateranges:true,hide_side_toolbar:false,save_image:false,studies:['RSI@tv-basicstudies']});
 c.appendChild(s);w.appendChild(c);
 setTimeout(function(){if(!w.querySelector('iframe')){w.innerHTML='<iframe style="width:100%;height:100%;border:0" src="https://s.tradingview.com/widgetembed/?symbol='+encodeURIComponent(sym)+'&interval=60&hidesidetoolbar=0&symboledit=1&saveimage=0&studies=RSI%40tv-basicstudies&theme='+(dark?'dark':'light')+'&style=1&timezone=America%2FSao_Paulo&locale=br"></iframe>'}},4000);
 document.querySelectorAll('.sy button').forEach(function(b){b.classList.toggle('on',b.dataset.s==sym)})}
document.querySelectorAll('.sy button').forEach(function(b){b.onclick=function(){chart(b.dataset.s)}});
var f=document.getElementById('qs');if(f)f.addEventListener('keydown',function(e){if(e.key=='Enter'&&f.value.trim())chart(f.value.trim().toUpperCase())});
var t0=document.getElementById('tvt');if(t0){var t=document.createElement('div');t.className='tradingview-widget-container';var dd=document.createElement('div');dd.className='tradingview-widget-container__widget';t.appendChild(dd);t0.appendChild(t);var s=document.createElement('script');s.src='https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js';s.async=true;
 s.text=JSON.stringify({symbols:[{proName:'BINANCE:BTCUSDT',title:'BTC'},{proName:'BINANCE:ETHUSDT',title:'ETH'},{proName:'BMFBOVESPA:IBOV',title:'Ibovespa'},{proName:'AMEX:SPY',title:'S&P 500'},{proName:'NASDAQ:QQQ',title:'Nasdaq'},{proName:'FX_IDC:USDBRL',title:'USD/BRL'},{proName:'TVC:DXY',title:'DXY'},{proName:'TVC:GOLD',title:'Ouro'}],showSymbolLogo:true,colorTheme:dark?'dark':'light',isTransparent:true,displayMode:'adaptive',locale:'br'});t.appendChild(s)}
chart(get('gsym')||'BINANCE:BTCUSDT');
if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js').catch(function(){})}
})();
"""


def graficos(arq, titulo, paginas):
    h = [cabeca(titulo, paginas, arq).replace("<meta http-equiv=refresh content=330>", ""), f"<h1>{titulo}</h1><p class=sub>Gráficos do TradingView com RSI. Cripto e EUA em tempo quase real; ações da B3 com 15 minutos de atraso. Escolha um ativo ou digite um símbolo (ex.: NASDAQ:NVDA) e tecle Enter.</p>",
         "<div class=tvt id=tvt></div><div class=bar><input id=qs placeholder='Símbolo TradingView, ex.: BMFBOVESPA:PETR4'></div>"]
    for grupo, L in SIMBOLOS:
        h.append(f"<div class=sy><span class=mu style='align-self:center;min-width:60px'>{grupo}</span>" + "".join(f"<button data-s='{s}'>{H.escape(n)}</button>" for n, s in L) + "</div>")
    h.append(f"<div class=tvw id=tvc></div></main><script>{GJS}</script></body></html>")
    return "".join(h)
