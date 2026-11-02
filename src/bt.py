import pandas as pd, numpy as np
from stoch import slow_stoch

TICK = 0.01
def tick(p):
    return min(TICK, p * 0.0005)  # avoid huge relative ticks on split-adjusted penny prices
MAXW = 52

import os
BASE = os.environ.get('DATA', '.')
W = pd.read_csv(os.path.join(BASE, 'w.csv') if BASE != '.' else 'qqq_w.csv')
D = pd.read_csv(os.path.join(BASE, 'd.csv') if BASE != '.' else 'qqq_d.csv')
W = slow_stoch(W)
W['sma50'] = W['c'].rolling(50).mean()
W['trend'] = W['sma50'] > W['sma50'].shift(4)
W['trend1'] = W['sma50'] > W['sma50'].shift(1)
W['trend10'] = W['sma50'] > W['sma50'].shift(10)
W['above40'] = W['c'] > W['c'].rolling(40).mean()
W['date'] = pd.to_datetime(W['t'], unit='s')
D['date'] = pd.to_datetime(D['t'], unit='s')
D['wi'] = np.searchsorted(W['t'].values, D['t'].values, side='right') - 1
NW = len(W)

# ---------- pivots (2 bars each side), confirmed at i+2 ----------
def pivots(lo, hi):
    n = len(lo); pl = np.zeros(n, bool); ph = np.zeros(n, bool)
    for i in range(2, n - 2):
        if lo[i] < min(lo[i-2], lo[i-1]) and lo[i] <= min(lo[i+1], lo[i+2]): pl[i] = True
        if hi[i] > max(hi[i-2], hi[i-1]) and hi[i] >= max(hi[i+1], hi[i+2]): ph[i] = True
    return pl, ph
WPL, WPH = pivots(W['l'].values, W['h'].values)

WL = W['l'].values
def last_pivot_low_below(price, known_wi):
    """'Último fundo mais baixo que o preço': most recent bottom below price, among
    (a) the correction low = lowest low since the last confirmed weekly pivot high, and
    (b) confirmed weekly pivot lows formed after that correction low and never violated since.
    Falls back to older unviolated pivots only if (a)/(b) are not below price."""
    B = None
    for p in range(known_wi - 2, max(known_wi - 300, 1), -1):
        if WPH[p]: B = p; break
    if B is not None:
        q = B + int(np.argmin(WL[B:known_wi + 1]))
        best = (WL[q], q) if WL[q] < price else None
        for p in range(known_wi - 2, q, -1):
            if WPL[p] and WL[p] < price and WL[p + 1:known_wi + 1].min() > WL[p]:
                best = (WL[p], p); break
        if best: return best
    for p in range(known_wi - 2, max(known_wi - 300, 1), -1):
        if WPL[p] and WL[p] < price and WL[p + 1:known_wi + 1].min() > WL[p]:
            return WL[p], p
    return None, None

def last_pivot_high_above(price, known_wi):
    for p in range(known_wi - 2, max(known_wi - 300, 1), -1):
        if WPH[p] and W.at[p, 'h'] > price: return W.at[p, 'h'], p
    return None, None

def fib_targets(known_wi):
    # B = last confirmed pivot high; A = last confirmed pivot low before B; C = lowest low between B and known_wi
    B = None
    for p in range(known_wi - 2, max(known_wi - 300, 1), -1):
        if WPH[p]: B = p; break
    if B is None: return None, None
    A = None
    for p in range(B - 1, max(B - 300, 1), -1):
        if WPL[p]: A = p; break
    if A is None: return None, None
    leg = W.at[B, 'h'] - W.at[A, 'l']
    C = W.loc[B:known_wi, 'l'].min()
    return C + 1.0 * leg, C + 1.618 * leg

