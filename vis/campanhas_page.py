"""Página interativa da estratégia Campanhas para um ativo: candles, sinais (candles coloridos por gatilho) e trades
de cada teste x saída. Roda o backtest na hora (mesmas regras de src/campanhas.py, meses D).
uso: python vis/campanhas_page.py TICKER [--desde AAAA-MM-DD]   -> results/campanhas_<TICKER>.html"""
import os, sys, json
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(here), 'src'))
import numpy as np, pandas as pd
from config import DATA_ROOT, RESULTS
from split import is_dev
import campanhas as C

a = sys.argv[1:]; sym = a[0].replace('.', '_'); since = '2020-01-01'
if '--desde' in a: since = a[a.index('--desde') + 1]
since = pd.Timestamp(since).date()

rows, trades = C.run((sym, since))
df = pd.read_csv(os.path.join(DATA_ROOT, sym, 'd.csv')); df.attrs['sym'] = sym; d = C.prep(df)
i0 = max(0, int(np.searchsorted(d['date'], since)) - 60)   # 60 pregões antes para contexto
dates = d['date']
sig = {}
for kind, s, trig, stop, win in C.signals(d, 1):
    if not d['trend'][s]: continue
    if kind == 'gap':                          # gap: só o que fechou (máxima do candle do gap atingiu o gatilho)
        if s + 1 >= len(dates) or d['h'][s + 1] < trig: continue
        marks = [(s + 1, None)]
    elif kind == '123': marks = [(s - 2, 1), (s - 1, 2), (s, 3)]   # os 3 candles do 123 (papel 1, 2, 3)
    else: marks = [(s, None)]
    for j, role in marks:
        if i0 <= j < len(dates):
            sig.setdefault(j - i0, []).append([C.KINDS.index(kind), round(float(trig), 4), None if stop is None else round(float(stop), 4), role])
for j, v in sig.items():   # um registro por gatilho em cada candle (no 123 vale o papel de candle do sinal), na ordem dos gatilhos
    best = {}
    for e in v:
        if e[0] not in best or (e[3] or 3) > (best[e[0]][3] or 3): best[e[0]] = e
    sig[j] = [best[k] for k in sorted(best)]
idx = {dt: k - i0 for k, dt in enumerate(dates)}
T = [[t['teste'], t['saida'], idx[t['edate']], idx[t['xdate']], C.KINDS.index(t['trig']), round(t['entry'], 4), round(t['stop_px'], 4),
      None if t['tgt_px'] is None or t['tgt_px'] != t['tgt_px'] else round(t['tgt_px'], 4), round(t['exit'], 4), t['reason']] for t in trades]
S = {f"{r['teste']}|{r['saida']}": [r['trades'], round(r['ret'], 2), round(r['ret_ano'], 2), None if r['acerto'] != r['acerto'] else round(r['acerto'], 1),
                                    None if r['pf'] != r['pf'] else round(r['pf'], 2), round(r['dd'], 2)] for r in rows}
sl = slice(i0, len(dates))
data = dict(sym=a[0], since=str(since), t=[str(x) for x in dates[sl]], o=d['o'][sl].round(4).tolist(), h=d['h'][sl].round(4).tolist(),
            l=d['l'][sl].round(4).tolist(), c=d['c'][sl].round(4).tolist(),
            ma=[None if v != v else round(v, 4) for v in d['sma'][sl]], up=[bool(x) for x in d['trend'][sl]],
            dev=[bool(x) for x in is_dev(dates[sl])], sig=sig, trades=T, stats=S, kinds=C.KINDS)

