const fs=require('fs'),path=require('path');
const v=__dirname,output=JSON.parse(fs.readFileSync(path.join(v,'storage-plan.json'))).output;
process.env.TMPDIR=path.join(output,'tmp');
const {bundle}=require('../v7/studio/node_modules/@remotion/bundler');
const {selectComposition,renderStill,renderMedia}=require('../v7/studio/node_modules/@remotion/renderer');
(async()=>{const start=Date.now();const mode=process.argv[2]||'stills';const serveUrl=await bundle({entryPoint:path.join(v,'studio/src/index.tsx'),outDir:path.join(output,'build'),publicDir:path.join(output,'assets')});
let last=-1;const common={serveUrl,browserExecutable:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',chromiumOptions:{gl:'angle'}};
const composition=await selectComposition({...common,id:'TrendHistoryLong'});
if(mode==='stills'){for(const frame of [450,735,1275,1710,2385,2790,3345,3870,4650,5190,5790,6360,6990]){await renderStill({...common,composition,frame,output:path.join(output,`frame-${frame}.png`)});console.log('frame',frame);}}
else{await renderMedia({...common,composition,codec:'h264',crf:18,pixelFormat:'yuv420p',concurrency:4,onProgress:({progress})=>{const n=Math.floor(progress*10);if(n!==last){console.log('render',n*10+'%');last=n}},outputLocation:path.join(output,'trend-history.mp4')});console.log('render complete');}
fs.writeFileSync(path.join(output,mode+'-timing.json'),JSON.stringify({started:new Date(start).toISOString(),elapsed_seconds:(Date.now()-start)/1000}));})().catch(e=>{console.error(e);process.exit(1)});
