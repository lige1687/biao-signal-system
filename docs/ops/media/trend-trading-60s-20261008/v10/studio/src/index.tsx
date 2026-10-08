import React from 'react';
import {AbsoluteFill,Audio,Composition,Img,interpolate,registerRoot,staticFile,useCurrentFrame,Easing} from 'remotion';
const bg='#080d15',ivory='#ebe5d8',gold='#deb78d',dim='#93a2ad',coral='#d97b72',teal='#63b8ac';
const song='"Songti SC", "STSong", serif';
const clamp={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
const e=(f:number,a:number,b:number)=>interpolate(f,[a,b],[0,1],{...clamp,easing:Easing.bezier(.22,.75,.23,1)});
const pts=Array.from({length:100},(_,i)=>({x:625+i*10.5,y:699-i*3.6+Math.sin(i*.23)*61+Math.sin(i*1.31)*22}));
const path=(p:typeof pts)=>p.map((p,i)=>`${i?'L':'M'}${p.x},${p.y}`).join(' ');
const Reveal:React.FC<{start:number;children:React.ReactNode;style?:React.CSSProperties}>=({start,children,style})=>{const f=useCurrentFrame(),t=e(f,start,start+23);return <div style={{position:'absolute',opacity:t,transform:`translateY(${(1-t)*24}px)`,...style}}>{children}</div>};
const Film=()=>{const f=useCurrentFrame(),cut=e(f,101,130),line=e(f,140,195),main=e(f,207,245),pull=e(f,267,293),micro=e(f,327,350);return <AbsoluteFill style={{background:bg,color:ivory,fontFamily:'"PingFang SC",sans-serif',overflow:'hidden'}}>
<Audio src={staticFile('music.m4a')} startFrom={1260} volume={x=>.72*e(x,0,30)*(1-e(x,420,450))}/><Audio src={staticFile('sfx.wav')} volume={.85}/>
<AbsoluteFill style={{opacity:1-cut,transform:`scale(${1+f*.00024}) translateX(${-cut*85}px)`}}><Img src={staticFile('ticker.png')} style={{width:'100%',height:'100%',objectFit:'cover'}}/><AbsoluteFill style={{background:'linear-gradient(90deg,#080d15e6,#080d1580 40%,transparent 70%),linear-gradient(0deg,#080d15db,transparent 28%)'}}/>
<Reveal start={0} style={{top:78,left:104,color:gold,fontSize:25,letterSpacing:5}}>01　趋势交易思想史</Reveal>
<Reveal start={8} style={{left:100,top:237,fontFamily:song,fontWeight:900,fontSize:142,lineHeight:1.23,letterSpacing:4}}>趋势交易<br/><span style={{color:gold}}>从何而来</span></Reveal>
<Reveal start={30} style={{left:108,top:690,fontSize:37,lineHeight:1.65}}>从读价格，到识别趋势。<br/><span style={{fontSize:28,color:dim}}>一场延续百年的思想演变。</span></Reveal>
<Reveal start={44} style={{bottom:85,left:108,fontFamily:song,color:gold,fontSize:40,letterSpacing:7}}>1900 — 2012</Reveal>
<div style={{position:'absolute',right:75,bottom:40,fontSize:21,color:dim}}>AI 情境示意</div></AbsoluteFill>
<AbsoluteFill style={{opacity:cut,transform:`translateX(${(1-cut)*120}px)`,background:'radial-gradient(ellipse at 65% 43%,#26354d70,transparent 63%)'}}>
<Reveal start={115} style={{top:80,left:100,color:gold,fontSize:25,letterSpacing:4}}>02　1900 前后 · 道氏思想</Reveal>
<Reveal start={125} style={{left:96,top:243,fontFamily:song,fontSize:100,fontWeight:900,lineHeight:1.26}}>涨跌之中<br/><span style={{color:gold}}>先辨趋势</span></Reveal>
<Reveal start={148} style={{left:104,top:579,fontSize:34,lineHeight:1.9,color:'#bbc2c7'}}>同一段价格里，<br/>藏着不同层次的运动。</Reveal>
<svg width="1920" height="1080" style={{position:'absolute',inset:0}}><defs><filter id="soft"><feGaussianBlur stdDeviation="8"/></filter><clipPath id="trace"><rect x="615" y="170" width={1120*line} height="630"/></clipPath></defs>
{[390,510,630,750].map(y=><path key={y} d={`M620 ${y}H1798`} stroke="#8196ae" opacity={.12*line}/>)}{[670,870,1070,1270,1470,1670].map(x=><path key={x} d={`M${x} 286V760`} stroke="#8196ae" opacity={.09*line}/>)}
<path d={path(pts)} fill="none" stroke={dim} strokeWidth="2.7" opacity=".8" clipPath="url(#trace)"/>
<path d="M655 699 C1000 625 1400 435 1710 327" pathLength="1" strokeDasharray="1" strokeDashoffset={1-main} fill="none" stroke={gold} strokeWidth="19" opacity=".2" filter="url(#soft)"/>
<path d="M655 699 C1000 625 1400 435 1710 327" pathLength="1" strokeDasharray="1" strokeDashoffset={1-main} fill="none" stroke={gold} strokeWidth="5"/>
<path d={path(pts.slice(47,64))} pathLength="1" strokeDasharray="1" strokeDashoffset={1-pull} fill="none" stroke={coral} strokeWidth="5"/>
<path d={path(pts.slice(65,74))} pathLength="1" strokeDasharray="1" strokeDashoffset={1-micro} fill="none" stroke={teal} strokeWidth="5"/>
<g opacity={main}><circle cx="1710" cy="327" r="7" fill={gold}/><circle cx="1710" cy="327" r={22+8*Math.sin(f*.045)} fill="none" stroke={gold} opacity=".4"/><path d="M1580 372V239H1510" fill="none" stroke={gold} opacity=".7"/></g>
<g opacity={pull}><circle cx={pts[57].x} cy={pts[57].y} r="6" fill={coral}/><path d={`M${pts[57].x} ${pts[57].y}V634H1210`} fill="none" stroke={coral} opacity=".7"/></g>
<path d={`M${pts[70].x} ${pts[70].y}V736H1440`} fill="none" stroke={teal} opacity={micro*.7}/>
</svg>
<Reveal start={228} style={{left:1385,top:178,fontSize:43,fontFamily:song,color:gold}}>主要趋势</Reveal>
<Reveal start={280} style={{left:1232,top:611,fontSize:39,fontFamily:song,color:coral}}>次级回调</Reveal>
<Reveal start={339} style={{left:1460,top:715,fontSize:39,fontFamily:song,color:teal}}>日常波动</Reveal>
<Reveal start={376} style={{left:105,bottom:78,fontFamily:song,fontSize:40}}>先分清层次，才谈如何跟随。</Reveal>
<div style={{position:'absolute',left:103,right:101,bottom:147,height:1,background:'#c5ad8933',opacity:micro}}/><div style={{position:'absolute',bottom:40,right:75,fontSize:21,color:dim}}>概念示意 · 非真实行情</div>
</AbsoluteFill>
<svg width="1920" height="1080" style={{position:'absolute',inset:0,pointerEvents:'none',mixBlendMode:'screen',opacity:.055}}><defs><filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".65" numOctaves="3" stitchTiles="stitch"/></filter></defs><rect width="1920" height="1080" filter="url(#grain)"/></svg>
<div style={{position:'absolute',left:0,top:0,height:3,width:`${f/449*100}%`,background:gold,opacity:.55}}/>
</AbsoluteFill>};
registerRoot(()=> <Composition id="TrendSample" component={Film} durationInFrames={450} fps={30} width={1920} height={1080}/>);
