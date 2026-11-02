"""Divisão fixa de meses: metade de cada ano sorteada para DESENVOLVIMENTO (ajustar filtros), a outra metade RESERVADA (validação final).
Seed 20261102, estratificado por ano (6 meses por ano), 1960–2040. Classificar cada trade pelo mês da ENTRADA."""
import numpy as np, pandas as pd
SEED = 20261102
def make():
    out = {}
    for y in range(1960, 2041):
        rng = np.random.default_rng([SEED, y])  # sorteio próprio de cada ano: estender o período não muda os anos já sorteados
        m = sorted(rng.choice(np.arange(1, 13), 6, replace=False).tolist())
        out[y] = ''.join('D' if i in m else 'R' for i in range(1, 13))
    return out
SPLIT = make()
def is_dev(dates):
    d = pd.to_datetime(pd.Series(dates))
    return np.array([SPLIT[y][m - 1] == 'D' for y, m in zip(d.dt.year, d.dt.month)])
if __name__ == '__main__':
    for y, s in SPLIT.items(): print(y, s)