HTML = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campanhas __SYM__</title>
<style>
:root{--surface:#fcfcfb;--panel:#ffffff;--ink:#0b0b0b;--ink2:#52514b;--muted:#6f6e66;--grid:#e1e0d9;--axis:#c3c2b7;--ring:rgba(11,11,11,.10);
 --candle:#8f8e86;--rshade:rgba(11,11,11,.045);--win:#006300;--loss:#d03b3b;--ma:#52514b;
 --k0:#2a78d6;--k1:#eb6834;--k2:#1baf7a;--k3:#eda100;--k4:#e87ba4;--k5:#008300;--k6:#6250d6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--surface:#1a1a19;--panel:#222220;--ink:#f0efec;--ink2:#c3c2b7;--muted:#9b9a92;
 --grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--candle:#77766f;--rshade:rgba(255,255,255,.04);--win:#0ca30c;--loss:#e66767;--ma:#c3c2b7;
 --k0:#3987e5;--k1:#d95926;--k2:#199e70;--k3:#c98500;--k4:#d55181;--k5:#008300;--k6:#9085e9}}
:root[data-theme="dark"]{color-scheme:dark;--surface:#1a1a19;--panel:#222220;--ink:#f0efec;--ink2:#c3c2b7;--muted:#9b9a92;--grid:#2c2c2a;--axis:#383835;
 --ring:rgba(255,255,255,.10);--candle:#77766f;--rshade:rgba(255,255,255,.04);--win:#0ca30c;--loss:#e66767;--ma:#c3c2b7;
 --k0:#3987e5;--k1:#d95926;--k2:#199e70;--k3:#c98500;--k4:#d55181;--k5:#008300;--k6:#9085e9}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{padding:16px;display:flex;flex-direction:column;gap:12px;max-width:none}
h1{margin:0;font-size:22px;font-weight:600}.sub{margin:0;color:var(--ink2);max-width:90ch}
.bar{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center}
select,button{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--axis);border-radius:6px;padding:4px 8px}
label{display:inline-flex;gap:6px;align-items:center;cursor:pointer;color:var(--ink2)}
.tiles{display:flex;flex-wrap:wrap;gap:8px}
.tile{background:var(--panel);border:1px solid var(--grid);border-radius:8px;padding:6px 12px;min-width:110px}
.tile b{display:block;font-size:17px;font-weight:600;font-variant-numeric:tabular-nums}.tile span{font-size:12px;color:var(--muted)}
.legend{display:flex;flex-wrap:wrap;gap:6px}
.chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--grid);background:var(--panel);border-radius:999px;padding:3px 10px;cursor:pointer;color:var(--ink);font-size:13px}
.chip i{width:12px;height:12px;border-radius:3px;display:inline-block}.chip.off{opacity:.4}.chip small{color:var(--muted)}
#box{position:relative;background:var(--panel);border:1px solid var(--grid);border-radius:8px;touch-action:none}
canvas{display:block;width:100%}
#tip{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--axis);border-radius:6px;padding:6px 9px;font-size:12px;
 box-shadow:0 2px 8px rgba(0,0,0,.12);display:none;max-width:320px;white-space:nowrap;font-variant-numeric:tabular-nums}
#tip .k{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px}
.hint{color:var(--muted);font-size:12px}
details summary{cursor:pointer;color:var(--ink2)}
table{border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums;margin-top:6px}
th,td{padding:3px 8px;border-bottom:1px solid var(--grid);text-align:right}th{color:var(--muted);font-weight:500}td:first-child,th:first-child{text-align:left}
@media (max-width:600px){.tile{min-width:90px}.tile b{font-size:15px}}
</style></head><body><div class="wrap">
<h1>__SYM__ · Campanhas (diário)</h1>
<p class="sub">Candles cinza = sem sinal. Candle colorido = sinal de compra com a MM50 subindo (cor = gatilho; o 123 pinta os 3 candles; o gap marca o próprio candle e só quando fechou). Candle com mais de um sinal tem a cor de um deles e a sigla de todos. ▲ entrada, ● saída; linha verde = trade com lucro, vermelha = prejuízo; tracejados = stop e alvo. Faixas sombreadas = meses R (sem entradas). Roda do mouse dá zoom, arrastar move.</p>
<div class="bar">
 <label>Teste <select id="teste"></select></label>
 <label>Saída <select id="saida"></select></label>
 <label><input type="checkbox" id="cSig" checked> Sinais</label>
 <label><input type="checkbox" id="cTr" checked> Trades</label>
 <label><input type="checkbox" id="cSt" checked> Stop/alvo</label>
 <label><input type="checkbox" id="cMa" checked> MM50</label>
 <label><input type="checkbox" id="cR" checked> Meses R</label>
 <button id="all">Ver tudo</button>
