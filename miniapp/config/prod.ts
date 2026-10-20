// 生产环境配置（由 config/index.ts 在 NODE_ENV=production 时合并）
const prodConfig: Record<string, unknown> = {
  mini: {
    compress: true,
  },
  h5: {},
}

export default prodConfig
