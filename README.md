# Monitor de mercado

Categorias, cada uma com sua pasta em `categorias/`:

| Pasta | Referência do RRG | RRG |
|---|---|---|
| `setores` | IBOV / SPY | índices setoriais da B3 (RRG vs Ibovespa) e ETFs setoriais dos EUA (RRG vs SPY) |
| `commodities` | – | ouro, Brent |
| `cripto` | BTC | desligado por enquanto (`"rrg": false`) |
| `eua` | NASDAQ (QQQ) ou S&P 500 (SPY), conforme o grupo do ativo | ligado |
| `brasil` | BOVA11 | ligado |

Em cada pasta:
- `config.json` define os ativos (é o único arquivo que se edita)
- `dados/` guarda os CSVs coletados (diário e 30 min)
- `relatorio.html` é o relatório mais recente

Ativos dos EUA: `"AAPL": "nasdaq"` ou `"JPM": "sp500"`.
Ativos do Brasil: só o código, por exemplo `"PETR4"`.

A coleta roda pelo GitHub Actions (`.github/workflows/coleta.yml`): cripto a cada 15 min, 24h; Brasil e EUA de hora em hora, seg-sex, das 10h às 18h de Brasília.
