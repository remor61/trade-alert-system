from config import DATA_ROOT, RESULTS, EXCLUDE
import pandas as pd, numpy as np, glob
BANK, RISK, RLO, RHI = 10_000, 100, 85, 115
B=pd.concat([pd.read_csv(f) for f in glob.glob(DATA_ROOT+'/*/trades.csv') if f.split('/')[-2] not in EXCLUDE])
Wd=pd.concat([pd.read_csv(f) for f in glob.glob(DATA_ROOT+'/*/wedge_trades.csv')])
from config import months_filter, MONTHS
A=pd.concat([B,Wd]); A=A[A.reason!='open'].copy()
A=months_filter(A).copy(); print('meses:',MONTHS,'| trades:',len(A))
d=A.entry-A.stop_px
# quantidade com risco mais perto de 100 USD dentro de 85–115 (arredonda para cima ou para baixo); se nenhuma cabe, a de baixo; sem alavancagem
cap=np.maximum(np.floor(BANK/A.entry),1); lo_q=np.minimum(np.floor(RISK/d),cap); hi_q=np.minimum(np.ceil(RISK/d),cap)
ok=lambda q:(q>=1)&(q*d>=RLO)&(q*d<=RHI)
sh=np.where(ok(lo_q)&(~ok(hi_q)|((RISK-lo_q*d)<=(hi_q*d-RISK))),lo_q,np.where(ok(hi_q),hi_q,lo_q)); sh=np.maximum(sh,1)
A['shares']=sh; A['risk$']=sh*d; A['pnl']=sh*(A.exit-A.entry); A['pos$']=sh*A.entry
A['t_exit']=pd.to_datetime(A.edate)+pd.to_timedelta(A.weeks.fillna(0)*7,unit='D')
def st(g):
    g=g.sort_values('t_exit'); p=g.pnl.values; c=np.cumsum(p); dd=(np.maximum.accumulate(np.r_[0,c])[1:]-c).max()
    yrs=max((g.t_exit.max()-pd.to_datetime(g.edate).min()).days/365.25,1)
    w,l=p[p>0],p[p<=0]
    return pd.Series({'trades':len(p),'acerto %':100*len(w)/len(p),'retorno total %':100*p.sum()/BANK,'retorno/ano %':100*p.sum()/BANK/yrs,
      'por trade %':100*p.mean()/BANK,'ganho médio $':w.mean() if len(w) else 0,'perda média $':l.mean() if len(l) else 0,
      'payoff':(w.mean()/-l.mean()) if len(w) and len(l) else np.nan,'profit factor':(w.sum()/-l.sum()) if len(l) else np.nan,
      'max DD %':100*dd/BANK,'ativos':g.sym.nunique(),'risco médio $':g['risk$'].mean()})
pd.set_option('display.width',250); pd.set_option('display.float_format','{:.2f}'.format)
lab={'123':'123','brk':'Rompimento','inside':'Inside bar','trap':'Trap','wedge':'Cunha','wedge_vol':'Cunha + volume','ns':'Cunha sem Stoch (T3)','ns_vol':'T3 + volume','close':'Fech. do toque','open':'Abert. seguinte'}
out=[]
for tg in ['topo','2R','fib161','tempo26']:
    g=A[(A.stop=='pivot')&(A.tgt==tg)&A.trend]
    for (tf,trig),gg in g.groupby(['tf','trig']):
        s=st(gg); s['alvo']=tg; s['tf']='Diário' if tf=='D' else 'Semanal'; s['gatilho']=lab[trig]; out.append(s)
R=pd.DataFrame(out).set_index(['alvo','tf','gatilho'])
R.to_csv(RESULTS+'/bank.csv')
for tg in ['topo','tempo26']: print('\n',tg); print(R.loc[tg].drop(columns=['risco médio $']).to_string())
print('\nrisco médio $ (topo):'); print(R.loc['topo']['risco médio $'].round(0).to_string())
# T2 filter in $
g=A[(A.stop=='pivot')&(A.tgt=='topo')&A.trend&A.trig.isin(['123','brk','inside','trap','wedge','ns'])]
print('\nT2 bloqueio, por trade %:'); print(g.groupby(['trig','blk']).pnl.agg(lambda p:100*p.mean()/BANK).unstack().round(2).to_string())
