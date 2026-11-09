"""Estratégia "Campanhas": só compras, tudo no diário. Independente do setup Slow Stoch semanal.
Filtro: MM50 diária subindo (MM50 > MM50 de 4 pregões atrás), medida no último candle fechado antes da entrada.
Gatilhos (compra por ordem stop 1 tick acima do preço de gatilho; tick = min(0,01; 0,05% do preço)). Nos gatilhos de
  rompimento (todos menos o gap) o candle da entrada precisa passar pelo preço de gatilho: se abrir acima (gap), não há trade.
  123     fundo de 3 candles (mínima do meio < vizinhas); gatilho máx. do 3º; stop mín. do 2º
  inside  candle dentro do anterior; gatilho máx. do inside; stop mín. do candle-mãe
  trap    candle perde o último fundo de 123 não violado (até 50 candles atrás) e tem sombra inferior >= 70% da amplitude;
          gatilho máx. dele no candle seguinte (ou no 2º se o 1º for inside); stop mín. do candle da armadilha
  bvi     barra vermelha ignorada: único candle vermelho depois de >= 3 brancos; gatilho máx. dele, acima da MME8; stop mín.
  ssi     sombra superior ignorada: sombra superior >= 50% da amplitude; gatilho máx., acima da MME8; stop mín.
  trapmm  trap na MM50: mínima toca/fura a MM50 e fecha acima, vindo de fechamento acima; gatilho máx.; stop mín.
  gap     gap de baixa (abertura < mín. anterior); entrada quando volta à mín. anterior + 1 tick no próprio candle do gap;
          stop na mínima do candle que fechou o gap conhecida até a entrada (candle de baixa: a abertura)
Saídas (cada teste roda com todas): topo (último topo diário acima da entrada, senão 2R), 2R, 3R,
  sinal (qualquer gatilho de venda espelhado formado depois da entrada), stoch (Slow Stoch 14/3 %K > 80 no fechamento).
  O stop vale sempre; saída por tempo após 260 pregões. Uma posição por vez por ativo; entradas só nos meses D.
Earnings: sem entrada se houver divulgação de resultado do pregão da entrada (após a abertura) até 3 pregões depois
  (data/<TICKER>/earnings.csv; sem o arquivo a regra não é aplicada naquele ativo).
uso: python src/campanhas.py [--desde AAAA-MM-DD] [TICKER ...]   (sem tickers = todos de data/)"""
import os, sys, glob, numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
from config import DATA_ROOT, RESULTS, EXCLUDE, MONTHS
from split import is_dev
from sizing import shares

KINDS = ['123', 'inside', 'trap', 'bvi', 'ssi', 'trapmm', 'gap']
EXITS = ['topo', '2R', '3R', 'sinal', 'stoch']
NWHITE, SHADOW, TRAPLB, GAPWAIT, MAXBARS = 3, 0.5, 50, 1, 260   # GAPWAIT = 1: o gap fecha no candle que abriu abaixo
TRAPSHADOW, EARNDAYS = 0.7, 3   # trap: sombra inferior >= 70% do candle; earnings nos próximos 3 pregões bloqueiam a entrada
USA_EARNINGS = False
PASSA_GATILHO = True   # rompimento só vale se o candle da entrada passar pelo gatilho (abrir abaixo dele)
BANK = 10_000
# CAMP_GAP=pior: limite pessimista do gap (a mínima do dia sempre veio depois da entrada: stop na abertura,
# acionado no mesmo dia se a mínima ficou abaixo dela). O dado diário não diz a ordem intradiária.
GAP_PIOR = os.environ.get('CAMP_GAP') == 'pior'
# CAMP_GAP=1h ou 15m: resolve o dia da entrada com barras intradiárias (data/<TICKER>/h1.csv ou m15.csv), em todos os
# gatilhos: barra da entrada, mínima conhecida até ela (stop do gap) e stop/alvo no resto do dia. Dias sem dado intradiário
# seguem a convenção diária. Sufixo _pior (1h_pior, 15m_pior): dentro da barra da entrada a mínima vem sempre depois dela.
_MODE = os.environ.get('CAMP_GAP', '')
INTRA = {'1h': 'h1.csv', '15m': 'm15.csv'}.get(_MODE.replace('_pior', ''))
INTRA_PIOR = _MODE.endswith('_pior') and INTRA is not None

def tick(p): return min(0.01, p * 0.0005)

