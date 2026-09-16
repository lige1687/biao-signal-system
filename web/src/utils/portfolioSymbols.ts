/**
 * 持仓基金 -> 行情标的的映射（纯函数，供持仓页「看图 / 问助手」入口使用）。
 *
 * 红线：映射必须能证明是**同一个产品**，名称相似不算证据，布尔“可信”标记
 * 也不算。来源必须自带明确的市场、产品类型或可信目录身份（SourceIdentity）：
 *
 *   - "cn_exchange_fund"：来源标识符本身证明是境内场内基金——裸代码在
 *     场内基金段（沪 50/51/52/56/58、深 15/16）且段内市场与 symbol 后缀
 *     一致（5 开头必须 .SS）。此时持仓代码相等 = 同一产品，再以名称整段
 *     包含做同人核对（多出部分不得含括号/联接/QDII/LOF/指数等身份标记）。
 *   - "us_etf_catalog"：来源来自明确的美股 ETF 目录（可信目录身份），且
 *     symbol 是无后缀的纯字母 ticker——ticker 在该目录体系内即唯一标识，
 *     持仓代码相等 = 同一产品。**带市场后缀的一律不算**（ABC.L 是另一个
 *     市场的产品，剥掉后缀跨市场匹配禁止）。
 *   - "insufficient"：身份不足（普通自选里的字母代码、指数、板块、场外
 *     段等），永不映射——普通自选不能自动视为美股 ETF。
 *
 * 持仓侧同样要求身份信息：6 位代码必须落在场内基金段（指数段 000/399、
 * 场外段 00/01/02/04/07、股票段一律拒绝）；纯字母代码只按上面对齐目录
 * ticker。缺少足够身份信息 => unmapped，页面明确提示，不提供看图入口。
 */

export interface HoldingLike {
  holding_id: string;
  name: string;
  code: string | null;
}

export type SourceIdentity = "cn_exchange_fund" | "us_etf_catalog" | "insufficient";

export interface SymbolSource {
  symbol: string;
  name: string;
  /** 来源的市场/产品类型/目录身份（见文件头），不是“可信与否”布尔值。 */
  identity: SourceIdentity;
}

export interface HoldingSymbolMap {
  symbol: string;
  displayName: string;
  matchedBy: "code";
}

/** 515880.SS -> 515880；^IXIC -> ^IXIC；BK1128 -> BK1128 */
export function bareCode(symbol: string): string {
  const dot = symbol.indexOf(".");
  return dot > 0 ? symbol.slice(0, dot) : symbol;
}

/** symbol 市场后缀（SS/SZ/L/…，无后缀返回 ""）。 */
export function suffixOf(symbol: string): string {
  const dot = symbol.indexOf(".");
  return dot > 0 ? symbol.slice(dot + 1).toUpperCase() : "";
}

/**
 * 境内场内基金代码段 -> 市场后缀。沪 50/51/52/56/58，深 15/16。
 * 指数（000/399）、股票（600/000/300…）、场外基金（00/01/02/04/07…）
 * 一律返回 null：代码段本身不能证明产品类型是场内基金。
 */
export function exchangeFundSuffix(code: string): "SS" | "SZ" | null {
  if (!/^\d{6}$/.test(code)) return null;
  if (/^5[01268]/.test(code)) return "SS";
  if (/^1[56]/.test(code)) return "SZ";
  return null;
}

/**
 * 仅从标识符判定一个行情 symbol 的身份（调用方给 watchlist 来源用）：
 * 裸代码在场内基金段且段内市场与后缀一致 => cn_exchange_fund；
 * 其余（字母代码、指数、板块、场外段、段-后缀错配）=> insufficient。
 * 普通自选里的纯字母代码不推断为美股 ETF——那需要目录身份。
 */
export function classifySymbol(symbol: string): SourceIdentity {
  const seg = exchangeFundSuffix(bareCode(symbol));
  return seg !== null && seg === suffixOf(symbol) ? "cn_exchange_fund" : "insufficient";
}

/** 纯字母 ticker（是否美股产品要看来源目录身份，不在此判断）。 */
function isAlphaTicker(code: string): boolean {
  return /^[A-Za-z]{1,6}$/.test(code);
}

/** 名称规范化：只去空白。括号是身份信息（(QDII)、A/C 份额），不删除。 */
function normalizeName(name: string): string {
  return name.replace(/\s+/g, "").trim();
}

/** 身份标记：多出部分含这些就不是同一产品（(QDII)、联接、LOF、指数增强等）。 */
const IDENTITY_MARKERS = /[（(]|联接|QDII|LOF|FOF|指数|增强/;

/**
 * 同人核对：去空格后一方完整包含另一方，且较长一方多出的部分不得携带
 * 身份信息——「通信ETF国泰」⊂「通信ETF国泰(QDII)A」也算不同产品
 * （括号里就是身份）；「红利低波ETF」⊂「红利低波ETF华泰柏瑞」多出的只是
 * 公司名，算同一产品。片段重叠（共同词）不算包含。
 */
export function nameContains(a: string, b: string): boolean {
  const na = normalizeName(a);
  const nb = normalizeName(b);
  if (!na || !nb) return false;
  if (na === nb) return true;
  const [longer, shorter] = na.length >= nb.length ? [na, nb] : [nb, na];
  if (!longer.includes(shorter)) return false;
  const extra = longer.replace(shorter, "");
  return !IDENTITY_MARKERS.test(extra);
}

/** 来源是否与持仓代码构成同市场、同产品类型的唯一标识匹配。 */
function identityMatch(code: string, source: SymbolSource): boolean {
  if (isAlphaTicker(code)) {
    // 纯字母代码：只对齐“目录身份为美股 ETF 且无市场后缀”的 ticker。
    // 带后缀（ABC.L）是另一个市场的产品，禁止剥后缀跨市场匹配。
    return (
      source.identity === "us_etf_catalog" &&
      suffixOf(source.symbol) === "" &&
      source.symbol.toUpperCase() === code.toUpperCase()
    );
  }
  // 境内 6 位代码：持仓代码段必须是场内基金段；来源必须自带
  // cn_exchange_fund 身份（标识符已证明段-后缀一致），再核对代码相等。
  return (
    source.identity === "cn_exchange_fund" &&
    exchangeFundSuffix(code) !== null &&
    exchangeFundSuffix(code) === suffixOf(source.symbol) &&
    bareCode(source.symbol) === code
  );
}

export function mapHoldingsToSymbols(
  holdings: HoldingLike[],
  sources: SymbolSource[],
): Map<string, HoldingSymbolMap> {
  const out = new Map<string, HoldingSymbolMap>();
  for (const h of holdings) {
    if (!h.code) continue;
    const code = h.code.trim();
    const hits = sources.filter(
      (s) =>
        identityMatch(code, s) &&
        // 境内 6 位代码再要名称互相包含做同人核对；目录 ticker 代码即身份
        (isAlphaTicker(code) || nameContains(h.name, s.name)),
    );
    // 同码多来源命中 = 歧义，不映射（宁缺毋错）
    if (hits.length === 1) {
      out.set(h.holding_id, {
        symbol: hits[0].symbol,
        displayName: hits[0].name,
        matchedBy: "code",
      });
    }
  }
  return out;
}
