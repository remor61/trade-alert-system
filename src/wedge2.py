"""Wedge detector for trading (no lookahead).
Falling wedge: lines through 2 pivot highs and 2 pivot lows, both descending, upper steeper (converging),
  inclinação inferior/superior >= MINRATIO (limite TSLA, definido pelo usuário), >= 2 toques por linha,
  preço contido até a confirmação do último pivô (t0 = último pivô + k barras),
  sinal = primeiro FECHAMENTO acima da linha superior a partir de t0 (entrada no fechamento desse candle).
Rising wedge: same detector on the mirrored series (-o, -l, -h, -c) -> sinal = fechamento abaixo da linha inferior.
"""
import numpy as np

P = {'D': dict(k=3, minlen=25, maxlen=160, gh=12, gl=10, wait=40, lowext=40),
     'W': dict(k=2, minlen=10, maxlen=80, gh=5, gl=4, wait=20, lowext=20)}
MINRATIO = 0.0485

def atr_arr(h, l, c, n=20):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    a = np.convolve(tr, np.ones(n) / n, mode='full')[:len(tr)]
    a[:n] = tr[:n].mean() if len(tr) else 0
    return a

def pivots(h, l, k):
    n = len(h); ph, pl = [], []
    for i in range(k, n - k):
        if h[i] == h[i - k:i + k + 1].max() and h[i] > h[i - k:i].max(): ph.append(i)
        if l[i] == l[i - k:i + k + 1].min() and l[i] < l[i - k:i].min(): pl.append(i)
    return np.array(ph, int), np.array(pl, int)

def detect_fall(o, h, l, c, a, tf):
    p = P[tf]; k = p['k']; n = len(c)
    PH, PL = pivots(h, l, k)
    out = []
    for ia, h1 in enumerate(PH):
        for h2 in PH[ia + 1:]:
            if h2 - h1 > p['maxlen']: break
            if h2 - h1 < p['gh'] or h[h2] >= h[h1]: continue
            su = (h[h2] - h[h1]) / (h2 - h1)
            lows = PL[(PL > h1) & (PL < h2 + p['lowext'])]
            for ib, l1 in enumerate(lows):
                for l2 in lows[ib + 1:]:
                    if l2 - l1 < p['gl'] or l[l2] >= l[l1]: continue
                    sl = (l[l2] - l[l1]) / (l2 - l1)
                    if not (su < sl < 0): continue
                    start, end = h1, max(h2, l2); t0 = end + k
                    if t0 >= n or end - start < p['minlen'] or end - start > p['maxlen']: continue
                    U = lambda x: h[h1] + su * (x - h1)
                    L = lambda x: l[l1] + sl * (x - l1)
                    xs = np.arange(start, t0)
                    ux, lx, tol = U(xs), L(xs), 0.35 * a[xs]
                    if (ux <= lx).any(): continue
                    if (c[xs] > ux + tol).any() or (c[xs] < lx - tol).any(): continue
                    if (h[xs] > ux + 2 * tol).any() or (l[xs] < lx - 2 * tol).any(): continue
                    w0, w1 = U(start) - L(start), U(end) - L(end)
                    if w0 <= 0 or w1 / w0 > 0.65: continue
                    b = None
                    for j in range(t0, min(n, t0 + p['wait'])):
                        if U(j) <= L(j): break
                        if c[j] < L(j) - 0.5 * a[j]: break
                        if c[j] > U(j): b = j; break
                    if b is None: continue
                    tu = sum(1 for q in PH if start <= q <= end and abs(h[q] - U(q)) <= 0.5 * a[q])
                    tl = sum(1 for q in PL if start <= q <= end and abs(l[q] - L(q)) <= 0.5 * a[q])
                    if tu < 2 or tl < 2: continue
                    out.append(dict(h1=int(h1), h2=int(h2), l1=int(l1), l2=int(l2), start=int(start), end=int(end),
                                    b=int(b), tu=tu, tl=tl, su=su, sl=sl, length=int(end - start),
                                    stop_setup=float(l[l2:b + 1].min()), top=float(h[h1])))
    best = {}
    for w in out:
        key = (w['tu'] + w['tl'], w['length'])
        if w['b'] not in best or key > (best[w['b']]['tu'] + best[w['b']]['tl'], best[w['b']]['length']):
            best[w['b']] = w
    return sorted([w for w in best.values() if w['sl'] / w['su'] >= MINRATIO], key=lambda w: w['b'])

def vol_ok(v, b, n=20, x=1.2):
    if b < n: return False
    m = v[b - n:b].mean()
    return bool(m > 0 and v[b] >= x * m)
