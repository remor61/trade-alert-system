# Instruções para o Claude

- Responda em português.
- Este repositório implementa o método descrito no README e na skill `setup-slowstoch-sobrevenda`. Antes de mudar uma regra, leia o README.
- **Backtests usam só os meses de desenvolvimento** (`MONTHS=D`, padrão de `src/config.py`). Nunca rode com `MONTHS=R` ou `MONTHS=ALL` para escolher filtros. Os meses reservados só entram na validação final, quando o usuário disser que a configuração está fechada; nesse caso mostre D e R lado a lado e registre no README a data e a configuração validada.
- **Resultados em banca de 10.000 USD com risco de ~100 USD por trade** (`src/bank.py`). Não reportar em R.
- Dados de mercado vêm do conector TradingView (`mcp-tv-get-ohlcv`, diário, `date_from: 2000-01-01`, `count: 7000`, `format: columns`). Depois de buscar, rode `python src/import_tv.py --claude-logs`. Nunca digite preços à mão.
- `data/` e `results/` não vão para o git.
- Cada mudança de regra em um commit próprio, com o resultado (meses D) na mensagem.
- Cunhas ainda estão em estudo: não adicionar à skill até o usuário pedir.
