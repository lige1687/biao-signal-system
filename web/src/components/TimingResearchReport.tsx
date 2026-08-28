import { useEffect, useState } from "react";
import { timingBacktestApi } from "../api/client";
import type { TimingPortfolio } from "../types";

/**
 * 宽度择时研究报告（23 轮回测总决算，2026-08-28）。
 * 数据为静态入册结论（docs/timing-sweep/execution_playbook_20260827.md），
 * 仅「当前实况」卡片实时取 /timing-backtest/portfolio。
 */

const ROUNDS: { n: number; title: string; verdict: string; good: boolean }[] = [
  { n: 1, title: "参数扫描 v1-v6（~7500 组）", verdict: "冠军= B200 逆势三档（档位线 43.3/56.7）", good: true },
  { n: 2, title: "稳健性套件（5年滚动/邻域/费用/起点/ETF交叉）", verdict: "创业板 +4.4% 超额全维度通过；黄金阴性对照 ≈0 ✓", good: true },
  { n: 3, title: "美股宽度做收益增强", verdict: "全参数跑输（动量市场）→ 转防守定位", good: false },
  { n: 4, title: "全A 长历史宽度回算", verdict: "1990→2026 数据补齐（幸存者偏差入册）", good: true },
  { n: 5, title: "系统六条预警规则直测", verdict: "双≤20 后 120 日：13/13 标的正，A股+29%/美股+37%", good: true },
  { n: 6, title: "完整规则策略（20/90 买卖全执行）", verdict: "只胜冠军 4/13 → 规则=哨兵不是指挥官", good: false },
  { n: 7, title: "阈值精扫（15/20/85/90）", verdict: "底=双≤20 跨市场最优；顶需 ≥90 且限高贝塔", good: true },
  { n: 8, title: "行业 ETF/指数全家桶终审", verdict: "进攻组成型：证券+16.3%/房地产+11.7%/新能车+12.1%", good: true },
  { n: 9, title: "数据事故修复（ETF 除权假摔隔离 8 只）", verdict: "行业结论改指数口径复核", good: true },
  { n: 10, title: "本轮科技牛专项诊断", verdict: "冠军全线跑输（-21~-46%）＝全场动量牛，非虹吸误判", good: false },
  { n: 11, title: "结构行情历史普适检验", verdict: "失效判据=与宽度分母脱钩（白酒 2019-21 -54.2% 极值案例）", good: true },
  { n: 12, title: "行情分段矩阵（B200×MA200 六格）", verdict: "钱全在高·上格；超额来源=复苏格（低·上+127%）", good: true },
  { n: 13, title: "RS 虹吸判别器 + 条件引擎", verdict: "RS 灯定案（误报 8%）；高·上改持有被否=失血是保费", good: true },
  { n: 14, title: "全标的终审扩容", verdict: "执行配置 11→17；新入 6 标的（中证1000/创新药/食品/钢铁/红利沪/通信）", good: true },
  { n: 15, title: "接刀格补丁三变体", verdict: "全否：2018 与 2024 事前不可区分（本质发现）", good: false },
  { n: 16, title: "宽度推力事件研究", verdict: "无独立超额；真实角色=低位过滤器（+13.0% vs +3.8%）", good: true },
  { n: 17, title: "宽度背离（两市场四级检验）", verdict: "全面证伪：A股被复苏期宽度滞后污染（方向反了）", good: false },
  { n: 18, title: "宽度×技术协同（MA20 代理）", verdict: "技术层=风控实证：1~6pp 年化换 9~34pp 回撤削减", good: true },
  { n: 19, title: "组合层（8 sleeve 等权）", verdict: "共同窗口冠军组合 +12.2%/-36% vs 持有 +2.6%/-46%；2015 股灾 +18.5% vs -51.8%", good: true },
  { n: 20, title: "动态入池·动量轮动", verdict: "证伪：追 RS 前5 共同窗 -3.6%（负 alpha）", good: false },
  { n: 21, title: "组合变体 + 工程化上线", verdict: "全配置组合 2021+ +10.1%/-21% 最优；组合仓位卡上线", good: true },
  { n: 22, title: "多因子入池 × 宽度预算", verdict: "因子选股零增量；预算挣全部超额；等权全池是最强基准", good: false },
  { n: 23, title: "真实 LEI 信号做执行层", verdict: "风控定位确认；2018/V底两场景显著优于代理（-37%→-17%）", good: true },
];

