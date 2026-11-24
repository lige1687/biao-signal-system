export type MicroPoint = {date:string; value:number|null};
export type MicroLine = {key:string; label:string; values:(number|null)[]};
export type MicroCard = {id:string; title:string; market:'cn'|'us'; unit:'%'|'百分点'|'倍'|'相关系数'; frequency:'daily'|'monthly'; scope:string; meaning:string; sourceName:string; sourceUrl:string; refreshedAt:string; refreshMode:'snapshot'; points:MicroPoint[]; lines?:MicroLine[]; references?:{label:string; value:number}[]; latestDetails?:{label:string; value:string}[]; limitations:string[]; percentileWindow:number|null; percentiles?:MicroPoint[]};
export type MissingMicro = {id:string; title:string; market:'cn'|'us'; reason:string; nextRequirement:string};
export type MicroPacket = {schemaVersion:1; generatedAt:string; cards:MicroCard[]; unavailable:MissingMicro[]};
export function selectedMicro<T extends {id:string;market:'cn'|'us'}>(items:readonly T[],market:'cn'|'us',selectedIds?:readonly string[]):T[]{return items.filter(c=>c.market===market&&(!selectedIds||selectedIds.includes(c.id)));}
const record=(v:unknown):v is Record<string,unknown>=>typeof v==='object'&&v!==null&&!Array.isArray(v);
const text=(v:unknown):v is string=>typeof v==='string'&&v.trim().length>0;
const finite=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v);
const date=(v:unknown,today:string):v is string=>text(v)&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v).toISOString().slice(0,10)===v&&v<=today;
export const todayShanghai=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export function parseMicrostructure(raw:unknown,today=todayShanghai()):MicroPacket {
  if(!record(raw)||raw.schemaVersion!==1||!text(raw.generatedAt)||!Number.isFinite(Date.parse(raw.generatedAt))||!Array.isArray(raw.cards)||!Array.isArray(raw.unavailable))throw Error('观察资料结构无效');
  const ids=new Set<string>();
  for(const c of raw.cards){
    if(!record(c)||!['id','title','scope','meaning','sourceName','sourceUrl','refreshedAt'].every(k=>text(c[k]))||!['cn','us'].includes(c.market as string)||!['%','百分点','倍','相关系数'].includes(c.unit as string)||!['daily','monthly'].includes(c.frequency as string)||c.refreshMode!=='snapshot'||!Array.isArray(c.points)||!c.points.length||!Array.isArray(c.limitations)||!c.limitations.every(text))throw Error('观察指标口径缺失');
    if(!/^https:\/\//.test(c.sourceUrl as string)||ids.has(c.id as string)||!Number.isFinite(Date.parse(c.refreshedAt as string)))throw Error('来源或指标标识无效');
    ids.add(c.id as string);let previous='';
    for(const p of c.points){if(!record(p)||!date(p.date,today)||p.date<=previous||p.value!==null&&!finite(p.value))throw Error('观察日期或数值无效');previous=p.date;}
    if(c.percentileWindow!==null&&(!Number.isInteger(c.percentileWindow)||(c.percentileWindow as number)<1))throw Error('历史参照窗口无效');
    if(c.percentiles!==undefined){if(!Array.isArray(c.percentiles)||c.percentiles.length!==c.points.length)throw Error('历史位置日期未对齐');c.percentiles.forEach((p,i)=>{if(!record(p)||p.date!==(c.points as MicroPoint[])[i].date||p.value!==null&&(!finite(p.value)||p.value<0||p.value>100))throw Error('历史位置无效');});}
    if(c.references!==undefined&&(!Array.isArray(c.references)||!c.references.every(r=>record(r)&&text(r.label)&&finite(r.value))))throw Error('参考线无效');
    if(c.lines!==undefined){
      if(!Array.isArray(c.lines)||!c.lines.length)throw Error('合并曲线无效');
      const keys=new Set<string>();
      for(const line of c.lines){
        if(!record(line)||!text(line.key)||!text(line.label)||keys.has(line.key as string)||!Array.isArray(line.values)||line.values.length!==c.points.length||!line.values.every(v=>v===null||finite(v)))throw Error('合并曲线未对齐');
        keys.add(line.key as string);
      }
    }
    if(c.latestDetails!==undefined&&(!Array.isArray(c.latestDetails)||!c.latestDetails.every(r=>record(r)&&text(r.label)&&text(r.value))))throw Error('最新读数说明无效');
  }
  for(const m of raw.unavailable){if(!record(m)||!['id','title','reason','nextRequirement'].every(k=>text(m[k]))||!['cn','us'].includes(m.market as string)||ids.has(m.id as string))throw Error('缺失资料说明无效');ids.add(m.id as string);}
  const packet=raw as unknown as MicroPacket;
  const buy=packet.cards.find(c=>c.id==='cn-margin-buy-share-a-stocks');
  const ma20=packet.cards.find(c=>c.id==='cn-margin-buy-share-a-stocks-ma20');
  if(buy&&ma20){
    const ma20ByDate=new Map(ma20.points.map(p=>[p.date,p.value]));
    buy.lines=[{key:'buy',label:'融资买入额占成交额',values:buy.points.map(p=>p.value)},{key:'ma20',label:'20日均值',values:buy.points.map(p=>ma20ByDate.get(p.date)??null)}];
    buy.title='沪深A股融资买入额占成交额 · 含20日均值';
    packet.cards=packet.cards.filter(c=>c.id!==ma20.id);
  }
  return packet;
}
export function reading(c:MicroCard){const latest=c.points[c.points.length-1];const prior=c.points[c.points.length-2];return {...latest,change:latest.value!==null&&prior?.value!=null?latest.value-prior.value:null,previousDate:prior?.date,percentile:c.percentiles?.[c.points.length-1]?.value??null};}
export function formatMicro(v:number|null,unit:string){return v===null?'待补':`${v.toFixed(unit==='相关系数'||unit==='倍'?3:2)}${unit==='相关系数'?'':unit}`;}
