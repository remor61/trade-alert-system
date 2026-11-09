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
| `src/campanhas.py`, `src/sizing.py` | Estratégia **Campanhas** (independente do setup Slow Stoch): backtest por ativo de cada gatilho e de todos juntos, com as 5 saídas. `sizing.py` é o sizing comum às duas estratégias. |
| `tradingview/campanhas.pine` | Indicador do TradingView com os 7 gatilhos da Campanhas (setups armados, compras executadas e, opcional, sinais de venda). |
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
Banca de 10.000 USD, risco de ~100 USD por trade: quantidade = ⌊100 ÷ (entrada − stop)⌋ ou ⌈100 ÷ (entrada − stop)⌉, a que deixar o risco mais perto de 100 USD dentro de 85–115 USD (se nenhuma cabe, a de baixo; mínimo 1), sem alavancagem (posição máxima de 10.000 USD), sem custos e sem juros compostos. Reportar acerto, retorno total e por trade em % da banca, ganho e perda médios, risco/retorno (ganho médio ÷ perda média), profit factor e drawdown máximo. Não usar R.

### Setup
- **Toque**: %K lento semanal cruza para ≤ 20. O episódio dura enquanto ficar ≤ 20.
- **Filtro de tendência**: MM50 semanal subindo (MM50 > MM50 de 4 semanas atrás).
- **Gatilhos**: 123, inside bar (stop na mínima do candle-mãe), trap (sem filtro do estocástico), rompimento simples; no semanal e no diário (diário só com o semanal ≤ 20).
- **Cunha descendente no diário**: gatilho à parte, sem toque do Slow Stoch. O único filtro é a MM50 semanal subindo, medida na última semana fechada antes do rompimento. Entrada no fechamento do primeiro candle diário acima da linha superior da cunha (regra da cunha abaixo). Mesmo stop e alvos dos outros gatilhos. No código é o `ns` diário (`bt_wedge.py`, T3).
- **Stop**: último fundo semanal abaixo da entrada (pivô de 2 candles de cada lado; mínima da correção ou pivô não violado mais recente).
- **Alvos**: último topo, 2× o risco, Fibonacci 100% e 161,8%, saída por tempo (13 e 26 semanas).
- **Order blocks**: só zonas de interesse; não melhoraram o resultado como filtro.

### Cunhas (gatilho no diário; ainda fora da skill)
- Linhas por 2 pivôs de alta e 2 de baixa, ≥ 2 toques em cada linha, convergentes. Formato: inclinação inferior ÷ superior ≥ 0,0485 (limite definido pela cunha da TSLA dez/2024–abr/2025).
- Entrada no fechamento do primeiro candle acima da linha superior, sem olhar o futuro.
- O rompimento consome a estrutura: uma cunha nova só vale se o topo de origem vier depois do último rompimento aceito, separadamente no diário e no semanal.
- Volume no rompimento (≥ 1,2× a média de 20) não ajudou.

## Estratégia Campanhas

Estratégia própria, sem relação com o setup Slow Stoch. Só compras, tudo no diário. Mesma banca, sizing e regra de meses D/R acima.

- **Filtro**: MM50 diária subindo (MM50 > MM50 de 4 pregões atrás), medida no último candle fechado antes da entrada. O preço não precisa estar acima da média.
- **Entrada**: ordem stop 1 tick acima do preço de gatilho (tick = 0,01, ou 0,05% do preço em preços muito baixos), no candle seguinte ao sinal. Nos gatilhos de rompimento (todos menos o gap) o candle da entrada precisa passar pelo preço de gatilho: se abrir acima dele (gap), não há trade.
- **Gatilhos**:
  1. **123 de compra**: mínima do 2º candle abaixo das do 1º e do 3º; gatilho na máxima do 3º; stop na mínima do 2º.
  2. **Inside bar**: candle dentro do anterior; gatilho na máxima do inside; stop na mínima do candle-mãe.
  3. **Trap**: candle que perde o último fundo de 123 ainda não violado, até 50 candles atrás, e deixa sombra inferior de pelo menos 70% da amplitude do candle; gatilho na máxima dele, no candle seguinte (ou no segundo, se o primeiro for inside); stop na mínima do candle da armadilha.
  4. **Barra vermelha ignorada**: único candle vermelho depois de pelo menos 3 brancos; gatilho na máxima dele, que precisa estar acima da MME8; stop na mínima.
  5. **Sombra superior ignorada**: sombra superior ≥ 50% da amplitude do candle; gatilho na máxima, acima da MME8; stop na mínima.
  6. **Trap na MM50**: mínima toca ou fura a MM50 e o candle fecha acima dela (sombra inferior), vindo de fechamento acima; gatilho na máxima; stop na mínima.
  7. **Gap de compra**: abertura abaixo da mínima anterior; compra quando o preço volta à mínima anterior + 1 tick no próprio candle do gap (o que abriu abaixo); stop na mínima do candle que fechou o gap, conhecida até a entrada (candle de baixa: a abertura).
- **Saídas** (cada teste roda com todas): topo anterior (último topo diário acima da entrada; sem topo, 2R), 2R, 3R, sinal de venda (qualquer gatilho espelhado formado depois da entrada) e Slow Stoch 14/3 com %K > 80 no fechamento. O stop vale sempre; saída por tempo após 260 pregões.
- **Execução**: uma posição por vez por ativo; com posição aberta, novos sinais são ignorados. Banca independente por ativo.
- **Gap e dado diário**: o stop do gap fica muito perto da entrada (~0,4–0,7% do preço, mediana) e o resultado depende da ordem dos preços dentro do dia. Na convenção do repositório (candle de alta: abertura → mínima → máxima → fechamento) o gap é o melhor gatilho; no limite pessimista (`CAMP_GAP=pior`: a mínima sempre veio depois da entrada) é o pior. Por isso o teste "todos sem gap" existe à parte. `CAMP_GAP=1h` ou `15m` resolve o dia da entrada com barras intradiárias (`data/<TICKER>/h1.csv`, desde jan/2023; `m15.csv`, desde fev/2026); o sufixo `_pior` dá o limite pessimista dentro da barra. Nos 15 ativos do estudo, com o gap fechando no próprio candle: 1h desde 2023 +86% a +157% (pior dentro da hora −16% a −94%); 15 min desde fev/2026 +12% a +23% (pior dentro da barra −8% a +5%). A vantagem do gap existe, mas é bem menor do que o diário sugere e a amostra intradiária ainda é curta.
- Rodar: `python src/campanhas.py [--desde AAAA-MM-DD] [TICKER ...]` grava `results/campanhas_*.csv`.

## Dados
`data/` e `results/` ficam fora do git: os dados são do TradingView e podem ser refeitos com `import_tv.py`.
