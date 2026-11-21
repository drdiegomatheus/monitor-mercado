"""Aba Baleias: carteiras grandes da Hyperliquid, mapa de liquidação, heatmap no tempo, posições e movimentações."""
import json
import html as H
import os
import ui
import momento as M0
import momento_cripto as MC

CSS = MC.CSS + """
.bl-top{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}.bl-top button{border:1px solid var(--line);background:var(--card);color:var(--tx);border-radius:999px;padding:6px 14px;font-weight:700;font-size:13px;cursor:pointer}
.bl-top button.on{background:var(--tx);color:var(--bg)}
.bl-sel{display:inline-flex;gap:4px;margin-left:auto}.bl-sel button{border:1px solid var(--line);background:var(--card2);color:var(--mu);border-radius:8px;padding:3px 9px;font-size:12px;font-weight:700;cursor:pointer}.bl-sel button.on{background:var(--tx);color:var(--bg)}
.bl-c{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;margin:0 0 14px}
.bl-c h3{margin:0 0 8px;font-size:13px;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.bl-c canvas{width:100%;height:340px;display:block}.bl-c canvas.m{height:300px}
.bl-n{color:var(--mu);font-size:12px;margin:6px 0 0}
.bl-t{width:100%;border-collapse:collapse;font-size:12.5px}.bl-t th{text-align:right;font-size:11px;color:var(--mu);text-transform:uppercase;padding:6px 8px;border-bottom:1px solid var(--line);cursor:default;background:none;position:static}.bl-t td{text-align:right;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap;background:none;position:static}
.bl-t th:first-child,.bl-t td:first-child{text-align:left;position:static;background:none;padding-left:8px}
.bl-t a{color:var(--ac);text-decoration:none;font-weight:700}
.lg{color:var(--gr);font-weight:700}.sh2{color:var(--rd);font-weight:700}
.bl-f{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 8px;align-items:center}.bl-f select,.bl-f input{background:var(--card);border:1px solid var(--line);color:var(--tx);border-radius:10px;padding:6px 10px;font-size:13px}
.bl-ev{display:flex;gap:10px;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px;align-items:center}.bl-ev small{color:var(--mu)}
.bl-sc{overflow-x:auto}
"""


def dados(raiz):
    f = os.path.join(raiz, "categorias", "cripto", "baleias.json")
    if not os.path.exists(f): return None
    e = json.load(open(f, encoding="utf-8"))
    contas = e.get("contas", {})
    mark, oi = e.get("mark", {}), e.get("oi", {})
    tot = {}
    pos = {}
    linhas = []
    cont = {}
    for a, c in contas.items():
        for p in c["p"]:
            coin, szi, ent, ntl, liq, lev, up, tp = p
            t = tot.setdefault(coin, [0, 0, 0, 0])
            i = 0 if szi > 0 else 1
            t[i] += ntl
            t[2 + i] += 1
            if liq: pos.setdefault(coin, []).append([round(liq, 4), ntl if szi > 0 else -ntl])
            linhas.append((ntl, a, c, p))
    coins = sorted((k for k, v in tot.items() if v[0] + v[1] >= 5e6), key=lambda k: -(tot[k][0] + tot[k][1]))[:14]
    for k in coins:
        pos[k] = sorted(pos.get(k, []), key=lambda x: -abs(x[1]))[:6000]
    linhas.sort(key=lambda x: -x[0])
    top = []
    for ntl, a, c, p in linhas[:400]:
        top.append([a, c.get("nome"), p[0], "long" if p[1] > 0 else "short", ntl, p[2], p[4], p[5], p[6], c["av"], c["pnl"][2], p[7]])
    ranking = []
    for a, c in sorted(contas.items(), key=lambda x: -x[1]["av"])[:30]:
        liq_ = sum(p[3] for p in c["p"] if p[1] > 0)
        sho = sum(p[3] for p in c["p"] if p[1] < 0)
        maior = max(c["p"], key=lambda p: p[3]) if c["p"] else None
        ranking.append([a, c.get("nome"), c["av"], c["pnl"], c.get("roi"), liq_, sho, (maior[0] + (" long" if maior[1] > 0 else " short") + " " + str(maior[3])) if maior else None])
    hist = e.get("hist", [])
    H_ = {"t": [h["t"] for h in hist], "px": {}, "tot": {}, "hm": {}, "passos": e.get("passos", {})}
    for coin in coins:
        H_["px"][coin] = [h["px"].get(coin) for h in hist]
        H_["tot"][coin] = [h["tot"].get(coin) for h in hist]
    for coin in e.get("passos", {}):
        H_["hm"][coin] = [h["hm"].get(coin) for h in hist]
    return {"ts": e.get("ts"), "cob": e.get("cobertura", {}), "mark": {k: mark.get(k) for k in coins}, "oi": {k: oi.get(k) for k in coins},
            "coins": coins, "tot": {k: tot[k] for k in coins}, "pos": {k: pos[k] for k in coins}, "top": top, "rank": ranking, "ev": e.get("eventos", [])[-120:][::-1], "hist": H_}