# ---------- path & simulation ----------
DSET = set(D['wi'].unique())
DA = D[['o', 'h', 'l', 'c', 'wi']].to_numpy(float)
WA = W[['o', 'h', 'l', 'c']].to_numpy(float)
D_first_of_week = {}
for k, wi in enumerate(D['wi'].values):
    D_first_of_week.setdefault(int(wi), k)
_cache = {}
def path_after(entry_kind, entry_idx):
    key = (entry_kind, int(entry_idx))
    if key in _cache: return _cache[key]
    bars = []
    if entry_kind == 'D':
        d = entry_idx + 1; wi_last = DA[entry_idx, 4]
    else:
        start_w = entry_idx + 1
        d = D_first_of_week.get(start_w); wi_last = start_w - 1
    if d is not None:
        w0 = wi_last
        while d < len(DA) and DA[d, 4] - wi_last <= 1 and DA[d, 4] - w0 <= MAXW + 2:
            bars.append(tuple(DA[d])); wi_last = DA[d, 4]; d += 1
        start_w = int(wi_last) + 1
        if DA[min(d, len(DA) - 1), 4] - w0 > MAXW + 2:
            _cache[key] = bars; return bars
    for w in range(start_w, min(NW, start_w + MAXW + 2)):
        bars.append((*WA[w], w))
    _cache[key] = bars
    return bars

def _old_path_after(entry_kind, entry_idx):
    """yield (o,h,l,c,weeks_elapsed_marker) bars after entry bar. entry_kind 'D' (daily idx) or 'W' (weekly idx).
    Uses daily bars while contiguous daily data exists, then weekly bars."""
    bars = []
    if entry_kind == 'D':
        d = entry_idx + 1; wi_last = D.at[entry_idx, 'wi']
        while d < len(D) and D.at[d, 'wi'] - wi_last <= 1:
            r = D.loc[d]; bars.append((r.o, r.h, r.l, r.c, r.wi)); wi_last = r.wi; d += 1
        start_w = wi_last + 1
    else:
        start_w = entry_idx + 1
        # if daily data covers the following weeks, use them
        if start_w in DSET:
            d0 = D.index[D['wi'] == start_w][0]
            wi_last = start_w - 1; d = d0
            while d < len(D) and D.at[d, 'wi'] - wi_last <= 1:
                r = D.loc[d]; bars.append((r.o, r.h, r.l, r.c, r.wi)); wi_last = r.wi; d += 1
            start_w = wi_last + 1
    for w in range(start_w, NW):
        r = W.loc[w]; bars.append((r.o, r.h, r.l, r.c, w))
    return bars

def simulate(entry_price, entry_wi, entry_kind, entry_idx, stop, target, max_weeks=MAXW, entry_bar=None):
    """entry_bar = (o,h,l,c) of the bar where the entry happened (None if entry at that bar's close).
    Intrabar path convention: bullish bar O->L->H->C, bearish bar O->H->L->C."""
    if stop is None or stop >= entry_price: return None
    if entry_bar is not None:
        o, h, l, c = entry_bar
        if o >= entry_price:            # gap entry at open: everything after open counts
            seq_after = [l, h] if c >= o else [h, l]
        elif c >= o:                    # O->L->H->C: low came before the breakout
            seq_after = [h]             # after entry only the rest of the rise, then close
        else:                           # O->H->L->C: entry on the way up, then the drop to the low
            seq_after = [h, l]
        for px in seq_after:
            if px <= stop: return dict(exit=stop, reason='stop', weeks=0)
            if target is not None and px >= target: return dict(exit=target, reason='target', weeks=0)
        if c <= stop: return dict(exit=stop, reason='stop', weeks=0)
    prev_c = entry_price
    for (o, h, l, c, wi) in path_after(entry_kind, entry_idx):
        weeks = wi - entry_wi
        if weeks > max_weeks:
            return dict(exit=prev_c, reason='time', weeks=max_weeks)
        if o <= stop: return dict(exit=o, reason='stop', weeks=weeks)
        if target is not None and o >= target: return dict(exit=o, reason='target', weeks=weeks)
        first, second = ((l, 'L'), (h, 'H')) if c >= o else ((h, 'H'), (l, 'L'))
        for px, k in (first, second):
            if k == 'L' and px <= stop: return dict(exit=stop, reason='stop', weeks=weeks)
            if k == 'H' and target is not None and px >= target: return dict(exit=target, reason='target', weeks=weeks)
        prev_c = c
    return dict(exit=None, reason='open', weeks=None)

