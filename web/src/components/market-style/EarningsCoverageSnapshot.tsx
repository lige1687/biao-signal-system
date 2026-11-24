import { useEffect, useState } from "react";
import "./earnings-coverage.css";

type CoverageIndex = { code: string; name: string; available: number; total: number; notReturned: number; missingField: number };
type EarningsCoverageData = {
  capturedAt: string; membershipDate: string; forecastYear: number; source: string; sourceDocUrl: string; rawSha256: string;
  sourceUpdateAt: null; analystCoverage: null; revisionStatus: "未知"; indices: CoverageIndex[];
};

export function isEarningsCoverageSnapshot(value: unknown): value is EarningsCoverageData {
  if (!value || typeof value !== "object") return false;
  const d = value as Partial<EarningsCoverageData>;
  if (!d.capturedAt || !Number.isFinite(Date.parse(d.capturedAt)) || !d.membershipDate || !Number.isInteger(d.forecastYear)
      || !d.source || !d.sourceDocUrl?.startsWith("https://akshare.akfamily.xyz/") || !d.rawSha256
      || d.sourceUpdateAt !== null || d.analystCoverage !== null || d.revisionStatus !== "未知" || !Array.isArray(d.indices) || !d.indices.length) return false;
  return d.indices.every((x) => x && typeof x.code === "string" && typeof x.name === "string"
    && [x.available, x.total, x.notReturned, x.missingField].every(Number.isInteger)
    && x.total > 0 && x.available >= 0 && x.notReturned >= 0 && x.missingField >= 0
    && x.available + x.notReturned + x.missingField === x.total);
}

export function EarningsCoverageView({ data, onOpenGuide }: { data: EarningsCoverageData; onOpenGuide: () => void }) {
  const captured = data.capturedAt.replace("T", " ").slice(0, 16);
  return <div className="earnings-coverage-view">
    <h4>{data.forecastYear}E 聚合预测字段覆盖</h4>
    <p>{data.membershipDate} 固定名单 · {captured} 取得；来源更新时间未知。</p>
    <div className="earnings-coverage-rows">{data.indices.map((index) => {
      const pct = index.available / index.total * 100;
      return <div key={index.code}>
        <div className="earnings-coverage-row"><b>{index.name}</b><span>{`${index.available}/${index.total}`}</span><span>{pct.toFixed(1)}%</span></div>
        <div className="earnings-coverage-track" role="img" aria-label={`${index.name}预测EPS字段本次覆盖${index.available}只，共${index.total}只`}>
          <span style={{ width: `${pct}%` }} />
        </div>
        {index.notReturned > 0 && <small>{index.notReturned} 只本次请求未返回，不代表没有预测或分析师覆盖。</small>}
        {index.missingField > 0 && <small>{index.missingField} 只已返回但该年度预测 EPS 字段无有效值。</small>}
      </div>;
    })}</div>
    <p>聚合预测目前只有一版，全指数修正广度未知；另已取得4家公司同团队原研报变化样例，可在「指标分类」查看。</p>
    <p><a href={data.sourceDocUrl} target="_blank" rel="noreferrer">东方财富预测接口字段说明 ↗</a> · <button type="button" onClick={onOpenGuide}>查看修正指标说明</button></p>
  </div>;
}

export default function EarningsCoverageSnapshot({ onOpenGuide }: { onOpenGuide: () => void }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<EarningsCoverageData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!open || data) return;
    const controller = new AbortController();
    setError(false);
    fetch("/research/earnings-coverage-20261115.json", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("snapshot unavailable");
        return response.json() as Promise<unknown>;
      })
      .then((value) => {
        if (!isEarningsCoverageSnapshot(value)) throw new Error("invalid snapshot");
        setData(value);
      })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [open, data]);

  return <details className="earnings-snapshot" onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>盈利预期 · 聚合字段覆盖</summary>
    {error && <p role="alert">预测覆盖快照读取失败，请稍后重试。</p>}
    {open && !data && !error && <p role="status">正在读取预测覆盖快照…</p>}
    {data && <EarningsCoverageView data={data} onOpenGuide={onOpenGuide} />}
  </details>;
}
