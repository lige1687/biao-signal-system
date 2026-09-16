import { subjectLabel } from "../../utils/agentUx";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { backtestApi } from "../../api/client";
import {
  EXIT_CN_SIMPLE, EXIT_HINT_CN_SIMPLE, MODULE_CN_SIMPLE, MODULE_HINT_CN,
  resolveExitAfterModuleChange, validExitsFor,
} from "../../utils/agentUx";

/**
 * UX 第一期（2026-09-13）：补测的中文选择面板（两入口共用）。
 * - 不再要求用户手敲"模块A/退出1"或运行编号：用中文选项+一句解释展示
 *   引擎既有能力（选项值直接来自 /backtest/options，词典只管显示名）；
 * - U2 返修（主控复核 2026-09-13）：能力清单**加载中、失败或为空时一律
 *   不可提交**——静态词典只给已加载结果命名，绝不在加载期用静态 A/B/C/D
 *   顶替可提交能力；失败给"重新读取"；预选的原话方法不在能力清单里时
 *   如实提示并要求重选，不静默保留；
 * - 切换打法时核对当前退出仍合法：失效即清空并回落到该打法下的合法默认，
 *   摘要与实际提交参数一致，不发送隐藏的旧选项；
 * - 明确选择才能提交：模块必须选；退出方式预选引擎默认但**可见可改**，
 *   不静默替用户选最优打法；
 * - 提交只产生一个既有补测任务（onSubmit 回调走各入口现有创建流程）；
 * - 窗口如实显示：原问题有冻结窗口则写明"沿用原问题窗口"，没有则说明
 *   "无可核实的窗口选择"，不统一称"未指定"。
 */
export type BacktestSetupPayload = {
  symbol: string;
  displayName?: string | null;
  /** 既有问题绑定（必填：补测任务必须挂在原问题上，调用方负责先守卫） */
  sessionId: string;
  questionId: number;
  /** 用户在原话里已明确给出的模块（预选；不在能力清单里则要求重选）。 */
  defaultModule?: string | null;
  /** 原问题窗口的如实展示（来自冻结比较配置）；null=没有可核实窗口。 */
  windowLabel?: string | null;
  /** 面板上方的说明（如 ATR 暂未支持的如实提示）。 */
  hint?: string | null;
};

