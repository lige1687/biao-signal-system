# 焦点图总览与局部波动阅读 — active 2026-11-05T19:22:58.779824+08:00

- 原task/owner/本轮遮线修复继续，scope_released=false；checked_coordination_sha=e97046a552d2895ccb220c6bd210632dff211d82（自己刚推且读回、相关任务无新增同写）。用户追加：一年图波动扁、三五年点难辨，要求合适的展示。
- root在原price-projection.tsx范围外增补price-projection.css、chart-navigation.ts及现有.test.mjs、crossing-markers.ts。方案：默认3年总览、增加近3/6个月快捷局部窗口和返回总览、加高两图、纵轴取可见值并保留动量0参照、适当放大中等跨度原始点；选中读数仍放图外栏，保留所有原始事件。
- 只改变观察呈现，不新造信号/阈值/金融数据或跑收益研究。针对窗口边界/空值的必要测试、旧标记测试、TypeScript及真实桌面1/3/5年与局部缩放验收。自有QA记录在原阶段目录；其余模块、报告/registry/数据只读。无需代理或额外设计批准。
