"""Wedge tests for one symbol. usage: DATA=dir python3 bt_wedge.py TICKER
T1/T2: falling-wedge breakout as an extra trigger inside Slow Stoch episodes (D and W); rising-wedge breakdown
       flags (block buys) computed for every trade (base triggers + wedge).
T3:    every falling-wedge breakout (no Slow Stoch), with the same block flags.
Each in two modes: no volume / breakout bar volume >= 1.2x MA20."""
import os, sys, numpy as np, pandas as pd
import bt
from wedge2 import detect_fall, atr_arr, vol_ok

tick = sys.argv[1]
W, D = bt.W, bt.D
arr = {'W': {x: W[x].values.astype(float) for x in 'ohlcv'}, 'D': {x: D[x].values.astype(float) for x in 'ohlcv'}}
FALL, RISE = {}, {}
for tf in ('W', 'D'):
    A = arr[tf]; a = atr_arr(A['h'], A['l'], A['c'])
    f = detect_fall(A['o'], A['h'], A['l'], A['c'], a, tf)
    r = detect_fall(-A['o'], -A['l'], -A['h'], -A['c'], a, tf)
    for w in f: w['vol'] = vol_ok(A['v'], w['b'])
    for w in r: w['vol'] = vol_ok(A['v'], w['b'])
    FALL[tf], RISE[tf] = f, r

DWI = D['wi'].values
# --- rompimento consome a estrutura: cunha só vale se o topo de origem vier depois do último rompimento aceito (D e W juntos)
_lastday = {}
for _k, _wi in enumerate(D['wi'].values): _lastday[int(_wi)] = _k
def _consume(groups):
    items = []
    for tf, L in groups.items():
        t = (W if tf == 'W' else D).t.values
        for w in L:
            tb = D.t.values[_lastday.get(w['b'], len(D) - 1)] if tf == 'W' else t[w['b']]
            items.append((tb, t[w['start']], tf, w))
    items.sort(key=lambda x: x[0]); keep = {tf: [] for tf in groups}; last = -1
    for tb, ts, tf, w in items:
        if os.environ.get('NOCONSUME') or ts > last:
            keep[tf].append(w); last = max(last, tb)
    return keep
FALL = {tf: _consume({tf: FALL[tf]})[tf] for tf in FALL}; RISE = {tf: _consume({tf: RISE[tf]})[tf] for tf in RISE}  # timeframes isolados
last_d_of_w = {}
for k, wi in enumerate(DWI): last_d_of_w[int(wi)] = k
first_d_of_w = {}
for k, wi in enumerate(DWI): first_d_of_w.setdefault(int(wi), k)
RB = {(tf, vm): np.array([w['b'] for w in RISE[tf] if (w['vol'] or not vm)]) for tf in ('W', 'D') for vm in (False, True)}

def blocked(td, tw, vm):
    """rising-wedge breakdown in the last 20 known daily bars or last 8 known weekly bars"""
    bd, bw = RB[('D', vm)], RB[('W', vm)]
    return bool(((bd >= td - 19) & (bd <= td)).any() or ((bw >= tw - 7) & (bw <= tw)).any())

def make(tf, b, px, setup_stop, known_w, ewi, ep, trig):
    recs = []
    pstop, _ = bt.last_pivot_low_below(px, known_w)
    ph, _ = bt.last_pivot_high_above(px, known_w)
    f100, f161 = bt.fib_targets(known_w)
    for sname, st in {'pivot': pstop, 'setup': setup_stop}.items():
        if st is None or st >= px: continue
        risk = px - st
        tgts = {'topo': ph if (ph and ph > px) else None, '2R': px + 2 * risk,
                'fib100': f100 if (f100 and f100 > px) else None, 'fib161': f161 if (f161 and f161 > px) else None,
                'tempo13': None, 'tempo26': None}
        for tname, tg in tgts.items():
            if tname in ('topo', 'fib100', 'fib161') and tg is None: continue
            mw = 13 if tname == 'tempo13' else (26 if tname == 'tempo26' else bt.MAXW)
            res = bt.simulate(px, ewi, 'W' if tf == 'W' else 'D', b, st, tg, mw, None)
            if res is None: continue
            recs.append(dict(ep, sym=tick, tf=tf, trig=trig, edate=str(pd.to_datetime((W if tf == 'W' else D).t.iloc[b], unit='s').date()), stop=sname, tgt=tname, entry=px, stop_px=st, tgt_px=tg,
                             risk_pct=risk / px, **res))
    return recs

