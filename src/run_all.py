"""Roda o backtest completo (gatilhos do Slow Stoch + testes de cunha) em todos os ativos de data/, em paralelo.
uso: python src/run_all.py [TICKER ...]"""
import os, sys, subprocess, glob
from concurrent.futures import ThreadPoolExecutor
from config import DATA_ROOT, EXCLUDE
here = os.path.dirname(os.path.abspath(__file__))
syms = sys.argv[1:] or sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(f'{DATA_ROOT}/*/d.csv'))
syms = [s for s in syms if s not in EXCLUDE]
def run(s):
    env = dict(os.environ, DATA=os.path.join(DATA_ROOT, s))
    r = subprocess.run([sys.executable, os.path.join(here, 'bt_wedge.py'), s], env=env, capture_output=True, text=True, cwd=here)
    return s, r.returncode, (r.stdout.strip().splitlines() or [''])[-1], r.stderr[-400:]
with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
    for s, rc, out, err in ex.map(run, syms):
        print(out if rc == 0 else f'{s} FALHOU\n{err}')