JS = M0.LIB + r"""
var COIN=D.coins[0],RNG=20,SZ=0,FS='todos',FC='todas',Q='';
function usd(v){return v==null?'–':'US$ '+M(v)}
function fx(p){return p==null?'–':(p>=1000?f1(p,0):p>=10?f1(p,2):f1(p,4))}
function sh(a){return a.slice(0,6)+'…'+a.slice(-4)}
function nm(a,n){return '<a href="https://hypurrscan.io/address/'+a+'" target=_blank rel=noopener>'+(n?n:sh(a))+'</a>'}
function ago(t){var s=Math.round(Date.now()/1000-t);return s<90?'agora':s<5400?Math.round(s/60)+' min':s<172800?Math.round(s/3600)+' h':Math.round(s/86400)+' d'}
function tp(t,x){return '<span class=tip data-tip="'+t.replace(/"/g,'&quot;')+'">i</span>'}
function agoraNet(c){var T=D.tot[c],net=T[0]-T[1],r=net/(T[0]+T[1]);return r>.2?'As baleias estão claramente compradas ('+f1(r*100,0)+'% a mais no long): apostam na alta.':r<-.2?'As baleias estão claramente vendidas ('+f1(-r*100,0)+'% a mais no short): apostam na queda.':'Posição equilibrada entre compradas e vendidas: sem viés forte.'}
function head(){var C=D.cob,h='<div class=mo-h>';
 function k(t,v,s,tt){return'<div class=mo-k><small>'+t+(tt?tp(tt):'')+'</small><b>'+v+'</b>'+(s?'<em>'+s+'</em>':'')+'</div>'}
 var T=D.tot[COIN],px=D.mark[COIN],oi=D.oi[COIN];
 h+=k('Carteiras monitoradas',f1(C.contas,0),'conta ≥ US$ '+M(C.minimo)+' · '+f1(C.consultadas,0)+' já lidas','Carteiras da Hyperliquid com saldo acima do mínimo, listadas no ranking público da própria exchange. Cada uma é consultada a cada poucos minutos para ler suas posições abertas e o preço em que seriam liquidadas.');
 h+=k('Última atualização',ago(D.ts),'varredura em andamento','As posições são lidas aos poucos, das mais antigas para as mais novas. Posições muito recentes podem ainda não ter sido lidas.');
 h+=k('Long das baleias · '+COIN,usd(T[0]),f1(T[2],0)+' carteiras','Valor total das posições compradas (apostam na alta) das carteiras monitoradas neste ativo.');
 h+=k('Short das baleias · '+COIN,usd(T[1]),f1(T[3],0)+' carteiras','Valor total das posições vendidas (apostam na queda) das carteiras monitoradas neste ativo.');
 var net=T[0]-T[1];
 h+=k('Saldo (long − short)',(net>=0?'+':'−')+usd(Math.abs(net)),f1((T[0]+T[1])/oi*100,0)+'% do open interest total ('+M(oi)+')','Diferença entre o que está comprado e o que está vendido nas carteiras monitoradas. Positivo = viés de alta. A porcentagem mostra quanto do mercado de perpétuos desse ativo na Hyperliquid essas carteiras representam. AGORA: '+agoraNet(COIN));
 return h+'</div>'}
function bandas(){var px=D.mark[COIN],lo=px*(1-RNG/100),hi=px*(1+RNG/100),n=70,st=(hi-lo)/n,L=[],S=[],i;for(i=0;i<n;i++){L.push(0);S.push(0)}
 D.pos[COIN].forEach(function(p){var q=p[0];if(q<lo||q>=hi)return;var b=Math.floor((q-lo)/st);if(p[1]>0)L[b]+=p[1];else S[b]-=p[1]});return{lo:lo,hi:hi,n:n,st:st,L:L,S:S}}
var MAPA=null;
function drawMapa(){var cv=document.getElementById('mapa'),B=bandas(),px=D.mark[COIN];MAPA=B;
 var dpr=window.devicePixelRatio||1,W=cv.clientWidth,Hh=cv.clientHeight;cv.width=W*dpr;cv.height=Hh*dpr;var g=cv.getContext('2d');g.scale(dpr,dpr);
 var cs=getComputedStyle(document.body),mu=cs.getPropertyValue('--mu')||'#888',ln=cs.getPropertyValue('--line')||'#ddd';
 var pl=52,pr=58,pt=14,pb=26,mx=1,i;for(i=0;i<B.n;i++)mx=Math.max(mx,B.L[i],B.S[i]);
 var cumL=[],cumS=[],a=0;var ip=Math.floor((px-B.lo)/B.st);
 a=0;for(i=Math.min(ip,B.n-1);i>=0;i--){a+=B.L[i];cumL[i]=a}a=0;for(i=Math.max(ip+1,0);i<B.n;i++){a+=B.S[i];cumS[i]=a}
 var cm=Math.max(1,a,cumL[0]||0);B.cumL=cumL;B.cumS=cumS;
 function X(i){return pl+(W-pl-pr)*i/B.n}function Y(v){return pt+(Hh-pt-pb)*(1-v/mx)}function Y2(v){return pt+(Hh-pt-pb)*(1-v/cm)}
 g.font='10px system-ui';g.strokeStyle=ln;g.fillStyle=mu;
 for(i=0;i<=4;i++){var v=mx*i/4,y=Y(v);g.beginPath();g.moveTo(pl,y);g.lineTo(W-pr,y);g.stroke();g.textAlign='right';g.fillText(M(v),pl-4,y+3);g.textAlign='left';g.fillText(M(cm*i/4),W-pr+4,y+3)}
 var bw=(W-pl-pr)/B.n;
 for(i=0;i<B.n;i++){if(B.L[i]){g.fillStyle='rgba(239,68,68,.75)';g.fillRect(X(i)+1,Y(B.L[i]),bw-1,Y(0)-Y(B.L[i]))}if(B.S[i]){g.fillStyle='rgba(16,185,129,.75)';g.fillRect(X(i)+1,Y(B.S[i]),bw-1,Y(0)-Y(B.S[i]))}}
 g.lineWidth=2;g.strokeStyle='#ef4444';g.beginPath();var f=0;for(i=Math.min(ip,B.n-1);i>=0;i--){var x=X(i)+bw/2,y=Y2(cumL[i]);if(!f){g.moveTo(x,y);f=1}else g.lineTo(x,y)}g.stroke();
 g.strokeStyle='#10b981';g.beginPath();f=0;for(i=Math.max(ip+1,0);i<B.n;i++){var x2=X(i)+bw/2,y2=Y2(cumS[i]);if(!f){g.moveTo(x2,y2);f=1}else g.lineTo(x2,y2)}g.stroke();g.lineWidth=1;
 var xp=pl+(W-pl-pr)*(px-B.lo)/(B.hi-B.lo);g.setLineDash([4,4]);g.strokeStyle=mu;g.beginPath();g.moveTo(xp,pt);g.lineTo(xp,Hh-pb);g.stroke();g.setLineDash([]);
 g.fillStyle=mu;g.textAlign='center';g.fillText('preço '+fx(px),Math.min(Math.max(xp,pl+40),W-pr-40),pt+22);for(i=0;i<=4;i++){var pp=B.lo+(B.hi-B.lo)*i/4;g.fillText(fx(pp),pl+(W-pl-pr)*i/4,Hh-6)}g.textAlign='left';
 g.fillStyle='#ef4444';g.fillText('● longs (liquidam se o preço cair)',pl,10);g.fillStyle='#10b981';g.fillText('● shorts (liquidam se o preço subir)',pl+190,10)}
function mapaTip(e){var cv=e.target,r=cv.getBoundingClientRect(),x=e.clientX-r.left,B=MAPA,W=cv.clientWidth,pl=52,pr=58,px=D.mark[COIN];if(!B)return;
 var i=Math.floor((x-pl)/(W-pl-pr)*B.n);if(i<0||i>=B.n){TB.style.display='none';return}
 var p0=B.lo+B.st*i,p1=p0+B.st,mid=(p0+p1)/2,t='Faixa '+fx(p0)+' – '+fx(p1)+' ('+sg((mid/px-1)*100,1)+'%)\n';
 if(B.L[i])t+='Longs nesta faixa: '+usd(B.L[i])+'\n';if(B.S[i])t+='Shorts nesta faixa: '+usd(B.S[i])+'\n';
 if(mid<px&&B.cumL[i]!=null)t+='Se o preço cair até aqui: '+usd(B.cumL[i])+' de longs liquidados';if(mid>px&&B.cumS[i]!=null)t+='Se o preço subir até aqui: '+usd(B.cumS[i])+' de shorts liquidados';
 TB.textContent=t;TB.style.display='block';TB.style.left=Math.min(e.clientX+14,innerWidth-TB.offsetWidth-8)+'px';TB.style.top=(e.clientY+14)+'px'}
function proxLiq(){var B=bandas(),px=D.mark[COIN],a=0,b=0;D.pos[COIN].forEach(function(p){var d=p[0]/px-1;if(p[1]>0&&d<0&&d>=-.05)a+=p[1];if(p[1]<0&&d>0&&d<=.05)b-=p[1]});return[a,b]}
function drawHM(){var cv=document.getElementById('hm'),Hs=D.hist,n=Hs.t.length,note=document.getElementById('hmn');
 var dpr=window.devicePixelRatio||1,W=cv.clientWidth,Hh=cv.clientHeight;cv.width=W*dpr;cv.height=Hh*dpr;var g=cv.getContext('2d');g.scale(dpr,dpr);
 var st=Hs.passos[COIN],hm=Hs.hm[COIN];if(!st||!hm||n<2){g.fillStyle='#888';g.font='13px system-ui';g.fillText('O histórico começou agora: o heatmap aparece depois de 2 ou mais registros (um a cada ≈ 25 minutos, guardados por ≈ 6 dias).',12,30);note.textContent='';return}
 var px=D.mark[COIN],lo=px*(1-RNG/100),hi=px*(1+RNG/100),pl=52,pr=8,pt=8,pb=22,mx=1,i,j;
 hm.forEach(function(s){if(s)s.forEach(function(b){mx=Math.max(mx,b[1]+b[2])})});
 function Y(p){return pt+(Hh-pt-pb)*(1-(p-lo)/(hi-lo))}
 var cw=Math.max(2,(W-pl-pr)/n);
 for(i=0;i<n;i++){var s=hm[i];if(!s)continue;s.forEach(function(b){var p0=b[0]*st,p1=p0+st;if(p1<lo||p0>hi)return;var v=(b[1]+b[2])/mx,a=Math.pow(v,.45);
   var r,gg,bb;if(a<.5){var u=a/.5;r=20+u*10;gg=30+u*150;bb=110+u*20}else{var u2=(a-.5)/.5;r=30+u2*225;gg=180+u2*60;bb=130-u2*100}
   g.fillStyle='rgb('+Math.round(r)+','+Math.round(gg)+','+Math.round(bb)+')';g.fillRect(pl+i*(W-pl-pr)/n,Y(p1),cw+.5,Math.max(1,Y(p0)-Y(p1))+.5)})}
 g.strokeStyle='#fff';g.lineWidth=1.6;g.beginPath();var f=0;Hs.px[COIN].forEach(function(p,i2){if(p==null)return;var x=pl+(i2+.5)*(W-pl-pr)/n,y=Y(p);if(!f){g.moveTo(x,y);f=1}else g.lineTo(x,y)});g.stroke();
 g.fillStyle='#888';g.font='10px system-ui';g.textAlign='right';for(j=0;j<=4;j++){var pp=lo+(hi-lo)*j/4;g.fillText(fx(pp),pl-4,Y(pp)+3)}
 g.textAlign='center';[0,.5,1].forEach(function(u){var k=Math.min(n-1,Math.round((n-1)*u)),d=new Date(Hs.t[k]*1000);g.fillText(d.toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}),pl+(W-pl-pr)*(k+.5)/n,Hh-6)});
 note.textContent=n+' registros · de '+new Date(Hs.t[0]*1000).toLocaleString('pt-BR')+' até '+new Date(Hs.t[n-1]*1000).toLocaleString('pt-BR')}
function drawNet(){var cv=document.getElementById('net'),Hs=D.hist,s=Hs.tot[COIN]||[],n=s.length;
 var dpr=window.devicePixelRatio||1,W=cv.clientWidth,Hh=cv.clientHeight;cv.width=W*dpr;cv.height=Hh*dpr;var g=cv.getContext('2d');g.scale(dpr,dpr);
 var ok=s.filter(function(x){return x}).length;if(ok<2){g.fillStyle='#888';g.font='13px system-ui';g.fillText('Aguardando mais registros do histórico.',12,30);return}
 var L=s.map(function(x){return x?x[0]:null}),S=s.map(function(x){return x?x[1]:null}),N=s.map(function(x){return x?x[0]-x[1]:null});
 line(cv,[{v:L,c:'#ef4444',l:'long (US$ mi)'},{v:S,c:'#10b981',l:'short (US$ mi)'},{v:N,c:'#4f46e5',w:1.8,l:'saldo'}],{dates:Hs.t.map(function(t){return Math.floor(t/86400)}),d:0})}
function tabela(){var h='<div class=bl-f><select id=fs><option value=todos>Long e short</option><option value=long>Só long</option><option value=short>Só short</option></select><select id=fc><option value=todas>Todos os ativos</option>'+D.coins.map(function(c){return'<option>'+c+'</option>'}).join('')+'</select><input id=fq placeholder="Buscar endereço ou nome" size=22></div>';
 var rows=D.top.filter(function(r){return(FS=='todos'||r[3]==FS)&&(FC=='todas'||r[2]==FC)&&(!Q||(r[0]+(r[1]||'')).toLowerCase().indexOf(Q)>=0)}).slice(0,60);
 h+='<div class=bl-sc><table class=bl-t><thead><tr><th>Carteira</th><th>Ativo</th><th>Lado</th><th>Tamanho</th><th>Entrada</th><th>Liquidação'+tp('Preço em que a posição seria liquidada à força. Quanto mais perto do preço atual, mais frágil a posição. Posições em margem cruzada podem ter a liquidação bem distante ou nem ter.')+'</th><th>Dist.</th><th>Alav.</th><th>Lucro/prejuízo</th><th>Conta</th><th>PnL 30d</th></tr></thead><tbody>';
 rows.forEach(function(r){var px=D.mark[r[2]],d=r[6]&&px?(r[6]/px-1)*100:null;
  h+='<tr><td>'+nm(r[0],r[1])+'</td><td>'+r[2]+'</td><td class='+(r[3]=='long'?'lg':'sh2')+'>'+r[3]+'</td><td>'+usd(r[4])+'</td><td>'+fx(r[5])+'</td><td>'+(r[6]?fx(r[6]):'–')+'</td><td>'+(d==null?'–':sg(d,1)+'%')+'</td><td>'+(r[7]||'–')+'×'+(r[11]=='i'?' iso':'')+'</td><td class='+(r[8]>=0?'lg':'sh2')+'>'+(r[8]>=0?'+':'−')+usd(Math.abs(r[8]))+'</td><td>'+usd(r[9])+'</td><td class='+(r[10]>=0?'lg':'sh2')+'>'+(r[10]>=0?'+':'−')+usd(Math.abs(r[10]))+'</td></tr>'});
 return h+'</tbody></table></div>'}
function eventos(){var A={abriu:'abriu',fechou:'fechou',aumentou:'aumentou',reduziu:'reduziu',virou:'inverteu'};
 if(!D.ev.length)return'<div class=bl-n>Ainda sem movimentações registradas: elas aparecem quando uma carteira é lida duas vezes e a posição mudou.</div>';
 return D.ev.slice(0,40).map(function(e){return'<div class=bl-ev><span class="'+(e.l=='long'?'lg':'sh2')+'">'+(e.l=='long'?'▲':'▼')+'</span><div>'+nm(e.a,e.n)+' '+A[e.ac]+' <b>'+e.c+' '+e.l+'</b> de '+usd(Math.abs(e.d))+(e.ac=='abriu'||e.ac=='fechou'?'':' (agora '+usd(e.v)+')')+'<br><small>há '+ago(e.t)+(e.px?' · preço '+fx(e.px):'')+'</small></div></div>'}).join('')}
function rank(){var h='<div class=bl-sc><table class=bl-t><thead><tr><th>Carteira</th><th>Conta</th><th>PnL dia</th><th>PnL semana</th><th>PnL mês</th><th>PnL total</th><th>Long</th><th>Short</th><th>Maior posição</th></tr></thead><tbody>';
 D.rank.forEach(function(r){function c(v){return'<td class='+(v>=0?'lg':'sh2')+'>'+(v>=0?'+':'−')+usd(Math.abs(v))+'</td>'}
  h+='<tr><td>'+nm(r[0],r[1])+'</td><td>'+usd(r[2])+'</td>'+c(r[3][0])+c(r[3][1])+c(r[3][2])+c(r[3][3])+'<td>'+usd(r[5])+'</td><td>'+usd(r[6])+'</td><td>'+(r[7]?r[7].replace(/ (\d+)$/,function(m,n){return' '+usd(+n)}):'–')+'</td></tr>'});return h+'</tbody></table></div>'}
function draw(){
 var T=D.tot[COIN],pl=proxLiq(),px=D.mark[COIN];
 var h='<div class=bl-top>'+D.coins.map(function(c){return'<button class="'+(c==COIN?'on':'')+'" data-c='+c+'>'+c+'</button>'}).join('')+'</div>'+head();
 var rg=[10,20,30,50].map(function(r){return'<button data-r='+r+' class="'+(r==RNG?'on':'')+'">±'+r+'%</button>'}).join('');
 h+='<div class=bl-c><h3>Mapa de liquidação · '+COIN+' · preço '+fx(px)+tp('Mostra, faixa por faixa de preço, quanto dinheiro das baleias seria liquidado à força se o preço chegasse ali. Barras vermelhas abaixo do preço = longs que quebram se o preço cair; barras verdes acima = shorts que quebram se o preço subir. As linhas mostram o total acumulado a partir do preço atual. Liquidações forçadas viram ordens a mercado, que empurram o preço e podem causar efeito cascata, então grandes concentrações funcionam como ímãs de preço. AGORA: até 5% abaixo há '+usd(pl[0])+' de longs e até 5% acima há '+usd(pl[1])+' de shorts a serem liquidados.')+'<span class=bl-sel>'+rg+'</span></h3><canvas id=mapa class=m></canvas><div class=bl-n>Passe o mouse para ver quanto seria liquidado até cada preço. Considera só as carteiras monitoradas e posições com preço de liquidação definido (margem cruzada com pouca alavancagem pode não ter).</div></div>';
 h+='<div class=bl-c><h3>Heatmap de liquidação ao longo do tempo · '+COIN+tp('Cada coluna é uma leitura no tempo; a cor mostra a concentração de liquidações em cada faixa de preço (mais claro = mais dinheiro). A linha branca é o preço. Quando o preço se aproxima de uma faixa quente, o risco de cascata de liquidações aumenta; faixas que o preço atravessa deixam de existir porque as posições já foram liquidadas ou ajustadas.')+'</h3><canvas id=hm></canvas><div class=bl-n id=hmn></div></div>';
 h+='<div class=bl-c><h3>Posição das baleias ao longo do tempo · '+COIN+tp('Evolução do total comprado (long), vendido (short) e do saldo entre os dois. Saldo subindo = baleias aumentando a aposta de alta; caindo = migrando para a queda. Em US$ milhões. AGORA: '+agoraNet(COIN))+'</h3><canvas id=net class=m></canvas></div>';
 h+='<div class=bl-c><h3>Maiores posições abertas'+tp('As maiores posições individuais das carteiras monitoradas. Distância = quanto o preço precisa andar para a posição ser liquidada. Alavancagem alta com liquidação próxima indica posição frágil. PnL 30d é o resultado da carteira no último mês, útil para ver se a baleia costuma acertar.')+'</h3>'+tabela()+'</div>';
 h+='<div class=bl-c><h3>Movimentações recentes das baleias'+tp('Aberturas, fechamentos e variações grandes (acima de US$ 2 milhões) detectadas entre duas leituras da mesma carteira. O horário é o da detecção, não necessariamente o da operação.')+'</h3>'+eventos()+'</div>';
 h+='<div class=bl-c><h3>Maiores carteiras'+tp('As 30 maiores contas da Hyperliquid por saldo, com resultado recente e posição atual.')+'</h3>'+rank()+'</div>';
 h+='<div class=mo-note>Fonte: ranking público de carteiras e consulta pública de posições da Hyperliquid, atualizados a cada poucos minutos. Cobre apenas contas com mais de US$ '+M(D.cob.minimo)+'; não inclui o que está fora desse grupo nem posições em outras exchanges.</div>';
 document.getElementById('bl').innerHTML=h;
 document.querySelectorAll('[data-c]').forEach(function(b){b.onclick=function(){COIN=b.dataset.c;draw()}});
 document.querySelectorAll('[data-r]').forEach(function(b){b.onclick=function(){RNG=+b.dataset.r;draw()}});
 var fs=document.getElementById('fs'),fc=document.getElementById('fc'),fq=document.getElementById('fq');fs.value=FS;fc.value=FC;fq.value=Q;
 function rt(){document.getElementById('bl').querySelector('.bl-sc').outerHTML;draw();document.getElementById('fq').focus()}
 fs.onchange=function(){FS=fs.value;draw()};fc.onchange=function(){FC=fc.value;draw()};fq.oninput=function(){Q=fq.value.toLowerCase();var p=fq.selectionStart;draw();var q=document.getElementById('fq');q.focus();q.setSelectionRange(p,p)};
 drawMapa();drawHM();drawNet();var cv=document.getElementById('mapa');cv.onmousemove=mapaTip;cv.onmouseleave=function(){TB.style.display='none'}}
var TB=document.createElement('div');TB.id='tipbox';document.body.appendChild(TB);
function tipShow(el){TB.textContent=el.dataset.tip;TB.style.display='block';var r=el.getBoundingClientRect(),w=TB.offsetWidth,h=TB.offsetHeight,x=Math.min(Math.max(8,r.left-8),innerWidth-w-8),y=r.bottom+8;if(y+h>innerHeight-8)y=Math.max(8,r.top-h-8);TB.style.left=x+'px';TB.style.top=y+'px'}
document.addEventListener('mouseover',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t)tipShow(t);else if(e.target.id!='mapa')TB.style.display='none'});
document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('.tip');if(t){if(TB.style.display=='block'&&TB.textContent==t.dataset.tip)TB.style.display='none';else tipShow(t)}else TB.style.display='none'});
window.addEventListener('resize',function(){drawMapa();drawHM();drawNet()});
draw();
"""


def pagina(arq, titulo, paginas, D):
    topo = ui.cabeca(titulo, paginas, arq) + f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>"
    if not D:
        return topo + "<p class=sub>Os dados das baleias ainda estão sendo coletados. Volte em alguns minutos.</p></main></body></html>"
    return (topo + "<p class=sub>Carteiras grandes da Hyperliquid: onde estão as posições, em que preço seriam liquidadas e o que estão fazendo agora. Passe o mouse no <b>i</b> para ver o que cada item significa e o que está dizendo no momento.</p>"
            "<div id=bl></div></main><script>var D=" + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";" + JS + "</script></body></html>")
