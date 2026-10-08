const fs=require('fs'),path=require('path');
const v=__dirname,output=JSON.parse(fs.readFileSync(path.join(v,'storage-plan.json'))).output;
process.env.TMPDIR=path.join(output,'tmp');
const {bundle}=require('../v7/studio/node_modules/@remotion/bundler');
const {selectComposition,renderStill,renderMedia}=require('../v7/studio/node_modules/@remotion/renderer');
(async()=>{const start=Date.now();const mode=process.argv[2]||'stills';const serveUrl=await bundle({entryPoint:path.join(v,'studio/src/index.tsx'),outDir:path.join(output,'build'),publicDir:path.join(output,'assets')});
const common={serveUrl,browserExecutable:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',chromiumOptions:{gl:'angle'}};
const composition=await selectComposition({...common,id:'TrendHistoryContinuity'});
if(mode==='stills'){for(const frame of [600,870,1025,1145,1415]){await renderStill({...common,composition,frame,output:path.join(output,`frame-${frame}.png`)});console.log('frame',frame);}}
else{await renderMedia({...common,composition,codec:'h264',crf:18,pixelFormat:'yuv420p',concurrency:3,outputLocation:path.join(output,'trend-history.mp4')});console.log('render complete');}
fs.writeFileSync(path.join(output,mode+'-timing.json'),JSON.stringify({started:new Date(start).toISOString(),elapsed_seconds:(Date.now()-start)/1000}));})().catch(e=>{console.error(e);process.exit(1)});
