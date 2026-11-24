import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  mindsetApi,
  type MindsetCategory,
  type MindsetItem,
  type MindsetStatus,
} from "../api/client";

/** 认知与心态页（/mindset）：调研观点的判断题卡片。
 *  逐条点 认可/中立/不认可；认可项进"篮子"随机温习；自己可新增认知/复盘。
 *  纯个人知识沉淀，不参与任何信号判定。首个来源：小红书博主「文主任」
 *  2026-09-05 调研（26 条种子，configs/mindset_seed.json，首启自动导入）。 */

const STATUS_TABS: { key: MindsetStatus | "all"; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "unevaluated", label: "待评价" },
  { key: "agree", label: "认可（篮子）" },
  { key: "neutral", label: "中立" },
  { key: "disagree", label: "不认可" },
];
const CATEGORIES: (MindsetCategory | "all")[] = ["all", "认知", "心态", "纪律", "复盘"];
const CAT_COLOR: Record<string, string> = {
  认知: "#4a6fa5",
  心态: "#a5584a",
  纪律: "#4a8a63",
  复盘: "#8a6d3b",
};

const btnBase: React.CSSProperties = {
  padding: "5px 14px",
  borderRadius: 8,
  border: "1px solid #d8d4dc",
  background: "#fff",
  cursor: "pointer",
  fontSize: 13,
};

