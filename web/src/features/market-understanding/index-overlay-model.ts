import type {EChartsOption} from 'echarts';
import type {Pair} from './comparison-model';
import type {Metric} from './dashboard-model';

export const overlayColors = {index:'#326bc4', metric:'#c46d18'};
export function overlayNumber(value:number|null) {
 return value===null?'缺失':value.toLocaleString('zh-CN',{maximumFractionDigits:4});
}
const escape=(text:string)=>text.replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]!));
export function overlayTooltip(pairs:Pair[],position:number,metric:Metric,indexTitle:string) {
 const p=pairs[position];if(!p)return '';
 return [`<strong>${escape(p.date)} · 同期观察</strong>`,
  `蓝线 · ${escape(indexTitle)}价格：${overlayNumber(p.index)} 点（左轴）`,
  `橙线 · ${escape(metric.title)}：${overlayNumber(p.metric)} ${escape(metric.unit)}（右轴）`,
  `指标观测日期 ${escape(p.metricDate)}；指数观测日期 ${escape(p.indexDate||'缺失')}`,
  '观测日期不是首次公布日期'].join('<br/>');
}
export function indexOverlayOption(pairs:Pair[],metric:Metric,indexTitle:string,referenceLines:unknown[],eventLines:unknown[]):EChartsOption {
 return {
  tooltip:{trigger:'axis',confine:true,extraCssText:'max-width:260px;white-space:normal;overflow-wrap:anywhere;line-height:1.6',formatter:(params:unknown)=>{
   const first=Array.isArray(params)?params[0]:params;return overlayTooltip(pairs,(first as {dataIndex:number})?.dataIndex,metric,indexTitle);
  }},
  legend:{top:4,data:[`${indexTitle}价格`,metric.title],textStyle:{fontSize:11},itemGap:12},
  grid:{left:64,right:72,top:72,bottom:62},
  xAxis:{type:'category',data:pairs.map(p=>p.date),boundaryGap:false,axisLabel:{hideOverlap:true,fontSize:10}},
  yAxis:[
   {type:'value',name:'价格（点）· 左轴',scale:true,axisLabel:{color:overlayColors.index,fontSize:10},nameTextStyle:{color:overlayColors.index},splitLine:{lineStyle:{color:'#e5ebf2'}}},
   {type:'value',name:`${metric.unit} · 右轴`,position:'right',scale:true,axisLabel:{color:overlayColors.metric,fontSize:10},nameTextStyle:{color:overlayColors.metric},splitLine:{show:false}},
  ],
  dataZoom:[{type:'slider',xAxisIndex:0,bottom:8,height:18},{type:'inside',xAxisIndex:0}],
  series:[
   {type:'line',name:`${indexTitle}价格`,yAxisIndex:0,data:pairs.map(p=>p.index),showSymbol:false,connectNulls:false,itemStyle:{color:overlayColors.index},lineStyle:{color:overlayColors.index,width:3},markLine:{symbol:'none',data:eventLines as never}},
   {type:'line',name:metric.title,yAxisIndex:1,data:pairs.map(p=>p.metric),showSymbol:false,connectNulls:false,itemStyle:{color:overlayColors.metric},lineStyle:{color:overlayColors.metric,width:2.5},markLine:{symbol:'none',data:referenceLines as never}},
  ],
 };
}
