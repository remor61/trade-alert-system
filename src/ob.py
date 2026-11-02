"""Order blocks (SMC), without FVG requirement.
Bullish OB: when a close breaks above the most recent confirmed swing high that is still unbroken (BOS up),
  take the leg low L = lowest low between that swing high and the BOS bar; the OB is the last bearish candle
  (close < open) among L-5..L (closest to L); if none, the candle at L. Zone = candle low..high (wick to wick).
  Invalidated by a later close below the zone low.
Bearish OB: mirror (BOS down below an unbroken swing low; last bullish candle before the drop; invalidated by a
  close above the zone high).
Swing = pivot with k bars on each side, usable only after confirmation (k bars later).
"""
import numpy as np

def find_obs(o, h, l, c, k=2):
    n = len(c)
    obs = []
    sh = sl = None            # current unbroken confirmed swing high / low index
    for i in range(n):
        p = i - k             # pivot candidate confirmed at bar i
        if p >= k:
            if h[p] == max(h[p - k:p + k + 1]) and h[p] > max(h[p - k:p]):
                sh = p
            if l[p] == min(l[p - k:p + k + 1]) and l[p] < min(l[p - k:p]):
                sl = p
        if sh is not None and c[i] > h[sh] and i > sh:
            L = sh + int(np.argmin(l[sh:i + 1]))
            j = next((j for j in range(L, max(L - 6, -1), -1) if c[j] < o[j]), L)
            obs.append(dict(kind='bull', i=j, bos=i, lo=l[j], hi=h[j]))
            sh = None
        if sl is not None and c[i] < l[sl] and i > sl:
            H = sl + int(np.argmax(h[sl:i + 1]))
            j = next((j for j in range(H, max(H - 6, -1), -1) if c[j] > o[j]), H)
            obs.append(dict(kind='bear', i=j, bos=i, lo=l[j], hi=h[j]))
            sl = None
    # validity / first mitigation
    for ob in obs:
        ob['dead'] = None; ob['touch'] = None
        for t in range(ob['bos'] + 1, n):
            if ob['kind'] == 'bull':
                if ob['touch'] is None and l[t] <= ob['hi']: ob['touch'] = t
                if c[t] < ob['lo']: ob['dead'] = t; break
            else:
                if ob['touch'] is None and h[t] >= ob['lo']: ob['touch'] = t
                if c[t] > ob['hi']: ob['dead'] = t; break
    return obs

def valid_at(obs, t, kind):
    """OBs of `kind` already formed (BOS <= t) and not invalidated up to t."""
    return [ob for ob in obs if ob['kind'] == kind and ob['bos'] <= t and (ob['dead'] is None or ob['dead'] > t)]

def nearest(obs, t, price, n=2):
    bull = sorted([ob for ob in valid_at(obs, t, 'bull') if ob['lo'] < price], key=lambda ob: -ob['hi'])[:n]
    bear = sorted([ob for ob in valid_at(obs, t, 'bear') if ob['hi'] > price], key=lambda ob: ob['lo'])[:n]
    return bull, bear
