"""Página "Cotações": 50 mais negociados de cada mercado separados por setor + aba "Outros ativos" com busca.
Lê universo/linhas.json (gerado por universo.py). Só dados factuais; sem recomendação."""
import html as H
import json
import os

import ui

TOP = 50
CSS = """
.ct-tabs{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 14px}
.ct-tabs button{background:var(--card);border:1px solid var(--line);color:var(--mu);border-radius:999px;padding:7px 16px;font-weight:700;font-size:13px;cursor:pointer}
.ct-tabs button.at{background:var(--tx);color:var(--bg);border-color:var(--tx)}
.ct-sec{background:var(--card);border:1px solid var(--line);border-radius:16px;margin:0 0 14px;overflow:hidden;box-shadow:var(--shadow)}
.ct-sec h3{margin:0;padding:10px 14px;font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--mu);background:var(--card2);display:flex;justify-content:space-between}
.ct-w{overflow-x:auto}
.ct table{width:100%;min-width:960px;table-layout:fixed;border-collapse:collapse;font-size:13px}.ct th:first-child,.ct td:first-child{width:270px;overflow:hidden;text-overflow:ellipsis}
.ct th{color:var(--mu);font-size:11px;text-transform:uppercase;letter-spacing:.04em;text-align:right;padding:6px 10px;font-weight:600;white-space:nowrap}
.ct td{padding:7px 10px;text-align:right;border-top:1px solid var(--line);white-space:nowrap}
.ct th:first-child,.ct td:first-child{text-align:left;position:sticky;left:0;background:var(--card)}
.ct td:first-child b{font-weight:800}.ct td:first-child span{color:var(--mu);font-size:11.5px;margin-left:6px;font-weight:500}
.ct .tr{display:inline-block;width:10px;height:10px;border-radius:50%;vertical-align:middle}
.ct .tr.alta{background:var(--gr)}.ct .tr.mista{background:#f59e0b}.ct .tr.baixa{background:var(--rd)}.ct .tr.x{background:var(--line)}
.ct .rb{display:inline-block;min-width:26px;padding:1px 6px;border-radius:7px;background:var(--card2);font-weight:700}
.ct .rb.ex{background:color-mix(in srgb,#f59e0b 25%,transparent)}
.ct-s{display:block;width:100%;max-width:420px;margin:0 0 12px;background:var(--card);border:1px solid var(--line);color:var(--tx);border-radius:12px;padding:10px 14px;font-size:14px;outline:none}
.ct-n{color:var(--mu);font-size:12.5px;margin:6px 2px 12px}
"""

