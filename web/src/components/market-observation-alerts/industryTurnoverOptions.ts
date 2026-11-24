export const INDUSTRY_TURNOVER_ID = "cn-industry-turnover";

export const INDUSTRY_TURNOVER_OPTIONS = [
  { id: "cn-industry-turnover-bk0448", label: "通信设备" },
  { id: "cn-industry-turnover-bk1036", label: "半导体" },
  { id: "cn-industry-turnover-bk1326", label: "半导体设备" },
  { id: "cn-industry-turnover-bk1325", label: "半导体材料" },
  { id: "cn-industry-turnover-bk0478", label: "有色金属" },
  { id: "cn-industry-turnover-bk0428", label: "电力" },
  { id: "cn-industry-turnover-bk0457", label: "电网设备" },
] as const;

export function isIndustryTurnoverSeries(id: string) {
  return id.startsWith(`${INDUSTRY_TURNOVER_ID}-`);
}