const LAYERS = [
  { name: "宽度预算层", what: "B200 三档（43.3/56.7）管总仓位", role: "增收：挣全部择时收益" },
  { name: "LEI 执行层", what: "三色/长趋势门在预算内执行", role: "风控：2018 阴跌 -37%→-17%，V 底保肉" },
  { name: "组合等权层", what: "8-17 sleeve 等权篮子", role: "平滑：特异性风险稀释 1/N" },
  { name: "RS 虹吸灯", what: "RS120>20pp 持续10日 → 引擎切换", role: "切换：灯亮=技术信号接管" },
  { name: "审计入池", what: "三窗超额全正才入池", role: "资格：静态，不轮动" },
];

export default function TimingResearchReport() {
  const [pf, setPf] = useState<TimingPortfolio | null>(null);
  useEffect(() => {
    timingBacktestApi.portfolio().then(setPf).catch(() => undefined);
  }, []);

  return (
    <div className="timing-report">
      <div className="header">
        <h1>宽度择时研究报告 · 23 轮总决算</h1>
        <p className="bt-sub">
          2026-08 · 约 7500+ 参数组 · 40+ 标的 · 全A宽度 1990→2026 · 每轮预注册协议，
          通过/证伪均入册（<code>docs/timing-sweep/execution_playbook_20260827.md</code>）
        </p>
      </div>

      {pf && pf.balanced_weight != null && (
        <section className="bt-cards">
          <div className="bt-card positive">
            <div className="bt-card-label">组合仓位 · 平衡型（实时）</div>
            <div className="bt-card-value">{Math.round((pf.balanced_weight ?? 0) * 100)}%</div>
          </div>
          <div className="bt-card">
            <div className="bt-card-label">组合仓位 · 防守型（实时）</div>
            <div className="bt-card-value">{Math.round((pf.defensive_weight ?? 0) * 100)}%</div>
          </div>
          <div className="bt-card">
            <div className="bt-card-label">进攻 sleeve</div>
            <div className="bt-card-value">
              {pf.n_sleeves ?? 0} <small>满仓 {pf.full_count ?? 0} · 空仓 {pf.empty_count ?? 0}</small>
            </div>
          </div>
          <div className={`bt-card ${(pf.siphon_count ?? 0) > 0 ? "negative" : ""}`}>
            <div className="bt-card-label">虹吸灯（技术引擎接管中）</div>
            <div className="bt-card-value">{pf.siphon_count ?? 0}</div>
          </div>
          <div className="bt-card">
            <div className="bt-card-label">数据截至</div>
            <div className="bt-card-value" style={{ fontSize: 18 }}>{pf.as_of ?? "—"}</div>
          </div>
        </section>
      )}

      <section className="bt-section">
        <h3>五层架构（每层独立回测支撑）</h3>
        <table className="bt-table">
          <thead><tr><th>层</th><th>机制</th><th>实证定位</th></tr></thead>
          <tbody>
            {LAYERS.map((l) => (
              <tr key={l.name}><td><b>{l.name}</b></td><td>{l.what}</td><td>{l.role}</td></tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="bt-section">
        <h3>核心战绩（口径含窗口）</h3>
        <table className="bt-table">
          <thead><tr><th>对象</th><th>窗口</th><th>策略</th><th>持有</th><th>回撤(策/持)</th></tr></thead>
          <tbody>
            <tr><td>冠军·创业板指</td><td>2010-06→2026-08</td><td className="positive">+13.4%</td><td>+9.0%</td><td>-40% / -70%</td></tr>
            <tr><td>冠军·证券指数</td><td>2015-05→2026-08</td><td className="positive">超额 +16.3%</td><td>—</td><td>-47% / -73%</td></tr>
            <tr><td>组合·平衡型（冠军8 sleeve）</td><td>2015-06→2026-08</td><td className="positive">+12.2%</td><td>+2.6%</td><td>-36% / -46%</td></tr>
            <tr><td>组合·防守型（协同版）</td><td>2002-01→2026-08</td><td>+3.6%</td><td>+7.9%</td><td className="positive">-26% / -72%</td></tr>
            <tr><td>2015 股灾段·冠军组合</td><td>2015-06→2016-02</td><td className="positive">+18.5%</td><td className="negative">-51.8%</td><td>-23% / -46%</td></tr>
            <tr><td>本轮科技牛·冠军组合</td><td>2024-09→2026-08</td><td>+26.6%</td><td>+29.9%</td><td>-13% / -16%</td></tr>
            <tr><td>美股防守版·纳指</td><td>1986→2026-08</td><td>+8.4%</td><td>+12.3%</td><td className="positive">-16% / -78%</td></tr>
          </tbody>
        </table>
      </section>

      <section className="bt-section">
        <h3>行情格矩阵（可当时判定：B200 低/中/高 × 价格 vs MA200）</h3>
        <table className="bt-table">
          <thead><tr><th>格</th><th>特征</th><th>创业板全历史实证</th></tr></thead>
          <tbody>
            <tr><td><b>高·上（动量牛）</b></td><td>市场钱几乎全在此格</td><td>43% 时间贡献 +1104%；冠军在此付费（-979% 格内超额）＝崩盘保费</td></tr>
            <tr><td><b>低·上 / 中·上（复苏）</b></td><td>冠军的超额来源</td><td>两格 +127% / +125% —— 肉在右侧确认，不在左侧抄底</td></tr>
            <tr><td><b>低·下（接刀格）</b></td><td>2018 与 2024 事前不可区分</td><td>宽度侧无解；LEI 执行门是唯一解药（-37%→-17%）</td></tr>
          </tbody>
        </table>
      </section>

      <section className="bt-section">
        <h3>证伪清单（同样入册，防止重蹈）</h3>
        <table className="bt-table">
          <thead><tr><th>假设</th><th>结果</th><th>根因</th></tr></thead>
          <tbody>
            <tr><td>宽度背离（顶/底）</td><td className="negative">A股方向反、美股太弱</td><td>B200 滞后价格，复苏期假阳性污染</td></tr>
            <tr><td>动量/RS 轮动入池</td><td className="negative">共同窗 -3.6%（负 alpha）</td><td>A股月频动量反转；前列=虹吸标的</td></tr>
            <tr><td>多因子选股（5因子）</td><td className="negative">全跑输全池等权</td><td>预算挣全部超额；等权分散是最强因子</td></tr>
            <tr><td>高·上格改持有</td><td className="negative">证券超额 +16.3%→+5.6%</td><td>行情格翻转滞后=裸扛下跌格</td></tr>
            <tr><td>宽度推力做独立信号</td><td className="negative">≈无条件基准</td><td>仅作低位过滤器（+13.0% vs +3.8%）</td></tr>
            <tr><td>B50 叠加 / 双指标仓位</td><td className="negative">不优于单 B200</td><td>重复计数 + 边界抖动</td></tr>
          </tbody>
        </table>
      </section>

      <section className="bt-section">
        <h3>23 轮时间线</h3>
        <div className="bt-trades-scroll">
          <table className="bt-table">
            <thead><tr><th>#</th><th>轮次</th><th>结论</th><th>判定</th></tr></thead>
            <tbody>
              {ROUNDS.map((r) => (
                <tr key={r.n}>
                  <td>{r.n}</td><td>{r.title}</td><td style={{ whiteSpace: "normal" }}>{r.verdict}</td>
                  <td className={r.good ? "positive" : "negative"}>{r.good ? "✓ 有效" : "✗ 证伪"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bt-section">
        <h3>诚实声明</h3>
        <p className="bt-meta" style={{ whiteSpace: "normal" }}>
          全A宽度由当前存续个股回算（早年幸存者偏差）；A股 ETF 为新浪不复权口径（绝对收益低估
          0.5-1%/年，8 只除权事故标的已隔离待修复）；美股宽度源截至 2026-08-14；冠军 +4.4% 为
          历史选优值，未来预期按 5 年滚动分布打折（83% 概率为正、中位 +6.6%、坏年份 -19%）；
          历史最优≠未来最优。样本外打分卡自 2026-08-27 起逐日自动存档
          （launchd com.lei.timing.daily，交易日 17:30），月度归因用六格框架对照。本页为研究结论，不构成投资建议。
        </p>
      </section>
    </div>
  );
}
