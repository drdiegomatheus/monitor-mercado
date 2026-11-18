"""Aba Mapa: mapa de calor (treemap) com a variação das ações da B3 e dos BDRs em R$.
Tamanho do quadrado = valor de mercado; cor = variação no período. Tudo calculado no navegador."""
import json
import html as H
import datetime as dt
import os
import statistics
import pandas as pd
import ui

CSS = """
.mp-bar{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;margin:0 0 12px}.mp-bar .g{display:flex;gap:4px;align-items:center;flex-wrap:wrap}.mp-bar small{color:var(--mu);font-weight:700;margin-right:2px}
.mp-bar button{border:1px solid var(--line);background:var(--card);color:var(--tx);border-radius:999px;padding:5px 12px;font-weight:700;font-size:12.5px;cursor:pointer}.mp-bar button.on{background:var(--ac);color:#fff;border-color:var(--ac)}
.mp-sum{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px;font-size:12.5px}.mp-sum .c{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:4px 9px}.mp-sum b.u{color:var(--gr)}.mp-sum b.d{color:var(--rd)}
#mpmap{position:relative;width:100%;border-radius:14px;overflow:hidden;background:var(--card2);border:1px solid var(--line)}
.mp-s{position:absolute;box-sizing:border-box;border:2px solid var(--bg);border-radius:6px;overflow:hidden}
.mp-sl{position:absolute;left:0;right:0;top:0;height:16px;padding:1px 5px;font-size:10.5px;font-weight:800;letter-spacing:.02em;text-transform:uppercase;color:var(--mu);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;background:color-mix(in srgb,var(--card) 70%,transparent)}
.mp-c{position:absolute;box-sizing:border-box;border:1px solid rgba(0,0,0,.28);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;overflow:hidden;line-height:1.15;cursor:default;color:#fff}
.mp-c.lt{color:#0b1b10}.mp-c b{font-weight:800;letter-spacing:-.01em}.mp-c i{font-style:normal;font-weight:700}.mp-c u{text-decoration:none;opacity:.85;font-size:.78em}
.mp-leg{display:flex;align-items:center;gap:0;margin:12px 0 0;font-size:11.5px;color:var(--mu)}.mp-leg span{flex:1;text-align:center;padding:4px 0;font-weight:700;color:#fff;max-width:90px}.mp-leg em{padding:0 8px;font-style:normal}
"""

