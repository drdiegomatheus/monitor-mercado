"""Aba Trades: ranking de trocas (day trade / swing curto) por confluência de sobrecomprado x sobrevendido.
O Python calcula os indicadores de cada ativo (candles de 30 min e diário); o navegador monta o ranking e as estrelas."""
import json
import html as H
import datetime as dt
import os
import numpy as np
import pandas as pd
import ui

CSS = """
.tr-top{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;margin:0 0 12px}.tr-top .g{display:flex;gap:4px;align-items:center;flex-wrap:wrap}.tr-top small{color:var(--mu);font-weight:700;margin-right:2px}
.tr-top button,.tr-chip{border:1px solid var(--line);background:var(--card);color:var(--tx);border-radius:999px;padding:5px 12px;font-weight:700;font-size:12.5px;cursor:pointer}.tr-top button.on,.tr-chip.on{background:var(--ac);color:#fff;border-color:var(--ac)}
.tr-chip i{font-style:normal;opacity:.6;margin-left:6px;font-weight:400}
.tr-in{border:1px solid var(--line);background:var(--card);color:var(--tx);border-radius:999px;padding:6px 12px;font-size:13px;min-width:190px}
.tr-warn{background:color-mix(in srgb,#f59e0b 18%,var(--card));border:1px solid #f59e0b;border-radius:10px;padding:8px 12px;margin:0 0 12px;font-size:13px}
.tr-held{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin:0 0 14px}
.tr-held h3{margin:0 0 6px;font-size:16px}.tr-held .row{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px}.tr-held .row span{white-space:nowrap}
.tr-card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:11px 14px;margin:0 0 10px}.tr-card.late{opacity:.5;filter:grayscale(.7)}
.tr-hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.tr-hd b.n{font-size:16px}.tr-tag{font-size:10.5px;font-weight:800;border-radius:6px;padding:1px 6px;background:var(--card2);color:var(--mu);text-transform:uppercase}
.tr-sc{margin-left:auto;text-align:right;line-height:1.1}.tr-sc b{font-size:22px}.tr-sc .st{font-size:15px;letter-spacing:1px}
.tr-gr{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:6px;margin-top:8px}
.tr-it{background:var(--card2);border-radius:9px;padding:5px 8px;font-size:12px}.tr-it small{display:block;color:var(--mu);font-size:10.5px;font-weight:700}.tr-it .s{letter-spacing:1px;font-size:13px}.tr-it .v{display:block;color:var(--tx);font-variant-numeric:tabular-nums}
.hf{background:linear-gradient(90deg,currentColor 50%,rgba(150,150,150,.45) 50%);-webkit-background-clip:text;background-clip:text;color:transparent}.tr-g{color:#16a34a}.tr-y{color:#eab308}.tr-r{color:#dc2626}.tr-m{color:var(--mu)}
.tr-obs{margin-top:7px;font-size:12px;color:var(--mu)}.tr-obs b{color:var(--tx)}
.tr-w{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin:0 0 12px}.tr-w label{display:inline-flex;align-items:center;gap:6px;margin:3px 14px 3px 0;font-size:12.5px}.tr-w input{width:46px}
"""

