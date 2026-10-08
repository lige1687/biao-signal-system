import React from 'react';
import {AbsoluteFill,Audio,Composition,Img,interpolate,registerRoot,staticFile,useCurrentFrame,Easing} from 'remotion';
const C={bg:'#080d15',ivory:'#ebe5d8',gold:'#deb78d',dim:'#93a2ad',teal:'#63b8ac'};const song='"Songti SC", "STSong", serif';
const ease=(f:number,a:number,b:number)=>interpolate(f,[a,b],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:Easing.bezier(.22,.75,.23,1)});
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const Text:React.FC<{from:number;to?:number;x:number;y:number;size:number;color?:string;children:React.ReactNode}>=({from,to=500,x,y,size,color=C.ivory,children})=>{const f=useCurrentFrame(),p=ease(f,from,from+22);return <div style={{position:'absolute',left:x,top:y,fontSize:size,color,opacity:p*(1-ease(f,to-16,to)),transform:`translateY(${(1-p)*18}px)`,lineHeight:1.35}}>{children}</div>};
const Video=()=>{const f=useCurrentFrame(),unroll=ease(f,8,60),morph=ease(f,98,182),focus=ease(f,281,331),scale=mix(1,.64,focus),tx=660*focus,ty=232*focus,photo=ease(f,285,322),ink=ease(f,152,187);const points=Array.from({length:85},(_,i)=>({x:220+i*17.4,y:mix(608+Math.sin(i*.43)*6,790-i*5.3+Math.sin(i*.25)*55+Math.sin(i*1.41)*15,morph)}));const line=points.map((p,i)=>`${i?'L':'M'}${p.x},${p.y}`).join(' ');const node=points[51];return <AbsoluteFill style={{background:C.bg,color:C.ivory,fontFamily:'"PingFang SC",sans-serif',overflow:'hidden'}}>
<Audio src={staticFile('music.m4a')} startFrom={1260} volume={x=>.72*ease(x,0,24)*(1-ease(x,420,450))}/><Audio src={staticFile('sfx.wav')} volume={.9}/>
<AbsoluteFill style={{opacity:.68*(1-ease(f,68,157)),transform:`scale(${1.03+f*.0002})`}}><Img src={staticFile('ticker.png')} style={{width:'100%',height:'100%',objectFit:'cover'}}/><AbsoluteFill style={{background:'linear-gradient(90deg,#080d15ec,transparent 75%),linear-gradient(0deg,#080d15cf,transparent 90%)'}}/></AbsoluteFill>
<AbsoluteFill style={{background:'radial-gradient(ellipse at 65% 48%,#26354d88,transparent 65%)',opacity:morph}}/>
<div style={{position:'absolute',inset:0,opacity:photo}}><Img src={staticFile('livermore.jpg')} style={{position:'absolute',left:-60-(1-photo)*80,top:0,width:710,height:1080,objectFit:'cover',filter:'grayscale(1) sepia(.12)',opacity:.85}}/><AbsoluteFill style={{background:'linear-gradient(90deg,transparent 14%,#080d1555 27%,#080d15 37%),linear-gradient(0deg,#080d15,transparent 45%)'}}/></div>
<Text from={3} to={105} x={105} y={79} size={25} color={C.gold}>趋势交易思想史</Text>
<Text from={10} to={101} x={99} y={225} size={112}><span style={{fontFamily:song,fontWeight:900}}>最初，只有价格。</span></Text>
<Text from={31} to={98} x={107} y={391} size={34} color={C.dim}>一串数字，如何变成一种判断？</Text>
<Text from={119} to={286} x={102} y={79} size={25} color={C.gold}>1900 前后 · 道氏思想</Text>
<Text from={142} to={274} x={102} y={218} size={104}><span style={{fontFamily:song,fontWeight:900}}>从价格里，<span style={{color:C.gold}}>看见趋势。</span></span></Text>
<Text from={211} to={282} x={106} y={884} size={37}>短期会回摆，主要方向仍能延续。</Text>
<svg width="1920" height="1080" style={{position:'absolute',inset:0}}><defs><linearGradient id="paper" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#eee4ce"/><stop offset=".5" stopColor="#d9c6a5"/><stop offset="1" stopColor="#bd9d72"/></linearGradient><filter id="shadow"><feDropShadow dx="0" dy="14" stdDeviation="15" floodColor="#000" floodOpacity=".7"/></filter><filter id="glow"><feGaussianBlur stdDeviation="7"/></filter><clipPath id="unroll"><rect x="180" y="405" width={1560*unroll} height="440"/></clipPath></defs>
<g transform={`translate(${tx} ${ty}) scale(${scale})`}>
<g opacity={morph*.12}>{[420,540,660,780].map(y=><path key={y} d={`M205 ${y}H1710`} stroke={C.dim}/>)}{[300,600,900,1200,1500].map(x=><path key={x} d={`M${x} 385V830`} stroke={C.dim}/>)}</g>
<g clipPath="url(#unroll)" transform={`rotate(${-4*(1-morph)} 960 608)`}>
<rect x="180" y={608-88*(1-morph)} width="1550" height={176*(1-morph)} rx={3} fill="url(#paper)" opacity={1-ease(f,147,175)} filter="url(#shadow)"/>
<g opacity={1-ease(f,84,119)}>{Array.from({length:11},(_,i)=><g key={i}><text x={230+i*133} y="575" fontFamily="monospace" fontSize="24" fill="#53412e">{(83.2+i*.65+(i%3)*.2).toFixed(2)}</text><path d={`M${215+i*133} 540V669`} stroke="#625039" opacity=".15"/><circle cx={245+i*133} cy="608" r="4" fill="#80643e"/></g>)}</g>
</g>
<path transform={`rotate(${-4*(1-morph)} 960 608)`} d={line} fill="none" stroke={C.gold} strokeWidth="13" opacity={.20*ink} filter="url(#glow)"/>
<path transform={`rotate(${-4*(1-morph)} 960 608)`} d={line} fill="none" stroke={ink>.2?C.gold:'#735333'} strokeWidth={mix(2.8,4,ink)} opacity={unroll} clipPath={morph<.05?'url(#unroll)':undefined}/>
<path d="M245 779 C600 700 1250 460 1700 348" fill="none" stroke={C.teal} strokeWidth="2.4" pathLength="1" strokeDasharray="1" strokeDashoffset={1-ease(f,183,225)} opacity={.75*(1-focus)}/>
<g opacity={ease(f,226,247)}><circle cx={node.x} cy={node.y} r="7" fill={C.ivory}/><circle cx={node.x} cy={node.y} r={29+5*Math.sin(f*.065)} stroke={C.gold} strokeWidth="2" fill="none"/><circle cx={node.x} cy={node.y} r={49} stroke={C.gold} opacity=".18" fill="none"/></g>
<path d={`M${node.x-180} ${node.y+33}H${node.x+185}`} stroke={C.dim} strokeWidth="1.5" strokeDasharray="7 9" opacity={ease(f,333,362)}/>
</g></svg>
<Text from={300} x={759} y={106} size={26} color={C.gold}>1940 · 利弗莫尔的交易纪律</Text>
<Text from={313} x={753} y={231} size={94}><span style={{fontFamily:song,fontWeight:900}}>看见趋势，<br/><span style={{color:C.gold}}>还要学会等待。</span></span></Text>
<Text from={348} x={771} y={809} size={38}>等待条件成立，再决定行动。</Text>
<Text from={319} x={100} y={876} size={34}>Jesse Livermore</Text>
<Text from={328} x={104} y={933} size={22} color={C.dim}>1923 年档案照片 · 文意概括</Text>
<svg width="1920" height="1080" style={{position:'absolute',inset:0,opacity:.045,mixBlendMode:'screen',pointerEvents:'none'}}><defs><filter id="grain"><feTurbulence baseFrequency=".65" numOctaves="3" stitchTiles="stitch"/></filter></defs><rect width="1920" height="1080" filter="url(#grain)"/></svg>
<div style={{position:'absolute',right:72,bottom:35,fontSize:20,color:C.dim}}>{f<112?'AI 情境图 · 数字为示意':f<290?'概念图 · 非真实行情':'思想线索 · 非直接师承'}</div>
</AbsoluteFill>};
registerRoot(()=> <Composition id="ContinuitySample" component={Video} durationInFrames={450} fps={30} width={1920} height={1080}/>);
