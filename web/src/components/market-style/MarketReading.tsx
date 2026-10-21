import { useRef, useState } from "react";
import "./market-reading.css";

type Source = { id: string; name: string; url: string };
type ReadingCard = { id: string; topic: string; title?: string; fact: string; reading: string; watch: string; source_ids: string[]; data_date: string | null; available: boolean };
type Snapshot = { snapshot_id: string; asof: string; cards: ReadingCard[]; sources: Source[]; limits: string[] };
type Reading = { generated: true; snapshot_id: string; cards: ReadingCard[]; model: string; generated_at: string; limits: string[]; usage?: Record<string, number> | null; elapsed_ms?: number };
type Context = { windowDays: number; ruleIds: string[]; priceKey: string; fingerprint: string };
const TOPICS: Record<string, string> = { style: "风格相对表现", breadth: "市场参与程度", risk: "风险条件", strategy: "策略是否重叠" };
const ERRORS: Record<string, string> = {
  model_unavailable: "模型尚未配置，资料可以继续看。",
  model_no_text: "模型没有返回有效正文，这次未生成解读。",
  model_failed: "模型调用失败，这次未生成解读。",
  invalid_model_selection: "模型结果未通过事实范围核对，这次未展示解读。",
  model_request_in_progress: "已有解读正在生成，请稍后再点。",
  unknown_snapshot: "这份资料已过期，请重新点击核对。",
  timeout: "本次模型请求超时，未自动重试。",
  connection_error: "暂时无法连接模型，未自动重试。",
};

async function readJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(ERRORS[data?.error] ?? "资料或解读服务暂时不可用，请稍后再试。");
  if (!data) throw new Error("没有收到有效资料，请稍后再试。");
  return data as T;
}