</div>
<div class="tiles" id="tiles"></div>
<div class="legend" id="legend"></div>
<div id="box"><canvas id="cv"></canvas><div id="tip"></div></div>
<div class="hint" id="ohlc"></div>
<details><summary>Tabela de trades do teste selecionado</summary><div id="tbl"></div></details>
</div>
<script>window.__D=__DATA__;</script>
<script>
(function(){
const D=window.__D,N=D.t.length,$=id=>document.getElementById(id),cv=$('cv'),ctx=cv.getContext('2d'),box=$('box'),tip=$('tip');
const KN={'123':'123','inside':'Inside bar','trap':'Trap','bvi':'Barra vermelha ign.','ssi':'Sombra sup. ign.','trapmm':'Trap MM50','gap':'Gap'};
const KS=['1','I','T','V','S','M','G'];
const TN={...KN,'todos':'Todos os gatilhos','todos_sem_gap':'Todos sem gap'};
const SX={'topo':'Topo anterior (ou 2R)','2R':'2R','3R':'3R','sinal':'Sinal de venda','stoch':'Stoch 14/3 > 80'};
const S={teste:'todos',saida:'3R',sig:true,tr:true,st:true,ma:true,r:true,on:D.kinds.map(()=>true)};
const view={start:Math.max(0,N-260),n:260};let W=0,H=0,AX=64,css={},hover=null;
// controles
for(const k of ['todos','todos_sem_gap',...D.kinds]){const o=document.createElement('option');o.value=k;o.textContent=TN[k];$('teste').appendChild(o)}
for(const k of Object.keys(SX)){const o=document.createElement('option');o.value=k;o.textContent=SX[k];$('saida').appendChild(o)}
$('teste').value=S.teste;$('saida').value=S.saida;
const nSig=D.kinds.map(()=>0);for(const v of Object.values(D.sig))for(const s of v)if(s[3]==null||s[3]===3)nSig[s[0]]++;
D.kinds.forEach((k,i)=>{const c=document.createElement('span');c.className='chip';c.innerHTML=`<i style="background:var(--k${i})"></i>${KN[k]} <small>${KS[i]} · ${nSig[i]}</small>`;
 c.onclick=()=>{S.on[i]=!S.on[i];c.classList.toggle('off',!S.on[i]);draw()};$('legend').appendChild(c)});
const trades=()=>D.trades.filter(t=>t[0]===S.teste&&t[1]===S.saida);
function tiles(){const s=D.stats[S.teste+'|'+S.saida],T=trades(),cnt=D.kinds.map(()=>0);T.forEach(t=>cnt[t[4]]++);
 const f=(v,d=1,p='')=>v==null?'–':(v>0&&p?'+':'')+v.toFixed(d)+p;
 let h=`<div class="tile"><b>${s[0]}</b><span>trades</span></div><div class="tile"><b>${f(s[1],1,'%')}</b><span>retorno total</span></div>
 <div class="tile"><b>${f(s[2],1,'%')}</b><span>ao ano</span></div><div class="tile"><b>${f(s[3],0,'%')}</b><span>acerto</span></div>
 <div class="tile"><b>${s[4]==null?'–':s[4].toFixed(2)}</b><span>profit factor</span></div><div class="tile"><b>${f(s[5],1,'%')}</b><span>DD máx</span></div>`;
 if(S.teste.startsWith('todos'))h+=`<div class="tile"><span>trades por gatilho</span><b style="font-size:13px;font-weight:500">${D.kinds.map((k,i)=>cnt[i]?`${KS[i]} ${cnt[i]}`:'').filter(Boolean).join(' · ')}</b></div>`;
 $('tiles').innerHTML=h;
 const rows=T.map(t=>{const R=(t[8]-t[5])/(t[5]-t[6]);return `<tr><td>${D.t[t[2]]}</td><td>${D.t[t[3]]}</td><td style="text-align:left">${KN[D.kinds[t[4]]]}</td><td>${t[5].toFixed(2)}</td><td>${t[6].toFixed(2)}</td><td>${t[7]==null?'–':t[7].toFixed(2)}</td><td>${t[8].toFixed(2)}</td><td>${t[9]}</td><td>${(R>0?'+':'')+R.toFixed(2)}R</td></tr>`}).join('');
 $('tbl').innerHTML=`<table><tr><th>Entrada</th><th>Saída</th><th>Gatilho</th><th>Preço</th><th>Stop</th><th>Alvo</th><th>Saída $</th><th>Motivo</th><th>R</th></tr>${rows}</table>`}
// desenho
function rc(){const s=getComputedStyle(document.documentElement);['surface','panel','ink','ink2','muted','grid','axis','candle','rshade','win','loss','ma','k0','k1','k2','k3','k4','k5','k6'].forEach(k=>css[k]=s.getPropertyValue('--'+k).trim())}
function size(){const r=devicePixelRatio||1;W=box.clientWidth;H=Math.max(360,Math.min(innerHeight-260,820));cv.width=W*r;cv.height=H*r;cv.style.height=H+'px';ctx.setTransform(r,0,0,r,0,0);AX=W<600?50:62}
const PW=()=>W-AX,bw=()=>PW()/view.n,xOf=i=>(i-view.start+.5)*bw();let lo,hi;const TOP=10,BOT=26;
function clamp(){view.n=Math.max(30,Math.min(N+10,view.n));view.start=Math.max(-5,Math.min(N-view.n*.3,view.start))}
function range(){const a=Math.max(0,Math.floor(view.start)),b=Math.min(N-1,Math.ceil(view.start+view.n));lo=1/0;hi=-1/0;for(let i=a;i<=b;i++){lo=Math.min(lo,D.l[i]);hi=Math.max(hi,D.h[i])}const p=(hi-lo)*.06||1;lo-=p;hi+=p}
const yOf=p=>TOP+(H-TOP-BOT)*(1-(p-lo)/(hi-lo));
function ticks(){const raw=(hi-lo)/6,m=10**Math.floor(Math.log10(raw)),st=[1,2,5,10].map(x=>x*m).find(x=>x>=raw),o=[];for(let v=Math.ceil(lo/st)*st;v<=hi;v+=st)o.push(v);return o}
function draw(){rc();range();const a=Math.max(0,Math.floor(view.start)),b=Math.min(N-1,Math.ceil(view.start+view.n)),bwv=bw();
 ctx.fillStyle=css.panel;ctx.fillRect(0,0,W,H);ctx.font='11px system-ui,sans-serif';
 if(S.r){ctx.fillStyle=css.rshade;let i=a;while(i<=b){if(!D.dev[i]){let j=i;while(j+1<=b&&!D.dev[j+1])j++;ctx.fillRect(xOf(i)-bwv/2,TOP,(j-i+1)*bwv,H-TOP-BOT);i=j+1}else i++}}
 ctx.strokeStyle=css.grid;ctx.lineWidth=1;ctx.fillStyle=css.muted;for(const v of ticks()){const y=Math.round(yOf(v))+.5;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(PW(),y);ctx.stroke();ctx.fillText(v>=100?v.toFixed(0):v.toFixed(2),PW()+6,y+4)}
 let lm=null;for(let i=a;i<=b;i++){const m=D.t[i].slice(0,7);if(m!==lm){const mm=+m.slice(5);const show=view.n<160||mm===1||(view.n<500&&mm%3===1);if(show&&i>a){ctx.fillStyle=css.muted;ctx.fillText(mm===1?m.slice(0,4):m.slice(5)+'/'+m.slice(2,4),xOf(i)-8,H-8)}lm=m}}
 if(S.ma){ctx.strokeStyle=css.ma;ctx.lineWidth=1.5;ctx.setLineDash([]);ctx.beginPath();let on=false;for(let i=a;i<=b;i++){const v=D.ma[i];if(v==null){on=false;continue}const x=xOf(i),y=yOf(v);on?ctx.lineTo(x,y):ctx.moveTo(x,y);on=true}ctx.stroke()}
 const cw=Math.max(1,Math.min(14,bwv*.7));
 for(let i=a;i<=b;i++){const x=xOf(i),up=D.c[i]>=D.o[i];const ss=S.sig?(D.sig[i]||[]).filter(s=>S.on[s[0]]):[];const col=ss.length?css['k'+ss[0][0]]:css.candle;
  ctx.strokeStyle=col;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(Math.round(x)+.5,yOf(D.h[i]));ctx.lineTo(Math.round(x)+.5,yOf(D.l[i]));ctx.stroke();
  const y1=yOf(Math.max(D.o[i],D.c[i])),y2=yOf(Math.min(D.o[i],D.c[i])),hh=Math.max(1,y2-y1);
  if(bwv>2.5){if(up&&!ss.length){ctx.fillStyle=css.panel;ctx.fillRect(x-cw/2,y1,cw,hh);ctx.strokeRect(x-cw/2+.5,y1+.5,cw-1,Math.max(0,hh-1))}else{ctx.fillStyle=col;ctx.fillRect(x-cw/2,y1,cw,hh)}}
  if(ss.length>1&&bwv>=6){ctx.fillStyle=css.ink2;ctx.textAlign='center';ctx.fillText(ss.map(s=>KS[s[0]]).join(''),x,yOf(D.h[i])-4);ctx.textAlign='left'}}
 if(S.tr){for(const t of trades()){const[,,e,xd,k,en,st,tg,ex]=t;if(xd<a-1||e>b+1)continue;const win=ex>en,xe=xOf(e),xx=xOf(xd);
   if(S.st){ctx.setLineDash([4,3]);ctx.lineWidth=1;ctx.strokeStyle=css.loss;ctx.beginPath();ctx.moveTo(xe,yOf(st));ctx.lineTo(xx,yOf(st));ctx.stroke();
    if(tg!=null){ctx.strokeStyle=css.win;ctx.beginPath();ctx.moveTo(xe,yOf(tg));ctx.lineTo(xx,yOf(tg));ctx.stroke()}ctx.setLineDash([])}
   ctx.strokeStyle=win?css.win:css.loss;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(xe,yOf(en));ctx.lineTo(xx,yOf(ex));ctx.stroke();
   const ye=yOf(en);ctx.fillStyle=css['k'+k];ctx.strokeStyle=css.panel;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(xe,ye-7);ctx.lineTo(xe-6,ye+4);ctx.lineTo(xe+6,ye+4);ctx.closePath();ctx.stroke();ctx.fill();
   ctx.fillStyle=win?css.win:css.loss;ctx.beginPath();ctx.arc(xx,yOf(ex),4.5,0,7);ctx.stroke();ctx.fill()}}
 if(hover!=null&&hover>=a&&hover<=b){ctx.strokeStyle=css.axis;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(Math.round(xOf(hover))+.5,TOP);ctx.lineTo(Math.round(xOf(hover))+.5,H-BOT);ctx.stroke()}
 ctx.strokeStyle=css.axis;ctx.beginPath();ctx.moveTo(PW()+.5,TOP);ctx.lineTo(PW()+.5,H-BOT);ctx.stroke()}
function showTip(i,px,py){const f=v=>v.toFixed(2);let h=`<b>${D.t[i]}</b>${D.dev[i]?'':' <span style="color:var(--muted)">(mês R)</span>'}<br>A ${f(D.o[i])} · M ${f(D.h[i])} · m ${f(D.l[i])} · F ${f(D.c[i])}`;
 if(D.ma[i]!=null)h+=`<br>MM50 ${f(D.ma[i])} ${D.up[i]?'subindo':'caindo'}`;
 for(const s of (D.sig[i]||[]))h+=s[3]===1||s[3]===2?`<br><span class="k" style="background:var(--k${s[0]})"></span>123: candle ${s[3]} de 3`:`<br><span class="k" style="background:var(--k${s[0]})"></span>Sinal ${KN[D.kinds[s[0]]]}: gatilho ${f(s[1])}${s[2]!=null?' · stop '+f(s[2]):''}`;
 for(const t of trades()){if(t[2]===i||t[3]===i){const R=(t[8]-t[5])/(t[5]-t[6]);h+=`<br>${t[2]===i?'▲ Entrada':'● Saída'} ${KN[D.kinds[t[4]]]}: ${f(t[2]===i?t[5]:t[8])}`+(t[3]===i?` (${t[9]}, ${(R>0?'+':'')+R.toFixed(2)}R)`:` · stop ${f(t[6])}${t[7]!=null?' · alvo '+f(t[7]):''}`)}}
 tip.innerHTML=h;tip.style.display='block';const r=box.getBoundingClientRect();let x=px+14,y=py+14;if(x+tip.offsetWidth>r.width)x=px-tip.offsetWidth-14;if(y+tip.offsetHeight>r.height)y=py-tip.offsetHeight-14;tip.style.left=Math.max(0,x)+'px';tip.style.top=Math.max(0,y)+'px'}
let drag=null;
cv.addEventListener('wheel',e=>{e.preventDefault();const r=cv.getBoundingClientRect(),fx=Math.min(1,(e.clientX-r.left)/PW()),i=view.start+fx*view.n;view.n*=e.deltaY>0?1.15:1/1.15;view.start=i-fx*view.n;clamp();draw()},{passive:false});
cv.addEventListener('pointerdown',e=>{drag={x:e.clientX,s:view.start};cv.setPointerCapture(e.pointerId)});
cv.addEventListener('pointermove',e=>{const r=cv.getBoundingClientRect(),px=e.clientX-r.left,py=e.clientY-r.top;
 if(drag){view.start=drag.s-(e.clientX-drag.x)/bw();clamp();tip.style.display='none';draw();return}
 const i=Math.round(view.start+px/bw()-.5);if(i>=0&&i<N&&px<PW()){hover=i;draw();showTip(i,px,py);$('ohlc').textContent=''}else{hover=null;tip.style.display='none';draw()}});
cv.addEventListener('pointerup',()=>drag=null);cv.addEventListener('pointerleave',()=>{hover=null;tip.style.display='none';draw()});
$('teste').onchange=e=>{S.teste=e.target.value;tiles();draw()};$('saida').onchange=e=>{S.saida=e.target.value;tiles();draw()};
[['cSig','sig'],['cTr','tr'],['cSt','st'],['cMa','ma'],['cR','r']].forEach(([id,k])=>$(id).onchange=e=>{S[k]=e.target.checked;draw()});
$('all').onclick=()=>{view.start=0;view.n=N+5;clamp();draw()};
addEventListener('resize',()=>{size();draw()});matchMedia('(prefers-color-scheme: dark)').addEventListener('change',draw);
size();tiles();draw();
})();
</script></body></html>"""
os.makedirs(RESULTS, exist_ok=True)
out = os.path.join(RESULTS, f'campanhas_{sym}.html')
open(out, 'w').write(HTML.replace('__SYM__', a[0]).replace('__DATA__', json.dumps(data, separators=(',', ':'), default=str)))
print(out, os.path.getsize(out))
