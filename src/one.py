"""Full skill run for one symbol: backtest (bt.py), OB confluence tags, current state. usage: DATA=dir python3 one.py TICKER"""
import os, sys, json, numpy as np, pandas as pd
import bt
from ob import find_obs, valid_at, nearest

tick = sys.argv[1]
W, D = bt.W, bt.D
n = len(W); cur = n - 1
Wo, Wh, Wl, Wc = (W[x].values for x in 'ohlc')
Do, Dh, Dl, Dc = (D[x].values for x in 'ohlc')
WOB = find_obs(Wo, Wh, Wl, Wc, k=2)
DOB = find_obs(Do, Dh, Dl, Dc, k=3)

# ---------- trades + OB confluence ----------
R = pd.read_csv(os.path.join(bt.BASE, 'trades.csv'))
R['sym'] = tick
d_of_w = {}
for k, wi in enumerate(D['wi'].values):
    d_of_w.setdefault(int(wi), k)

def ob_flag_w(i0, ewi):
    """weekly bull OB valid at the week before entry, formed before the touch, whose zone the episode reached."""
    lo = Wl[i0:ewi + 1].min()
    for ob in valid_at(WOB, max(ewi - 1, i0), 'bull'):
        if ob['bos'] < i0 and lo <= ob['hi'] and lo >= ob['lo'] - 0.5 * (ob['hi'] - ob['lo']):
            return True
    return False

def ob_flag_d(i0, ekind, eidx, ewi):
    d0 = d_of_w.get(int(i0))
    if d0 is None: return False
    de = eidx if ekind == 'D' else d_of_w.get(int(ewi), len(D) - 1)
    if de <= d0: de = d0 + 1
    lo = Dl[d0:de + 1].min()
    for ob in valid_at(DOB, de - 1, 'bull'):
        if ob['bos'] < d0 and lo <= ob['hi'] and lo >= ob['lo'] - 0.5 * (ob['hi'] - ob['lo']):
            return True
    return False

if len(R):
    keys = R[['i0', 'ewi', 'ekind', 'eidx']].drop_duplicates()
    fw = {tuple(r): ob_flag_w(r[0], r[1]) for r in keys.itertuples(index=False)}
    fd = {tuple(r): ob_flag_d(r[0], r[2], r[3], r[1]) for r in keys.itertuples(index=False)}
    R['obw'] = [fw[(a, b, c, d)] for a, b, c, d in zip(R.i0, R.ewi, R.ekind, R.eidx)]
    R['obd'] = [fd[(a, b, c, d)] for a, b, c, d in zip(R.i0, R.ewi, R.ekind, R.eidx)]
    R.to_csv(os.path.join(bt.BASE, 'trades.csv'), index=False)

C = R[R.reason != 'open'].copy() if len(R) else R
if len(C):
    C['Rf'] = (C.exit - C.entry) / np.maximum(C.entry - C.stop_px, 0.01 * C.entry)

def stat(g):
    if len(g) == 0: return None
    return dict(n=int(len(g)), win=float((g.ret > 0).mean()), ret=float(g.ret.mean()), R=float(g.Rf.mean()),
                risk=float(g.risk_pct.mean()))

touch_idx = [i for i in W.index[W.touch] if i < cur]
def fwd(idx, h):
    r = [Wc[i + h] / Wc[i] - 1 for i in idx if i + h < n]
    return (float(np.mean(r)), float(np.mean(np.array(r) > 0)), len(r)) if r else None
up = [i for i in touch_idx if W.trend[i]]; dn = [i for i in touch_idx if not W.trend[i]]
base13 = (W.c.shift(-13) / W.c - 1).dropna()

combos = {}
if len(C):
    for (tf, trig, stop, tgt), g in C.groupby(['tf', 'trig', 'stop', 'tgt']):
        combos[f'{tf}|{trig}|{stop}|{tgt}'] = dict(all=stat(g), up=stat(g[g.trend]))
best = None
for k, v in combos.items():
    s = v['up']
    if s and s['n'] >= 8 and k.split('|')[1] not in ('close', 'open') and k.split('|')[3] in ('topo', '2R', 'fib100', 'fib161'):
        if best is None or s['R'] > combos[best]['up']['R']: best = k

# ---------- current state ----------
K, Dk = float(W.K.iloc[-1]), float(W.D.iloc[-1])
Kprev = float(W.K.iloc[-2])
f = 100 * (W.c - W.l.rolling(8).min()) / (W.h.rolling(8).max() - W.l.rolling(8).min())
l8, h8 = Wl[-8:].min(), Wh[-8:].max()
close_need = float(l8 + (60 - f.iloc[-3] - f.iloc[-2]) / 100 * (h8 - l8))
px = float(Wc[-1])
if Kprev <= 20: status = 'toque confirmado (episódio em curso)'
elif K <= 20: status = 'toque em formação'
elif K <= 35 and K < Kprev: status = 'aproximando'
else: status = '-'
stop, _ = bt.last_pivot_low_below(px, cur)
top, _ = bt.last_pivot_high_above(px, cur)
f100, f161 = bt.fib_targets(cur)
wb, wr = nearest(WOB, cur, px, 2)
db, dr = nearest(DOB, len(D) - 1, px, 2)
z = lambda obs, df: [dict(date=str(pd.to_datetime(df.t.iloc[o['i']], unit='s').date()), lo=round(float(o['lo']), 2),
                          hi=round(float(o['hi']), 2), touched=o['touch'] is not None) for o in obs]
in_ob_w = any(o['lo'] <= Wl[-3:].min() <= o['hi'] or o['lo'] <= px <= o['hi'] for o in wb)
in_ob_d = any(o['lo'] <= Dl[-10:].min() <= o['hi'] or o['lo'] <= px <= o['hi'] for o in db)
state = dict(px=px, K=K, D=Dk, Kprev=Kprev, status=status, close_need=close_need, trend=bool(W.trend.iloc[-1]),
             sma50=float(W.sma50.iloc[-1]), w_last_high=float(Wh[-2]), w_cur_high=float(Wh[-1]), w_cur_low=float(Wl[-1]),
             w_prev_low=float(Wl[-2]), d_high=float(Dh[-1]), d_prev_high=float(Dh[-2]),
             stop=float(stop) if stop else None, top=float(top) if top else None,
             fib100=float(f100) if f100 else None, fib161=float(f161) if f161 else None,
             wob_bull=z(wb, W), wob_bear=z(wr, W), dob_bull=z(db, D), dob_bear=z(dr, D),
             in_ob_w=bool(in_ob_w), in_ob_d=bool(in_ob_d),
             last_date=str(pd.to_datetime(D.t.iloc[-1], unit='s').date()))

out = dict(sym=tick, weeks=n, first=str(W.date.iloc[0].date()), touches=len(touch_idx),
           fwd13_up=fwd(up, 13), fwd13_dn=fwd(dn, 13), base13=float(base13.mean()),
           best=best, combos=combos, state=state)
json.dump(out, open(os.path.join(bt.BASE, 'summary.json'), 'w'))
print(tick, 'ok', len(touch_idx), 'toques', best)
