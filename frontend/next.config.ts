import type { NextConfig } from "next";

/**
 * Next.js 配置。
 *
 * rewrites：将 /api/* 代理到后端 FastAPI（localhost:8000），
 * 避免前端硬编码后端 URL 与跨域问题（遵循 ExperienceRecall 教训：优先代理）。
 *
 * allowedDevOrigins：Next.js 16 默认阻止跨域访问 dev 资源（HMR / client chunks）。
 * 沙箱预览环境通过代理域名访问 localhost:3000，必须显式放行，
 * 否则 client component 的 JS chunk 被阻止加载，导致 React 无法 hydrate
 * （表现为按钮 onClick 不触发、状态不更新）。
 */
const nextConfig: NextConfig = {
  turbopack: {
    root: __dirname,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
    // 沙箱预览代理域名（Trae 远程开发环境）
    // 注意：沙箱每次重启实例 ID 会变，用通配符匹配整个域名模式
    "*.traecontent.cn",
    "*.trae-preview.com",
    "*.remote-agent.svc.cluster.local",
    "*.agent-sandbox-bj-d3-gw.traecontent.cn",
  ],
};

export default nextConfig;
