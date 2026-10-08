import React from 'react';
import {AbsoluteFill,Audio,Composition,Img,Sequence,interpolate,registerRoot,staticFile,useCurrentFrame,Easing} from 'remotion';
import {Opening} from './opening';
const C={bg:'#080d15',ivory:'#ebe5d8',gold:'#deb78d',dim:'#93a2ad',teal:'#63b8ac'};
const song='"Songti SC", "STSong", serif';
const e=(f:number,a:number,b:number)=>interpolate(f,[a,b],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:Easing.bezier(.22,.75,.23,1)});
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const show=(f:number,a:number,b:number)=>e(f,a,a+22)*(1-e(f,b-18,b));
const Text=({from,to=1800,x=103,y,size=36,color=C.ivory,children}:{from:number;to?:number;x?:number;y:number;size?:number;color?:string;children:React.ReactNode})=>{const f=useCurrentFrame();return <div style={{position:'absolute',left:x,top:y,fontSize:size,lineHeight:1.4,color,opacity:show(f,from,to),transform:`translateY(${18*(1-e(f,from,from+22))}px)`}}>{children}</div>};
const Head=({from,to,a,b}:{from:number;to:number;a:string;b:string})=><Text from={from} to={to} y={230} size={92}><span style={{fontFamily:song,fontWeight:900}}>{a}<br/><span style={{color:C.gold}}>{b}</span></span></Text>;
const Rest=()=>{const f=useCurrentFrame(),channel=e(f,570,625),machine=e(f,840,900),turtle=e(f,1110,1180),research=e(f,1380,1450),end=e(f,1640,1685);
const scale=mix(mix(.64,.63,channel),.18,machine),tx=mix(mix(660,610,channel),745,machine),ty=mix(mix(232,30,channel),365,machine);
const pts=Array.from({length:85},(_,i)=>({x:220+i*17.4,y:mix(790-i*5.3+Math.sin(i*.25)*55+Math.sin(i*1.41)*15,900-i*4.3+Math.sin(i*.25)*55+Math.sin(i*1.41)*15,channel)}));const line=pts.map((p,i)=>`${i?'L':'M'}${p.x},${p.y}`).join(' ');const point=pts[51];
return <AbsoluteFill style={{background:C.bg,color:C.ivory,fontFamily:'"PingFang SC",sans-serif',overflow:'hidden'}}>
<AbsoluteFill style={{background:'radial-gradient(ellipse at 65% 48%,#26354d88,transparent 65%)'}}/>
<div style={{position:'absolute',inset:0,opacity:1-channel}}><Img src={staticFile('livermore.jpg')} style={{position:'absolute',left:-60-channel*120,top:0,width:710,height:1080,objectFit:'cover',filter:'grayscale(1) sepia(.12)',opacity:.85}}/><AbsoluteFill style={{background:'linear-gradient(90deg,transparent 14%,#080d1555 27%,#080d15 37%),linear-gradient(0deg,#080d15,transparent 45%)'}}/></div>
<Text from={430} to={577} x={759} y={106} size={26} color={C.gold}>1940 · 利弗莫尔的交易纪律</Text>
<Text from={430} to={577} x={753} y={231} size={94}><span style={{fontFamily:song,fontWeight:900}}>看见趋势，<br/><span style={{color:C.gold}}>还要学会等待。</span></span></Text>
<Text from={430} to={481} x={771} y={809} size={38}>等待条件成立，再决定行动。</Text>
{['等待条件','持有趋势','失效退出'].map((s,i)=><Text key={s} from={474+i*15} to={577} x={770+i*330} y={809} size={38} color={i===2?C.teal:C.ivory}>{s}</Text>)}
<Text from={430} to={577} x={100} y={876} size={34}>Jesse Livermore</Text><Text from={430} to={577} x={104} y={933} size={22} color={C.dim}>1923 年档案照片 · 文意概括</Text>
<Text from={604} to={842} y={79} size={25} color={C.gold}>20 世纪中期 · 理查德·唐奇安</Text><Head from={618} to={842} a="把经验" b="写成规则。"/>
<Text from={650} to={839} y={536} size={34} color={C.dim}>观察一段时间的高低点，<br/>把突破条件说清楚。</Text><Text from={716} to={839} y={870} size={39}>同一条规则，可以重复判断。</Text>
<Text from={652} to={832} x={1673} y={404} size={27} color={C.gold}>前期高点</Text><Text from={664} to={832} x={1673} y={598} size={27} color={C.dim}>前期低点</Text>
<Text from={870} to={1118} y={79} size={25} color={C.gold}>1970 前后 · 埃德·塞柯塔</Text><Head from={886} to={1118} a="让规则" b="重复执行。"/>
<Text from={920} to={1118} y={538} size={34} color={C.dim}>把趋势跟随写进程序，<br/>减少临场随意改动。</Text><Text from={1010} to={1118} y={870} size={38}>纪律，成为可运行的流程。</Text>
<Text from={1148} to={1389} y={79} size={25} color={C.gold}>1983 · 海龟实验 · 丹尼斯与埃克哈特</Text><Head from={1164} to={1389} a="交易方法" b="能否传授？"/>
<Text from={1210} to={1389} y={540} size={34} color={C.dim}>传授的是整套约束，<br/>不只是一个入场信号。</Text><Text from={1290} to={1389} y={873} size={36}>不同的人，学习同一套方法。</Text><Text from={1306} to={1389} y={939} size={25} color={C.dim}>训练故事不等于人人都能盈利。</Text>
<Text from={1415} to={1645} y={79} size={25} color={C.gold}>2012 · 时间序列动量研究</Text><Head from={1432} to={1645} a="从个人经验" b="到跨市场检验。"/>
<Text from={1470} to={1645} y={542} size={31} color={C.dim}>Moskowitz · Ooi · Pedersen<br/>58 种期货及远期合约</Text><Text from={1555} to={1645} y={863} size={34}>让一个观点，接受更广的历史检验。</Text><Text from={1580} to={1645} y={926} size={25} color={C.dim}>图形为概念示意，历史结果不保证未来。</Text>
<svg width="1920" height="1080" style={{position:'absolute',inset:0}}><defs><filter id="glow2"><feGaussianBlur stdDeviation="7"/></filter></defs>
<g transform={`translate(${tx} ${ty}) scale(${scale})`} opacity={1-turtle}>
<g opacity={.12*(1-machine)}>{[420,540,660,780].map(y=><path key={y} d={`M205 ${y}H1710`} stroke={C.dim}/>)}{[300,600,900,1200,1500].map(x=><path key={x} d={`M${x} 385V830`} stroke={C.dim}/>)}</g>
<path d={line} fill="none" stroke={C.gold} strokeWidth="13" opacity=".2" filter="url(#glow2)"/><path d={line} fill="none" stroke={C.gold} strokeWidth={mix(4,9,machine)}/>
<g opacity={1-machine}><circle cx={point.x} cy={point.y} r="7" fill={C.ivory}/><circle cx={point.x} cy={point.y} r={29+5*Math.sin(f*.065)} fill="none" stroke={C.gold} strokeWidth="2"/><circle cx={point.x} cy={point.y} r="49" fill="none" stroke={C.gold} opacity=".18"/></g>
<path d={`M${point.x-180} ${point.y+33}H${point.x+185}`} stroke={C.dim} strokeWidth="1.5" strokeDasharray="7 9" opacity={(1-channel)}/>
</g>
{/* The range boundaries close into the first machine box. */}
<g opacity={channel*(1-turtle)}>
<rect x={mix(745,770,machine)} y={mix(427,423,machine)} width={mix(917,320,machine)} height={mix(195,190,machine)} rx={mix(0,24,machine)} fill="#deb78d06" stroke={C.gold} strokeWidth="2"/>
<path d="M1090 518H1635" stroke={C.dim} strokeWidth="2" opacity={machine}/>
<circle cx={1090+545*((Math.max(0,f-940)%90)/90)} cy="518" r="5" fill={C.gold} opacity={machine*e(f,940,960)}/>
</g>
{/* The engine and output boxes become four method nodes, then four market windows. */}
{[0,1,2,3].map(i=>{const mx=[930,1290,1635,1690][i],tt=[800,1090,1380,1670][i],rx=995+(i%2)*485,ry=427+Math.floor(i/2)*262;const x=mix(mix(mx,tt,turtle),rx,research),y=mix(mix(518,546,turtle),ry,research);const w=mix(mix(i===0?320:210,136,turtle),410,research),h=mix(mix(190,136,turtle),182,research);return <g key={i} opacity={(i===3?turtle:machine)*(1-end)}>
<rect x={x-w/2} y={y-h/2} width={w} height={h} rx={mix(mix(24,68,turtle),8,research)} fill={i===0?'none':C.bg} stroke={i%2?C.teal:C.gold} strokeWidth={i===0?2:2} opacity={i===0?turtle:1}/>
{i===2&&<path d={`M${x-44} ${y}l28 28 62-62`} fill="none" stroke={C.teal} strokeWidth="4" pathLength="1" strokeDasharray="1" strokeDashoffset={1-e(f,990,1020)} opacity={1-turtle}/>}{i===1&&<g opacity={1-turtle}>{[0,1,2,3,4].map(j=><path key={j} d={`M${x-63} ${y-52+j*26}h${92+(j%2)*22}`} stroke={C.gold} strokeWidth="3" pathLength="1" strokeDasharray="1" strokeDashoffset={1-e(f,930+j*7,958+j*7)}/>)}</g>}
<g opacity={turtle*(1-research)}><path d={`M${x} ${y+68}V${y+151}`} stroke={C.dim}/>{[-36,0,36].map((dx,j)=><circle key={dx} cx={x+dx} cy={y+177+(j%2)*18} r="7" fill={C.teal} opacity={e(f,1270+i*8,1290+i*8)}/>)}</g>
<g opacity={research}><path d={`M${x-185} ${y+68}H${x+185}`} stroke="#93a2ad55"/><path d={Array.from({length:25},(_,j)=>`${j?'L':'M'}${x-178+j*14.8},${y+45-j*3.8+Math.sin(j*.56+i)*22}`).join(' ')} stroke={i%2?C.teal:C.gold} strokeWidth="2.8" fill="none" pathLength="1" strokeDasharray="1" strokeDashoffset={1-e(f,1450+i*17,1510+i*17)}/></g>
</g>})}
<path d="M800 435V380H1670V435M1090 380V435M1380 380V435" stroke={C.dim} opacity={show(f,1200,1385)*.5} fill="none"/>
</svg>
<Text from={941} to={1115} x={885} y={652} size={31}>价格</Text><Text from={958} to={1115} x={1225} y={652} size={31} color={C.gold}>固定规则</Text><Text from={975} to={1115} x={1602} y={652} size={31}>执行</Text>
{['入场','仓位','止损','退出'].map((s,i)=><Text key={s} from={1190+i*13} to={1382} x={758+i*290} y={522} size={38}>{s}</Text>)}
{['股票指数','货币','商品','国债'].map((s,i)=><Text key={s} from={1450+i*17} to={1643} x={810+(i%2)*485} y={286+Math.floor(i/2)*262} size={30} color={C.gold}>{s}</Text>)}
<Text from={1672} y={108} size={26} color={C.gold}>1900—2012 · 一条思想发展的线索</Text>
<Text from={1685} x={151} y={278} size={86}><span style={{fontFamily:song,fontWeight:900}}>识别趋势 → 写成规则<br/><span style={{color:C.gold}}>一致执行 → 接受检验</span></span></Text>
<Text from={1710} x={158} y={590} size={34} color={C.dim}>不同人物，各有贡献；这不是直接师承关系。</Text>
<div style={{position:'absolute',left:160,right:170,top:760,opacity:e(f,1715,1740),display:'flex',justifyContent:'space-between',borderTop:'1px solid #deb78d66',paddingTop:24,fontSize:26,color:C.gold}}>{['道氏思想','利弗莫尔','唐奇安','机械执行','海龟训练','跨市场研究'].map(s=><span key={s}>{s}</span>)}</div>
<Text from={1730} x={160} y={922} size={22} color={C.dim}>音乐 Oxygen Garden · Chris Zabriskie · CC BY 4.0</Text>
<div style={{position:'absolute',right:72,bottom:35,fontSize:20,color:C.dim}}>思想线索 · 非直接师承 · 图形为概念示意</div>
<svg width="1920" height="1080" style={{position:'absolute',inset:0,opacity:.045,mixBlendMode:'screen',pointerEvents:'none'}}><defs><filter id="grain"><feTurbulence baseFrequency=".65" numOctaves="3" stitchTiles="stitch"/></filter></defs><rect width="1920" height="1080" filter="url(#grain)"/></svg>
</AbsoluteFill>};
const Full=()=>{const f=useCurrentFrame();return <AbsoluteFill style={{background:C.bg}}><Audio src={staticFile('music.m4a')} startFrom={1260} volume={x=>.72*e(x,0,24)*(1-e(x,1750,1800))}/><Audio src={staticFile('sfx.wav')} volume={.9}/>{f<450?<Sequence durationInFrames={450}><Opening/></Sequence>:<Rest/>}</AbsoluteFill>};
registerRoot(()=> <Composition id="TrendHistoryContinuity" component={Full} durationInFrames={1800} fps={30} width={1920} height={1080}/>);
