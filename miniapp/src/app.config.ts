export default defineAppConfig({
  pages: [
    'pages/signals/index',
    'pages/dashboard/index',
    'pages/brief/index',
    'pages/detail/index',
    'pages/settings/index',
    'pages/plans/index',
  ],
  window: {
    navigationBarTitleText: 'LEI 信号看板',
    navigationBarBackgroundColor: '#0f1115',
    navigationBarTextStyle: 'white',
    backgroundColor: '#0f1115',
    backgroundTextStyle: 'dark',
  },
  tabBar: {
    color: '#8a8f98',
    selectedColor: '#e33d47',
    backgroundColor: '#16181d',
    borderStyle: 'black',
    list: [
      { pagePath: 'pages/signals/index', text: '今日信号' },
      { pagePath: 'pages/dashboard/index', text: '自选看板' },
      { pagePath: 'pages/brief/index', text: '收盘简报' },
    ],
  },
})
