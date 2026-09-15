import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    // 端口与后端代理可用环境变量覆盖（UX 第一期 2026-09-13：隔离预览用，
    // 不占用 8000/5173；不设时行为与原来完全一致）。
    port: Number(process.env.LEI_WEB_PORT ?? 5173),
    proxy: {
      "/api": process.env.LEI_API_PROXY ?? "http://127.0.0.1:8000",
    },
  },
  build: {
    rollupOptions: {
      output: {
        // echarts / react 各自成块：主业务包显著变小，且这两个库内容
        // 基本不变，浏览器缓存可长期命中，改业务代码不用重下图表库。
        manualChunks: {
          echarts: ["echarts"],
          react: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
});
