"""Falling wedge detector (daily). Lines through 2 pivot highs and 2 pivot lows, both descending, converging,
price contained between them, >=2 touches per line, breakout = first close above the upper line."""
from config import DATA_ROOT, RESULTS, EXCLUDE
import numpy as np, pandas as pd, glob, os, json

K = 3          # pivot strength (bars each side)
MINLEN, MAXLEN = 25, 160
MINRATIO = 0.0485   # inclinação inferior / superior; limite = TSLA dez/2024–abr/2025 (0,0513), definido pelo usuário

def atr(df, n=20):
    tr = pd.concat([df.h - df.l, (df.h - df.c.shift()).abs(), (df.l - df.c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().bfill().values

def pivots(h, l, k):
    n = len(h); ph, pl = [], []
    for i in range(k, n - k):
        if h[i] == h[i - k:i + k + 1].max() and h[i] > h[i - k:i].max(): ph.append(i)
        if l[i] == l[i - k:i + k + 1].min() and l[i] < l[i - k:i].min(): pl.append(i)
    return np.array(ph), np.array(pl)

def line(i1, y1, i2, y2):
    s = (y2 - y1) / (i2 - i1); return lambda x: y1 + s * (np.asarray(x) - i1), s

def detect(df):
    o, h, l, c = (df[x].values for x in 'ohlc'); n = len(c); a = atr(df)
    PH, PL = pivots(h, l, K)
    out = []
    for ia, h1 in enumerate(PH):
        for h2 in PH[ia + 1:]:
            if h2 - h1 > MAXLEN: break
            if h2 - h1 < 12 or h[h2] >= h[h1]: continue
            U, su = line(h1, h[h1], h2, h[h2])
            lows = PL[(PL > h1) & (PL < h2 + 40)]
            for ib, l1 in enumerate(lows):
                for l2 in lows[ib + 1:]:
                    if l2 - l1 < 10 or l[l2] >= l[l1]: continue
                    L, sl = line(l1, l[l1], l2, l[l2])
                    if not (su < sl < 0): continue                 # both down, upper steeper -> converging
                    start, end = h1, max(h2, l2)
                    if end - start < MINLEN or end - start > MAXLEN: continue
                    xs = np.arange(start, end + 1)
                    tol = 0.35 * a[xs]
                    if (U(xs) <= L(xs)).any(): continue
                    if (c[xs] > U(xs) + tol).any() or (c[xs] < L(xs) - tol).any(): continue
                    if (h[xs] > U(xs) + 2 * tol).any() or (l[xs] < L(xs) - 2 * tol).any(): continue
                    w0, w1 = U(start) - L(start), U(end) - L(end)
                    if w0 <= 0 or w1 / w0 > 0.65: continue
                    # breakout
                    b = None
                    for j in range(end + 1, min(n, end + 40)):
                        if U(j) <= L(j): break
                        if c[j] < L(j) - 0.5 * a[j]: break           # broke down first -> invalid
                        if c[j] > U(j): b = j; break
                    if b is None: continue
                    tu = [p for p in PH if start <= p <= end and abs(h[p] - U(p)) <= 0.5 * a[p]]
                    tl = [p for p in PL if start <= p <= end and abs(l[p] - L(p)) <= 0.5 * a[p]]
                    if len(tu) < 2 or len(tl) < 2: continue
                    out.append(dict(h1=int(h1), h2=int(h2), l1=int(l1), l2=int(l2), start=int(start), end=int(end), b=int(b),
                                    tu=len(tu), tl=len(tl), su=su, sl=sl, conv=w1 / w0, length=int(end - start),
                                    drop=(h[h1] - l[l2]) / h[h1]))
    # dedupe: one wedge per breakout bar (most touches, then longest)
    best = {}
    for w in out:
        k = w['b']; key = (w['tu'] + w['tl'], w['length'])
        if k not in best or key > (best[k]['tu'] + best[k]['tl'], best[k]['length']): best[k] = w
    # the wedge is the best-fitting pair of lines (most touches); only then judge its shape
    res = sorted([w for w in best.values() if w['sl'] / w['su'] >= MINRATIO], key=lambda w: w['b'])
    # remove overlapping wedges (keep the one with more touches)
    final = []
    for w in res:
        if final and w['start'] < final[-1]['b']:
            if w['tu'] + w['tl'] > final[-1]['tu'] + final[-1]['tl']: final[-1] = w
            continue
        final.append(w)
    return final

if __name__ == '__main__':
    allw = []
    for d in sorted(glob.glob(DATA_ROOT+'/*/d.csv')):
        sym = d.split('/')[-2]
        if sym in EXCLUDE: continue
        df = pd.read_csv(d)
        ws = detect(df)
        c = df.c.values; dates = pd.to_datetime(df.t, unit='s').dt.date.values
        for w in ws:
            b = w['b']; w['sym'] = sym; w['date_b'] = str(dates[b]); w['date_s'] = str(dates[w['start']])
            w['r20'] = float(c[min(b + 20, len(c) - 1)] / c[b] - 1); w['r60'] = float(c[min(b + 60, len(c) - 1)] / c[b] - 1)
            w['target_hit'] = bool((df.h.values[b:b + 60] >= df.h.values[w['h1']]).any())
        allw += ws
        print(sym, len(ws))
    json.dump(allw, open(DATA_ROOT+'/wedges.json', 'w'))
    print('total', len(allw))
