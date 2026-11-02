import pandas as pd, numpy as np

def load(path):
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['t'], unit='s').dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.date
    return df

def slow_stoch(df, k=8, ks=3, d=3):
    ll = df['l'].rolling(k).min(); hh = df['h'].rolling(k).max()
    fast = 100 * (df['c'] - ll) / (hh - ll)
    df['K'] = fast.rolling(ks).mean()
    df['D'] = df['K'].rolling(d).mean()
    return df

if __name__ == '__main__':
    w = slow_stoch(load('qqq_w.csv'))
    w['touch'] = (w['K'] <= 20) & (w['K'].shift(1) > 20)
    ev = w[w['touch']]
    print(len(ev), 'episodes (K crosses into <=20)')
    hz = [4, 8, 13, 26, 52]
    rows = []
    for i in ev.index:
        r = {'date': w.loc[i, 'date'], 'K': round(w.loc[i, 'K'], 1), 'close': w.loc[i, 'c']}
        for h in hz:
            if i + h < len(w):
                r[f'r{h}_close'] = w.loc[i + h, 'c'] / w.loc[i, 'c'] - 1
                r[f'r{h}_next'] = w.loc[i + h, 'c'] / w.loc[i + 1, 'o'] - 1
        # weeks K stayed <=20
        j = i
        while j < len(w) and w.loc[j, 'K'] <= 20: j += 1
        r['weeks_below'] = j - i
        r['low_after'] = w.loc[i:i + 8, 'l'].min() / w.loc[i, 'c'] - 1
        rows.append(r)
    R = pd.DataFrame(rows)
    pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
    print(R.round(3).to_string())
    print()
    for h in hz:
        for m in ['close', 'next']:
            s = R[f'r{h}_{m}'].dropna()
            print(f'{h:>2}w {m:5s} n={len(s):2d} mean={s.mean():+.2%} median={s.median():+.2%} win={(s>0).mean():.0%}')
    # benchmark: unconditional
    for h in hz:
        u = (w['c'].shift(-h) / w['c'] - 1).dropna()
        print(f'baseline {h}w mean={u.mean():+.2%} win={(u>0).mean():.0%}')
    w.to_csv('qqq_w_stoch.csv', index=False)