JS = r"""
function st(k,v){try{if(v===undefined)return localStorage.getItem(k);localStorage.setItem(k,v)}catch(e){return null}}
var PER={d:{l:'Dia',k:1,u:3},w:{l:'5 dias',k:5,u:6},m:{l:'1 mês',k:21,u:12},q:{l:'3 meses',k:63,u:22},y:{l:'No ano',k:0,u:45}};
var MAP=st('mpmap')||'br',PR=st('mpper')||'d',SZ=st('mpsz')||'eq';if(!MD[MAP])MAP='br';if(!PER[PR])PR='d';
function f2(v,d){return (v==null||v!==v)?'–':v.toLocaleString('pt-BR',{minimumFractionDigits:d==null?2:d,maximumFractionDigits:d==null?2:d})}
function pc(v){return(v>=0?'+':'−')+f2(Math.abs(v))+'%'}
function chg(a){var c=a.dc,n=c.length,k=PER[PR].k,i;if(PR=='y'){var y=new Date(a.dt[n-1]*864e5).getUTCFullYear();i=-1;for(var j=0;j<n;j++){if(new Date(a.dt[j]*864e5).getUTCFullYear()<y)i=j}if(i<0)return null}else{i=n-1-k;if(i<0)return null}return(c[n-1]/c[i]-1)*100}
var COR=[['#8b1d1d','#fff'],['#c0392b','#fff'],['#f1a9a0','#3b0b0b'],['#6b7280','#fff'],['#9fd9b0','#0b2415'],['#2f9e5a','#fff'],['#14703a','#fff']];
function cor(p){var r=p/PER[PR].u,s=r<0?-1:1,a=Math.abs(r);if(a<.12)return COR[3];var l=a<.4?1:a<.75?2:3;return s>0?COR[3+l]:COR[3-l]}
function squar(items,x,y,w,h){var out=[],tot=items.reduce(function(s,i){return s+i.v},0);if(tot<=0||w<=0||h<=0)return out;var sc=w*h/tot,L=items.map(function(i){return{i:i,a:i.v*sc}}).sort(function(a,b){return b.a-a.a});
 function worst(r,s){var sum=r.reduce(function(t,q){return t+q.a},0),mx=Math.max.apply(null,r.map(function(q){return q.a})),mn=Math.min.apply(null,r.map(function(q){return q.a}));return Math.max(s*s*mx/(sum*sum),sum*sum/(s*s*mn))}
 while(L.length){var s=Math.min(w,h),row=[L.shift()];while(L.length&&worst(row.concat([L[0]]),s)<=worst(row,s))row.push(L.shift());
  var sum=row.reduce(function(t,q){return t+q.a},0);if(w>=h){var rw=sum/h,yy=y;row.forEach(function(q){var hh=q.a/rw;out.push({i:q.i,x:x,y:yy,w:rw,h:hh});yy+=hh});x+=rw;w-=rw}else{var rh=sum/w,xx=x;row.forEach(function(q){var ww=q.a/rh;out.push({i:q.i,x:xx,y:y,w:ww,h:rh});xx+=ww});y+=rh;h-=rh}}
 return out}
function draw(){var D=MD[MAP],el=document.getElementById('mpmap'),W=el.clientWidth,H=Math.max(520,Math.min(820,Math.round(W*.62)));if(W<500)H=Math.round(W*1.35);el.style.height=H+'px';
 var items=[],sec={};D.a.forEach(function(a){var p=chg(a);if(p==null)return;var it={a:a,p:p,v:SZ=='cap'?a.cap:1};items.push(it);var s=sec[a.s]=sec[a.s]||{n:a.s,v:0,it:[],w:0,pw:0};s.v+=it.v;s.it.push(it);s.pw+=p*it.v;s.w+=it.v});
 var S=Object.keys(sec).map(function(k){return sec[k]}),o='';
 squar(S,0,0,W,H).forEach(function(r){var s=r.i,lab=r.h>34&&r.w>60,top=lab?16:0,sp=s.pw/s.w;
  o+='<div class=mp-s style="left:'+r.x+'px;top:'+r.y+'px;width:'+r.w+'px;height:'+r.h+'px">'+(lab?'<div class=mp-sl>'+s.n+' · '+pc(sp)+'</div>':'');
  squar(s.it,0,top,r.w-4,r.h-4-top).forEach(function(c){var a=c.i.a,cc=cor(c.i.p),m=Math.min(c.w,c.h),fs=Math.min(26,m/3.4,c.w/(Math.max(a.n.length,6)*.8)),show=fs>=7.5&&c.h>fs*2.3,pr=c.h>fs*4.3&&c.w>fs*7;
   o+='<div class="mp-c" style="left:'+c.x+'px;top:'+c.y+'px;width:'+c.w+'px;height:'+c.h+'px;background:'+cc[0]+';color:'+cc[1]+';font-size:'+fs+'px" title="'+a.n+' · '+a.s+' · R$ '+f2(a.dc[a.dc.length-1])+' · '+PER[PR].l+' '+pc(c.i.p)+'">'+(show?'<b>'+a.n+'</b><i>'+pc(c.i.p)+'</i>'+(pr?'<u>R$ '+f2(a.dc[a.dc.length-1])+'</u>':''):'')+'</div>'});
  o+='</div>'});
 el.innerHTML=o;
 var up=items.filter(function(i){return i.p>0.005}).length,dn=items.filter(function(i){return i.p<-0.005}).length,tw=0,tp=0;items.forEach(function(i){var w=SZ=='cap'?i.a.cap:1;tw+=w;tp+=i.p*w});
 var srt=items.slice().sort(function(a,b){return b.p-a.p});function chips(l,cl){return l.map(function(i){return'<span class=c><b>'+i.a.n+'</b> <b class='+cl+'>'+pc(i.p)+'</b></span>'}).join('')}
 document.getElementById('mpsum').innerHTML='<span class=c>▲ <b class=u>'+up+'</b> · ▼ <b class=d>'+dn+'</b></span><span class=c>Média '+(SZ=='cap'?'ponderada ':'')+'<b class='+(tp>=0?'u':'d')+'>'+pc(tp/tw)+'</b></span>'+chips(srt.slice(0,4),'u')+chips(srt.slice(-4).reverse(),'d');
 var u=PER[PR].u,lg=[-u,-u*.75,-u*.4,0,u*.4,u*.75,u];document.getElementById('mpleg').innerHTML=COR.map(function(c,i){return'<span style="background:'+c[0]+';color:'+c[1]+'">'+(i==3?'0':(lg[i]>0?'+':'−')+Math.abs(Math.round(lg[i]*10)/10)+'%')+'</span>'}).join('');
 document.getElementById('mpdate').textContent=ULT[MAP]}
function bar(){var h='<div class=g><small>Mapa</small>'+Object.keys(MD).map(function(k){return'<button data-k=map data-v='+k+' class="'+(k==MAP?'on':'')+'">'+MD[k].t+'</button>'}).join('')+'</div>';
 h+='<div class=g><small>Período</small>'+Object.keys(PER).map(function(k){return'<button data-k=per data-v='+k+' class="'+(k==PR?'on':'')+'">'+PER[k].l+'</button>'}).join('')+'</div>';
 h+='<div class=g><small>Tamanho</small><button data-k=sz data-v=eq class="'+(SZ=='eq'?'on':'')+'">Igual</button><button data-k=sz data-v=cap class="'+(SZ=='cap'?'on':'')+'">Valor de mercado</button></div>';
 var b=document.getElementById('mpbar');b.innerHTML=h;b.querySelectorAll('button').forEach(function(x){x.onclick=function(){var k=x.dataset.k,v=x.dataset.v;if(k=='map'){MAP=v;st('mpmap',v)}else if(k=='per'){PR=v;st('mpper',v)}else{SZ=v;st('mpsz',v)}bar();draw()}})}
bar();draw();var rt;window.addEventListener('resize',function(){clearTimeout(rt);rt=setTimeout(draw,120)});
"""


