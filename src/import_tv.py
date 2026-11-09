"""Monta data/<TICKER>/d.csv e w.csv (e h1.csv / m15.csv, se houver respostas de 1h / 15m) a partir de respostas do TradingView (ferramenta mcp-tv-get-ohlcv, format: columns).
Também grava data/<TICKER>/earnings.csv a partir de respostas de mcp-tv-get-documents com event=earning (uma linha por evento de resultado).
Aceita arquivos .json/.txt salvos com essas respostas e, com --claude-logs, varre os logs de sessão do Claude Code
(~/.claude/projects/**/*.jsonl e tool-results/*.txt). Respostas mais novas sobrescrevem as antigas (candle em formação).
O semanal é montado a partir do diário (semana seg–sex, t = primeiro pregão da semana).
uso: python src/import_tv.py [--claude-logs] [arquivos...]"""
import json, glob, os, sys
import pandas as pd
from config import DATA_ROOT

dec = json.JSONDecoder(); res = {}; earn = {}

def take(s, stamp):
    i = s.find('{"bars"')
    while i >= 0:
        try: j, end = dec.raw_decode(s[i:])
        except Exception: i = s.find('{"bars"', i + 1); continue
        if j.get('interval') in ('1D', '1h', '15m') and j.get('symbol'):
            res.setdefault((j['symbol'], j['interval']), []).append((stamp, j['bars']))
        i = s.find('{"bars"', i + end)
    i = s.find('{"items"')
    while i >= 0:
        try: j, end = dec.raw_decode(s[i:])
        except Exception: i = s.find('{"items"', i + 1); continue
        for it in j.get('items', []) if isinstance(j.get('items'), list) else []:
            if isinstance(it, dict) and it.get('event') == 'earning' and it.get('reported') and it.get('symbols'):
                for sy in it['symbols']:
                    earn.setdefault(sy['symbol'], {}).setdefault(it.get('correlation_id') or it['reported'], (it['reported'], it.get('fiscal_period'), it.get('fiscal_year')))
        i = s.find('{"items"', i + end)

def walk(x, stamp):
    if isinstance(x, str):
        if '"bars"' in x or '"items"' in x: take(x, stamp)
    elif isinstance(x, dict): [walk(v, stamp) for v in x.values()]
    elif isinstance(x, list): [walk(v, stamp) for v in x]

args = sys.argv[1:]
if '--claude-logs' in args:
    args.remove('--claude-logs'); home = os.path.expanduser('~/.claude/projects')
    for p in glob.glob(f'{home}/**/*.jsonl', recursive=True):
        for line in open(p, errors='ignore'):
            if 'bars' not in line and '"event\\":\\"earning' not in line and 'earning' not in line: continue
            try: d = json.loads(line)
            except Exception: continue
            walk(d, pd.Timestamp(d.get('timestamp', '1970-01-01')).timestamp())
    for p in glob.glob(f'{home}/**/tool-results/*.txt', recursive=True):
        take(open(p, errors='ignore').read(), os.path.getmtime(p))
for p in args:
    take(open(p, errors='ignore').read(), os.path.getmtime(p))

for (sym, itv), lst in res.items():
    rows = {}
    for _, b in sorted(lst, key=lambda x: x[0]):
        for r in zip(b['t'], b['o'], b['h'], b['l'], b['c'], b['v']): rows[r[0]] = r
    d = pd.DataFrame(sorted(rows.values()), columns=['t', 'o', 'h', 'l', 'c', 'v'])
    d['v'] = pd.to_numeric(d['v'], errors='coerce').fillna(0)
    tick = sym.split(':')[-1].replace('.', '_')
    out = os.path.join(DATA_ROOT, tick); os.makedirs(out, exist_ok=True)
    if itv in ('1h', '15m'):
        d.to_csv(f'{out}/{"h1" if itv == "1h" else "m15"}.csv', index=False)
        print(f'{sym:22s} {itv:6s} {len(d):5d} ({pd.to_datetime(d.t.iloc[0], unit="s").date()} → {pd.to_datetime(d.t.iloc[-1], unit="s").date()})')
        continue
    d.to_csv(f'{out}/d.csv', index=False)
    dt = pd.to_datetime(d.t, unit='s').dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    wk = (dt - pd.to_timedelta(dt.dt.weekday, unit='D')).dt.date
    w = d.groupby(wk).agg(t=('t', 'first'), o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), v=('v', 'sum')).reset_index(drop=True)
    w.to_csv(f'{out}/w.csv', index=False)
    print(f'{sym:22s} diário {len(d):5d} ({pd.to_datetime(d.t.iloc[0], unit="s").date()} → {pd.to_datetime(d.t.iloc[-1], unit="s").date()})  semanal {len(w)}')
for sym, ev in earn.items():
    E = pd.DataFrame(sorted(ev.values()), columns=['t', 'fiscal_period', 'fiscal_year']).drop_duplicates('t')
    et = pd.to_datetime(E.t, unit='s').dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    E['data_et'] = et.dt.strftime('%Y-%m-%d'); E['hora_et'] = et.dt.strftime('%H:%M')
    E['so_data'] = (E.t % 86400 == 0)   # horário ausente: só a data (UTC) é confiável
    E.loc[E.so_data, 'data_et'] = pd.to_datetime(E.t[E.so_data], unit='s').dt.strftime('%Y-%m-%d')
    out = os.path.join(DATA_ROOT, sym.split(':')[-1].replace('.', '_')); os.makedirs(out, exist_ok=True)
    E.to_csv(f'{out}/earnings.csv', index=False)
    print(f'{sym:22s} earnings {len(E):3d} ({E.data_et.min()} → {E.data_et.max()})')
if not res: print('Nenhuma resposta de OHLCV diário encontrada.')
