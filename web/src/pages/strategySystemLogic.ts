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

/** 连起原文表格行之间的空行；代码块的内容保持原样。仅用于阅读展示。 */
export function normalizeStrategyMarkdown(markdown: string): string {
  const lines = markdown.split("\n");
  let fence = "";
  return lines.filter((line, index) => {
    const marker = line.match(/^ {0,3}(`{3,}|~{3,})/);
    if (marker) {
      const token = marker[1];
      if (!fence) fence = token;
      else if (token[0] === fence[0] && token.length >= fence.length) fence = "";
      return true;
    }
    if (fence || line.trim()) return true;
    let before = index - 1, after = index + 1;
    while (before >= 0 && !lines[before].trim()) before--;
    while (after < lines.length && !lines[after].trim()) after++;
    return !(lines[before]?.startsWith("|") && lines[before]?.trimEnd().endsWith("|")
      && lines[after]?.startsWith("|"));
  }).join("\n");
}
export function strategyReadingParams(documentId: string, guide = false, section?: string): URLSearchParams {
  const params = new URLSearchParams({ doc: documentId });
  if (guide) params.set("collection", "factor-guide");
  if (section) params.set("section", section);
  return params;
}
