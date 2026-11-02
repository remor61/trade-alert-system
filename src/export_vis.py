from config import DATA_ROOT, RESULTS, EXCLUDE
import os, sys, json, numpy as np, pandas as pd
import bt
from wedge2 import detect_fall, atr_arr, vol_ok
tick=sys.argv[1]; W,D=bt.W,bt.D
arr={'W':{x:W[x].values.astype(float) for x in 'ohlcv'},'D':{x:D[x].values.astype(float) for x in 'ohlcv'}}
T={'W':W.t.values.astype(int),'D':D.t.values.astype(int)}
DWI=D.wi.values.astype(int)
first_d={};[first_d.setdefault(int(w),k) for k,w in enumerate(DWI)]
wedges=[]
lastday={}
for k,wi in enumerate(DWI): lastday[int(wi)]=k
raw={}
for tf in ('W','D'):
    A=arr[tf]; a=atr_arr(A['h'],A['l'],A['c'])
    raw[(tf,'fall')]=(detect_fall(A['o'],A['h'],A['l'],A['c'],a,tf),(A['o'],A['h'],A['l'],A['c']))
    raw[(tf,'rise')]=(detect_fall(-A['o'],-A['l'],-A['h'],-A['c'],a,tf),(-A['o'],-A['l'],-A['h'],-A['c']))
for kind,tfs in [(k,[tf]) for k in ('fall','rise') for tf in ('W','D')]:
    items=[]
    for tf in tfs:
        for w in raw[(tf,kind)][0]:
            tb=T['D'][lastday.get(w['b'],len(D)-1)] if tf=='W' else T['D'][w['b']]
            items.append((tb,T[tf][w['start']],tf,w))
    items.sort(key=lambda x:x[0]); last=-1
    for tb,ts,tf,w in items:
        if ts<=last: continue
        last=max(last,tb)
        A=arr[tf]; t=T[tf]; src=raw[(tf,kind)][1]; s_=-1 if kind=='rise' else 1
        uh=lambda x:s_*(src[1][w['h1']]+w['su']*(x-w['h1'])); ll=lambda x:s_*(src[2][w['l1']]+w['sl']*(x-w['l1']))
        b=w['b']; st=w['start']
        up=[[int(t[st]),round(uh(st),4)],[int(t[b]),round(uh(b),4)]]; lo=[[int(t[st]),round(ll(st),4)],[int(t[b]),round(ll(b),4)]]
        if kind=='rise': up,lo=lo,up
        piv=[[int(t[i]),round(float(A['h' if (kind=='fall')==(j<2) else 'l'][i]),4)] for j,i in enumerate([w['h1'],w['h2'],w['l1'],w['l2']])]
        wedges.append(dict(tf=tf,kind=kind,si=int(st),bi=int(b),up=up,lo=lo,b=int(t[b]),bpx=float(A['c'][b]),vol=vol_ok(A['v'],b),piv=piv,tu=w['tu'],tl=w['tl']))
def exit_day(entry_day_next, ewi, entry, stop, tgt, maxw):
    """walk daily bars from index entry_day_next; returns (day idx, exit px, reason)"""
    do,dh,dl,dc=(arr['D'][x] for x in 'ohlc'); prev=None; pd_=entry_day_next-1
    for d in range(entry_day_next,len(dc)):
        if DWI[d]-ewi>maxw: return pd_, dc[pd_], 'time'
        o,h,l,c=do[d],dh[d],dl[d],dc[d]
        if o<=stop: return d,o,'stop'
        if tgt==tgt and tgt is not None and o>=tgt: return d,o,'target'
        seq=((l,'L'),(h,'H')) if c>=o else ((h,'H'),(l,'L'))
        for px,k in seq:
            if k=='L' and px<=stop: return d,stop,'stop'
            if k=='H' and tgt==tgt and tgt is not None and px>=tgt: return d,tgt,'target'
        pd_=d
    return None,None,'open'
X=pd.read_csv(os.path.join(bt.BASE,'wedge_trades.csv'))
trades=[]; mism=0
for _,r in X[(X.stop=='pivot')&(X.tgt=='topo')].iterrows():
    tf=r.tf
    # entry bar = close of breakout bar; recover from date
    if r.trig in ('wedge','wedge_vol'):
        cand=[w for w in wedges if w['tf']==tf and w['kind']=='fall' and abs(w['bpx']-r.entry)<1e-6]
    else:
        cand=[w for w in wedges if w['tf']==tf and w['kind']=='fall' and abs(w['bpx']-r.entry)<1e-6 and str(pd.to_datetime(w['b'],unit='s').date())==r.ep_date]
    if not cand: continue
    w=cand[0]; tb=w['b']
    if tf=='D':
        b=int(np.searchsorted(T['D'],tb)); ewi=int(DWI[b]); nd=b+1
    else:
        b=int(np.searchsorted(T['W'],tb)); ewi=b; nd=first_d.get(b+1,len(D))
    tgt=r.tgt_px if r.tgt_px==r.tgt_px else None
    d,px,why=exit_day(nd,ewi,r.entry,r.stop_px,tgt,bt.MAXW)
    if why!='open' and (abs(px-r.exit)>1e-6*max(1,r.exit)): mism+=1
    trades.append(dict(set=('T1' if r.trig.startswith('wedge') else 'T3'),vol=bool(r.trig.endswith('vol')),tf=tf,t_in=int(tb),
        t_out=int(T['D'][d]) if d is not None else None,entry=r.entry,stop=r.stop_px,tgt=tgt,exit=(px if px is not None else None),
        reason=why,trend=bool(r.trend),blk=bool(r.blk),ep=str(r.ep_date),
        R=((px-r.entry)/max(r.entry-r.stop_px,0.01*r.entry)) if px is not None else None))
# dedupe T1/T3 identical rows (wedge & wedge_vol same trade)
seen={}; out=[]
for t in trades:
    k=(t['set'],t['tf'],t['t_in'])
    if k in seen: seen[k]['vol']=seen[k]['vol'] or t['vol']; continue
    seen[k]=t; out.append(t)
# volume flag from wedge itself
for t in out:
    w=[w for w in wedges if w['tf']==t['tf'] and w['kind']=='fall' and w['b']==t['t_in']][0]; t['vol']=w['vol']
eps=[[int(W.t.iloc[i0]),int(W.t.iloc[min(iend,len(W)-1)]), bool(W.trend.iloc[i0])] for i0,iend in bt.episodes]
data=dict(sym=tick,
  D=[[int(t),*[round(float(v),4) for v in x]] for t,x in zip(T['D'],zip(*(arr['D'][k] for k in 'ohlc')))],
  W=[[int(t),*[round(float(v),4) for v in x]] for t,x in zip(T['W'],zip(*(arr['W'][k] for k in 'ohlc')))],
  K=[[int(t),round(float(k),2) if k==k else None] for t,k in zip(T['W'],W.K.values)],
  wedges=wedges,trades=out,episodes=eps)
json.dump(data,open(f'{RESULTS}/vis_{tick}.json','w'),separators=(',',':'))
print('wedges',len(wedges),'trades',len(out),'T1',sum(t['set']=='T1' for t in out),'mismatch',mism, os.path.getsize(f'{RESULTS}/vis_{tick}.json'))