def prep(df):
    d = {k: df[k].values.astype(float) for k in 'ohlc'}
    c = pd.Series(d['c'])
    sma = c.rolling(50).mean().values
    d['sma'] = sma
    d['trend'] = np.r_[[False] * 4, sma[4:] > sma[:-4]]
    d['ema'] = c.ewm(span=8, adjust=False).mean().values
    ll, hh = df.l.rolling(14).min(), df.h.rolling(14).max()
    d['k'] = (100 * (df.c - ll) / (hh - ll)).rolling(3).mean().values
    d['date'] = pd.to_datetime(df.t, unit='s').dt.date.values
    d['earn'] = earnings_block(df.attrs.get('sym', ''), d['date'])
    d['h1'] = {}
    f = os.path.join(DATA_ROOT, df.attrs.get('sym', ''), INTRA or 'h1.csv')
    if INTRA and os.path.exists(f):
        H = pd.read_csv(f); H['date'] = pd.to_datetime(H.t, unit='s').dt.date
        d['h1'] = {k: g[['o', 'h', 'l', 'c']].values.astype(float) for k, g in H.groupby('date')}
    return d

def earnings_block(sym, dates):
    """True no pregão e se sai resultado entre a abertura de e e o fim do dia do pregão e+3 (None: sem dados de earnings)"""
    f = os.path.join(DATA_ROOT, sym, 'earnings.csv')
    if not USA_EARNINGS or not os.path.exists(f): return None
    E = pd.read_csv(f); n = len(dates); blk = np.zeros(n, bool)
    D = pd.to_datetime(pd.Series(dates)).values.astype('datetime64[D]')
    end = np.r_[D[EARNDAYS:], np.busday_offset(D[-1], np.arange(1, EARNDAYS + 1), roll='forward')]   # data do pregão e+3
    for dt, hr, so in zip(pd.to_datetime(E.data_et).values.astype('datetime64[D]'), E.hora_et, E.so_data):
        after_open = so or hr >= '09:30'
        blk |= ((dt > D) | ((dt == D) & after_open)) & (dt <= end)
    return blk

def entry_1h(B, trig):
    """barras intradiárias do dia: (barra da entrada, preço, menor preço conhecido até a entrada) ou None"""
    lsf = np.inf
    for k, (o, h, l, c) in enumerate(B):
        if h >= trig:
            px = max(o, trig)
            lsf = min(lsf, l if (c >= o and o < px and not INTRA_PIOR) else o)   # barra de alta: a mínima veio antes
            return k, px, lsf
        lsf = min(lsf, l)
    return None

def signals(d, side):
    """side = 1: compras; -1: vendas (espelho). Lista de (kind, s, gatilho, stop, janela de pregões)."""
    if side == 1: o, h, l, c, ema, sma = d['o'], d['h'], d['l'], d['c'], d['ema'], d['sma']
    else: o, h, l, c, ema, sma = -d['o'], -d['l'], -d['h'], -d['c'], -d['ema'], -d['sma']
    n = len(c); out = []
    tk = lambda x: tick(abs(x))
    for s in range(3, n):
        nxt = [s + 1] if s + 1 < n else []
        a, b = s - 2, s - 1
        if l[b] < l[a] and l[b] < l[s]: out.append(('123', s, h[s] + tk(h[s]), l[b], nxt))
        if h[s] < h[s - 1] and l[s] > l[s - 1]: out.append(('inside', s, h[s] + tk(h[s]), l[s - 1], nxt))
        # trap: último fundo de 123 (b-1 > b < b+1) ainda não violado, até TRAPLB candles atrás
        rng = h[s] - l[s]
        for r in range(s - 2, max(s - TRAPLB, 1) - 1, -1):
            if l[r] < l[r - 1] and l[r] < l[r + 1] and l[r + 1:s].min() > l[r]:
                # s é o primeiro candle a perder esse fundo e deixa sombra inferior >= 70% do candle
                if l[s] < l[r] and rng > 0 and min(o[s], c[s]) - l[s] >= TRAPSHADOW * rng:
                    win = nxt + ([s + 2] if s + 2 < n and h[s + 1] <= h[s] and l[s + 1] >= l[s] else [])
                    out.append(('trap', s, h[s] + tk(h[s]), l[s], win))
                break
        red = c[s] < o[s]
        if red and s >= NWHITE and all(c[s - j] > o[s - j] for j in range(1, NWHITE + 1)) and h[s] + tk(h[s]) > ema[s]:
            out.append(('bvi', s, h[s] + tk(h[s]), l[s], nxt))
        if rng > 0 and (h[s] - max(o[s], c[s])) >= SHADOW * rng and h[s] + tk(h[s]) > ema[s]:
            out.append(('ssi', s, h[s] + tk(h[s]), l[s], nxt))
        if not np.isnan(sma[s - 1]) and l[s] <= sma[s] < c[s] and c[s - 1] > sma[s - 1]:
            out.append(('trapmm', s, h[s] + tk(h[s]), l[s], nxt))
        if s + 1 < n and o[s + 1] < l[s]:   # gap no pregão s+1; s = último candle antes do gap
            out.append(('gap', s, l[s] + tk(l[s]), None, list(range(s + 1, min(n, s + 1 + GAPWAIT)))))
    if side == -1:   # volta para preços reais
        out = [(k, s, -g, None if st is None else -st, w) for k, s, g, st, w in out]
    return out

