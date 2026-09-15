/** 浏览器本地存储（localStorage）旧键名迁移。
 *
 * 背景：前端品牌命名 lei -> biao 时，一批本地存储的键名也跟着改了。
 * 但用户浏览器里存的还是旧键名下的值，新键名读出来是空的 —— 表现为
 * 「我以前关注的板块 / 打星的行业 / 调过的阈值全没了」。
 *
 * 这里在应用启动时把旧键的值搬到新键上（新键已有值就不动），搬完删旧键。
 * 只跑一次，失败也不影响页面（私密模式等场景下 localStorage 可能不可用）。
 */

const MIGRATIONS: ReadonlyArray<readonly [from: string, to: string]> = [
  ["lei.sentiment.watchBoards", "biao.sentiment.watchBoards"],
  ["lei.sector.stars", "biao.sector.stars"],
  ["lei-overlay-active-rules", "biao-overlay-active-rules"],
  ["lei-overlay-cn-threshold", "biao-overlay-cn-threshold"],
  ["lei-overlay-us-threshold", "biao-overlay-us-threshold"],
];

let ran = false;

export function migrateStorageKeys(): void {
  if (ran) return;
  ran = true;
  try {
    for (const [from, to] of MIGRATIONS) {
      if (localStorage.getItem(to) !== null) continue; // 新键已有值，不覆盖
      const legacy = localStorage.getItem(from);
      if (legacy === null) continue; // 旧键本来就没值
      localStorage.setItem(to, legacy);
      localStorage.removeItem(from);
    }
  } catch {
    /* localStorage 不可用（私密模式 / 禁用 cookie）时静默跳过 */
  }
}
