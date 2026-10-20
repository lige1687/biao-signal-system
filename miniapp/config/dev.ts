// 开发环境配置（由 config/index.ts 在 NODE_ENV=development 时合并）
const devConfig: Record<string, unknown> = {
  logger: { quiet: false, stats: true },
  mini: {},
  h5: {},
}

export default devConfig
