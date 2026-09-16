import { useEffect, useRef, useState } from "react";

interface Props {
  /** 当前容器的实时宽度（px）。父组件据此调整列宽。 */
  width: number;
  /** 拖动时的最小/最大边界 */
  min?: number;
  max?: number;
  /** 拖动结束、布局已稳定后回调；用于把宽度持久化到 localStorage */
  onChange: (width: number) => void;
  /** 鼠标悬停/拖动时显示的指针类型（左右分栏用 col-resize；上下用 row-resize） */
  cursor?: "col-resize" | "row-resize";
  /** 可选：标题，悬浮提示 */
  title?: string;
}

/**
 * 可拖拽的分隔条。父组件负责把 ``width`` 应用到对应列的 CSS。
 *
 * 为什么这样实现
 * --------------
 * - 不用任何第三方库（react-resizable-panels 等会拖慢首屏且 API 与本项目不匹配）
 * - 拖动期间用 mousemove 全局监听，避免鼠标超出容器边缘失焦
 * - 拖动期间临时设置 user-select 禁止文字选中
 * - 释放后清除监听，避免内存泄漏
 */
export default function ResizeHandle({
  width,
  min = 180,
  max = 560,
  onChange,
  cursor = "col-resize",
  title,
}: Props) {
  const [dragging, setDragging] = useState(false);
  const startRef = useRef<{ x: number; w: number } | null>(null);

  useEffect(() => {
    if (!dragging) return undefined;
    const onMove = (e: MouseEvent) => {
      if (!startRef.current) return;
      const dx = e.clientX - startRef.current.x;
      const next = Math.max(min, Math.min(max, startRef.current.w + dx));
      onChange(next);
    };
    const onUp = () => {
      setDragging(false);
      startRef.current = null;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    document.body.style.userSelect = "none";
    document.body.style.cursor = cursor;
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [dragging, min, max, onChange, cursor]);

  return (
    <div
      className={`resize-handle ${dragging ? "dragging" : ""}`}
      style={{ cursor }}
      title={title}
      onMouseDown={(e) => {
        e.preventDefault();
        startRef.current = { x: e.clientX, w: width };
        setDragging(true);
      }}
    />
  );
}