def last_top_above(d, px, e):
    h = d['h']
    for p in range(e - 3, max(e - 300, 2), -1):
        if h[p] > max(h[p - 2], h[p - 1]) and h[p] >= max(h[p + 1], h[p + 2]) and h[p] > px: return h[p]
    return None

def backtest(d, buys, sells_by_bar, kinds, exit_kind, start_date):
    o, h, l, c, k = d['o'], d['h'], d['l'], d['c'], d['k']; n = len(c)
    dev = is_dev(d['date']) if MONTHS == 'D' else (~is_dev(d['date']) if MONTHS == 'R' else np.ones(n, bool))
    # candidatos: primeira barra da janela que atinge o gatilho
    cands = []
    for kind, s, trig, stop, win in buys:
        if kind not in kinds: continue
        for e in win:
            if h[e] >= trig:
                if PASSA_GATILHO and kind != 'gap' and o[e] >= trig: break   # abriu acima do gatilho (gap): o rompimento não acontece, sem trade
                px = max(o[e], trig); hk = None
                # gap: stop na mínima do candle que fechou o gap, conhecida até a entrada
                # (alta O->L->H: a mínima veio antes; baixa O->H->L: até a entrada a mínima era a abertura)
                st = (l[e] if c[e] >= o[e] and not GAP_PIOR else o[e]) if kind == 'gap' else stop
                B = d['h1'].get(d['date'][e])
                if B is not None and (r := entry_1h(B, trig)) is not None:
                    hk, px, lsf = r
                    if kind == 'gap': st = lsf
                ok_earn = d['earn'] is None or not d['earn'][e]
                if d['date'][e] >= start_date and dev[e] and d['trend'][e - 1] and st < px and ok_earn:
                    cands.append((e, px, KINDS.index(kind), kind, s, st, hk))
                break
    cands.sort()
    trades, free = [], -1
    for e, px, _, kind, s, st, hk in cands:
        if e <= free: continue
        risk = px - st
        tg = {'topo': last_top_above(d, px, e) or px + 2 * risk, '2R': px + 2 * risk, '3R': px + 3 * risk}.get(exit_kind)
        x = sim(d, e, px, st, tg, exit_kind, sells_by_bar, hk)
        if x is None: break   # trade ainda aberto: fim da série
        xd, xp, why = x; free = xd
        trades.append(dict(trig=kind, edate=d['date'][e], xdate=d['date'][xd], entry=px, stop_px=st, tgt_px=tg, exit=xp, reason=why))
    return trades

def bar_path(o, h, l, c, px=None):
    """preços depois da entrada no candle (convenção: alta O->L->H->C, baixa O->H->L->C); px=None: candle inteiro"""
    if px is None or o >= px: return [l, h] if c >= o else [h, l]
    return [h] if c >= o and not INTRA_PIOR else [h, l]

def sim(d, e, px, st, tg, exit_kind, sells_by_bar, hk=None):
    o, h, l, c, k = d['o'], d['h'], d['l'], d['c'], d['k']; n = len(c)
    if hk is not None:   # dia da entrada barra a barra (intradiário)
        B = d['h1'][d['date'][e]]
        for i in range(hk, len(B)):
            ho, hh, hl, hc = B[i]
            if i > hk:
                if ho <= st: return e, ho, 'stop'
                if tg is not None and ho >= tg: return e, ho, 'alvo'
            for p in bar_path(ho, hh, hl, hc, px if i == hk else None):
                if p <= st: return e, st, 'stop'
                if tg is not None and p >= tg: return e, tg, 'alvo'
        return sim_after(d, e, st, tg, exit_kind, sells_by_bar)
    # resto do candle de entrada (convenção: alta O->L->H->C, baixa O->H->L->C)
    seq = ([l[e], h[e]] if c[e] >= o[e] else [h[e], l[e]]) if o[e] >= px else ([h[e]] if c[e] >= o[e] and not (GAP_PIOR and st == o[e]) else [h[e], l[e]])
    for p in seq:
        if p <= st: return e, st, 'stop'
        if tg is not None and p >= tg: return e, tg, 'alvo'
    if c[e] <= st: return e, st, 'stop'
    return sim_after(d, e, st, tg, exit_kind, sells_by_bar)