JS = r"""
function st(k,v){try{if(v===undefined)return localStorage.getItem(k);localStorage.setItem(k,v)}catch(e){return null}}
function f1(v,d){return(v==null||v!==v)?'–':v.toLocaleString('pt-BR',{minimumFractionDigits:d==null?1:d,maximumFractionDigits:d==null?1:d})}
function sg(v,d){return(v>=0?'+':'−')+f1(Math.abs(v),d)}
var A={};D.a.forEach(function(a){A[a.n]=a});
var NOMES=Object.keys(A).sort();
var CMP=[
 {k:'r30',l:'RSI 30 min',x:function(a){return a.r30==null?null:(a.r30-50)/25},v:function(h,c){return f1(h.r30,0)+' → '+f1(c.r30,0)}},
 {k:'r60',l:'RSI 1 hora',x:function(a){return a.r60==null?null:(a.r60-50)/25},v:function(h,c){return f1(h.r60,0)+' → '+f1(c.r60,0)}},
 {k:'rd',l:'RSI diário',x:function(a){return a.rd==null?null:(a.rd-50)/25},v:function(h,c){return f1(h.rd,0)+' → '+f1(c.rd,0)}},
 {k:'ema',l:'Distância da MM20 (30 min)',x:function(a){return a.ea==null?null:a.ea/3},v:function(h,c){return sg(h.ea)+' → '+sg(c.ea)+' ATR'}},
 {k:'bb',l:'Banda de Bollinger (%B)',x:function(a){return a.bb==null?null:(a.bb-.5)/.5},v:function(h,c){return f1(h.bb,2)+' → '+f1(c.bb,2)}},
 {k:'dz',l:'Movimento do dia',x:function(a){return a.dz==null?null:a.dz/2.5},v:function(h,c){return sg(h.dp)+'% ('+sg(h.dz)+'σ) → '+sg(c.dp)+'% ('+sg(c.dz)+'σ)'}},
 {k:'ctx',l:'Força vs. mercado',x:function(a){return a.rel==null?null:a.rel/3},v:function(h,c){return sg(h.rel)+' → '+sg(c.rel)+' pp'}},
 {k:'rv',l:'Volume relativo',x:null,v:function(h,c){return(h.rv==null?'–':f1(h.rv,1)+'x')+' / '+(c.rv==null?'–':f1(c.rv,1)+'x')}}
];
var W0={day:{r30:3,r60:1.5,rd:.5,ema:2.5,bb:1.5,dz:2,ctx:1.5,rv:1,tp:.12},swing:{r30:1,r60:2.5,rd:2.5,ema:1.5,bb:1,dz:1.5,ctx:1.5,rv:.5,tp:.25}};
var W;try{W=JSON.parse(st('trw')||'null')}catch(e){W=null}if(!W)W=JSON.parse(JSON.stringify(W0));
var MODE=st('trmode')||'day',GR=JSON.parse(st('trgr')||'{"B3":1,"BDR":1,"EUA":1}'),HELD=[],SEL=st('trsel')||'',MORE=0;
try{HELD=JSON.parse(st('trheld')||'[]')}catch(e){}HELD=HELD.filter(function(n){return A[n]});
if(!HELD.length)HELD=['M2ST34','MRVE3','NVDC34'].filter(function(n){return A[n]});
if(!A[SEL])SEL=HELD[0]||'';
function brt(){var p=new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',hour:'2-digit',minute:'2-digit',weekday:'short',hour12:false}).formatToParts(new Date()),o={};p.forEach(function(x){o[x.type]=x.value});return{h:+o.hour%24,m:+o.minute,wd:o.weekday}}
function stars(p){var n=Math.round(Math.max(0,Math.min(1,p))*10)/2,o='';for(var i=1;i<=5;i++)o+=n>=i?'★':(n>=i-.5?'<span class=hf>★</span>':'☆');return o}
function scl(p){return p>=.6?'tr-g':(p>=.3?'tr-y':'tr-r')}
function pair(h,c){var w=W[MODE],tot=0,sw=0,items=[];
 CMP.forEach(function(m){var p=null,ww=w[m.k]||0;
  if(m.k=='rv'){var r=[h.rv,c.rv].filter(function(x){return x!=null});if(r.length){var avg=r.reduce(function(a,b){return a+b},0)/r.length;p=Math.max(0,Math.min(1,(avg-.7)/1.3))}}
  else{var xh=m.x(h),xc=m.x(c);if(xh!=null&&xc!=null)p=Math.max(0,Math.min(1,(Math.max(-1,Math.min(1,xh))-Math.max(-1,Math.min(1,xc)))/1.6))}
  items.push({m:m,p:p});if(p!=null){tot+=ww*p;sw+=ww}});
 var base=sw?tot/sw:0,pen=0,notes=[];
 if(h.tr>0){pen+=w.tp;notes.push('<span class=tr-y>⚠ '+h.n+' em tendência de alta (vender contra a tendência)</span>')}else if(h.tr<0)notes.push('<span class=tr-g>✓ '+h.n+' em tendência de baixa</span>');
 if(c.tr<0){pen+=w.tp;notes.push('<span class=tr-y>⚠ '+c.n+' em tendência de baixa (faca caindo)</span>')}else if(c.tr>0)notes.push('<span class=tr-g>✓ '+c.n+' em tendência de alta</span>');
 return{s:Math.max(0,base*(1-pen))*10,items:items,notes:notes}}
function cutoff(h,c,b){var now=b.h*60+b.m,lim=(h.g=='EUA'&&c.g=='EUA')?16*60+30:15*60+30;return now>=lim}
function ev(a){return a.ev?'<span class=tr-y>📅 resultado '+a.ev+'</span>':''}
function heldCard(a){var r=['RSI 30m <b>'+f1(a.r30,0)+'</b>','1h <b>'+f1(a.r60,0)+'</b>','diário <b>'+f1(a.rd,0)+'</b>','MM20 <b>'+sg(a.ea)+' ATR</b> ('+sg(a.ep)+'%)','%B <b>'+f1(a.bb,2)+'</b>','dia <b>'+sg(a.dp)+'%</b> ('+sg(a.dz)+'σ)','vol. rel. <b>'+(a.rv==null?'–':f1(a.rv,1)+'x')+'</b>','tendência <b>'+(a.tr>0?'▲ alta':a.tr<0?'▼ baixa':'lateral')+'</b>','mercado ('+a.cx+') RSI <b>'+f1(a.cr,0)+'</b>, dia <b>'+sg(a.cd)+'%</b>'];
 return'<div class=tr-held><h3>'+a.n+' <span class=tr-tag>'+a.g+'</span> <span class=tr-m style="font-weight:400;font-size:13px">'+a.s+' · '+a.cu+' '+f1(a.p,2)+'</span></h3><div class=row>'+r.map(function(x){return'<span>'+x+'</span>'}).join('')+ev(a)+'</div></div>'}
function render(){
 var b=brt(),h=A[SEL],o='';
 var tp=Object.keys(GR).filter(function(k){return GR[k]});
 var top='<div class=g><small>Tenho</small>'+HELD.map(function(n){return'<span class="tr-chip'+(n==SEL?' on':'')+'" data-a=sel data-v='+n+'>'+n+'<i data-a=del data-v='+n+'>✕</i></span>'}).join('')+'<input class=tr-in id=trin list=trdl placeholder="adicionar ativo…"><datalist id=trdl>'+NOMES.map(function(n){return'<option value='+n+'>'}).join('')+'</datalist></div>';
 top+='<div class=g><small>Modo</small><button data-a=mode data-v=day class="'+(MODE=='day'?'on':'')+'">Day trade</button><button data-a=mode data-v=swing class="'+(MODE=='swing'?'on':'')+'">Swing curto</button><button data-a=wt>Pesos</button></div>';
 top+='<div class=g><small>Trocar por</small>'+['B3','BDR','EUA'].map(function(k){return'<button data-a=gr data-v='+k+' class="'+(GR[k]?'on':'')+'">'+k+'</button>'}).join('')+'</div>';
 document.getElementById('trtop').innerHTML=top;
 var wp=document.getElementById('trw');if(wp.dataset.open=='1'){wp.innerHTML='<b>Pesos — '+(MODE=='day'?'Day trade':'Swing curto')+'</b> (0 ignora o indicador) <br>'+CMP.map(function(m){return'<label>'+m.l+' <input type=number step=.5 min=0 max=10 data-a=w data-v='+m.k+' value='+W[MODE][m.k]+'></label>'}).join('')+'<label>Penalidade de tendência <input type=number step=.05 min=0 max=1 data-a=w data-v=tp value='+W[MODE].tp+'></label> <button data-a=wr>Restaurar padrão</button>';wp.style.display='block'}else wp.style.display='none';
 var nowS=Date.now()/1000;function old(a){return nowS-a.t>45*60}
 function hhmm(a){var d=new Date(a.t*1000-3*36e5);function z(x){return(x<10?'0':'')+x}return z(d.getUTCDate())+'/'+z(d.getUTCMonth()+1)+' '+z(d.getUTCHours())+':'+z(d.getUTCMinutes())}
 if(h&&old(h))o+='<div class=tr-warn>Mercado de '+h.n+' provavelmente fechado: indicadores com candles até <b>'+hhmm(h)+'</b> (Brasília). O filtro de horário fica desligado.</div>';
 if(!h){document.getElementById('trbody').innerHTML=o+'<p class=sub>Adicione o ativo que você tem na caixa acima.</p>';return}
 o+=heldCard(h);
 if(h.r30!=null&&h.r30<35&&(h.r60==null||h.r60<40))o+='<div class=tr-warn>'+h.n+' está <b>sobrevendido</b> (RSI 30m '+f1(h.r30,0)+'): vender agora é ir contra o movimento esticado. As notas abaixo tendem a ser baixas; a leitura útil aqui é o contrário (esperar repique ou ver outros esticados para cima).</div>';
 var L=[];NOMES.forEach(function(n){var c=A[n];if(n==SEL||!GR[c.g]||c.u==h.u||c.r30==null||h.r30==null)return;var r=pair(h,c);L.push({c:c,r:r,late:!old(h)&&!old(c)&&cutoff(h,c,b)})});
 L.sort(function(a,b){return b.r.s-a.r.s});
 var lim=MORE?40:12;
 L.slice(0,lim).forEach(function(x){var c=x.c,s=x.r.s,cl=s>=7?'tr-g':s>=5?'tr-y':'tr-m';
  o+='<div class="tr-card'+(x.late?' late':'')+'"><div class=tr-hd><b class=n>'+h.n+' → '+c.n+'</b><span class=tr-tag>'+c.g+'</span><span class=tr-m style="font-size:12px">'+c.s+' · '+c.cu+' '+f1(c.p,2)+'</span>'+ev(c)+'<div class=tr-sc><b class='+cl+'>'+f1(s,1)+'<small class=tr-m style="font-size:12px">/10</small></b><div class="st '+cl+'">'+stars(s/10)+'</div></div></div>'
   +'<div class=tr-gr>'+x.r.items.map(function(i){return'<div class=tr-it><small>'+i.m.l+'</small>'+(i.p==null?'<span class=tr-m>sem dados</span>':'<span class="s '+scl(i.p)+'">'+stars(i.p)+'</span>')+'<span class=v>'+i.m.v(h,c)+'</span></div>'}).join('')+'</div>'
   +'<div class=tr-obs>'+(old(c)?'<span class=tr-y>dados do '+c.n+' até '+hhmm(c)+'</span> · ':'')+x.r.notes.join(' · ')+(x.r.notes.length?' · ':'')+'mercado: '+h.cx+' RSI '+f1(h.cr,0)+' / '+c.cx+' RSI '+f1(c.cr,0)+(x.late?' · <b>⏰ tarde para voltar no mesmo dia</b>':'')+'</div></div>'});
 if(L.length&&L[0].r.s<5)o+='<p class=sub>Nenhuma troca com confluência forte agora (melhor nota '+f1(L[0].r.s,1)+').</p>';
 if(L.length>lim)o+='<button class=tr-chip data-a=more>Ver mais</button>';
 if(!L.length)o+='<p class=sub>Nenhum candidato com dados nos grupos escolhidos.</p>';
 document.getElementById('trbody').innerHTML=o}
document.addEventListener('click',function(e){var t=e.target.closest('[data-a]');if(!t)return;var a=t.dataset.a,v=t.dataset.v;
 if(a=='sel'){SEL=v;st('trsel',v)}else if(a=='del'){HELD=HELD.filter(function(n){return n!=v});st('trheld',JSON.stringify(HELD));if(SEL==v)SEL=HELD[0]||'';e.stopPropagation()}
 else if(a=='mode'){MODE=v;st('trmode',v)}else if(a=='gr'){GR[v]=GR[v]?0:1;st('trgr',JSON.stringify(GR))}
 else if(a=='wt'){var w=document.getElementById('trw');w.dataset.open=w.dataset.open=='1'?'0':'1'}
 else if(a=='wr'){W[MODE]=JSON.parse(JSON.stringify(W0[MODE]));st('trw',JSON.stringify(W))}
 else if(a=='more')MORE=1;else return;render()});
document.addEventListener('change',function(e){var t=e.target;if(t.id=='trin'){var n=t.value.trim().toUpperCase();if(A[n]){if(HELD.indexOf(n)<0)HELD.push(n);SEL=n;st('trheld',JSON.stringify(HELD));st('trsel',n)}t.value='';render()}
 else if(t.dataset.a=='w'){W[MODE][t.dataset.v]=Math.max(0,+t.value||0);st('trw',JSON.stringify(W));render()}});
render();
"""