JS = r"""
var M={brasil:"R$",eua:"US$",cripto:"US$"},NM={brasil:"Brasil",eua:"EUA",cripto:"Cripto"},at="brasil";
function f(x,n){return x==null?"–":x.toLocaleString("pt-BR",{minimumFractionDigits:n,maximumFractionDigits:n})}
function pr(p,m){var d=p>=1000?0:p>=1?2:p>=0.01?4:8;return f(p,d)}
function pc(x){if(x==null)return "<td class=mu>–</td>";return "<td class="+(x>=0?"up":"dn")+">"+(x>0?"+":"")+f(x,2)+"%</td>"}
function rs(x){if(x==null)return "<td class=mu>–</td>";return "<td><span class='rb"+(x>=70||x<=30?" ex":"")+"'>"+f(x,0)+"</span></td>"}
function lin(r,mostrar){
  var tt={alta:"Acima da MM200 diária e da semanal",mista:"Entre a MM200 diária e a semanal",baixa:"Abaixo da MM200 diária e da semanal"};
  var t=r.tr?"<span class='tr "+r.tr+"' title='"+tt[r.tr]+"'></span>":"<span class='tr x' title='Histórico curto para a MM200'></span>";
  return "<tr><td><b>"+r.t+"</b><span>"+r.n+(mostrar?" · "+NM[r.m]+" · "+r.s:"")+"</span></td><td>"+M[r.m]+" "+pr(r.p,r.m)+"</td>"+pc(r.d1)+pc(r.w1)+pc(r.m1)+rs(r.rd)+rs(r.rw)+rs(r.rm)+"<td>"+t+"</td>"+pc(r.d200)+pc(r.h52)+"</tr>"}
var CAB="<tr><th>Ativo<th>Preço<th>Dia<th>Semana<th>30 dias<th>RSI dia<th>RSI sem<th>RSI mês<th>MM200<th>vs MM200 dia<th>vs máx. 52 sem</tr>";
function tab(){
  var q=document.getElementById("q");var h="";
  if(at=="outros"){
    var t=(q.value||"").trim().toLowerCase(),L=D.linhas.filter(function(r){return !t||r.t.toLowerCase().indexOf(t)>=0||r.n.toLowerCase().indexOf(t)>=0||r.s.toLowerCase().indexOf(t)>=0});
    var tot=L.length;L=L.slice(0,150);
    h="<p class=ct-n>"+tot+" ativo"+(tot==1?"":"s")+" encontrado"+(tot==1?"":"s")+(tot>150?" (mostrando 150: refine a busca)":"")+". Busque por código, nome ou setor.</p><div class=ct-sec><div class=ct-w><table>"+CAB+L.map(function(r){return lin(r,true)}).join("")+"</table></div></div>";
    q.style.display="block";
  }else{
    q.style.display="none";
    var L=D.linhas.filter(function(r){return r.m==at&&r.r&&r.r<="""+str(TOP)+r"""}),S={};
    L.forEach(function(r){(S[r.s]=S[r.s]||[]).push(r)});
    var ult=function(k){return k=="Outras"||k=="Outros"?1:0};var ks=Object.keys(S).sort(function(a,b){return ult(a)-ult(b)||S[b].length-S[a].length||a.localeCompare(b)});
    h="<p class=ct-n>"+L.length+(at=="cripto"?" maiores criptomoedas por valor de mercado (sem stablecoins e tokens embrulhados)":" ativos mais negociados em "+NM[at]+" (média do volume financeiro dos últimos 30 dias)")+"; lista revista toda semana, separados por setor.</p>";
    ks.forEach(function(k){h+="<div class=ct-sec><h3><span>"+k+"</span><span>"+S[k].length+"</span></h3><div class=ct-w><table>"+CAB+S[k].sort(function(a,b){return a.r-b.r}).map(function(r){return lin(r,false)}).join("")+"</table></div></div>"});
  }
  document.getElementById("ct-b").innerHTML=h;
  [].forEach.call(document.querySelectorAll(".ct-tabs button"),function(b){b.className=b.dataset.k==at?"at":""});
}
function go(k){at=k;tab()}
document.getElementById("q").oninput=tab;tab();
"""


def dados(raiz):
    f = os.path.join(raiz, "universo", "linhas.json")
    return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {"gerado": "", "linhas": []}


def pagina(arq, titulo, paginas, D):
    btn = "".join(f"<button data-k={k} onclick=\"go('{k}')\">{n}</button>" for k, n in (("brasil", "Brasil"), ("eua", "EUA"), ("cripto", "Cripto"), ("outros", "Outros ativos")))
    n = len(D["linhas"])
    return "".join([
        ui.cabeca(titulo, paginas, arq), f"<style>{CSS}</style><h1>{H.escape(titulo)}</h1>",
        f"<p class=sub>{n} ativos acompanhados: B3 (200 mais negociadas), S&amp;P 500 e Nasdaq-100, e as principais criptomoedas. Fechamentos diários; semana e mês calculados a partir deles. "
        "O ponto de tendência compara o preço com a MM200 diária e a semanal: verde = acima das duas, amarelo = entre elas, vermelho = abaixo das duas. "
        "RSI acima de 70 ou abaixo de 30 aparece destacado e costuma ser lido como sobrecompra ou sobrevenda; o indicador não prevê preço. Dados informativos, sem recomendação de compra ou venda."
        f" Atualizado em {H.escape(D.get('gerado', ''))}.</p>",
        f"<div class=ct><div class=ct-tabs>{btn}</div><input id=q class=ct-s placeholder='Buscar por código, nome ou setor' style='display:none'><div id=ct-b></div></div>",
        "</main><script>var D=" + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";" + JS + "</script></body></html>"])