def sim_after(d, e, st, tg, exit_kind, sells_by_bar):
    o, h, l, c, k = d['o'], d['h'], d['l'], d['c'], d['k']; n = len(c)
    for j in range(e + 1, n):
        if j - e > MAXBARS: return j - 1, c[j - 1], 'tempo'
        down = st
        if exit_kind == 'sinal':
            act = [g for s, g in sells_by_bar.get(j, []) if s >= e]
            if act: down = max(down, max(act))
        if o[j] <= down: return j, o[j], 'stop' if down == st else 'sinal'
        if tg is not None and o[j] >= tg: return j, o[j], 'alvo'
        for p, kind in (((l[j], 'L'), (h[j], 'H')) if c[j] >= o[j] else ((h[j], 'H'), (l[j], 'L'))):
            if kind == 'L' and p <= down: return j, down, 'stop' if down == st else 'sinal'
            if kind == 'H' and tg is not None and p >= tg: return j, tg, 'alvo'
        if exit_kind == 'stoch' and k[j] > 80: return j, c[j], 'stoch'
    return None

def stats(T, start, end):
    yrs = max((pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25, 0.25)
    if not T: return dict(trades=0, ret=0.0, ret_ano=0.0, acerto=np.nan, pf=np.nan, dd=0.0)
    df = pd.DataFrame(T)
    sh = shares(df.entry.values, df.stop_px.values)
    p = sh * (df.exit.values - df.entry.values); cum = np.cumsum(p)
    dd = (np.maximum.accumulate(np.r_[0, cum])[1:] - cum).max()
    w, ls = p[p > 0], p[p <= 0]
    return dict(trades=len(p), ret=100 * p.sum() / BANK, ret_ano=100 * p.sum() / BANK / yrs, acerto=100 * len(w) / len(p),
                pf=w.sum() / -ls.sum() if ls.sum() < 0 else np.nan, dd=100 * dd / BANK, **{f'n_{k}': int((df.trig == k).sum()) for k in KINDS})

def run(args):
    sym, since = args
    df = pd.read_csv(os.path.join(DATA_ROOT, sym, 'd.csv')); df.attrs['sym'] = sym; d = prep(df)
    buys = signals(d, 1)
    sells = {}
    for _, s, g, _, win in signals(d, -1):
        for j in win: sells.setdefault(j, []).append((s, g))
    start = max(since, d['date'][60]); end = d['date'][-1]
    rows, allT = [], []
    for test in KINDS + ['todos', 'todos_sem_gap']:
        kinds = KINDS if test == 'todos' else [k for k in KINDS if k != 'gap'] if test == 'todos_sem_gap' else [test]
        for ex in EXITS:
            T = backtest(d, buys, sells, kinds, ex, start)
            rows.append(dict(sym=sym, teste=test, saida=ex, inicio=start, fim=end, **stats(T, start, end)))
            allT += [dict(t, sym=sym, teste=test, saida=ex) for t in T]
    return rows, allT

if __name__ == '__main__':
    a = sys.argv[1:]; since = pd.Timestamp('1900-01-01').date()
    if a[:1] == ['--desde']: since = pd.Timestamp(a[1]).date(); a = a[2:]
    syms = [s.replace('.', '_') for s in a] or sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(f'{DATA_ROOT}/*/d.csv'))
    syms = [s for s in syms if s not in EXCLUDE]
    rows, trades = [], []
    with ProcessPoolExecutor() as ex:
        for r, t in ex.map(run, [(s, since) for s in syms]): rows += r; trades += t
    R = pd.DataFrame(rows); tag = f'{since}' if a else 'pool'
    R.to_csv(f'{RESULTS}/campanhas_{tag}.csv', index=False); pd.DataFrame(trades).to_csv(f'{RESULTS}/campanhas_trades_{tag}.csv', index=False)
    print(f'meses: {MONTHS} | ativos: {len(syms)} | desde {since} | {RESULTS}/campanhas_{tag}.csv')
