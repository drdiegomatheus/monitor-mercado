# Monitor de mercado

Três categorias, cada uma com sua pasta em `categorias/`:

| Pasta | Referência do RRG | RRG |
|---|---|---|
| `cripto` | BTC | desligado por enquanto (`"rrg": false`) |
| `eua` | NASDAQ (QQQ) ou S&P 500 (SPY), conforme o grupo do ativo | ligado |
| `brasil` | BOVA11 | ligado |

Em cada pasta:
- `config.json` define os ativos (é o único arquivo que se edita)
- `dados/` guarda os CSVs coletados (diário e 30 min)
- `relatorio.html` é o relatório mais recente

Ativos dos EUA: `"AAPL": "nasdaq"` ou `"JPM": "sp500"`.
Ativos do Brasil: só o código, por exemplo `"PETR4"`.

A coleta roda a cada 15 minutos pelo GitHub Actions (`.github/workflows/coleta.yml`).
