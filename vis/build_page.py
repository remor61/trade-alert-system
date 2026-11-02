"""Gera a página interativa de cunhas/trades de um ativo: results/cunhas_<TICKER>.html.
Antes rode: DATA=data/<TICKER> python src/export_vis.py <TICKER>
uso: python vis/build_page.py TICKER [AAAA-MM-DD do trade inicial]"""
import os, sys, json, datetime as dt
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
sys.path.insert(0, os.path.join(root, 'src')); from config import RESULTS
sym = sys.argv[1]; start = sys.argv[2] if len(sys.argv) > 2 else None
data = open(f'{RESULTS}/vis_{sym}.json').read(); D = json.loads(data)['D']
mes = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
f = lambda t: (lambda d: f'{mes[d.month-1]}/{d.year}')(dt.datetime.fromtimestamp(t, dt.timezone.utc))
rd = lambda n: open(os.path.join(here, n)).read()
html = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + rd('head.html').replace('{{SYM}}', sym) + rd('body.html').replace('{{SYM}}', sym).replace('{{RANGE}}', f'{f(D[0][0])} a {f(D[-1][0])}')
        + f'<script>window.__START={json.dumps(start)};window.__DATA={data};</script><script>' + rd('app.js') + '</script></body></html>')
out = f'{RESULTS}/cunhas_{sym}.html'; open(out, 'w').write(html); print(out)