def known(tf, b):
    """(known daily idx, known weekly idx, entry week) for an entry at the close of bar b"""
    if tf == 'W': return last_d_of_w.get(b, len(D) - 1), b, b
    return b, int(DWI[b]) - 1, int(DWI[b])

out = []
# ---------- T1/T2: inside episodes ----------
for (i0, iend) in bt.episodes:
    ep = dict(ep_date=W.at[i0, 'date'].date(), i0=i0, iend=iend, trend=bool(W.at[i0, 'trend']))
    d0 = first_d_of_w.get(i0 + 1); d1 = last_d_of_w.get(iend + 1)
    for vm in (False, True):
        trig = 'wedge_vol' if vm else 'wedge'
        cw = [w for w in FALL['W'] if i0 <= w['b'] <= iend + 1 and (w['vol'] or not vm)]
        if cw:
            w = cw[0]; b = w['b']; td, tw, ewi = known('W', b)
            for r in make('W', b, arr['W']['c'][b], w['stop_setup'], tw, ewi, ep, trig):
                r['blk'] = blocked(td, tw, False); r['blkv'] = blocked(td, tw, True); out.append(r)
        if d0 is not None and d1 is not None:
            cd = [w for w in FALL['D'] if d0 <= w['b'] <= d1 and (w['vol'] or not vm)]
            if cd:
                w = cd[0]; b = w['b']; td, tw, ewi = known('D', b)
                for r in make('D', b, arr['D']['c'][b], w['stop_setup'], tw, ewi, ep, trig):
                    r['blk'] = blocked(td, tw, False); r['blkv'] = blocked(td, tw, True); out.append(r)

# ---------- T3: no Slow Stoch ----------
for tf in ('W', 'D'):
    gap = 4 if tf == 'W' else 10
    for vm in (False, True):
        lastb = -10 ** 9
        for w in FALL[tf]:
            if vm and not w['vol']: continue
            b = w['b']
            if b - lastb < gap: continue
            td, tw, ewi = known(tf, b)
            if tw < 55: continue
            lastb = b
            ep = dict(ep_date=pd.to_datetime((W if tf == 'W' else D).t.iloc[b], unit='s').date(), i0=-1, iend=-1,
                      trend=bool(W.trend.iloc[tw]))
            for r in make(tf, b, arr[tf]['c'][b], w['stop_setup'], tw, ewi, ep, 'ns_vol' if vm else 'ns'):
                r['blk'] = blocked(td, tw, False); r['blkv'] = blocked(td, tw, True); out.append(r)

pd.DataFrame(out).to_csv(os.path.join(bt.BASE, 'wedge_trades.csv'), index=False)

# ---------- block flags for base trades ----------
R = pd.read_csv(os.path.join(bt.BASE, 'trades.csv'))
fl, flv = [], []
for trig, ek, ei, ew, i0 in zip(R.trig, R.ekind, R.eidx, R.ewi, R.i0):
    if trig in ('close', 'open'):
        tw = i0; td = last_d_of_w.get(i0, len(D) - 1)
    elif ek == 'D':
        td = ei - 1; tw = ew - 1
    else:
        tw = ew - 1; td = last_d_of_w.get(tw, len(D) - 1)
    fl.append(blocked(td, tw, False)); flv.append(blocked(td, tw, True))
R['blk'] = fl; R['blkv'] = flv; R['sym'] = tick
R['edate'] = [str(pd.to_datetime((D.t.iloc[int(ei)] if ek == 'D' else W.t.iloc[int(ew)]), unit='s').date()) for ek, ei, ew in zip(R.ekind, R.eidx, R.ewi)]
R.to_csv(os.path.join(bt.BASE, 'trades.csv'), index=False)
print(tick, 'cunhas D', len(FALL['D']), len(RISE['D']), 'W', len(FALL['W']), len(RISE['W']), 'trades', len(out))
