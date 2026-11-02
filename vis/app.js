(function(){
const DATA=window.__DATA;
const $=id=>document.getElementById(id);
const cv=$('cv'),ctx=cv.getContext('2d'),box=$('box'),tip=$('tip'),ohlc=$('ohlc');
const S={tf:'D',log:false,set:'T1',sel:null,L:{T1:true,T3:false,fall:true,allw:false,rise:true,ep:true}};
const times={D:DATA.D.map(b=>b[0]),W:DATA.W.map(b=>b[0])};
const fmtD=t=>{const d=new Date(t*1000);return d.toISOString().slice(0,10)};
const fmtP=p=>p==null?'–':(p>=10?p.toFixed(2):p>=1?p.toFixed(3):p.toFixed(4));
function ub(a,x){let lo=0,hi=a.length;while(lo<hi){const m=(lo+hi)>>1;if(a[m]<=x)lo=m+1;else hi=m}return lo}
function tIdx(t){return Math.max(0,ub(times[S.tf],t)-1)}
function tF(t){const T=times[S.tf];const i=Math.max(0,ub(T,t)-1);if(i>=T.length-1)return i;const f=(t-T[i])/(T[i+1]-T[i]);return i+Math.max(0,Math.min(1,f))-(S.tf==='W'?0.4:0)}
// weekly K mapped to each bar of a timeframe
const Kw=DATA.K.map(k=>k[1]);
const Kmap={W:Kw,D:times.D.map(t=>Kw[Math.max(0,ub(times.W,t)-1)])};
const view={start:0,n:200};
function dedupe(list){const out=[];for(const w of list.slice().sort((a,b)=>a.bi-b.bi)){const p=out[out.length-1];if(p&&w.si<p.bi){if(w.tu+w.tl>p.tu+p.tl)out[out.length-1]=w;continue}out.push(w)}return out}
const SHOWN=new Set();['D','W'].forEach(tf=>['fall','rise'].forEach(k=>dedupe(DATA.wedges.filter(w=>w.tf===tf&&w.kind===k)).forEach(w=>SHOWN.add(w))));
const LINK={T1:new Set(),T3:new Set()};DATA.trades.forEach(t=>{const w=DATA.wedges.find(w=>w.kind==='fall'&&w.tf===t.tf&&w.b===t.t_in);if(w){LINK[t.set].add(w);t.w=w}});
function wedgeOn(w){if(w.kind==='rise')return S.L.rise&&SHOWN.has(w);if(!S.L.fall)return false;if(S.L.allw&&SHOWN.has(w))return true;return (S.L.T1&&LINK.T1.has(w))||(S.L.T3&&LINK.T3.has(w))}
let css={},Wd=0,H=0,PW=0,MH=0,SH=0,AX=64,TA=22;
function readCss(){const s=getComputedStyle(document.documentElement);['bg','panel','ink','muted','line','grid','up','down','fall','rise','ep','t3','win','loss'].forEach(k=>css[k]=s.getPropertyValue('--'+k).trim())}
function size(){const dpr=window.devicePixelRatio||1;Wd=box.clientWidth;const small=Wd<600;const vh=window.innerHeight||900;const top=Math.max(0,box.getBoundingClientRect().top+window.scrollY);const wide=Wd>=1200;H=small?380+90+TA:Math.max(560,Math.min(wide?vh-(top>vh*0.5?60:top+60):700,2200));SH=small?90:Math.round(Math.min(220,Math.max(110,H*0.17)));MH=small?380:H-SH-TA;
  cv.width=Wd*dpr;cv.height=H*dpr;cv.style.height=H+'px';ctx.setTransform(dpr,0,0,dpr,0,0);AX=small?54:64;PW=Wd-AX}
const bars=()=>DATA[S.tf];
function clampView(){const N=bars().length;view.n=Math.max(20,Math.min(N+20,view.n));view.start=Math.max(-10,Math.min(N-view.n*0.3,view.start))}
const bw=()=>PW/view.n;
const xOf=i=>(i-view.start+0.5)*bw();
let lo=1,hi=2;
function range(){const B=bars();const a=Math.max(0,Math.floor(view.start)),b=Math.min(B.length-1,Math.ceil(view.start+view.n));lo=Infinity;hi=-Infinity;
  for(let i=a;i<=b;i++){if(B[i][3]<lo)lo=B[i][3];if(B[i][2]>hi)hi=B[i][2]}
  if(!isFinite(lo)){lo=1;hi=2}
  if(S.log){const l=Math.log(lo),h=Math.log(hi),p=(h-l)*0.08||0.05;lo=Math.exp(l-p);hi=Math.exp(h+p)}else{const p=(hi-lo)*0.08||1;lo=Math.max(lo-p,hi>0?1e-6:lo-p);hi=hi+p}}
function yOf(p){if(S.log){p=Math.max(p,1e-6);return 8+(MH-16)*(1-(Math.log(p)-Math.log(lo))/(Math.log(hi)-Math.log(lo)))}return 8+(MH-16)*(1-(p-lo)/(hi-lo))}
function pOf(y){const f=1-(y-8)/(MH-16);return S.log?Math.exp(Math.log(lo)+f*(Math.log(hi)-Math.log(lo))):lo+f*(hi-lo)}
const yK=k=>MH+6+(SH-12)*(1-k/100);
function niceTicks(){const out=[];if(S.log){const l=Math.log10(lo),h=Math.log10(hi);const steps=[1,2,5];for(let e=Math.floor(l)-1;e<=Math.ceil(h);e++)for(const s of steps){const v=s*10**e;if(v>=lo&&v<=hi)out.push(v)}
  if(out.length<4){out.length=0;const st=(hi-lo)/5;for(let i=0;i<=5;i++)out.push(lo+st*i)}return out}
  const raw=(hi-lo)/6,m=10**Math.floor(Math.log10(raw));const st=[1,2,5,10].map(x=>x*m).find(x=>x>=raw);for(let v=Math.ceil(lo/st)*st;v<=hi;v+=st)out.push(v);return out}
function visT(){const B=bars();const a=Math.max(0,Math.floor(view.start)),b=Math.min(B.length-1,Math.ceil(view.start+view.n));return[B[a][0],B[b][0]+86400*7]}
function inView(t0,t1){const[a,b]=visT();return t1>=a&&t0<=b}
function tradeVisible(t){if(t.set==='T1'&&!S.L.T1)return false;if(t.set==='T3'&&!S.L.T3)return false;return true}

function draw(){readCss();range();const B=bars();const w=bw();
  ctx.fillStyle=css.panel;ctx.fillRect(0,0,Wd,H);
  // grid + price labels
  ctx.font='11px "IBM Plex Mono",monospace';ctx.textBaseline='middle';
  for(const v of niceTicks()){const y=yOf(v);if(y<4||y>MH-4)continue;ctx.strokeStyle=css.grid;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(0,y+.5);ctx.lineTo(PW,y+.5);ctx.stroke();ctx.fillStyle=css.muted;ctx.textAlign='left';ctx.fillText(fmtP(v),PW+6,y)}
  // time labels
  ctx.textAlign='center';ctx.textBaseline='alphabetic';const a=Math.max(0,Math.floor(view.start)),b=Math.min(B.length-1,Math.ceil(view.start+view.n));
  const spanDays=(B[b][0]-B[a][0])/86400;let lastKey=null,lastX=-99;
  for(let i=a;i<=b;i++){const d=new Date(B[i][0]*1000);const key=spanDays>1500?d.getUTCFullYear():spanDays>200?d.getUTCFullYear()*12+(Math.floor(d.getUTCMonth()/3)):d.getUTCFullYear()*12+d.getUTCMonth();
    if(key!==lastKey){const x=xOf(i);if(lastKey!==null&&x-lastX>60&&x<PW-20){ctx.strokeStyle=css.grid;ctx.beginPath();ctx.moveTo(x+.5,0);ctx.lineTo(x+.5,MH+SH);ctx.stroke();ctx.fillStyle=css.muted;
      ctx.fillText(spanDays>1500?String(d.getUTCFullYear()):(d.getUTCMonth()===0?String(d.getUTCFullYear()):['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'][d.getUTCMonth()]),x,MH+SH+15);lastX=x}lastKey=key}}
  ctx.save();ctx.beginPath();ctx.rect(0,0,PW,MH);ctx.clip();
  // episodes
  if(S.L.ep){ctx.fillStyle=css.ep;for(const[e0,e1]of DATA.episodes){if(!inView(e0,e1+7*86400))continue;const x0=xOf(tIdx(e0))-w/2;const x1=xOf(tIdx(e1+7*86400-1))+w/2;ctx.fillRect(x0,0,x1-x0,MH)}}
  // trade boxes (T1)
  const lastT=B[B.length-1][0];
  for(const t of DATA.trades){if(t.set!=='T1'||!S.L.T1)continue;const tout=t.t_out||lastT;if(!inView(t.t_in,tout))continue;
    const x0=xOf(tIdx(t.t_in)),x1=Math.max(xOf(tIdx(tout)),x0+w);const ye=yOf(t.entry),ys=yOf(t.stop),yt=t.tgt?yOf(t.tgt):ye;
    const selA=S.sel===t?1:0.85;ctx.globalAlpha=selA;ctx.fillStyle=css.win;ctx.fillRect(x0,yt,x1-x0,ye-yt);ctx.fillStyle=css.loss;ctx.fillRect(x0,ye,x1-x0,ys-ye);ctx.globalAlpha=1;
    ctx.strokeStyle=css.muted;ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(x0,ye+.5);ctx.lineTo(x1,ye+.5);ctx.stroke();ctx.setLineDash([]);
    if(S.sel===t){ctx.strokeStyle=css.ink;ctx.lineWidth=1.5;ctx.strokeRect(x0,Math.min(yt,ys),x1-x0,Math.abs(ys-yt));ctx.lineWidth=1}}
  // candles
  const cw=Math.max(1,Math.min(w*0.7,14));
  for(let i=a;i<=b;i++){const[t,o,h,l,c]=B[i];const x=xOf(i),up=c>=o;ctx.strokeStyle=ctx.fillStyle=up?css.up:css.down;
    ctx.beginPath();ctx.moveTo(Math.round(x)+.5,yOf(h));ctx.lineTo(Math.round(x)+.5,yOf(l));ctx.stroke();
    if(cw>2){const y1=yOf(Math.max(o,c)),y2=yOf(Math.min(o,c));ctx.fillRect(x-cw/2,y1,cw,Math.max(1,y2-y1))}}
  // wedges
  for(const wd of DATA.wedges){if(!wedgeOn(wd))continue;
    const N=DATA[wd.tf];if(!inView(N[wd.si][0],N[wd.bi][0]))continue;
    const col=wd.kind==='fall'?css.fall:css.rise;const isSel=S.sel&&S.sel.w===wd;const lw=(wd.tf==='W'?2.4:1.3)+(isSel?0.8:0);const span=wd.bi-wd.si;
    const pts=k=>{const arr=[];for(let i=wd.si;i<=wd.bi;i++){const f=(i-wd.si)/span;arr.push([xOf(wd.tf===S.tf?i:tF(N[i][0])),yOf(k[0][1]+(k[1][1]-k[0][1])*f)])}return arr};
    const U=pts(wd.up),Lo=pts(wd.lo);
    ctx.globalAlpha=0.08;ctx.fillStyle=col;ctx.beginPath();U.forEach((p,j)=>j?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));for(let j=Lo.length-1;j>=0;j--)ctx.lineTo(Lo[j][0],Lo[j][1]);ctx.closePath();ctx.fill();ctx.globalAlpha=1;
    ctx.strokeStyle=col;ctx.lineWidth=lw;for(const P of[U,Lo]){ctx.beginPath();P.forEach((p,j)=>j?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.stroke()}ctx.lineWidth=1;
    for(const[pt,pp]of wd.piv){const x=xOf(wd.tf===S.tf?tIdx(pt):tF(pt)),y=yOf(pp);ctx.fillStyle=col;ctx.beginPath();ctx.arc(x,y,2.6,0,7);ctx.fill()}
    const bx=xOf(wd.tf===S.tf?tIdx(wd.b):tF(wd.b)),by=yOf(wd.bpx);ctx.strokeStyle=col;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(bx-4,by-4);ctx.lineTo(bx+4,by+4);ctx.moveTo(bx+4,by-4);ctx.lineTo(bx-4,by+4);ctx.stroke();ctx.lineWidth=1}
  // markers
  for(const t of DATA.trades){if(!tradeVisible(t))continue;const tout=t.t_out||lastT;if(!inView(t.t_in,tout))continue;
    const x=xOf(tIdx(t.t_in)),ib=tIdx(t.t_in);const y=yOf(B[ib][3])+10;ctx.fillStyle=t.set==='T1'?css.up:css.t3;
    ctx.beginPath();ctx.moveTo(x,y-6);ctx.lineTo(x-5,y+3);ctx.lineTo(x+5,y+3);ctx.closePath();ctx.fill();
    if(t.set==='T1'&&t.t_out){const xe=xOf(tIdx(t.t_out)),yex=yOf(t.exit);ctx.fillStyle=t.reason==='target'?css.up:t.reason==='stop'?css.down:css.muted;ctx.strokeStyle=css.panel;ctx.beginPath();ctx.arc(xe,yex,4.5,0,7);ctx.fill();ctx.stroke()}}
  ctx.restore();
  // stoch pane
  ctx.strokeStyle=css.line;ctx.beginPath();ctx.moveTo(0,MH+.5);ctx.lineTo(Wd,MH+.5);ctx.moveTo(0,MH+SH+.5);ctx.lineTo(Wd,MH+SH+.5);ctx.moveTo(PW+.5,0);ctx.lineTo(PW+.5,MH+SH);ctx.stroke();
  ctx.fillStyle=css.loss;ctx.fillRect(0,yK(20),PW,yK(0)-yK(20));
  ctx.textBaseline='middle';ctx.textAlign='left';ctx.fillStyle=css.muted;[20,80].forEach(v=>{ctx.fillText(String(v),PW+6,yK(v));ctx.strokeStyle=css.grid;ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(0,yK(v)+.5);ctx.lineTo(PW,yK(v)+.5);ctx.stroke();ctx.setLineDash([])});
  ctx.fillText('Slow Stoch K',6,MH+14);
  const K=Kmap[S.tf];ctx.save();ctx.beginPath();ctx.rect(0,MH,PW,SH);ctx.clip();ctx.strokeStyle=css.fall;ctx.lineWidth=1.4;ctx.beginPath();let st=false;
  for(let i=a;i<=b;i++){const k=K[i];if(k==null){st=false;continue}const x=xOf(i),y=yK(k);st?ctx.lineTo(x,y):ctx.moveTo(x,y);st=true}ctx.stroke();ctx.restore();ctx.lineWidth=1;
  if(hover)drawCross()}
let hover=null;
function drawCross(){const{x,y}=hover;if(x>PW)return;ctx.strokeStyle=css.muted;ctx.setLineDash([2,3]);ctx.beginPath();ctx.moveTo(x+.5,0);ctx.lineTo(x+.5,MH+SH);if(y<MH){ctx.moveTo(0,y+.5);ctx.lineTo(PW,y+.5)}ctx.stroke();ctx.setLineDash([]);
  if(y<MH){const p=pOf(y);ctx.fillStyle=css.ink;ctx.fillRect(PW,y-9,AX,18);ctx.fillStyle=css.panel;ctx.textAlign='left';ctx.textBaseline='middle';ctx.fillText(fmtP(p),PW+6,y)}}
function tradeAt(x,y){let best=null,bd=1e9;const lastT=bars()[bars().length-1][0];
  for(const t of DATA.trades){if(!tradeVisible(t))continue;const x0=xOf(tIdx(t.t_in));const ib=tIdx(t.t_in);const my=yOf(bars()[ib][3])+8;const d=Math.hypot(x-x0,y-my);if(d<10&&d<bd){bd=d;best=t}}
  if(best)return best;
  for(const t of DATA.trades){if(t.set!=='T1'||!S.L.T1)continue;const x0=xOf(tIdx(t.t_in)),x1=xOf(tIdx(t.t_out||lastT));const ya=yOf(t.tgt||t.entry),yb=yOf(t.stop);if(x>=x0&&x<=Math.max(x1,x0+bw())&&y>=Math.min(ya,yb)&&y<=Math.max(ya,yb))return t}return null}
function resTxt(t){return t.reason==='target'?'Alvo':t.reason==='stop'?'Stop':t.reason==='time'?'Tempo (52 sem)':'Aberto'}
function tipHtml(t){return `<b>${t.set} · ${t.tf==='D'?'cunha diária':'cunha semanal'}</b><br>Entrada ${fmtD(t.t_in)} @ ${fmtP(t.entry)}<br>Stop ${fmtP(t.stop)} · Alvo ${fmtP(t.tgt)}<br>Risco ${((t.entry-t.stop)/t.entry*100).toFixed(1)}%<br>${resTxt(t)}${t.t_out?' em '+fmtD(t.t_out):''} @ ${fmtP(t.exit)}<br>R ${t.R==null?'–':t.R.toFixed(2)} · MM50 ${t.trend?'subindo':'caindo'}${t.vol?' · volume ✓':''}${t.blk?' · cunha asc. recente':''}`}
function onMove(x,y){hover={x,y};const B=bars();const i=Math.round(view.start+x/bw()-0.5);if(i>=0&&i<B.length){const[t,o,h,l,c]=B[i];ohlc.textContent=`${fmtD(t)}  A ${fmtP(o)}  M ${fmtP(h)}  m ${fmtP(l)}  F ${fmtP(c)}  K ${Kmap[S.tf][i]==null?'–':Kmap[S.tf][i].toFixed(1)}`}
  const t=y<MH?tradeAt(x,y):null;if(t){tip.innerHTML=tipHtml(t);tip.hidden=false;const tw=tip.offsetWidth;tip.style.left=Math.min(x+14,Wd-tw-6)+'px';tip.style.top=Math.min(y+14,H-tip.offsetHeight-6)+'px'}else tip.hidden=true;
  requestAnimationFrame(draw)}
// interaction
const ptrs=new Map();let drag=null,pinch=null;
cv.addEventListener('pointerdown',e=>{cv.setPointerCapture(e.pointerId);ptrs.set(e.pointerId,{x:e.offsetX,y:e.offsetY});
  if(ptrs.size===1)drag={x:e.offsetX,start:view.start,moved:false};else if(ptrs.size===2){const p=[...ptrs.values()];pinch={d:Math.abs(p[0].x-p[1].x)||1,n:view.n,c:view.start+((p[0].x+p[1].x)/2)/bw()};drag=null}});
cv.addEventListener('pointermove',e=>{if(ptrs.has(e.pointerId))ptrs.set(e.pointerId,{x:e.offsetX,y:e.offsetY});
  if(pinch&&ptrs.size===2){const p=[...ptrs.values()];const d=Math.abs(p[0].x-p[1].x)||1;view.n=pinch.n*pinch.d/d;clampView();const cx=(p[0].x+p[1].x)/2;view.start=pinch.c-cx/bw();clampView();requestAnimationFrame(draw);return}
  if(drag){const dx=e.offsetX-drag.x;if(Math.abs(dx)>3)drag.moved=true;view.start=drag.start-dx/bw();clampView()}onMove(e.offsetX,e.offsetY)});
const end=e=>{ptrs.delete(e.pointerId);if(drag&&!drag.moved&&e.type==='pointerup'){const t=tradeAt(e.offsetX,e.offsetY);if(t){S.sel=t;renderTable(true)}}if(ptrs.size<2)pinch=null;if(ptrs.size===0)drag=null};
cv.addEventListener('pointerup',end);cv.addEventListener('pointercancel',end);
cv.addEventListener('pointerleave',()=>{hover=null;tip.hidden=true;requestAnimationFrame(draw)});
cv.addEventListener('wheel',e=>{e.preventDefault();const c=view.start+e.offsetX/bw();const f=e.deltaY>0?1.15:1/1.15;if(Math.abs(e.deltaX)>Math.abs(e.deltaY)){view.start+=e.deltaX/bw();}else{view.n*=f;clampView();view.start=c-e.offsetX/bw()}clampView();requestAnimationFrame(draw)},{passive:false});
cv.addEventListener('dblclick',()=>{fitAll()});
function zoom(f){const c=view.start+view.n/2;view.n*=f;clampView();view.start=c-view.n/2;clampView();draw()}
function fitAll(){view.n=bars().length+10;view.start=-5;clampView();draw()}
$('zin').onclick=()=>zoom(1/1.5);$('zout').onclick=()=>zoom(1.5);$('zall').onclick=fitAll;
function setTf(tf,keepT){const mid=keepT??bars()[Math.max(0,Math.min(bars().length-1,Math.round(view.start+view.n/2)))][0];const ratio=tf===S.tf?1:(tf==='W'?1/5:5);
  S.tf=tf;$('tfD').setAttribute('aria-pressed',tf==='D');$('tfW').setAttribute('aria-pressed',tf==='W');view.n=view.n*ratio;clampView();view.start=tIdx(mid)-view.n/2;clampView();draw()}
$('tfD').onclick=()=>setTf('D');$('tfW').onclick=()=>setTf('W');
$('scLog').onclick=()=>{S.log=true;$('scLog').setAttribute('aria-pressed',true);$('scLin').setAttribute('aria-pressed',false);draw()};
$('scLin').onclick=()=>{S.log=false;$('scLin').setAttribute('aria-pressed',true);$('scLog').setAttribute('aria-pressed',false);draw()};
[['lT1','T1'],['lT3','T3'],['lFall','fall'],['lAll','allw'],['lRise','rise'],['lEp','ep']].forEach(([id,k])=>$(id).onchange=e=>{S.L[k]=e.target.checked;draw()});
function focusTrade(t,noScroll){S.sel=t;if(t.set==='T3'&&!S.L.T3){S.L.T3=true;$('lT3').checked=true}
  S.tf=t.tf;$('tfD').setAttribute('aria-pressed',t.tf==='D');$('tfW').setAttribute('aria-pressed',t.tf==='W');
  const i0=tIdx(t.t_in),i1=tIdx(t.t_out||bars()[bars().length-1][0]);const span=Math.max(i1-i0,5);view.n=Math.max(t.tf==='D'?140:60,span*2.6,PW/(t.tf==='D'?9:12));clampView();view.start=i0-view.n*0.55;clampView();draw();if(!noScroll)box.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'})}
// stats + table
function stat(arr){const c=arr.filter(t=>t.R!=null&&t.reason!=='open');const n=c.length;if(!n)return null;return{n,win:c.filter(t=>t.exit>t.entry).length/n,R:c.reduce((s,t)=>s+t.R,0)/n,ret:c.reduce((s,t)=>s+(t.exit/t.entry-1),0)/n}}
function renderStats(){const T1=DATA.trades.filter(t=>t.set==='T1'),T3=DATA.trades.filter(t=>t.set==='T3');const cards=[
  ['T1 · todos',stat(T1)],['T1 · MM50 subindo',stat(T1.filter(t=>t.trend))],['T3 · todos',stat(T3)],['T3 · MM50 subindo',stat(T3.filter(t=>t.trend))]];
  $('stats').innerHTML=cards.map(([k,s])=>s?`<div class="stat"><span>${k}</span><b>${s.n} trades · R ${s.R>=0?'+':''}${s.R.toFixed(2)}</b><span style="text-transform:none;letter-spacing:0">acerto ${(s.win*100).toFixed(0)}% · ret. médio ${(s.ret*100).toFixed(1)}%</span></div>`:'').join('')}
function renderTable(scroll){const rows=DATA.trades.filter(t=>t.set===S.set).sort((a,b)=>b.t_in-a.t_in);
  $('tb').innerHTML=rows.map((t,j)=>{const cls=t.reason==='target'?'pw':t.reason==='stop'?'pl':'pn';return `<tr tabindex="0" data-j="${DATA.trades.indexOf(t)}" class="${S.sel===t?'sel':''}"><td>${fmtD(t.t_in)}</td><td>${t.tf==='D'?'D':'S'}</td><td>${t.trend?'sim':'não'}</td><td>${t.vol?'sim':'–'}</td><td>${t.blk?'sim':'–'}</td><td>${fmtP(t.entry)}</td><td>${fmtP(t.stop)}</td><td>${fmtP(t.tgt)}</td><td>${fmtP(t.exit)}</td><td>${t.t_out?fmtD(t.t_out):'–'}</td><td><span class="pill ${cls}">${resTxt(t)}</span></td><td>${t.R==null?'–':(t.R>=0?'+':'')+t.R.toFixed(2)}</td></tr>`}).join('');
  [...$('tb').querySelectorAll('tr')].forEach(tr=>{const go=()=>{focusTrade(DATA.trades[+tr.dataset.j]);renderTable()};tr.onclick=go;tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}}});
  if(scroll){const r=$('tb').querySelector('tr.sel');if(r&&S.sel.set===S.set)r.scrollIntoView({block:'nearest'})}draw()}
$('sT1').onclick=()=>{S.set='T1';$('sT1').setAttribute('aria-pressed',true);$('sT3').setAttribute('aria-pressed',false);renderTable()};
$('sT3').onclick=()=>{S.set='T3';$('sT3').setAttribute('aria-pressed',true);$('sT1').setAttribute('aria-pressed',false);if(!S.L.T3){S.L.T3=true;$('lT3').checked=true}renderTable()};
let rz;window.addEventListener('resize',()=>{clearTimeout(rz);rz=setTimeout(()=>{const pw=PW;size();view.n=view.n*PW/(pw||PW);clampView();draw()},80)});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',draw);
new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
size();renderStats();
const start=DATA.trades.filter(t=>t.set==='T1'&&t.tf==='D').sort((a,b)=>b.t_in-a.t_in).find(t=>window.__START?fmtD(t.t_in).startsWith(window.__START):true)||DATA.trades[0];
focusTrade(start,true);renderTable();
if(document.fonts)document.fonts.ready.then(draw);
})();