# ---------- episodes ----------
W['touch'] = (W['K'] <= 20) & (W['K'].shift(1) > 20)
episodes = []
for i0 in W.index[W['touch']]:
    if i0 >= NW - 1: continue  # unconfirmed (current forming week)
    j = i0
    while j + 1 < NW - 1 and W.at[j + 1, 'K'] <= 20: j += 1
    episodes.append((i0, j))

# ---------- pattern finders on a generic OHLC frame ----------
def find_trigger(df, kind, sig_ok, entry_ok, start, end):
    """scan signal bars s in [start,end]; returns (entry_bar, entry_price, setup_stop, signal_bar) or None.
    sig_ok(s): signal bar allowed; entry_ok(e): entry bar allowed."""
    o, h, l = df['o'].values, df['h'].values, df['l'].values
    n = len(df)
    if kind == 'brk':
        for s in range(start, end + 1):
            if s + 1 >= n or not sig_ok(s) or not entry_ok(s + 1): continue
            if h[s + 1] > h[s]:
                return s + 1, max(o[s + 1], h[s] + tick(h[s])), l[s], s
    if kind == '123':
        for c in range(max(start, 2), end + 1):
            if c + 1 >= n or not sig_ok(c) or not entry_ok(c + 1): continue
            a, b = c - 2, c - 1
            if l[b] < l[a] and l[b] < l[c] and h[c + 1] > h[c]:
                return c + 1, max(o[c + 1], h[c] + tick(h[c])), l[b], c
    if kind == 'inside':
        for c in range(max(start, 1), end + 1):
            if c + 1 >= n or not sig_ok(c) or not entry_ok(c + 1): continue
            if h[c] < h[c - 1] and l[c] > l[c - 1] and h[c + 1] > h[c]:
                return c + 1, max(o[c + 1], h[c] + tick(h[c])), l[c - 1], c
    if kind == 'trap':
        # reference bottom: most recent 123 bottom (middle-low b, confirmed at b+1) before t; trap t loses l[b]
        for t in range(max(start, 3), end + 1):
            if not sig_ok(t): continue
            ref = None
            for b in range(t - 1, max(t - 20, 1), -1):
                if b + 1 < t and l[b] < l[b - 1] and l[b] < l[b + 1]: ref = b; break
            if ref is None or not (l[t] < l[ref]): continue
            # previous bar must not already have lost the bottom (t is the first loss... or a new lower one)
            for e in (t + 1, t + 2):
                if e >= n or not entry_ok(e): break
                if e == t + 2:  # t+1 must have been inside (didn't break h[t] nor l[t])
                    if not (h[t + 1] <= h[t] and l[t + 1] >= l[t]): break
                if h[e] > h[t]:
                    return e, max(o[e], h[t] + tick(h[t])), l[t], t
                if l[e] < l[t]: break
    return None

