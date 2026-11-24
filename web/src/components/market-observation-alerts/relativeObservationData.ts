export const RELATIVE_OBSERVATION_CARDS = [
  { id: "cn-style-relative", market: "cn", kind: "relative", title: "大小盘 · 中证1000 / 沪深300" },
  { id: "us-semiconductor-relative", market: "us", kind: "relative", title: "半导体 / 纳指100" },
  { id: "us-equal-weight-relative", market: "us", kind: "relative", title: "标普500 · 等权 / 市值加权" },
  { id: "vix-term-structure", market: "us", kind: "term", title: "VIX · 期限结构" },
] as const;

type CardDefinition = typeof RELATIVE_OBSERVATION_CARDS[number];
const INSTRUMENT_PAIRS: Record<CardDefinition["id"], readonly [string, string]> = {
  "cn-style-relative": ["512100", "510300"],
  "us-semiconductor-relative": ["SMH", "QQQ"],
  "us-equal-weight-relative": ["RSP", "SPY"],
  "vix-term-structure": ["VIX", "VIX3M"],
};
type Instrument = { symbol: string; label: string };
type Source = { name: string; url: string };

export type RelativeObservationPoint = {
  date: string;
  ratio: number;
  ma60: number | null;
  numerator: number;
  denominator: number;
};

export type RelativeObservationCard = CardDefinition & {
  numerator: Instrument;
  denominator: Instrument;
  sources: Source[];
  price_note: string;
  points: RelativeObservationPoint[];
};

export type RelativeObservationSnapshot = {
  schema_version: 1;
  imported_at: string;
  refresh_mode: "snapshot";
  cards: RelativeObservationCard[];
};

const isoDate = (value: unknown): value is string =>
  typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)
  && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
const isoTimestamp = (value: unknown): value is string =>
  typeof value === "string" && isoDate(value.slice(0, 10))
  && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value)
  && Number.isFinite(Date.parse(value));
const positive = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value) && value > 0;
const nonempty = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;
const near = (value: number, expected: number) =>
  positive(expected) && Math.abs(value / expected - 1) <= 1e-8;

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid observation object");
  return value as Record<string, unknown>;
}

function parseInstrument(value: unknown): Instrument {
  const { symbol, label } = record(value);
  if (!nonempty(symbol) || !nonempty(label)) throw new Error("Invalid observation instrument");
  return { symbol, label };
}

function parseSource(value: unknown): Source {
  const { name, url } = record(value);
  if (!nonempty(name) || !nonempty(url)) throw new Error("Invalid observation source");
  const parsed = new URL(url);
  if (!["https:", "http:"].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new Error("Invalid observation source URL");
  }
  return { name, url: parsed.href };
}

function parsePoints(values: unknown): RelativeObservationPoint[] {
  if (!Array.isArray(values) || values.length < 120) throw new Error("Insufficient observation history");
  const points: RelativeObservationPoint[] = [];
  let previous = "";
  for (const value of values) {
    const { date, ratio, ma60, numerator, denominator } = record(value);
    if (!isoDate(date) || date < "2024-01-01" || date <= previous
      || !positive(ratio) || !positive(numerator) || !positive(denominator)
      || !near(ratio, numerator / denominator)) {
      throw new Error("Invalid observation point");
    }
    if (points.length < 59) {
      if (ma60 !== null) throw new Error("Invalid observation moving average");
    } else {
      const mean = points.slice(-59).reduce((sum, point) => sum + point.ratio / 60, ratio / 60);
      if (!positive(ma60) || !near(ma60, mean)) throw new Error("Invalid observation moving average");
    }
    previous = date;
    points.push({ date, ratio, ma60, numerator, denominator });
  }
  return points;
}

/** All four histories are required for a version 1 snapshot. */
export function parseRelativeObservationSnapshot(value: unknown): RelativeObservationSnapshot {
  const snapshot = record(value);
  if (snapshot.schema_version !== 1 || snapshot.refresh_mode !== "snapshot"
    || !isoTimestamp(snapshot.imported_at) || !Array.isArray(snapshot.cards)
    || snapshot.cards.length !== RELATIVE_OBSERVATION_CARDS.length) {
    throw new Error("Invalid observation snapshot");
  }
  const importedAt = snapshot.imported_at;
  const seen = new Set<CardDefinition["id"]>();
  const cards = snapshot.cards.map((value): RelativeObservationCard => {
    const card = record(value);
    const definition = RELATIVE_OBSERVATION_CARDS.find(({ id }) => id === card.id);
    if (!definition || seen.has(definition.id) || card.market !== definition.market
      || card.kind !== definition.kind || card.title !== definition.title
      || !Array.isArray(card.sources) || !card.sources.length || !nonempty(card.price_note)) {
      throw new Error("Invalid observation card");
    }
    seen.add(definition.id);
    const numerator = parseInstrument(card.numerator);
    const denominator = parseInstrument(card.denominator);
    const [expectedNumerator, expectedDenominator] = INSTRUMENT_PAIRS[definition.id];
    if (numerator.symbol !== expectedNumerator || denominator.symbol !== expectedDenominator) {
      throw new Error("Incorrect observation instrument pair");
    }
    const points = parsePoints(card.points);
    if (points[points.length - 1].date > importedAt.slice(0, 10)) {
      throw new Error("Observation date exceeds snapshot date");
    }
    return {
      ...definition, numerator, denominator, sources: card.sources.map(parseSource),
      price_note: card.price_note, points,
    };
  });
  return { schema_version: 1, refresh_mode: "snapshot", imported_at: importedAt, cards };
}

export function relativeObservationReading(card: RelativeObservationCard) {
  const latest = card.points[card.points.length - 1];
  const prior = card.points[card.points.length - 21];
  const change = (latest.ratio / prior.ratio - 1) * 100;
  const displayedChange = Math.abs(change).toFixed(2);
  const comparison = displayedChange === "0.00" ? "基本持平" : `${change > 0 ? "上升" : "下降"} ${displayedChange}%`;
  let headline = `近20个共同交易日比值${comparison}`;
  if (card.kind === "term") {
    headline = latest.ratio > 1 ? "短期隐含波动率高于3个月"
      : latest.ratio < 1 ? "短期隐含波动率低于3个月" : "短期与3个月隐含波动率相同";
  }
  return { latest, prior, comparison, headline, value: `${latest.ratio.toFixed(card.kind === "term" ? 3 : 4)}倍` };
}
