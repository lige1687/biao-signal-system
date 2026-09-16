import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Card, WatchlistGroup } from "../types";
import ColorBadge from "./ColorBadge";
import Sparkline from "./Sparkline";

interface Props {
  cards: Card[];
  selected: string;
  onSelect: (symbol: string) => void;
  onAddClick: (groupId: number | null) => void;
}

function fmtChange(v: number | null): { text: string; cls: string } {
  if (v == null) return { text: "--", cls: "flat" };
  return {
    text: `${v > 0 ? "+" : ""}${v.toFixed(2)}%`,
    cls: v > 0 ? "up" : v < 0 ? "down" : "flat",
  };
}

/** 左栏一只标的（带迷你K线）。 */
function SideItem({
  card,
  active,
  onSelect,
  groups,
  onMove,
  onRemove,
}: {
  card: Card;
  active: boolean;
  onSelect: () => void;
  groups: WatchlistGroup[];
  onMove: (symbol: string, groupId: number | null) => void;
  onRemove: (symbol: string) => void;
}) {
  const [menu, setMenu] = useState(false);
  const change = fmtChange(card.change_pct);
  const userGroups = groups.filter((g) => !g.builtin && g.group_id != null);

  // 点菜单外部关闭菜单（避免多个 ⋯ 菜单同时挂着）
  useEffect(() => {
    if (!menu) return undefined;
    const onDocClick = () => setMenu(false);
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, [menu]);

  if (card.error) {
    return (
      <div className={`side-item error ${active ? "active" : ""}`} onClick={onSelect}>
        <div className="si-row">
          <span className="si-name">{card.display_name}</span>
          <span className="si-symbol">{card.symbol}</span>
          <span className="spacer" style={{ flex: 1 }} />
          <span className="si-change flat">--</span>
          {card.group === "watchlist" && (
            <button
              className="si-remove"
              title="删除自选"
              onClick={(e) => {
                e.stopPropagation();
                if (confirm(`确认将「${card.display_name}」移出自选？`)) {
                  onRemove(card.symbol);
                }
              }}
            >
              ✕
            </button>
          )}
        </div>
        <div className="si-err">{card.error.split("\n")[0].slice(0, 40)}</div>
      </div>
    );
  }

  return (
    <div className={`side-item ${active ? "active" : ""}`} onClick={onSelect} title={card.symbol}>
      <div className="si-row">
        <span className="si-name" title={card.display_name}>{card.display_name}</span>
        <span className="spacer" style={{ flex: 1 }} />
        <span className={`si-change ${change.cls}`}>{change.text}</span>
        {card.group === "watchlist" && (
          <>
            <button
              className="si-remove"
              title="删除自选"
              onClick={(e) => {
                e.stopPropagation();
                if (confirm(`确认将「${card.display_name}」移出自选？`)) {
                  onRemove(card.symbol);
                }
              }}
            >
              ✕
            </button>
            <button
              className="si-menu-btn"
              onClick={(e) => {
                e.stopPropagation();
                setMenu(!menu);
              }}
              title="更多"
            >
              ⋯
            </button>
          </>
        )}
      </div>
      <div className="si-row2">
        <span className="si-price">{card.price != null ? card.price.toFixed(2) : "--"}</span>
        <ColorBadge color={card.color} colorCn={card.color_cn} days={card.color_days} />
      </div>
      <Sparkline
        points={card.sparkline}
        up={card.change_pct == null ? null : card.change_pct >= 0}
        height={20}
      />
      {menu && (
        <div className="si-menu" onClick={(e) => e.stopPropagation()}>
          <div className="si-menu-label">移动到分组</div>
          {userGroups.map((g) => (
            <button
              key={g.group_id}
              onClick={() => {
                onMove(card.symbol, g.group_id);
                setMenu(false);
              }}
            >
              {g.name}
            </button>
          ))}
          <button
            onClick={() => {
              onMove(card.symbol, null);
              setMenu(false);
            }}
          >
            移出分组
          </button>
          <div className="si-menu-sep" />
          <button
            className="danger"
            onClick={() => {
              if (confirm(`确认将「${card.display_name}」移出自选？`)) {
                onRemove(card.symbol);
              }
              setMenu(false);
            }}
          >
            删除自选
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * 左栏：最左一条分组导航轨道 + 右侧当前组标的列表。
 * 点轨道上的组即可切换右侧列表，不用再一个个收起/展开。
 * 点标的只切换中栏，不跳转页面——这样右栏解释与图表开关状态
 * 都不会因为「回首页再点进来」而丢失。
 */
export default function WatchlistSidebar({ cards, selected, onSelect, onAddClick }: Props) {
  const queryClient = useQueryClient();
  const [activeKey, setActiveKey] = useState<string>("");
  const [newGroupName, setNewGroupName] = useState("");
  const [adding, setAdding] = useState(false);
  const [renaming, setRenaming] = useState<number | null>(null);
  const [renameText, setRenameText] = useState("");
  const [groupFeedback, setGroupFeedback] = useState<{
    kind: "success" | "error";
    text: string;
  } | null>(null);

  const { data: groups = [] } = useQuery({
    queryKey: ["groups"],
    queryFn: () => api.groups(),
  });

  const groupKey = (g: WatchlistGroup) =>
    g.group_id == null ? `builtin:${g.name}` : `group:${g.group_id}`;

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["groups"] });
    queryClient.invalidateQueries({ queryKey: ["cards"] });
  };

  // 统一失败反馈：操作失败时左栏底部提示条可见，而不是界面毫无动静
  const onErrorWith = (action: string) => (error: unknown) => {
    setGroupFeedback({
      kind: "error",
      text: `${action}失败：${error instanceof Error ? error.message : String(error)}`,
    });
  };

  const createGroup = useMutation({
    mutationFn: (name: string) => api.createGroup(name),
    onSuccess: (group) => {
      setNewGroupName("");
      setAdding(false);
      invalidate();
      setActiveKey(groupKey(group)); // 建组后直接切到新组
    },
    onError: onErrorWith("建组"),
  });
  const renameGroup = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => api.renameGroup(id, name),
    onSuccess: (group) => {
      setRenaming(null);
      setRenameText("");
      setGroupFeedback({ kind: "success", text: `已改名为「${group.name}」` });
      invalidate();
    },
    onError: onErrorWith("改名"),
  });
  const deleteGroup = useMutation({
    mutationFn: (id: number) => api.deleteGroup(id),
    onSuccess: () => {
      setActiveKey(""); // 让 activeKey 重新解析到剩余分组
      invalidate();
    },
    onError: onErrorWith("删组"),
  });
  const moveItem = useMutation({
    mutationFn: ({ symbol, groupId }: { symbol: string; groupId: number | null }) =>
      api.moveToGroup(symbol, groupId),
    onSuccess: invalidate,
    onError: onErrorWith("移动"),
  });
  const removeItem = useMutation({
    mutationFn: (symbol: string) => api.removeWatchlist(symbol),
    onSuccess: invalidate,
    onError: onErrorWith("移除"),
  });

  const cardBySymbol = new Map(cards.map((c) => [c.symbol, c]));

  // 首次加载后把轨道定位到「当前标的所在组」，否则第一个组。
  useEffect(() => {
    if (activeKey || groups.length === 0) return;
    const target = groups.find((g) => g.symbols.includes(selected)) ?? groups[0];
    if (target) setActiveKey(groupKey(target));
  }, [activeKey, groups, selected]);

  const activeGroup =
    groups.find((g) => groupKey(g) === activeKey) ?? groups[0];
  const activeGroupKey = activeGroup ? groupKey(activeGroup) : "";
  const activeCards = activeGroup
    ? activeGroup.symbols
        .map((s) => cardBySymbol.get(s))
        .filter((c): c is Card => Boolean(c))
    : [];
  // 在用户自建组里点「＋ 添加自选」，新标的默认落进当前组。
  const addTargetGroupId =
    activeGroup && !activeGroup.builtin && activeGroup.group_id != null
      ? activeGroup.group_id
      : null;

  return (
    <aside className="sidebar">
      <nav className="sb-rail" aria-label="分组导航">
        {groups.map((g) => {
          const key = groupKey(g);
          return (
            <button
              key={key}
              type="button"
              className={`sb-rail-btn${key === activeGroupKey ? " active" : ""}`}
              title={`${g.name}（${g.symbols.length}）`}
              onClick={() => setActiveKey(key)}
            >
              {g.name.slice(0, 2).split("").map((ch, i) => (
                <span key={i}>{ch}</span>
              ))}
            </button>
          );
        })}
      </nav>

      <div className="sb-main">
        <div className="sb-head">
          <span>自选与大盘</span>
          <button
            className="btn small"
            onClick={() => setAdding(!adding)}
            title="新建分组"
          >
            ＋组
          </button>
        </div>

        {adding && (
          <div className="sb-newgroup">
            <input
              type="text"
              placeholder="分组名，如 科技"
              value={newGroupName}
              autoFocus
              onChange={(e) => setNewGroupName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newGroupName.trim())
                  createGroup.mutate(newGroupName.trim());
                if (e.key === "Escape") setAdding(false);
              }}
            />
            <button
              className="btn small primary"
              disabled={!newGroupName.trim()}
              onClick={() => createGroup.mutate(newGroupName.trim())}
            >
              建
            </button>
          </div>
        )}

        {groupFeedback && (
          <div
            className={`sb-feedback ${groupFeedback.kind}`}
            role={groupFeedback.kind === "error" ? "alert" : "status"}
            aria-live="polite"
          >
            <span>{groupFeedback.text}</span>
            <button
              type="button"
              aria-label="关闭提示"
              title="关闭"
              onClick={() => setGroupFeedback(null)}
            >
              ×
            </button>
          </div>
        )}

        <div className="sb-scroll">
          {activeGroup && (
            <section className="sb-group expanded">
              <div className="sb-group-head">
                {activeGroup.group_id != null && renaming === activeGroup.group_id ? (
                  <form
                    className="sb-rename-form"
                    onClick={(e) => e.stopPropagation()}
                    onSubmit={(e) => {
                      e.preventDefault();
                      const name = renameText.trim();
                      if (activeGroup.group_id == null || !name || renameGroup.isPending) return;
                      if (name === activeGroup.name) {
                        setRenaming(null);
                        setRenameText("");
                        setGroupFeedback({ kind: "success", text: "分组名称未变化" });
                        return;
                      }
                      setGroupFeedback(null);
                      renameGroup.mutate({ id: activeGroup.group_id, name });
                    }}
                  >
                    <input
                      type="text"
                      className="sb-rename"
                      value={renameText}
                      autoFocus
                      disabled={renameGroup.isPending}
                      onChange={(e) => setRenameText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Escape" && !renameGroup.isPending) {
                          setRenaming(null);
                          setRenameText("");
                        }
                      }}
                      onBlur={(e) => {
                        // 失焦视为取消；提交中不撤销，避免请求完成前编辑行跳走。
                        if (!renameGroup.isPending && e.relatedTarget?.tagName !== "BUTTON") {
                          setRenaming(null);
                          setRenameText("");
                        }
                      }}
                    />
                    {/* 显式提交按钮：点击 / Enter 都触发 form onSubmit */}
                    <button
                      type="submit"
                      className="sb-rename-ok"
                      title="确认改名（Enter）"
                      aria-label="确认改名"
                      disabled={!renameText.trim() || renameGroup.isPending}
                    >
                      {renameGroup.isPending ? "…" : "✓"}
                    </button>
                  </form>
                ) : (
                  <span className="sb-group-title">{activeGroup.name}</span>
                )}
                <span className="sb-count" aria-label={`${activeGroup.symbols.length} 个标的`}>
                  {activeGroup.symbols.length}
                </span>
                {!activeGroup.builtin && activeGroup.group_id != null && (
                  <span className="sb-group-actions" onClick={(e) => e.stopPropagation()}>
                    <button
                      title="添加标的到该组"
                      onClick={() => onAddClick(activeGroup.group_id)}
                    >
                      ＋
                    </button>
                    <button
                      title="重命名"
                      onClick={() => {
                        setGroupFeedback(null);
                        setRenaming(activeGroup.group_id);
                        setRenameText(activeGroup.name);
                      }}
                    >
                      ✎
                    </button>
                    <button
                      title="删除分组（组内标的转为未分组，不会删除）"
                      onClick={() => {
                        if (window.confirm(`删除分组「${activeGroup.name}」？组内标的将转为未分组，不会被删除。`))
                          deleteGroup.mutate(activeGroup.group_id!);
                      }}
                    >
                      ✕
                    </button>
                  </span>
                )}
              </div>

              <div className="sb-items">
                {activeCards.length === 0 && (
                  <div className="sb-empty">
                    该组暂无标的
                    {!activeGroup.builtin && (
                      <button className="link" onClick={() => onAddClick(activeGroup.group_id)}>
                        添加
                      </button>
                    )}
                  </div>
                )}
                {activeCards.map((c) => (
                  <SideItem
                    key={c.symbol}
                    card={c}
                    active={c.symbol === selected}
                    onSelect={() => onSelect(c.symbol)}
                    groups={groups}
                    onMove={(symbol, groupId) => moveItem.mutate({ symbol, groupId })}
                    onRemove={(symbol) => removeItem.mutate(symbol)}
                  />
                ))}
              </div>
            </section>
          )}

          <button className="sb-add-symbol" onClick={() => onAddClick(addTargetGroupId)}>
            ＋ 添加自选
          </button>
          <div
            style={{ padding: "6px 12px", fontSize: 11, opacity: 0.65 }}
            title="不用鼠标，直接用方向键在自选列表里快速换标的"
          >
            ↑↓ 方向键切换标的
          </div>
        </div>
      </div>
    </aside>
  );
}
