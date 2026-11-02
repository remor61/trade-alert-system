"""Summary tables + current state for one symbol. usage: DATA=../SYM python3 report.py"""
import os, numpy as np, pandas as pd
import bt
W, D = bt.W, bt.D
R = pd.read_csv(os.path.join(bt.BASE, 'trades.csv'))
C = R[R.reason != 'open'].copy()
C['Rf'] = (C.exit - C.entry) / np.maximum(C.entry - C.stop_px, 0.01 * C.entry)
def s(g):
    if len(g) == 0: return '  0 |   -  |    -   |   -  '
    return f"{len(g):>3} | {(g.ret>0).mean()*100:3.0f}% | {g.ret.mean()*100:+5.1f}% | {g.Rf.mean():+.2f}"

# touch forward returns by trend
Wn = W.copy(); n = len(Wn)
ev = Wn[Wn.touch & (Wn.index < n - 1)]
print('== retorno após toque (fechamento) | MM50 subindo vs não')
for k, g in ev.groupby('trend'):
    parts = []
    for h in [8, 13, 26]:
        r = np.array([Wn.c[i + h] / Wn.c[i] - 1 for i in g.index if i + h < n])
        parts.append(f"{h}w {r.mean()*100:+.1f}% ({(r>0).mean()*100:.0f}%) n={len(r)}")
    print('  subindo' if k else '  caindo', ' | '.join(parts))
for h in [13]:
    u = (Wn.c.shift(-h) / Wn.c - 1).dropna(); print(f'  baseline {h}w {u.mean()*100:+.1f}% ({(u>0).mean()*100:.0f}%)')

print('\n== ENTRADA (stop último fundo, alvo último topo): todos || MM50 subindo')
for tf, tr in [('W','close'),('W','open'),('W','brk'),('W','123'),('W','inside'),('W','trap'),('D','brk'),('D','123'),('D','inside'),('D','trap')]:
    g = C[(C.tf==tf)&(C.trig==tr)&(C.stop=='pivot')&(C.tgt=='topo')]
    print(f'{tf} {tr:7s} {s(g)}  ||  {s(g[g.trend])}')
print('\n== STOP (MM50 subindo, alvo topo)')
for tf, tr in [('W','brk'),('W','trap'),('D','brk'),('D','inside'),('D','123'),('D','trap')]:
    g = C[(C.tf==tf)&(C.trig==tr)&(C.tgt=='topo')&C.trend]
    a, b = g[g.stop=='pivot'], g[g.stop=='setup']
    print(f'{tf} {tr:7s} fundo {s(a)} risco {a.risk_pct.mean()*100:.1f}% || setup {s(b)} risco {b.risk_pct.mean()*100:.1f}%')
print('\n== ALVO (MM50 subindo, stop fundo, gatilhos brk/123/inside/trap W+D)')
for t in ['topo','2R','fib100','fib161','tempo13','tempo26']:
    g = C[(C.stop=='pivot')&(C.tgt==t)&C.trend&C.trig.isin(['brk','123','inside','trap'])]
    print(f'{t:8s} {s(g)}  sem {g.weeks.mean():.1f}')
print('\n== por período (MM50 subindo, D brk fundo topo | W brk setup topo)')
for cb in [('D','brk','pivot','topo'),('W','brk','setup','topo')]:
    g = C[(C.tf==cb[0])&(C.trig==cb[1])&(C.stop==cb[2])&(C.tgt==cb[3])&C.trend].copy()
    y = pd.to_datetime(g.ep_date).dt.year
    g['per'] = pd.cut(y, [1990, 2009, 2017, 2030], labels=['<=2009', '2010-17', '2018+'])
    print(cb, ' | '.join(f'{p}: {s(x)}' for p, x in g.groupby('per', observed=True)))

# current state
print('\n== ESTADO ATUAL')
cur = n - 1
print(W.tail(4)[['o','h','l','c','K','D','sma50','trend']].assign(date=W.date.tail(4).dt.date).round(2).to_string())
f = (100 * (W.c - W.l.rolling(8).min()) / (W.h.rolling(8).max() - W.l.rolling(8).min()))
f1, f2 = f.iloc[-3], f.iloc[-2]
l8, h8 = W.l.iloc[-8:].min(), W.h.iloc[-8:].max()
print('fechamento máx p/ K<=20 nesta semana:', round(l8 + (60 - f1 - f2) / 100 * (h8 - l8), 2))
px = W.c.iloc[-1]
print('preço', px, '| último fundo', bt.last_pivot_low_below(px, cur), '| último topo', bt.last_pivot_high_above(px, cur), '| fib', bt.fib_targets(cur))
print(D.tail(6)[['o','h','l','c']].assign(date=D.date.tail(6).dt.date).round(2).to_string())
