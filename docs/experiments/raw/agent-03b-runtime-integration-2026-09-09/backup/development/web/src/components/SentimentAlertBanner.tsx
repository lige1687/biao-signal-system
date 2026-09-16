import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { request } from "../api/client";

/**
 * 全局情绪信号横幅（2026-09-06 用户口径：打开系统第一眼可见的显眼提醒）。
 * 只在信号激活时渲染（冰点环境=冰蓝、热警报=暖红），平时不占任何空间；
 * 点击跳「今日操作」看明细。数据源 GET /api/sentiment/alerts（叙事层信号，
 * 不构成买卖点——样式醒目但措辞守红线）。
 */
type SentimentAlert = {
  level: "warn" | "alert";
  key: string;
  title_cn: string;
  body_cn: string;
};

export default function SentimentAlertBanner() {
  const navigate = useNavigate();
  const q = useQuery({
    queryKey: ["sentimentAlerts"],
    queryFn: () => request<{ alerts: SentimentAlert[] }>("/sentiment/alerts"),
    refetchInterval: 5 * 60_000,
    retry: 1,
    retryDelay: 8000,
  });
  const alerts = q.data?.alerts ?? [];
  if (alerts.length === 0) return null;
  return (
    <div className="sent-banner-wrap" role="alert">
      {alerts.slice(0, 2).map((a) => (
        <button
          key={a.key}
          className={`sent-banner sent-banner-${a.level}`}
          onClick={() => navigate("/ops")}
          title="点开今日操作查看信号明细（叙事层参考，不构成买卖点）"
        >
          <span className="sent-banner-title">{a.title_cn}</span>
          <span className="sent-banner-body">{a.body_cn}</span>
          <span className="sent-banner-go">查看 →</span>
        </button>
      ))}
    </div>
  );
}
