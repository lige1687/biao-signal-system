// babel-preset-taro 更多选项参考：
// https://docs.taro.zone/docs/next/babel-config
module.exports = {
  presets: [
    ['taro', {
      framework: 'react',
      ts: true,
      compiler: 'webpack5',
      useBuiltIns: process.env.TARO_ENV === 'h5' ? 'usage' : false,
    }],
  ],
}
