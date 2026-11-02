"""Caminhos do projeto. DATA_ROOT guarda os dados e os trades por ativo (data/<TICKER>/), RESULTS os relatórios."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.environ.get('DATA_ROOT', os.path.join(ROOT, 'data'))
RESULTS = os.environ.get('RESULTS', os.path.join(ROOT, 'results'))
EXCLUDE = {'DXY', 'USDBRL'}   # câmbio e índice de moeda ficam fora do pool
os.makedirs(RESULTS, exist_ok=True)

MONTHS = os.environ.get('MONTHS', 'D')   # D = desenvolvimento (padrão), R = reservados (só na validação final), ALL = todos

def months_filter(df, col='edate'):
    """Mantém só os trades cuja entrada cai nos meses escolhidos em MONTHS (ver split.py)."""
    if MONTHS == 'ALL': return df
    from split import is_dev
    dev = is_dev(df[col])
    if MONTHS == 'R':
        print('ATENÇÃO: rodando nos meses RESERVADOS (validação final).')
        return df[~dev]
    return df[dev]
