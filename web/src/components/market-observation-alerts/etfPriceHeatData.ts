export const ETF_PRICE_HEAT_ID = "etf-price-heat";
export const ETF_PRICE_HEAT_URL = "/research/etf-price-heat-20261108/data.json";
export const ETF_SYMBOLS = ["512480", "515880", "159915", "510300"] as const;

export type EtfHeatPoint = {
  date: string; price: number | null; heat: number | null; activity: number | null;
  amountSharePct: number | null; relativeTurnover: number | null; turnoverSurge: number | null;
  heatPeak20: number | null; heatDrop20: number | null; priceHigh20: boolean | null; divergence: boolean | null;
};
export type EtfHeatCard = {
  symbol: string; name: string; kind: "sector" | "index"; turnoverComparison: string;
  points: EtfHeatPoint[];
  research: { matureDays: number; spacedEvents: number; mean20: number; otherHighMean20: number; spacedMean20: number };
};
export type EtfPriceHeatSnapshot = {
  schemaVersion: 1; generatedAt: string; snapshotAsOf: string; sourceLabel: string;
  sourceNote: string; priceNote: string; cards: EtfHeatCard[];
};

const object = (v: unknown): Record<string, unknown> => {
  if (v === null || typeof v !== "object" || Array.isArray(v)) throw new Error("快照结构无效");
  return v as Record<string, unknown>;
};
const nonempty = (v: unknown): v is string => typeof v === "string" && v.trim().length > 0;
const date = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v)
  && Number.isFinite(Date.parse(`${v}T00:00:00Z`)) && new Date(`${v}T00:00:00Z`).toISOString().slice(0, 10) === v;
const timestamp = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(v)
  && Number.isFinite(Date.parse(v));
const numeric = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const optionalNumber = (v: unknown, min = -Infinity, max = Infinity): v is number | null =>
  v === null || numeric(v) && v >= min && v <= max;
const optionalBoolean = (v: unknown): v is boolean | null => v === null || typeof v === "boolean";

export function parseEtfPriceHeatSnapshot(value: unknown): EtfPriceHeatSnapshot {
  const root = object(value);
  if (root.schemaVersion !== 1 || !timestamp(root.generatedAt) || !date(root.snapshotAsOf)
    || !nonempty(root.sourceLabel) || !nonempty(root.sourceNote) || !nonempty(root.priceNote)
    || !Array.isArray(root.cards) || root.cards.length !== ETF_SYMBOLS.length) throw new Error("快照资料不完整");
  const seen = new Set<string>();
  const asOf = root.snapshotAsOf;
  const cards = root.cards.map((entry): EtfHeatCard => {
    const c = object(entry);
    if (!nonempty(c.symbol) || !ETF_SYMBOLS.some(s => s === c.symbol) || seen.has(c.symbol)
      || !nonempty(c.name) || !["sector", "index"].includes(String(c.kind))
      || !nonempty(c.turnoverComparison) || !Array.isArray(c.points) || c.points.length === 0) throw new Error("ETF资料不完整");
    seen.add(c.symbol);
    let previous = "";
    const points = c.points.map((entry): EtfHeatPoint => {
      const p = object(entry);
      if (!date(p.date) || p.date <= previous || p.date > asOf
        || !optionalNumber(p.price, 0) || !optionalNumber(p.heat, 0, 100)
        || !optionalNumber(p.activity, 0, 100) || !optionalNumber(p.amountSharePct, 0)
        || !optionalNumber(p.relativeTurnover, 0) || !optionalNumber(p.turnoverSurge, 0)
        || !optionalNumber(p.heatPeak20, 0, 100) || !optionalNumber(p.heatDrop20, 0, 100)
        || !optionalBoolean(p.priceHigh20) || !optionalBoolean(p.divergence)) throw new Error("ETF日期或读数无效");
      previous = p.date;
      return { date: p.date, price: p.price, heat: p.heat, activity: p.activity,
        amountSharePct: p.amountSharePct, relativeTurnover: p.relativeTurnover,
        turnoverSurge: p.turnoverSurge, heatPeak20: p.heatPeak20, heatDrop20: p.heatDrop20,
        priceHigh20: p.priceHigh20, divergence: p.divergence };
    });
    const r = object(c.research);
    if (!numeric(r.matureDays) || !Number.isInteger(r.matureDays) || r.matureDays < 0
      || !numeric(r.spacedEvents) || !Number.isInteger(r.spacedEvents) || r.spacedEvents < 0
      || !numeric(r.mean20) || !numeric(r.otherHighMean20) || !numeric(r.spacedMean20)) throw new Error("历史观察资料无效");
    return { symbol: c.symbol, name: c.name, kind: c.kind as EtfHeatCard["kind"],
      turnoverComparison: c.turnoverComparison, points, research: { matureDays: r.matureDays,
        spacedEvents: r.spacedEvents, mean20: r.mean20, otherHighMean20: r.otherHighMean20,
        spacedMean20: r.spacedMean20 } };
  });
  return { schemaVersion: 1, generatedAt: root.generatedAt, snapshotAsOf: root.snapshotAsOf,
    sourceLabel: root.sourceLabel, sourceNote: root.sourceNote, priceNote: root.priceNote, cards };
}
