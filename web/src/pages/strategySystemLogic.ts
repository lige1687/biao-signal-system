export type ResearchExtension = {
  id: string;
  name: string;
  plainDefinition: string;
  sourceClass: "原文与实现已有" | "体系外研究扩展";
  status: string;
  to: string;
};

export const RESEARCH_EXTENSIONS: ResearchExtension[] = [
  {
    id: "breadth", name: "市场宽度",
    plainDefinition: "一篮子成分里，有多少标的站上各自均线，用来判断上涨或下跌参与面。",
    sourceClass: "原文与实现已有", status: "模块 E 已定义，具体市场仍需独立检验", to: "/sectors",
  },
  {
    id: "institutional", name: "机构情绪",
    plainDefinition: "用 NAAIM 等资料观察机构风险敞口是否走到人性极端。",
    sourceClass: "原文与实现已有", status: "模块 E 已定义，数据资格和增量仍需检验", to: "/sentiment",
  },
  {
    id: "retail", name: "散户情绪",
    plainDefinition: "用 AAII 等调查观察散户看多和看空是否走到极端。",
    sourceClass: "原文与实现已有", status: "模块 E 已定义，数据资格和增量仍需检验", to: "/sentiment",
  },
  {
    id: "a-share-sentiment", name: "A 股情绪",
    plainDefinition: "研究适合 A 股市场的成交、涨跌分布和投资者行为信息。",
    sourceClass: "体系外研究扩展", status: "待逐项定义和检验，未经确认不进入正式策略", to: "/factors",
  },
];

export function normalizeSelectedDocumentId(requested: string | null, ids: string[]): string | null {
  if (requested && ids.includes(requested)) return requested;
  return ids[0] ?? null;
}
