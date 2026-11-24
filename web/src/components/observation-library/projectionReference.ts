/** Only definition-based references. None is an equity opportunity/risk threshold.
 * Historical quantiles are deliberately excluded: rarity does not establish a turning point.
 */
export interface ProjectionReference {
  value: number;
  label: string;
  meaning: string;
  source: string;
  url: string;
}

const REFERENCES: Record<string, ProjectionReference> = {
  "focus-momentum": { value: 0, label: "0 · 回看收益为零", meaning: "这组股票过去20日的平均收益为零，不代表底部。",
    source: "本地公式与检验", url: "/library?report=docs%2Fexperiments%2Ffocus-momentum-turning-points-2026-10-25.md" },
  "ofr-fsi": { value: 0, label: "0 · 压力平均水平", meaning: "相对官方标准化基准的压力水平，不是股市涨跌界线。",
    source: "OFR指标说明", url: "https://www.financialresearch.gov/financial-stress-index/" },
  nfci: { value: 0, label: "0 · 金融条件平均水平", meaning: "高于零表示比历史平均更紧，低于零表示更松；不对应股市顶底。",
    source: "芝加哥联储", url: "https://www.chicagofed.org/research/data/nfci/current-data" },
  aaii: { value: 0, label: "0 · 看涨看跌相等", meaning: "看涨比例减看跌比例等于零，是意见平衡点。",
    source: "AAII调查定义", url: "https://www.aaii.com/sentimentsurvey" },
  "pmi-cn": { value: 50, label: "50 · 扩张收缩分界", meaning: "制造业调查的扩张和收缩分界，不是股市机会或风险值。",
    source: "国家统计局PMI口径", url: "https://www.stats.gov.cn/zs/tjws/tjzb/202301/t20230101_1903972.html" },
};

export function projectionReference(id: string): ProjectionReference | null {
  return REFERENCES[id] ?? null;
}
