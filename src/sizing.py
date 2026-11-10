"""Sizing comum: risco mais perto de 100 USD dentro de 85–115 (arredonda para cima ou para baixo); se nenhuma
quantidade cabe na faixa, a de baixo (mínimo 1); sem alavancagem (posição máxima = banca de 10.000 USD)."""
import numpy as np
BANK, RISK, RLO, RHI = 10_000, 100, 85, 115

def shares(entry, stop):
    entry, d = np.asarray(entry, float), np.asarray(entry, float) - np.asarray(stop, float)
    cap = np.maximum(np.floor(BANK / entry), 1); lo_q = np.minimum(np.floor(RISK / d), cap); hi_q = np.minimum(np.ceil(RISK / d), cap)
    ok = lambda q: (q >= 1) & (q * d >= RLO) & (q * d <= RHI)
    sh = np.where(ok(lo_q) & (~ok(hi_q) | ((RISK - lo_q * d) <= (hi_q * d - RISK))), lo_q, np.where(ok(hi_q), hi_q, lo_q))
    return np.maximum(sh, 1)