# ---------- run ----------
records = []
for (i0, iend) in episodes:
    ep = dict(ep_date=W.at[i0, 'date'].date(), i0=i0, iend=iend,
              trend=bool(W.at[i0, 'trend']), trend1=bool(W.at[i0, 'trend1']), trend10=bool(W.at[i0, 'trend10']),
              above40=bool(W.at[i0, 'above40']))
    trades = []
    # reference entries
    trades.append(('W', 'close', 'W', i0, W.at[i0, 'c'], i0, None, None))
    trades.append(('W', 'open', 'W', i0 + 1, W.at[i0 + 1, 'o'], i0 + 1, None, W.at[i0 + 1, 'l']))
    # weekly triggers: signal week in run [i0, iend], entry week <= iend+1 (+1 more for trap inside)
    for kind in ['brk', '123', 'inside', 'trap']:
        r = find_trigger(W, kind, lambda s: i0 <= s <= iend, lambda e: e <= iend + 2 and e < NW, max(i0 - 3, 0) if kind in ('123', 'trap') else i0, iend)
        if kind in ('123', 'trap') and r is not None and r[3] < i0: r = None
        if r:
            e, px, st, s = r
            trades.append(('W', kind, 'W', e, px, e, st, W.at[e, 'l']))
    # daily triggers: days in weeks i0+1 .. iend+1 (last completed week K<=20)
    dmask = (D['wi'] >= i0 + 1) & (D['wi'] <= iend + 1)
    if dmask.any():
        didx = D.index[dmask]
        d0, d1 = didx[0], didx[-1]
        for kind in ['brk', '123', 'inside', 'trap']:
            r = find_trigger(D, kind, lambda s: d0 <= s <= d1, lambda e: e <= d1 + 2 and e < len(D) and D.at[e, 'wi'] <= iend + 2, d0, d1)
            if r:
                e, px, st, s = r
                trades.append(('D', kind, 'D', e, px, D.at[e, 'wi'], st, D.at[e, 'l']))
    for (tf, kind, ekind, eidx, px, ewi, setup_stop, ebar_low) in trades:
        known = ewi - 1  # last completed week before entry week
        if tf == 'W' and kind == 'close': known = i0
        pstop, _ = last_pivot_low_below(px, known)
        ph, _ = last_pivot_high_above(px, known)
        f100, f161 = fib_targets(known)
        # for 'close' entry, the entry bar is the touch bar itself (already closed): no intrabar check
        stops = {'pivot': pstop}
        if setup_stop is not None: stops['setup'] = setup_stop
        for sname, st in stops.items():
            if st is None or st >= px: continue
            risk = px - st
            tgts = {'topo': ph if (ph and ph > px) else None, '2R': px + 2 * risk,
                    'fib100': f100 if (f100 and f100 > px) else None,
                    'fib161': f161 if (f161 and f161 > px) else None,
                    'tempo13': None, 'tempo26': None}
            for tname, tg in tgts.items():
                if tname in ('topo', 'fib100', 'fib161') and tg is None: continue
                mw = 13 if tname == 'tempo13' else (26 if tname == 'tempo26' else MAXW)
                if kind == 'close':
                    res = simulate(px, ewi, 'W', i0, st, tg, mw, None)
                elif ekind == 'W':
                    # resolve the entry week with daily bars when available: entry on the first day reaching px
                    dd = D[D['wi'] == eidx]
                    hit = dd.index[dd['h'] >= px] if len(dd) else []
                    if len(hit):
                        k = hit[0]
                        res = simulate(px, ewi, 'D', k, st, tg, mw, tuple(D.loc[k, ['o', 'h', 'l', 'c']]))
                    else:
                        res = simulate(px, ewi, 'W', eidx, st, tg, mw, tuple(W.loc[eidx, ['o', 'h', 'l', 'c']]))
                else:
                    res = simulate(px, ewi, 'D', eidx, st, tg, mw, tuple(D.loc[eidx, ['o', 'h', 'l', 'c']]))
                rec = dict(ep, tf=tf, trig=kind, stop=sname, tgt=tname, entry=px, stop_px=st, tgt_px=tg, ewi=int(ewi), ekind=ekind, eidx=int(eidx),
                           risk_pct=risk / px, **res)
                records.append(rec)

R = pd.DataFrame(records)
R['ret'] = R['exit'] / R['entry'] - 1
R['R'] = (R['exit'] - R['entry']) / (R['entry'] - R['stop_px'])
R.to_csv(os.path.join(BASE, 'trades.csv'), index=False)
print(len(R), 'trade-rows;', len(episodes), 'episodes')