export default function BacktestSetupPanel({ setup, submitting, onSubmit, onCancel }: {
  setup: BacktestSetupPayload;
  submitting?: boolean;
  onSubmit: (module: string, exitVariant: string) => void;
  onCancel?: () => void;
}) {
  const opts = useQuery({
    queryKey: ["backtestOptions"],
    queryFn: () => backtestApi.options(),
    staleTime: 300_000,
  });
  // 能力清单只认服务端结果：加载中/失败/为空/结构不符都不渲染静态替身、不预选
  const ready = opts.isSuccess && !!opts.data && typeof opts.data === "object"
    && Array.isArray(opts.data.modules) && Array.isArray(opts.data.exit_variants);
  const modules: string[] = ready ? opts.data.modules.map(m => String(m.value)) : [];
  const allExits: string[] = ready ? opts.data.exit_variants.map(v => String(v.value)) : [];
  const [module, setModule] = useState<string | null>(setup.defaultModule ?? null);
  const [exitVariant, setExitVariant] = useState<string | null>(null);
  useEffect(() => { setModule(setup.defaultModule ?? null); }, [setup.defaultModule]);
  // 引擎默认退出晚到时作为回落值使用（不覆盖用户已明确选择的合法退出）
  const engineDefault: string | null =
    ready && opts.data.defaults?.exit_variant && allExits.includes(opts.data.defaults.exit_variant)
      ? opts.data.defaults.exit_variant
      : (allExits[0] ?? null);
  const exits = validExitsFor(module, allExits);
  // 预选/已选的模块不在能力清单 → 如实提示并要求重选（U2：不静默保留）
  const moduleInvalid = module != null && ready && !modules.includes(module);
  // 切换打法（或能力清单到达）后：失效的旧退出立即清空并回落到合法默认（U2）
  useEffect(() => {
    setExitVariant(cur => resolveExitAfterModuleChange(cur, module, allExits, engineDefault));
    // allExits/engineDefault 随加载结果变化，一并参与核对
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [module, ready, opts.data]);
  const canSubmit = ready && !!module && !moduleInvalid && !!exitVariant
    && exits.includes(exitVariant) && !submitting;
  const radioSuffix = `${setup.symbol}-${setup.questionId ?? ""}`;

  return (
    <section className="backtest-setup-panel" aria-label="选择补测方法">
      <header>
        <strong>准备补测 · {subjectLabel(setup.symbol, setup.displayName)}</strong>
        <span>选好方法后创建一次历史测试，结果会进入后续回答的依据卡</span>
      </header>
      {setup.hint && <p className="bsp-hint" role="note">{setup.hint}</p>}
      {opts.isLoading && <p className="bsp-hint" role="status">正在读取引擎支持的打法与退出方式…</p>}
      {opts.isError && (
        <p className="bsp-hint warn" role="alert">
          选项读取失败，暂不能提交。
          <button type="button" className="btn small" onClick={() => opts.refetch()}>重新读取</button>
        </p>
      )}
      {ready && !modules.length && (
        <p className="bsp-hint warn" role="alert">引擎没有返回可用打法，暂不能提交。</p>
      )}
      <fieldset className="bsp-field" disabled={!ready}>
        <legend>用哪种入场打法（必须选一项）</legend>
        {modules.map(m => (
          <label key={m} className={`bsp-option ${module === m ? "is-selected" : ""}`}>
            <input
              type="radio" name={`bsp-module-${radioSuffix}`}
              checked={module === m} onChange={() => setModule(m)} disabled={submitting}
            />
            <span className="bsp-option-name">{MODULE_CN_SIMPLE[m] ?? m}</span>
            <span className="bsp-option-hint">{MODULE_HINT_CN[m] ?? ""}</span>
          </label>
        ))}
        {moduleInvalid && (
          <p className="bsp-hint warn" role="alert">
            原话提到的打法不在当前支持清单里，请从上面重新选择一项。
          </p>
        )}
      </fieldset>
      <fieldset className="bsp-field" disabled={!ready || module == null}>
        <legend>用哪种退出方式（已预选系统默认，可改）</legend>
        {exits.map(v => (
          <label key={v} className={`bsp-option ${exitVariant === v ? "is-selected" : ""}`}>
            <input
              type="radio" name={`bsp-exit-${radioSuffix}`}
              checked={exitVariant === v} onChange={() => setExitVariant(v)} disabled={submitting}
            />
            <span className="bsp-option-name">
              {EXIT_CN_SIMPLE[v] ?? v}
              {v === engineDefault ? <em className="bsp-default-tag">系统默认</em> : null}
            </span>
            <span className="bsp-option-hint">{EXIT_HINT_CN_SIMPLE[v] ?? ""}</span>
          </label>
        ))}
      </fieldset>
      <div className="bsp-summary">
        <div><span>对象</span><strong>{subjectLabel(setup.symbol, setup.displayName)}</strong></div>
        <div><span>方法</span><strong>{module && !moduleInvalid ? MODULE_CN_SIMPLE[module] ?? module : "待选择"}</strong></div>
        <div><span>退出</span><strong>{exitVariant ? `${EXIT_CN_SIMPLE[exitVariant] ?? exitVariant}${exitVariant === engineDefault ? "（默认）" : ""}` : "待选择"}</strong></div>
        <div><span>研究区间</span><strong>{setup.windowLabel ?? "未单独指定（按系统默认处理，可在对话中说明起止日期）"}</strong></div>
      </div>
      <footer className="bsp-actions">
        <button
          type="button" className="btn primary" disabled={!canSubmit}
          onClick={() => module && exitVariant && onSubmit(module, exitVariant)}
        >
          {submitting ? "正在创建…" : "创建这次补测"}
        </button>
        {onCancel && <button type="button" className="btn small" onClick={onCancel} disabled={submitting}>先不测了</button>}
      </footer>
    </section>
  );
}
