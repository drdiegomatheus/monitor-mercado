"""Candles de 1 hora (até ~2 anos) dos ativos do Spread, para o backtest intradiário.
Guarda um arquivo pequeno por ativo em categorias/<cat>/dados/h1/<ATIVO>.json: {"ts": quando baixou, "t": minutos desde 1970, "c": fechamentos}.
Cada rodada baixa um lote: primeiro os que faltam (2 anos), depois atualiza os mais antigos (a cada 12 h)."""
import json, os, sys, time

RAIZ = os.path.dirname(os.path.abspath(__file__))
ORC = float(os.environ.get("HORARIO_ORC", "150"))   # segundos de orçamento por rodada
LOTE = 40
VELHO = 12 * 3600


def ativos():
    cats = os.path.join(RAIZ, "categorias")
    pc = json.load(open(os.path.join(cats, "pares", "config.json"), encoding="utf-8"))
    bc = json.load(open(os.path.join(cats, "brasil", "config.json"), encoding="utf-8"))
    suf = {"pares": pc.get("sufixo", ".SA"), "brasil": bc.get("sufixo", ".SA")}
    lista = [(n, "brasil") for n in pc.get("spread_acoes", [])]
    lista += [(n, "pares") for n in pc["ativos"]]
    lista += [(n, "brasil") for n in pc.get("spread_etfs", [])]
    ja = {x[0] for x in lista}
    lista += [(n, "brasil") for n in bc["ativos"] if n not in ja]
    vistos, out = set(), []
    for n, c in lista:
        if n in vistos: continue
        vistos.add(n)
        y = (pc["ativos"].get(n) if c == "pares" else bc["ativos"].get(n)) or {}
        yt = (y.get("yahoo") or [n + suf[c]])[0]
        out.append((n, c, yt))
    return out


def caminho(c, n):
    return os.path.join(RAIZ, "categorias", c, "dados", "h1", n + ".json")


def ler(c, n):
    try: return json.load(open(caminho(c, n), encoding="utf-8"))
    except Exception: return None


def baixar(yts, periodo):
    import yfinance as yf
    d = yf.download(yts, period=periodo, interval="1h", auto_adjust=False, progress=False, group_by="ticker", threads=True)
    res = {}
    for t in yts:
        try:
            s = (d[t] if len(yts) > 1 else d)["Close"].dropna()
            if len(s) < 10: continue
            res[t] = {int(i.timestamp()) // 60: round(float(v), 3) for i, v in s.items()}
        except Exception:
            continue
    return res


def main():
    t0 = time.time(); agora = int(t0)
    L = ativos(); est = {}
    for n, c, yt in L: est[n] = ler(c, n)
    falta = [x for x in L if est[x[0]] is None]
    velhos = sorted([x for x in L if est[x[0]] is not None and agora - est[x[0]].get("ts", 0) > VELHO], key=lambda x: est[x[0]].get("ts", 0))
    print(f"1h: {len(L)} ativos · faltam {len(falta)} · velhos {len(velhos)}")
    for grupo, periodo in ((falta, "730d"), (velhos, "10d")):
        for i in range(0, len(grupo), LOTE):
            if time.time() - t0 > ORC: return
            lote = grupo[i:i + LOTE]
            try: res = baixar([x[2] for x in lote], periodo)
            except Exception as e:
                print("falha", periodo, e); continue
            ok = 0
            for n, c, yt in lote:
                novo = res.get(yt)
                if not novo: 
                    if est[n] is None and periodo == "730d": est[n] = None
                    continue
                m = {}
                if est[n]:
                    m = dict(zip(est[n]["t"], est[n]["c"]))
                m.update(novo)
                ks = sorted(m)[-5200:]
                os.makedirs(os.path.dirname(caminho(c, n)), exist_ok=True)
                json.dump({"ts": agora, "t": ks, "c": [m[k] for k in ks]}, open(caminho(c, n), "w"), separators=(",", ":"))
                ok += 1
            print(f"lote {periodo}: {ok}/{len(lote)} gravados")
            if periodo == "730d" and ok == 0: return


if __name__ == "__main__":
    main()