def _cap(pasta):
    f = os.path.join(pasta, "mercado.json")
    try: return {k: float(v) for k, v in json.load(open(f)).items()}
    except Exception: return {}


def dados(raiz):
    cats = os.path.join(raiz, "categorias")
    cb = json.load(open(os.path.join(cats, "brasil", "config.json"), encoding="utf-8"))
    cp = json.load(open(os.path.join(cats, "pares", "config.json"), encoding="utf-8"))
    capb, cape = _cap(os.path.join(cats, "brasil")), _cap(os.path.join(cats, "eua"))
    try:
        fx = float(pd.read_csv(os.path.join(cats, "macro", "dados", "USDBRL_1D.csv")).dropna()["close"].iloc[-1])
    except Exception:
        fx = 5.5

    def serie(cat, n):
        f = os.path.join(cats, cat, "dados", f"{n}_1D.csv")
        if not os.path.exists(f): return None
        d = pd.read_csv(f).dropna().tail(300)
        if len(d) < 6: return None
        return [int(t) // 86400 for t in d["time"]], [round(float(x), 4) for x in d["close"]]

    mapas = {"br": {"t": "Brasil (B3)", "a": []}, "bdr": {"t": "BDRs em R$", "a": []}}
    pend = {"br": [], "bdr": []}
    for n, a in cb["ativos"].items():
        s = serie("brasil", n)
        if s: pend["br"].append((n, a.get("setor", ""), s, capb.get(n)))
    for n, a in cp["ativos"].items():
        s = serie("pares", n)
        if not s: continue
        setor = a.get("setor", "")
        sub, _, und = setor.partition(" · ")
        cap = None
        if und:
            for k in (und, und.replace(".", "-"), und.replace("-", ".")):
                if k in cape: cap = cape[k] * fx; break
        pend["bdr"].append((n, sub, s, cap))
    for m, L in pend.items():
        conhecidos = [c for *_, c in L if c]
        fb = (statistics.median(conhecidos) * .15) if conhecidos else 1e9
        for n, setor, (dts, cls), cap in L:
            mapas[m]["a"].append({"n": n, "s": setor, "cap": round(cap or fb), "dt": dts, "dc": cls})
    return mapas


def pagina(arq, titulo, paginas, mapas):
    agora = dt.datetime.now(ui.BRT)
    ult = {}
    for k, m in mapas.items():
        d = max((a["dt"][-1] for a in m["a"]), default=None)
        ult[k] = "último pregão: " + (dt.datetime(1970, 1, 1) + dt.timedelta(days=d)).strftime("%d/%m/%Y") if d else ""
    h = [ui.cabeca(titulo, paginas, arq), f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>",
         f"<p class=sub>Cada quadrado é um ativo, agrupado por setor, e a cor é a variação no período (todos do mesmo tamanho; se quiser, dá para trocar para valor de mercado). Nos BDRs, o preço e a variação são em R$ (já incluem o dólar). Atualizado em {agora:%d/%m %H:%M} · <span id=mpdate></span></p>",
         "<div class=mp-bar id=mpbar></div><div class=mp-sum id=mpsum></div><div id=mpmap></div><div class=mp-leg><em>Queda</em><div style='display:flex;flex:1;justify-content:center' id=mpleg></div><em>Alta</em></div>",
         "<details style='margin-top:14px'><summary>Como ler</summary><p>Os quadrados ficam agrupados por setor e o setor mostra a variação média ponderada pelo valor de mercado. Verde = alta, vermelho = queda; quanto mais escuro, maior o movimento (a escala muda com o período). "
         "Nos BDRs o tamanho usa o valor de mercado da empresa nos EUA convertido para R$; ETFs sem valor de mercado aparecem pequenos. Passe o mouse (ou toque) num quadrado para ver o setor, o preço e a variação. O botão Tamanho alterna entre todos iguais e proporcional ao valor de mercado.</p></details>",
         "</main><script>var MD=" + json.dumps(mapas, separators=(",", ":"), ensure_ascii=False) + ";var ULT=" + json.dumps(ult, ensure_ascii=False) + ";" + JS + "</script></body></html>"]
    return "".join(h)
