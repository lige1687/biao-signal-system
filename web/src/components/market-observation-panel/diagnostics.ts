import { finite, formatNumber, isFresh, latest, type ObservationPanelData } from "./model";

export type Reminder = { title: string; detail: string; state: "present" | "absent" | "unavailable" };
const get = (packet: ObservationPanelData, id: string) => {
  const card = packet.cards[id]; const point = latest(card);
  return { card, point, value: point?.value, date: point?.date };
};
const auxiliary = (packet: ObservationPanelData, id: string, label: RegExp) => packet.cards[id]?.auxiliary?.find(item => label.test(item.label));
const line = (packet: ObservationPanelData, id: string, key: string) => { const points = packet.cards[id]?.lines?.find(item => item.id.toLowerCase() === key)?.points; return points?.[points.length - 1]; };
const lineOn = (packet: ObservationPanelData, id: string, key: string, date?: string) =>
  packet.cards[id]?.lines?.find(item => item.id.toLowerCase() === key)?.points.find(point => point.date === date);
const missing = (title: string, detail: string): Reminder => ({ title, detail, state: "unavailable" });

/** Descriptive reminders only. Missing, old, and nonaligned inputs never become a negative finding. */
export function buildReminders(packet: ObservationPanelData, now = new Date()): Reminder[] {
  const fresh = (id: string) => { const x = get(packet, id); return !!x.card && isFresh(x.date, x.card.frequency, now) && finite(x.value); };
  const ofr = get(packet, "ofr-fsi"), credit = get(packet, "hy-oas"), term = get(packet, "vix-term-structure"), hv = get(packet, "hv-us");
  const hv60 = line(packet, "hv-us", "hv60") ?? line(packet, "hv-us", "long");
  const hv60Value = hv60?.value ?? auxiliary(packet, "hv-us", /60日|60D|HV60/i)?.value;
  const hv20Value = auxiliary(packet, "hv-us", /20日|20D|HV20/i)?.value ?? hv.value;
  const pressureReady = ["ofr-fsi", "hy-oas", "vix-term-structure", "hv-us"].every(fresh)
    && finite(hv20Value) && finite(hv60Value) && isFresh(hv60?.date ?? hv.date, "daily", now);
  const pressurePresent = term.value! > 1 && hv20Value! > hv60Value! && ofr.value! < 0 && credit.value! < 4;
  const pressure = !pressureReady
    ? missing("短期波动与信贷压力", "需要近期 VIX 期限比、标普20/60日波动、OFR 与高收益债利差，才能核对四项组合条件。")
    : { title: pressurePresent ? "短期去杠杆恐慌 · 宏观信贷压力未同步上升" : "短期波动与信贷压力",
      state: pressurePresent ? "present" : "absent",
      detail: `VIX 期限比 ${formatNumber(term.value, 3)}，标普20/60日波动 ${formatNumber(hv20Value)}% / ${formatNumber(hv60Value)}%，OFR ${formatNumber(ofr.value)}，高收益债利差 ${formatNumber(credit.value)}%。${pressurePresent ? "留意期限比能否回到1以下。" : "四项条件未同时满足。"}` } as Reminder;

  const concentration = get(packet, "cn-daily-amount-top5"), focus = get(packet, "focus-momentum");
  const concentrationMa20 = concentration.point?.ma20 ?? line(packet, "cn-daily-amount-top5", "ma20")?.value;
  const clusteringReady = fresh("cn-daily-amount-top5") && fresh("focus-momentum")
    && concentration.date === focus.date && finite(concentrationMa20);
  const clusteringPresent = concentration.value! > concentrationMa20! && focus.value! < -5;
  const clustering = !clusteringReady
    ? missing("局部抱团与焦点股动量", `成交集中度截至 ${concentration.date ?? "暂无"}，焦点股动量截至 ${focus.date ?? "暂无"}。等两项近期资料对齐后再判断。`)
    : { title: clusteringPresent ? "局部抱团拥挤 · 热门股亏钱效应显著" : "局部抱团与焦点股动量",
      state: clusteringPresent ? "present" : "absent",
      detail: `${concentration.date} 同日对照，成交集中度 ${formatNumber(concentration.value)}%，20日均值 ${formatNumber(concentrationMa20)}%，焦点股动量 ${formatNumber(focus.value)}%。${clusteringPresent ? "留意热门股亏钱效应是否继续扩散。" : "两项条件未同时触发。"}` } as Reminder;

  const financing = get(packet, "cn-financing"), basis = get(packet, "cn-index-futures-basis");
  const ih = lineOn(packet, "cn-index-futures-basis", "ih", financing.date);
  const ifPoint = lineOn(packet, "cn-index-futures-basis", "if", financing.date)
    ?? basis.card?.points.find(point => point.date === financing.date);
  const sameDay = financing.date && financing.date === ih?.date && financing.date === ifPoint?.date;
  const basisReady = fresh("cn-financing") && finite(ih?.value) && finite(ifPoint?.value)
    && isFresh(ih?.date, "daily", now) && isFresh(ifPoint?.date, "daily", now) && sameDay;
  // A ratio in auxiliary metadata must not silently substitute a different primary financing measure.
  const financingRatio = finite(financing.value) ? financing.value : auxiliary(packet, "cn-financing", /融资买入.*占比|买入.*成交/)
    ?.value;
  const deepDiscount = basisReady && finite(financingRatio) && financingRatio < 8 && ih!.value! < -8 && ifPoint!.value! < -8;
  const futures = !basisReady || !finite(financingRatio)
    ? missing("融资与期指贴水", "等同日的融资买入占比和 IH、IF 年化基差齐备后再判断。")
    : { title: deepDiscount ? "杠杆温和偏冷 · 蓝筹对冲贴水深" : "融资与期指贴水",
      state: deepDiscount ? "present" : "absent",
      detail: `${financing.date} 同日对照，融资买入占比 ${formatNumber(financingRatio)}%，IH / IF 基差 ${formatNumber(ih?.value)}% / ${formatNumber(ifPoint?.value)}%。${deepDiscount ? "留意贴水是否收敛。" : "两只大盘期指和融资条件未同时触发。"}` } as Reminder;
  return [pressure, clustering, futures];
}
