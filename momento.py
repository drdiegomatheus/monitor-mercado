"""Aba Momento: semáforo de compra/venda por empresa (técnica; fundamental e analistas entram depois).
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
.sf.g i{background:#16a34a;opacity:1}.sf.r i{background:#dc2626;opacity:1}.sf.n i{background:#9ca3af;opacity:1}.sf small{color:var(--mu);font-weight:500;font-size:11px}
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

JS = r"""
function f1(v,d){return(v==null||v!==v)?'–':v.toLocaleString('pt-BR',{minimumFractionDigits:d==null?1:d,maximumFractionDigits:d==null?1:d})}
function sg(v,d){return v==null?'–':(v>=0?'+':'−')+f1(Math.abs(v),d)}
function sf(t){if(!t||t.sc==null)return'<span class="sf"><i></i>–</span>';var c=t.sc>=6.5?'g':(t.sc<=3.5?'r':'n');return'<span class="sf '+c+'"><i></i>'+f1(t.sc,1)+'<small>'+(c=='g'?'compra':c=='r'?'venda':'neutro')+'</small></span>'}
var R=D.rows,SORT={k:'ger',d:-1},FG='',FS='',FQ='',FSIG='';
function ger(r){var v=[];['t1','t2'].forEach(function(k){if(r[k]&&r[k].sc!=null)v.push(r[k].sc)});return v.length?v.reduce(function(a,b){return a+b},0)/v.length:null}
R.forEach(function(r){r.ger=ger(r)});
var SET=Array.from(new Set(R.map(function(r){return r.s}).filter(Boolean))).sort();
function val(r,k){if(k=='n')return r.n;if(k=='ger')return r.ger;if(k=='t1')return r.t1&&r.t1.sc;if(k=='t2')return r.t2&&r.t2.sc;return null}
function build(){
 var bar='<div class=mo-bar><input id=q placeholder="buscar ativo…" value="'+FQ+'"><button data-g="" class="'+(FG==''?'on':'')+'">Todos</button><button data-g=B3 class="'+(FG=='B3'?'on':'')+'">B3</button><button data-g=EUA class="'+(FG=='EUA'?'on':'')+'">EUA + BDR</button><select id=st><option value="">Todos os setores</option>'+SET.map(function(s){return'<option'+(FS==s?' selected':'')+'>'+s+'</option>'}).join('')+'</select><button data-sg=g class="'+(FSIG=='g'?'on':'')+'">● Compra</button><button data-sg=r class="'+(FSIG=='r'?'on':'')+'">● Venda</button></div>';
 var L=R.filter(function(r){if(FG&&r.g!=FG)return false;if(FS&&r.s!=FS)return false;if(FQ&&(r.n+' '+(r.b||'')).toUpperCase().indexOf(FQ.toUpperCase())<0)return false;if(FSIG){var x=r.ger;if(x==null)return false;if(FSIG=='g'&&x<6.5)return false;if(FSIG=='r'&&x>3.5)return false}return true});
 L.sort(function(a,b){var x=val(a,SORT.k),y=val(b,SORT.k);if(x==null)return 1;if(y==null)return-1;return x<y?-SORT.d:x>y?SORT.d:0});
 var h=bar+'<table class=mo-t><thead><tr><th data-k=n>Empresa</th><th data-k=t1>Técnica (B3 / EUA)</th><th data-k=t2>Técnica BDR</th><th>Fundamental</th><th>Analistas</th><th data-k=ger>Geral ▾</th></tr></thead><tbody>';
 L.forEach(function(r){h+='<tr class=mr data-i="'+r.i+'"><td class=mo-n><b>'+r.n+(r.b?' <span class=mu style="font-weight:500">· '+r.b+'</span>':'')+'</b><small>'+(r.s||'')+'</small></td><td>'+sf(r.t1)+'</td><td>'+(r.t2?sf(r.t2):'<span class=mu>–</span>')+'</td><td><span class=mu>em breve</span></td><td><span class=mu>em breve</span></td><td>'+sf({sc:r.ger})+'</td></tr>'});
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
function drawD(){var r=CUR,lst=LST==0?r.t1:r.t2,tabs='';
 var tt=['tec','fun','ana'],tn={tec:'Técnica',fun:'Fundamental',ana:'Analistas'};
 var h='<button class=x>✕</button><h2>'+r.n+(r.b?' <span class=mu style="font-weight:500">· '+r.b+'</span>':'')+'</h2><div class=mo-note>'+(r.s||'')+'</div>';
 h+='<div class=mo-tabs>'+tt.map(function(k){return'<button data-tab='+k+' class="'+(TAB==k?'on':'')+'">'+tn[k]+'</button>'}).join('')+'</div>';
 if(TAB=='tec'){
  if(r.t2)h+='<div class=mo-tabs>'+[r.t1,r.t2].map(function(t,i){return'<button data-l='+i+' class="'+(LST==i?'on':'')+'">'+t.lb+' · '+t.cu+'</button>'}).join('')+'</div>';
  h+='<div>'+sf(lst)+' <span class=mu>Regime: <b>'+lst.rg+'</b></span> · <span class=mu>preço '+lst.cu+' '+f1(lst.p,2)+'</span></div>';
  h+='<div class=mo-g>'+[['RSI diário',f1(lst.rd,0)],['RSI semanal',f1(lst.rw,0)],['vs MM200 diária',sg(lst.d2,1)+'%'],['vs MM200 semanal',sg(lst.w2,1)+'%'],['vs máx. 52 sem.',sg(lst.h52,1)+'%'],['vs máx. 5 anos',sg(lst.h5,1)+'%'],['vs mín. 52 sem.',sg(lst.l52,1)+'%'],['1 mês',sg(lst.r1,1)+'%'],['3 meses',sg(lst.r3,1)+'%'],['6 meses',sg(lst.r6,1)+'%'],['12 meses',sg(lst.r12,1)+'%'],['Força 6m vs '+lst.ix,sg(lst.rs,1)+' pp']].map(function(x){return'<div class=mo-k><small>'+x[0]+'</small><b>'+x[1]+'</b></div>'}).join('')+'</div>';
  h+='<div class=mo-c><h4>Preço diário (≈ 1 ano) com MM 50 e MM 200</h4><canvas id=c1></canvas></div><div class=mo-c><h4>Preço semanal (5 anos) com MM 200 semanal</h4><canvas id=c2></canvas></div><div class=mo-c><h4>RSI diário e semanal</h4><canvas id=c3></canvas></div>';
  h+='<div class=mo-note>Nota técnica: média de RSI semanal, RSI diário, distância da MM 200 diária e queda desde a máxima de 52 semanas. Em regime de baixa (abaixo das duas MM 200) a nota de compra fica no máximo neutra, salvo RSI semanal abaixo de 30 (possível fundo). Pesos iniciais, ainda sem backtest.</div>'}
 else h+='<div class=mo-soon>'+(TAB=='fun'?'Fundamentos (valuation, crescimento, margens, dívida, caixa) entram na próxima etapa.':'Consenso de analistas, preço-alvo e resultados entram na próxima etapa.')+'</div>';
 var p=document.getElementById('mo-p');p.innerHTML=h;
 p.querySelectorAll('[data-tab]').forEach(function(b){b.onclick=function(){TAB=b.dataset.tab;drawD()}});
 p.querySelectorAll('[data-l]').forEach(function(b){b.onclick=function(){LST=+b.dataset.l;drawD()}});
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


def tecnica(c, idx, rotulo, moeda, idx_nome):
    """indicadores técnicos de uma série diária de fechamentos"""
    w = c.resample("W-FRI").last().dropna()
    s200, s50 = c.rolling(200).mean(), c.rolling(50).mean()
    w200 = w.rolling(200).mean()
    rd, rw = _rsi(c), _rsi(w)
    p = c.iloc[-1]
    d2 = (p / s200.iloc[-1] - 1) * 100 if np.isfinite(s200.iloc[-1]) else None
    w2 = (p / w200.iloc[-1] - 1) * 100 if len(w200) and np.isfinite(w200.iloc[-1]) else None
    h52 = (p / c.tail(252).max() - 1) * 100
    h5 = (p / c.max() - 1) * 100
    l52 = (p / c.tail(252).min() - 1) * 100
    def ret(n): return (p / c.iloc[-1 - n] - 1) * 100 if len(c) > n else None
    rs = None
    if idx is not None and len(idx) > 126 and len(c) > 126:
        ri = (idx.iloc[-1] / idx.iloc[-127] - 1) * 100
        rs = ret(126) - ri if ret(126) is not None else None
    ab_d = d2 is not None and d2 > 0
    ab_w = w2 is not None and w2 > 0
    rg = "Alta" if ab_d and ab_w else "Correção" if ab_w and not ab_d else "Repique" if ab_d and not ab_w else "Baixa"
    if d2 is None and w2 is None: rg = "–"
    sc = None
    xs = []
    if np.isfinite(rw.iloc[-1]): xs.append((_clip((50 - rw.iloc[-1]) / 20), 2))
    if np.isfinite(rd.iloc[-1]): xs.append((_clip((50 - rd.iloc[-1]) / 20), 1.5))
    if d2 is not None: xs.append((_clip(-d2 / 25), 1.5))
    xs.append((_clip((-h52 - 15) / 35), 1))
    if len(xs) >= 3:
        sc = 5 + 5 * sum(x * k for x, k in xs) / sum(k for _, k in xs)
        if rg == "Baixa" and sc > 6.4 and not (np.isfinite(rw.iloc[-1]) and rw.iloc[-1] < 30): sc = 6.4   # baixa confirmada: no máximo neutro, salvo capitulação (RSI semanal < 30)
        sc = max(0, min(10, sc))
    dc = c.tail(250)
    wc = w.tail(260)
    ch = {"d": [round(x, 2) for x in dc], "m50": [_n(x, 2) for x in s50.tail(250)], "m200": [_n(x, 2) for x in s200.tail(250)],
          "dd": [int(t.timestamp() // 86400) for t in dc.index],
          "w": [round(x, 2) for x in wc], "w200": [_n(x, 2) for x in w200.tail(260)], "wd": [int(t.timestamp() // 86400) for t in wc.index],
          "rwd": [_n(x, 1) for x in rd.tail(250)], "rww": [_n(x, 1) for x in rw.reindex(dc.index, method="ffill")]}
    return {"lb": rotulo, "cu": moeda, "p": _n(p, 2), "sc": _n(sc), "rg": rg, "rd": _n(rd.iloc[-1], 0), "rw": _n(rw.iloc[-1], 0),
            "d2": _n(d2), "w2": _n(w2), "h52": _n(h52), "h5": _n(h5), "l52": _n(l52), "r1": _n(ret(21)), "r3": _n(ret(63)), "r6": _n(ret(126)),
            "r12": _n(ret(252)), "rs": _n(rs), "ix": idx_nome, "ch": ch}


def dados(raiz):
    cats = os.path.join(raiz, "categorias")
    cfg = {c: json.load(open(os.path.join(cats, c, "config.json"), encoding="utf-8")) for c in ("brasil", "eua", "pares")}
    IX = {"BOVA11": _ler(raiz, "brasil", "BENCH_BOVA11"), "Nasdaq": _ler(raiz, "eua", "BENCH_NASDAQ"), "S&P 500": _ler(raiz, "eua", "BENCH_SP500")}
    rows = []
    for n, v in cfg["brasil"]["ativos"].items():
        c = _ler(raiz, "brasil", n)
        if c is None: continue
        rows.append({"i": len(rows), "n": n, "g": "B3", "s": (v or {}).get("setor", ""), "t1": tecnica(c, IX["BOVA11"], "B3", "R$", "BOVA11")})
    for n, v in cfg["eua"]["ativos"].items():
        c = _ler(raiz, "eua", n)
        if c is None: continue
        ixn = "Nasdaq" if v.get("grupo") == "nasdaq" else "S&P 500"
        r = {"i": len(rows), "n": n, "g": "EUA", "s": v.get("setor", ""), "t1": tecnica(c, IX[ixn], "EUA", "US$", ixn)}
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
         "<p class=sub>Semáforo por empresa: verde = momento de compra, vermelho = venda, cinza = neutro. BDR e ação dos EUA ficam na mesma linha, com a técnica de cada um. Clique em uma linha para ver os detalhes e gráficos.</p>",
         "<div id=mo></div><div class=mo-o id=mo-o><div class=mo-p id=mo-p></div></div>",
         "</main><script>var D=" + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";" + JS + "</script></body></html>"]
    return "".join(h)
