import { useState, type ReactNode } from "react";

interface Props {
  /** 折叠头显示的标题（通常就是被包裹卡片的标题）。 */
  title: ReactNode;
  children: ReactNode;
  /** 折叠头右侧的摘要文字（如「2 条确认」），可选。 */
  summary?: ReactNode;
  /** 默认是否收起，默认展开（保持页面原貌，仅新增折叠能力）。 */
  defaultCollapsed?: boolean;
  /** 提供后折叠状态写入 localStorage，刷新/换标的后保持。 */
  storageKey?: string;
}

function readStored(key: string, fallback: boolean): boolean {
  try {
    const raw = window.localStorage.getItem(key);
    if (raw == null) return fallback;
    return raw === "1";
  } catch {
    return fallback;
  }
}

/**
 * 通用可折叠容器：把任意一张「单独卡片」包起来，由统一的折叠头承载标题，
 * 内部卡片自身的卡片外观与 <h3> 标题由 styles.css 里的
 * .collapsible-panel__body 规则去除，避免双层边框与重复标题。
 *
 * 注意：被包裹的子组件若在运行时返回 null（如空数据），本组件无法感知
 * （children 仍是 truthy 的 React 元素），因此调用方需在数据为空时不渲染本组件。
 * 对于 `data.x && <Child/>` 这类字面量 false 子节点，本组件会直接返回 null。
 */
export default function CollapsiblePanel({
  title,
  children,
  summary,
  defaultCollapsed = false,
  storageKey,
}: Props) {
  // 字面量 false / null 子节点（如 `cond && <Child/>` 不成立时）直接不渲染，
  // 避免出现「空折叠头」。
  if (children == null || children === false) return null;

  const [collapsed, setCollapsed] = useState(() =>
    storageKey ? readStored(storageKey, defaultCollapsed) : defaultCollapsed,
  );

  const toggle = () => {
    setCollapsed((current) => {
      const next = !current;
      if (storageKey) {
        try {
          window.localStorage.setItem(storageKey, next ? "1" : "0");
        } catch {
          /* localStorage 不可用时忽略，仅本次会话内有效 */
        }
      }
      return next;
    });
  };

  return (
    <section className={`collapsible-panel${collapsed ? " is-collapsed" : ""}`}>
      <button
        type="button"
        className="collapsible-panel__head"
        aria-expanded={!collapsed}
        onClick={toggle}
      >
        <span className="collapsible-chevron" aria-hidden="true">
          ▾
        </span>
        <span className="collapsible-panel__title">{title}</span>
        {summary != null && (
          <span className="collapsible-panel__summary">{summary}</span>
        )}
      </button>
      {!collapsed && <div className="collapsible-panel__body">{children}</div>}
    </section>
  );
}