export default function MindsetPage() {
  const qc = useQueryClient();
  const [statusTab, setStatusTab] = useState<MindsetStatus | "all">("all");
  const [cat, setCat] = useState<MindsetCategory | "all">("all");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<{ category: MindsetCategory; text: string; quote: string; source: string }>(
    { category: "认知", text: "", quote: "", source: "自己记录" },
  );
  const [formError, setFormError] = useState("");
  const [reviewItem, setReviewItem] = useState<MindsetItem | null>(null);
  const [reviewDone, setReviewDone] = useState(0);

  const q = useQuery({
    queryKey: ["mindset", statusTab, cat],
    queryFn: () =>
      mindsetApi.list({
        status: statusTab === "all" ? undefined : statusTab,
        category: cat === "all" ? undefined : cat,
      }),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["mindset"] });
  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: MindsetStatus }) =>
      mindsetApi.setStatus(id, status),
    onSuccess: invalidate,
  });
  const create = useMutation({
    mutationFn: mindsetApi.create,
    onSuccess: () => {
      setForm({ category: "认知", text: "", quote: "", source: "自己记录" });
      setShowForm(false);
      setFormError("");
      invalidate();
    },
    onError: (e: Error) => setFormError(e.message),
  });
  const remove = useMutation({ mutationFn: mindsetApi.remove, onSuccess: invalidate });

  const pullReview = async () => {
    const item = await mindsetApi.reviewNext();
    setReviewItem(item);
    if (item) setReviewDone((n) => n + 1);
  };

  const summary = q.data?.summary;
  const items = useMemo(() => q.data?.items ?? [], [q.data]);

  /* 页头在加载/失败态也渲染：键值缺失显示"未知"，失败给重试动作（范式红线：不伪造状态） */
  const head = (
    <div className="pg-head">
      <div className="pg-head-title">
        <h1>认知与心态</h1>
        <span className="pg-head-sub">
          判断题卡片：逐条点认可/中立/不认可；认可的进"篮子"随机温习。
          只是认知沉淀，不影响任何买卖判定。
        </span>
      </div>
      {summary && (
        <div className="pg-head-kv">
          <span className="pg-kv"><span className="k">共</span><b>{summary.total} 条</b></span>
          <span className="pg-kv"><span className="k">待评价</span><b>{summary.unevaluated}</b></span>
          <span className="pg-kv"><span className="k">认可</span><b>{summary.agree}</b></span>
          <span className="pg-kv"><span className="k">中立</span><b>{summary.neutral}</b></span>
          <span className="pg-kv"><span className="k">不认可</span><b>{summary.disagree}</b></span>
        </div>
      )}
      <div className="pg-head-actions">
        <button className="btn small" onClick={pullReview} disabled={!q.data}>
          温习一条
        </button>
        <button className="btn small" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "收起新增" : "+ 新增认知/复盘"}
        </button>
      </div>
    </div>
  );

  if (q.isLoading)
    return (
      <div className="page" style={{ maxWidth: 1080 }}>
        {head}
        <div className="muted">加载中…</div>
      </div>
    );
  if (q.isError || !q.data)
    return (
      <div className="page" style={{ maxWidth: 1080 }}>
        {head}
        <div className="cp-error">加载失败。</div>
        <button className="btn small" style={{ marginTop: 10 }} onClick={() => q.refetch()}>
          重试
        </button>
      </div>
    );

  /* ---------- 温习模式（单卡） ---------- */
  if (reviewItem !== undefined && reviewItem !== null) {
    return (
      <div className="page" style={{ maxWidth: 720, margin: "0 auto" }}>
        <div className="page-head">
          <h1>温习 · 已看 {reviewDone} 条</h1>
          <button className="btn small" onClick={() => setReviewItem(null)}>
            退出温习
          </button>
        </div>
        <ReviewCard item={reviewItem} onNext={pullReview} />
      </div>
    );
  }
  const reviewEmpty = reviewItem === null && reviewDone > 0;

  /* ---------- 主列表 ---------- */
  return (
    <div className="page" style={{ maxWidth: 1080 }}>
      {head}
      {reviewEmpty && (
        <div className="muted" style={{ marginBottom: 10, fontSize: 13 }}>
          篮子里还没有可温习的条目——点几条"认可"，或自己新增一条。
        </div>
      )}

      {/* 新增表单 */}
      {showForm && (
        <div
          style={{
            background: "#fff",
            border: "1px solid #e8e4ec",
            borderRadius: 12,
            padding: 16,
            marginBottom: 14,
          }}
        >
          <div style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
            <span className="muted" style={{ fontSize: 13 }}>分类</span>
            {(["认知", "心态", "纪律", "复盘"] as MindsetCategory[]).map((c) => (
              <button
                key={c}
                style={{
                  ...btnBase,
                  ...(form.category === c
                    ? { background: "#2a2430", color: "#fff", borderColor: "#2a2430" }
                    : {}),
                }}
                onClick={() => setForm((f) => ({ ...f, category: c }))}
              >
                {c}
              </button>
            ))}
          </div>
          <textarea
            value={form.text}
            onChange={(e) => setForm((f) => ({ ...f, text: e.target.value }))}
            placeholder="一句话写下这条认知/心态/复盘（2-500 字，大白话）"
            style={{
              width: "100%",
              minHeight: 70,
              borderRadius: 8,
              border: "1px solid #d8d4dc",
              padding: 10,
              fontSize: 14,
              boxSizing: "border-box",
            }}
          />
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <input
              value={form.quote}
              onChange={(e) => setForm((f) => ({ ...f, quote: e.target.value }))}
              placeholder="原话（可选）"
              style={{ flex: 1, borderRadius: 8, border: "1px solid #d8d4dc", padding: "6px 10px", fontSize: 13 }}
            />
            <input
              value={form.source}
              onChange={(e) => setForm((f) => ({ ...f, source: e.target.value }))}
              placeholder="来源"
              style={{ width: 180, borderRadius: 8, border: "1px solid #d8d4dc", padding: "6px 10px", fontSize: 13 }}
            />
            <button
              className="btn small"
              disabled={create.isPending || form.text.trim().length < 2}
              onClick={() => create.mutate({ ...form, quote: form.quote || undefined })}
            >
              保存
            </button>
          </div>
          {formError && <div className="cp-error" style={{ marginTop: 6, fontSize: 12 }}>{formError}</div>}
        </div>
      )}

      {/* 筛选 */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
        {STATUS_TABS.map((t) => (
          <button
            key={t.key}
            style={{
              ...btnBase,
              ...(statusTab === t.key
                ? { background: "#4a6fa5", color: "#fff", borderColor: "#4a6fa5" }
                : {}),
            }}
            onClick={() => setStatusTab(t.key)}
          >
            {t.label}
          </button>
        ))}
        <span style={{ width: 12 }} />
        {CATEGORIES.map((c) => (
          <button
            key={c}
            style={{
              ...btnBase,
              ...(cat === c ? { background: "#2a2430", color: "#fff", borderColor: "#2a2430" } : {}),
            }}
            onClick={() => setCat(c)}
          >
            {c === "all" ? "全部分类" : c}
          </button>
        ))}
      </div>

      {/* 卡片列表 */}
      {items.length === 0 && (
        <div className="muted" style={{ padding: "30px 0", textAlign: "center" }}>
          这里没有条目——换个筛选条件看看。
        </div>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 12 }}>
        {items.map((it) => (
          <ItemCard
            key={it.id}
            item={it}
            busy={setStatus.isPending}
            onSet={(status) => setStatus.mutate({ id: it.id, status })}
            onDelete={it.origin === "user" ? () => remove.mutate(it.id) : undefined}
          />
        ))}
      </div>
      {remove.isError && (
        <div className="cp-error" style={{ marginTop: 10, fontSize: 12 }}>
          删除失败：{(remove.error as Error).message}
        </div>
      )}
    </div>
  );
}