export default function MarketReading({ market, context, viewRevision = 0, riskBasis = "" }: {
  market: "cn" | "us"; context: Context; viewRevision?: number; riskBasis?: string;
}) {
  const [mode, setMode] = useState<"weekly" | "monthly">("weekly");
  const binding = JSON.stringify({ market, context, viewRevision, riskBasis, mode });
  const bindingRef = useRef(binding);
  bindingRef.current = binding;
  const [pending, setPending] = useState<"facts" | "model" | null>(null);
  const busyRef = useRef(false);
  const [result, setResult] = useState<{ binding: string; snapshot: Snapshot; reading: Reading } | null>(null);
  const [failure, setFailure] = useState<{ binding: string; text: string } | null>(null);
  const visible = result?.binding === binding ? result : null;
  const visibleFailure = failure?.binding === binding ? failure.text : null;
  const changed = !!result && !visible;

  // No effect, timer, query retry or mount handler can invoke the model.
  async function generate() {
    if (busyRef.current) return;
    busyRef.current = true;
    const requestedBinding = binding;
    setPending("facts");
    setFailure(null);
    try {
      const snapshot = await readJson<Snapshot>(`/api/market-style/snapshot?market=${market}&window_days=${context.windowDays}&mode=${mode}`);
      // A context switch while facts load must not start a model call for the old view.
      if (bindingRef.current !== requestedBinding) return;
      setPending("model");
      const reading = await readJson<Reading>("/api/market-style/interpret", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ snapshot_id: snapshot.snapshot_id }),
      });
      if (reading.generated !== true || reading.snapshot_id !== snapshot.snapshot_id) {
        throw new Error("返回的解读与资料不一致，这次未展示。");
      }
      if (bindingRef.current === requestedBinding) setResult({ binding: requestedBinding, snapshot, reading });
    } catch (error) {
      if (bindingRef.current === requestedBinding) setFailure({
        binding: requestedBinding, text: error instanceof Error ? error.message : "这次未能生成解读。",
      });
    } finally {
      busyRef.current = false;
      setPending(null);
    }
  }

  return <section className="market-reading" aria-label="Agent按需解读">
    <header className="mr-heading">
      <div><strong>Agent 解读</strong><span>{mode === "monthly" ? "五问逐项核对，保留尚未回答的部分。" : "最近宽度、风险与风格变化的阅读重点。"}</span></div>
      <div className="mr-actions">
        <div className="ms-switch" role="group" aria-label="选择周观察或月复盘">
          <button type="button" aria-pressed={mode === "weekly"} onClick={() => setMode("weekly")}>周观察</button>
          <button type="button" aria-pressed={mode === "monthly"} onClick={() => setMode("monthly")}>月复盘</button>
        </div>
        <button type="button" className="mr-generate" disabled={pending !== null || !context.fingerprint} onClick={generate}>
          {pending === "facts" ? "核对资料…" : pending === "model" ? "整理重点…" : visible ? "重新核对解读" : mode === "monthly" ? "生成五问复盘" : "生成重点解读"}
        </button>
      </div>
    </header>
    {pending && <p className="mr-status" role="status">本次点击正在处理。切换观察对象后，本次旧结果不会展示到新图上。</p>}
    {visibleFailure && <p className="ms-error" role="alert">{visibleFailure} 可再次点击重试。</p>}
    {changed && !pending && <p className="mr-status">图表范围或资料已变化，旧解读已隐藏。需要时再点击生成。</p>}
    {visible && <details className="mr-result" open>
      <summary>{mode === "monthly" ? "本次月复盘 · 五问完整列出" : `本次周观察 · ${visible.reading.cards.length}个重点`}</summary>
      <p className="mr-scope">{mode === "monthly"
        ? `前四问：全球风格，日线与月末资料分别标日 · 第五问：${market === "cn" ? "A股" : "美股"}策略历史与前向记录`
        : `${market === "cn" ? "A股" : "美股"}宽度最近一次变化 · 全球风格近1年日线 · 策略历史比较`}</p>
      <div className="mr-grid">
        {visible.reading.cards.map((card) => <article key={card.id}>
          <h3>{card.title ?? TOPICS[card.topic] ?? "观察重点"}<small>{card.data_date ?? (card.available ? ["strategy", "q5"].includes(card.topic) ? "历史与前向分开" : "各项日期见下" : "缺资料")}</small></h3>
          <p>{card.fact}</p><p className="mr-reading">{card.reading}</p><p className="mr-watch"><span>{mode === "monthly" ? "未答／边界" : "接着看"}</span>{card.watch}</p>
        </article>)}
      </div>
      <details className="mr-sources">
        <summary>解读方法、资料与模型</summary>
        <p>Agent依据资料选择重点和顺序，事实、读法与数字由已核规则填入。MSCI与StockCharts提供阅读方法，不代表它们评价了本页当前市场。</p>
        <p>本次风格表现固定比较近1年日线；行业和估值仍使用独立标日的月末资料。不解释拖动缩放后的局部走势，也不推断条件色带之后的收益。页面变化后需重新点击。</p>
        <div>{visible.snapshot.sources.filter((source) => visible.reading.cards.some((card) => card.source_ids.includes(source.id))).map((source) =>
          <a key={source.id} href={source.url} target="_blank" rel="noreferrer">{source.name} ↗</a>)}</div>
        <p>{visible.reading.model} · {new Date(visible.reading.generated_at).toLocaleString("zh-CN")}
          {visible.reading.elapsed_ms != null ? ` · ${(visible.reading.elapsed_ms / 1000).toFixed(1)}秒` : ""} · {visible.reading.usage ? `用量 ${visible.reading.usage.total_tokens ?? ((visible.reading.usage.input_tokens ?? visible.reading.usage.prompt_tokens ?? 0) + (visible.reading.usage.output_tokens ?? visible.reading.usage.completion_tokens ?? 0))} tokens；费用未返回` : "用量与费用未返回"}。相同资料复用已生成结果。</p>
      </details>
    </details>}
    {!visible && !pending && !visibleFailure && !changed && <p className="mr-idle">仅点击生成才调用模型，切换周/月不触发。周观察挑重点；月复盘必须列齐五问，不把缺资料的问题跳过。</p>}
  </section>;
}
