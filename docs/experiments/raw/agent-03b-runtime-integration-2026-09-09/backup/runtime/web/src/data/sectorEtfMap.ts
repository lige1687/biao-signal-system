/**
 * 板块 ↔ 场内行业 ETF 映射（手工维护）。
 *
 * 用途：板块趋势页（东财 457 个板块）行/抽屉里给出「相关 ETF」直达入口，
 * 以及工作台反向显示 ETF 所属板块的阶段。贴合「不看个股、看 ETF」的用法：
 * 中观（板块强弱）→ 微观（可交易标的）一步直达。
 *
 * 维护原则：
 * - 宁缺毋滥：只收录主流、规模大、代码高置信的行业 ETF；不确定的宁可不列
 *   （列错代码比漏列伤信任——用户点进去发现是别的标的）。
 * - keyword 用东财板块名的常见子串（如「半导体」「光伏设备」「酿酒行业」），
 *   子串包含即命中；一个板块可命中多个 ETF（如 半导体 → 512480/159995），
 *   由用户自选更贴切的一只。
 * - 这是**研究直达入口**，不构成任何买卖建议；板块等权指数与 ETF 跟踪
 *   指数口径不同（research_proxy）。
 */

export interface SectorEtf {
  /** 场内代码（带交易所后缀，与系统 symbol 规范一致）。 */
  symbol: string;
  /** 简短中文名（徽章用）。 */
  name: string;
  /** 板块名关键词（子串包含命中）。 */
  keywords: string[];
}

export const SECTOR_ETFS: SectorEtf[] = [
  { symbol: "512480.SS", name: "半导体ETF", keywords: ["半导体", "集成电路", "芯片"] },
  { symbol: "159995.SZ", name: "芯片ETF", keywords: ["芯片", "半导体"] },
  { symbol: "159997.SZ", name: "电子ETF", keywords: ["电子", "消费电子", "光学光电子", "元件"] },
  { symbol: "515050.SS", name: "5G通信ETF", keywords: ["5G", "通信设备", "光通信", "通信服务"] },
  { symbol: "159998.SZ", name: "计算机ETF", keywords: ["计算机", "软件", "互联网服务", "软件开发"] },
  { symbol: "516010.SS", name: "游戏ETF", keywords: ["游戏", "动漫"] },
  { symbol: "512980.SZ", name: "传媒ETF", keywords: ["传媒", "影视", "文化", "广告包装"] },
  { symbol: "512690.SZ", name: "酒ETF", keywords: ["酒"] },
  { symbol: "515170.SS", name: "食品饮料ETF", keywords: ["食品", "饮料", "乳品", "调味品"] },
  { symbol: "159825.SZ", name: "农业ETF", keywords: ["农牧", "种植", "养殖", "饲料"] },
  { symbol: "512170.SS", name: "医疗ETF", keywords: ["医疗"] },
  { symbol: "512010.SS", name: "医药ETF", keywords: ["医药", "中药", "化学制药", "医药商业"] },
  { symbol: "159992.SZ", name: "创新药ETF", keywords: ["生物制品", "创新药"] },
  { symbol: "512800.SS", name: "银行ETF", keywords: ["银行"] },
  { symbol: "512000.SS", name: "券商ETF", keywords: ["证券"] },
  { symbol: "510230.SS", name: "金融ETF", keywords: ["保险", "多元金融"] },
  { symbol: "515790.SS", name: "光伏ETF", keywords: ["光伏"] },
  { symbol: "516160.SZ", name: "新能源ETF", keywords: ["电池", "电源设备", "新能源", "电网设备"] },
  { symbol: "515030.SS", name: "新能源车ETF", keywords: ["汽车"] },
  { symbol: "512400.SS", name: "有色ETF", keywords: ["有色", "贵金属", "黄金", "小金属", "能源金属", "工业金属"] },
  { symbol: "515210.SZ", name: "钢铁ETF", keywords: ["钢铁"] },
  { symbol: "512200.SS", name: "房地产ETF", keywords: ["房地产"] },
  { symbol: "159996.SZ", name: "家电ETF", keywords: ["家电"] },
  { symbol: "512660.SS", name: "军工ETF", keywords: ["军工", "航天", "航空", "船舶制造"] },
  { symbol: "512580.SS", name: "环保ETF", keywords: ["环保"] },
  { symbol: "515220.SS", name: "煤炭ETF", keywords: ["煤炭"] },
  { symbol: "159930.SZ", name: "能源ETF", keywords: ["石油"] },
  { symbol: "159870.SZ", name: "化工ETF", keywords: ["化学", "化工", "化纤"] },
];

/** 板块名 → 相关 ETF（命中多个时全部给出，用户自选更贴切的一只）。 */
export function etfsForSector(sectorName: string): SectorEtf[] {
  return SECTOR_ETFS.filter((e) => e.keywords.some((k) => sectorName.includes(k)));
}

/** ETF 代码 → 它覆盖的板块关键词（反向联动用：工作台显示 ETF 所属板块阶段）。 */
export function sectorKeywordsForEtf(symbol: string): string[] | null {
  const hit = SECTOR_ETFS.find((e) => e.symbol === symbol);
  return hit ? hit.keywords : null;
}
