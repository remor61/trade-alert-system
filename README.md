# trade-alert-system

Backtest e monitoramento do setup de compra em sobrevenda do **Slow Stochastic 8/3/3 semanal**, com gatilhos 123, inside bar, trap, rompimento e cunhas, stop no último fundo e alvos por estrutura. Os dados vêm do TradingView.

## Estrutura

| Pasta / arquivo | O que é |
|---|---|
| `src/config.py` | Caminhos (`data/`, `results/`), ativos excluídos do pool e o filtro de meses (`MONTHS`). |
| `src/import_tv.py` | Monta `data/<TICKER>/d.csv` e `w.csv` a partir das respostas do TradingView (`mcp-tv-get-ohlcv`). |
| `src/stoch.py` | Slow Stoch 8/3/3. |
| `src/bt.py` | Backtest base: episódios do Slow Stoch, gatilhos 123 / inside / trap / rompimento (semanal e diário), stop no último fundo, alvos, simulador com barras diárias. Grava `data/<TICKER>/trades.csv`. |
| `src/ob.py` | Order blocks (zonas de interesse, não gatilho). |
| `src/one.py`, `src/report.py` | Situação atual de um ativo e tabelas por ativo. |
| `src/wedge2.py` | Detector de cunhas sem olhar o futuro (descendente; ascendente pelo espelho da série). |
| `src/bt_wedge.py` | Testes das cunhas: T1 (gatilho dentro do episódio), T2 (cunha ascendente bloqueia compra), T3 (sem Slow Stoch). Grava `wedge_trades.csv`. |
| `src/split.py` | Sorteio fixo dos meses de desenvolvimento (D) e reservados (R). |
| `src/bank.py` | Relatório padrão: banca de 10.000 USD, risco de ~100 USD por trade. |
| `src/pool_wedge.py` | Análise exploratória das cunhas (versão antiga, em R). |
| `src/run_all.py` | Roda `bt_wedge.py` (que inclui `bt.py`) em todos os ativos em paralelo. |
| `src/export_vis.py`, `vis/` | Página interativa com cunhas, sinais e trades de um ativo. |
| `watchlist.txt` | Ativos da watchlist "US Stocks" do TradingView. |

## Como rodar

```bash
pip install -r requirements.txt

# 1. dados: salve as respostas do TradingView (mcp-tv-get-ohlcv, interval 1D, format columns, date_from 2000-01-01, count 7000)
#    em arquivos, ou deixe o Claude Code buscar e depois importe dos logs da sessão:
python src/import_tv.py --claude-logs        # ou: python src/import_tv.py respostas/*.json

# 2. backtest em todos os ativos
python src/run_all.py

# 3. relatório (meses de desenvolvimento por padrão)
python src/bank.py

# 4. gráfico de um ativo
DATA=data/MSTR python src/export_vis.py MSTR
python vis/build_page.py MSTR 2021-06-02     # abre results/cunhas_MSTR.html
```

## Regras do método

### Meses de desenvolvimento e reservados
Metade dos meses de cada ano foi sorteada para **desenvolvimento** (seed 20261102, ver `src/split.py`). Todo ajuste de filtro, gatilho, stop ou alvo usa só esses meses (`MONTHS=D`, padrão). Os meses **reservados** (`MONTHS=R`) só são usados na validação final, uma vez, quando a configuração estiver fechada. Cada trade é classificado pelo mês da entrada. As decisões tomadas antes de 02/11/2026 (filtro MM50, order blocks, gatilhos atuais, cunhas) já viram todos os meses.

### Medida de resultado
Banca de 10.000 USD, risco de ~100 USD por trade: quantidade = ⌊100 ÷ (entrada − stop)⌋, sem alavancagem (posição máxima de 10.000 USD), sem custos e sem juros compostos. Reportar acerto, retorno total e por trade em % da banca, ganho e perda médios, risco/retorno (ganho médio ÷ perda média), profit factor e drawdown máximo. Não usar R.

### Setup
- **Toque**: %K lento semanal cruza para ≤ 20. O episódio dura enquanto ficar ≤ 20.
- **Filtro de tendência**: MM50 semanal subindo (MM50 > MM50 de 4 semanas atrás).
- **Gatilhos**: 123, inside bar (stop na mínima do candle-mãe), trap (sem filtro do estocástico), rompimento simples; no semanal e no diário (diário só com o semanal ≤ 20).
- **Stop**: último fundo semanal abaixo da entrada (pivô de 2 candles de cada lado; mínima da correção ou pivô não violado mais recente).
- **Alvos**: último topo, 2× o risco, Fibonacci 100% e 161,8%, saída por tempo (13 e 26 semanas).
- **Order blocks**: só zonas de interesse; não melhoraram o resultado como filtro.

### Cunhas (em estudo, ainda fora da skill)
- Linhas por 2 pivôs de alta e 2 de baixa, ≥ 2 toques em cada linha, convergentes. Formato: inclinação inferior ÷ superior ≥ 0,0485 (limite definido pela cunha da TSLA dez/2024–abr/2025).
- Entrada no fechamento do primeiro candle acima da linha superior, sem olhar o futuro.
- O rompimento consome a estrutura: uma cunha nova só vale se o topo de origem vier depois do último rompimento aceito, separadamente no diário e no semanal.
- Volume no rompimento (≥ 1,2× a média de 20) não ajudou.

## Dados
`data/` e `results/` ficam fora do git: os dados são do TradingView e podem ser refeitos com `import_tv.py`.