function ItemCard({
  item,
  busy,
  onSet,
  onDelete,
}: {
  item: MindsetItem;
  busy: boolean;
  onSet: (s: MindsetStatus) => void;
  onDelete?: () => void;
}) {
  const cur = item.status;
  const verdictBtn = (s: MindsetStatus, label: string, activeBg: string) => (
    <button
      key={s}
      disabled={busy}
      style={{
        ...btnBase,
        ...(cur === s ? { background: activeBg, color: "#fff", borderColor: activeBg } : {}),
      }}
      onClick={() => onSet(s)}
    >
      {label}
    </button>
  );
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e8e4ec",
        borderRadius: 12,
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <span
          style={{
            fontSize: 11.5,
            color: "#fff",
            background: CAT_COLOR[item.category] ?? "#6f6a78",
            borderRadius: 6,
            padding: "2px 8px",
          }}
        >
          {item.category}
        </span>
        <span className="muted" style={{ fontSize: 11.5 }}>
          {item.origin === "user" ? "自己记录" : item.source}
        </span>
        <span style={{ flex: 1 }} />
        {item.review_count > 0 && (
          <span className="muted" style={{ fontSize: 11 }}>温习 {item.review_count} 次</span>
        )}
      </div>
      <div style={{ fontSize: 14.5, lineHeight: 1.65 }}>{item.text}</div>
      {item.quote && (
        <div
          style={{
            borderLeft: "3px solid #c9b8a8",
            background: "#faf6f0",
            padding: "6px 10px",
            fontSize: 13,
            color: "#6d5a4a",
            borderRadius: "0 8px 8px 0",
          }}
        >
          原话：{item.quote}
        </div>
      )}
      {item.source && item.origin !== "user" && (
        <div className="muted" style={{ fontSize: 11.5 }}>来源：{item.source}</div>
      )}
      <div style={{ display: "flex", gap: 6, marginTop: 2 }}>
        {verdictBtn("agree", "认可", "#3f8a63")}
        {verdictBtn("neutral", "中立", "#8a7d3b")}
        {verdictBtn("disagree", "不认可", "#a5584a")}
        {onDelete && (
          <>
            <span style={{ flex: 1 }} />
            <button
              style={{ ...btnBase, color: "#a5584a", borderColor: "#e0c4c0" }}
              onClick={() => {
                if (window.confirm("删除这条自建记录？")) onDelete();
              }}
            >
              删除
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function ReviewCard({ item, onNext }: { item: MindsetItem; onNext: () => void }) {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e8e4ec",
        borderRadius: 14,
        padding: "28px 26px",
        marginTop: 16,
      }}
    >
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 14 }}>
        <span
          style={{
            fontSize: 12,
            color: "#fff",
            background: CAT_COLOR[item.category] ?? "#6f6a78",
            borderRadius: 6,
            padding: "2px 10px",
          }}
        >
          {item.category}
        </span>
        <span className="muted" style={{ fontSize: 12 }}>
          {item.origin === "user" ? "自己记录" : item.source} · 已温习 {item.review_count} 次
        </span>
      </div>
      <div style={{ fontSize: 17, lineHeight: 1.8 }}>{item.text}</div>
      {item.quote && (
        <div
          style={{
            borderLeft: "3px solid #c9b8a8",
            background: "#faf6f0",
            padding: "8px 12px",
            fontSize: 14,
            color: "#6d5a4a",
            borderRadius: "0 8px 8px 0",
            marginTop: 12,
          }}
        >
          原话：{item.quote}
        </div>
      )}
      <div style={{ marginTop: 20 }}>
        <button className="btn small" onClick={onNext}>
          记住了，下一条
        </button>
      </div>
    </div>
  );
}