def _rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _ler(raiz, cat, nome, suf):
    f = os.path.join(raiz, "categorias", cat, "dados", f"{nome}_{suf}.csv")
    if not os.path.exists(f): return None
    d = pd.read_csv(f)
    if len(d) < 30: return None
    d.index = pd.to_datetime(d["time"], unit="s")
    return d


def _num(x, nd=2):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def feats(m, d):
    """indicadores de um ativo a partir dos candles de 30 min (m) e diários (d)"""
    c = m["close"]
    o = {}
    o["r30"] = _num(_rsi(c).iloc[-1], 1)
    h1 = c.resample("1h").last().dropna()
    o["r60"] = _num(_rsi(h1).iloc[-1], 1) if len(h1) > 30 else None
    o["rd"] = _num(_rsi(d["close"]).iloc[-1], 1) if d is not None and len(d) > 30 else None
    ema = c.ewm(span=20, adjust=False).mean()
    tr = pd.concat([m["high"] - m["low"], (m["high"] - c.shift()).abs(), (m["low"] - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    o["ep"] = _num((c.iloc[-1] / ema.iloc[-1] - 1) * 100)
    o["ea"] = _num((c.iloc[-1] - ema.iloc[-1]) / atr) if atr and atr > 0 else None
    mm, sd = c.rolling(20).mean().iloc[-1], c.rolling(20).std().iloc[-1]
    o["bb"] = _num((c.iloc[-1] - (mm - 2 * sd)) / (4 * sd)) if sd and sd > 0 else None
    dia = m.index.normalize()
    ult = dia[-1]
    ant = c[dia < ult]
    o["dp"] = _num((c.iloc[-1] / ant.iloc[-1] - 1) * 100) if len(ant) else None
    if d is not None and len(d) > 60:
        r = d["close"].pct_change().dropna().tail(60) * 100
        s = r.std()
        o["dz"] = _num(o["dp"] / s) if o["dp"] is not None and s > 0 else None
        s50, s20 = d["close"].rolling(50).mean(), d["close"].rolling(20).mean()
        up = d["close"].iloc[-1] > s50.iloc[-1] and s20.iloc[-1] > s20.iloc[-6]
        dn = d["close"].iloc[-1] < s50.iloc[-1] and s20.iloc[-1] < s20.iloc[-6]
        o["tr"] = 1 if up else (-1 if dn else 0)
    else:
        o["dz"], o["tr"] = None, 0
    # volume relativo: volume acumulado hoje até esta barra / média do mesmo ponto nos 20 dias anteriores
    o["rv"] = None
    if "volume" in m.columns and m["volume"].sum() > 0:
        g = m.groupby(dia)["volume"].apply(lambda x: x.cumsum().values)
        k = len(g.iloc[-1])
        prev = [v[k - 1] for v in g.iloc[:-1].tail(20) if len(v) >= k and v[k - 1] > 0]
        if len(prev) >= 5 and g.iloc[-1][-1] > 0:
            o["rv"] = _num(g.iloc[-1][-1] / np.mean(prev))
    o["p"] = _num(c.iloc[-1], 2)
    o["t"] = int(m["time"].iloc[-1])
    return o


def dados(raiz):
    cats = os.path.join(raiz, "categorias")
    cfg = {c: json.load(open(os.path.join(cats, c, "config.json"), encoding="utf-8")) for c in ("brasil", "eua", "pares")}
    # contexto de mercado: índice de referência de cada grupo
    ctx = {}
    for nome, cat, arq in [("BOVA11", "brasil", "BENCH_BOVA11"), ("Nasdaq", "eua", "BENCH_NASDAQ"), ("S&P 500", "eua", "BENCH_SP500"), ("Bitcoin", "cripto", "BTC")]:
        m = _ler(raiz, cat, arq, "30m")
        if m is not None:
            f = feats(m, None)
            ctx[nome] = {"r": f["r30"], "d": f["dp"] or 0.0}
            continue
        d = _ler(raiz, cat, arq, "1D")     # enquanto o 30 min do índice não existe: usa o diário
        if d is not None and len(d) > 20:
            ctx[nome] = {"r": _num(_rsi(d["close"]).iloc[-1], 1), "d": _num((d["close"].iloc[-1] / d["close"].iloc[-2] - 1) * 100) or 0.0}

    def ctx_de(und, grupo):
        if und == "MSTR": return "Bitcoin"
        return "Nasdaq" if grupo == "nasdaq" else "S&P 500"

    ev_us = {}
    for cat in ("brasil", "eua"):
        for arq in ("eventos.json", "resultados_manual.json"):
            f = os.path.join(cats, cat, arq)
            if os.path.exists(f):
                try: ev_us.update({k: v.lstrip("~") for k, v in json.load(open(f, encoding="utf-8")).items()})
                except Exception: pass
    hoje = dt.datetime.now(ui.BRT).date()

    def evento(n):
        v = ev_us.get(n)
        if not v: return None
        try: dd = (dt.date.fromisoformat(v[:10]) - hoje).days
        except Exception: return None
        return ("hoje" if dd == 0 else "amanhã") if dd in (0, 1) else None

    def und_bdr(bdr):
        for k, v in cfg["eua"]["ativos"].items():
            if isinstance(v, dict) and v.get("bdr") == bdr: return k, v
        return None, None

    out, tmax = [], 0
    def add(cat, n, v, g, setor, moeda, u, cx):
        nonlocal tmax
        m = _ler(raiz, cat, n, "30m")
        if m is None: return
        d = _ler(raiz, cat, n, "1D")
        f = feats(m, d)
        c = ctx.get(cx, {"r": None, "d": 0.0})
        f.update({"n": n, "g": g, "s": setor, "cu": moeda, "u": u, "cx": cx, "cr": c["r"], "cd": _num(c["d"]),
                  "rel": _num(f["dp"] - c["d"]) if f["dp"] is not None else None, "ev": evento(u)})
        out.append(f); tmax = max(tmax, f["t"])

    for n, v in cfg["brasil"]["ativos"].items():
        add("brasil", n, v, "B3", (v or {}).get("setor", ""), "R$", n, "BOVA11")
    for n, v in cfg["eua"]["ativos"].items():
        add("eua", n, v, "EUA", v.get("setor", ""), "US$", n, ctx_de(n, v.get("grupo")))
    for n, v in cfg["pares"]["ativos"].items():
        und, uv = und_bdr(n)
        if not und: continue
        add("pares", n, v, "BDR", v.get("setor", "").split(" · ")[0], "R$", und, ctx_de(und, uv.get("grupo")))
    return {"a": out, "ult": (dt.datetime.fromtimestamp(tmax, dt.timezone.utc) + dt.timedelta(hours=-3)).strftime("%d/%m %H:%M")}


def pagina(arq, titulo, paginas, D):
    h = [ui.cabeca(titulo, paginas, arq), f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>",
         "<p class=sub>Escolha o ativo que você tem. A lista mostra, para cada outro ativo, o quanto a troca está atraente agora: seu ativo esticado para cima e o outro esticado para baixo, "
         f"confirmado por vários indicadores ao mesmo tempo. Nota de 0 a 10 e estrelas com os valores reais ao lado (primeiro o seu ativo, depois o candidato). Dados até {D['ult']} (Brasília); B3 e BDR com 15 min de atraso.</p>",
         "<div class=tr-top id=trtop></div><div class=tr-w id=trw style='display:none'></div><div id=trbody></div>",
         "<details style='margin-top:14px'><summary>Como ler</summary><p>Cada indicador vira uma nota de 0 a 5 estrelas medindo a <b>diferença</b> entre o seu ativo e o candidato (seu ativo mais esticado para cima e o candidato mais esticado para baixo = mais estrelas). "
         "A nota final (0–10) é a média ponderada, com pesos diferentes para day trade (indicadores curtos) e swing curto (1 hora e diário). Tendência maior contra a troca desconta pontos. "
         "Volume relativo = volume acumulado hoje contra a média do mesmo horário nos 20 pregões anteriores. Força vs. mercado = variação do dia menos a do índice de referência "
         "(Nasdaq para ações e BDRs da Nasdaq, S&amp;P 500 para os do S&amp;P, Bitcoin para MSTR/M2ST34, BOVA11 para a B3). Depois das 15h30 (16h30 só entre ações dos EUA) a troca fica cinza: pouco tempo para voltar no mesmo dia. "
         "O 📅 avisa resultado hoje ou amanhã. Ainda não é recomendação de compra e venda: é um filtro para achar onde olhar.</p></details>",
         "</main><script>var D=" + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";" + JS + "</script></body></html>"]
    return "".join(h)
