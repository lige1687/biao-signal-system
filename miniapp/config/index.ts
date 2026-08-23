import { defineConfig } from '@tarojs/cli'
import devConfig from './dev'
import prodConfig from './prod'

// 编译目标：微信小程序（weapp）。其余端未启用。
export default defineConfig({
  projectName: 'lei-signal-miniapp',
  date: '2026-8-23',
  designWidth: 750,
  deviceRatio: {
    640: 2.34 / 2,
    750: 1,
    828: 1.81 / 2,
  },
  sourceRoot: 'src',
  outputRoot: 'dist',
  plugins: [],
  defineConstants: {},
  copy: {
    patterns: [],
    options: {},
  },
  framework: 'react',
  compiler: 'webpack5',
  mini: {
    postcss: {
      pxtransform: { enable: true },
      cssModules: { enable: false },
    },
    webpackChain(chain) {
      chain.resolve.symlinks(false)
    },
  },
  h5: {
    publicPath: '/',
    staticDirectory: 'static',
    postcss: {
      autoprefixer: { enable: true },
      pxtransform: { enable: true },
      cssModules: { enable: false },
    },
  },
  rn: { appName: 'leiSignalMiniapp' },
  ...(process.env.NODE_ENV === 'development' ? devConfig : prodConfig),
})
