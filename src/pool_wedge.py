from config import DATA_ROOT, RESULTS, EXCLUDE, months_filter
import pandas as pd, numpy as np, glob
B=pd.concat([pd.read_csv(f) for f in glob.glob(DATA_ROOT+'/*/trades.csv') if f.split('/')[-2] not in EXCLUDE])
Wd=pd.concat([pd.read_csv(f) for f in glob.glob(DATA_ROOT+'/*/wedge_trades.csv')])
A=pd.concat([B,Wd[Wd.trig.isin(['wedge','wedge_vol'])]])
def prep(X):
    X=months_filter(X[X.reason!='open']).copy(); X['ret']=X.exit/X.entry-1; X['Rf']=(X.exit-X.entry)/np.maximum(X.entry-X.stop_px,0.01*X.entry); return X
A=prep(A); N=prep(Wd[Wd.trig.isin(['ns','ns_vol'])])
def st(g): return pd.Series(dict(n=len(g),acerto=(g.ret>0).mean(),ret=g.ret.mean(),R=g.Rf.mean(),risco=g.risk_pct.mean(),sem=g.Rf.std()/np.sqrt(max(len(g),1))))
pd.set_option('display.width',200); pd.set_option('display.float_format','{:.3f}'.format)
for tg in ['topo','fib161','tempo26']:
    print('\n=== T1 gatilhos, stop pivot, alvo',tg,'| MM50 subindo ===')
    g=A[(A.stop=='pivot')&(A.tgt==tg)&(A.trend)]
    print(g.groupby(['tf','trig']).apply(st).to_string())
    print('-- cunha stop setup')
    g=A[(A.stop=='setup')&(A.tgt==tg)&(A.trend)]
    print(g.groupby(['tf','trig']).apply(st).to_string())
for tg in ['topo','tempo26']:
    print('\n=== T2 bloqueio por cunha ascendente (stop pivot, alvo',tg,', MM50 subindo) ===')
    g=A[(A.stop=='pivot')&(A.tgt==tg)&(A.trend)&~A.trig.isin(['close','open'])]
    for col in ['blk','blkv']:
        print(col); print(g.groupby(['tf',col]).apply(st).to_string())
    print('por gatilho (blk)'); print(g.groupby(['trig','blk']).apply(st).unstack().to_string())
for tg in ['topo','fib161','tempo26','2R']:
    print('\n=== T3 sem slowstoch, alvo',tg,'===')
    for sname in ['pivot','setup']:
        g=N[(N.stop==sname)&(N.tgt==tg)]
        print('stop',sname); print(g.groupby(['tf','trig','trend','blk']).apply(st).to_string())
