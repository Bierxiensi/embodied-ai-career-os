# 项目长期记忆 · Embodied AI Career OS

## 项目基础
- **类型**：面向 Agent 应用开发工程师转型的"具身智能职业 OS"，目标周期 3–6 个月
- **技术栈**：Next.js 16（App Router）+ React 19 + TypeScript + Tailwind v4（CSS-first @theme）
- **设计取向**：零第三方 UI 库（全部手写组件）、零图表库（雷达图等纯 SVG）、Geist 字体
- **数据流**：Server Component 拉取 + `router.refresh()` 增量更新
- **后端**：FastAPI 风格（路径 /api/career/... /api/tasks/...），snake_case 存储，
  前端用 adapter 转换为 camelCase
- **数据形态**：Career / Skill / Task（STATUS_CONFIG: todo/doing/done）/ Project / Milestone /
  AgentRunRecord / CommitSuggestion

## 命名与代码规范
- 组件 PascalCase.tsx，一文件一默认导出
- `type Props = {...}` 内联
- 常量 UPPER_SNAKE_CASE（如 `STATUS_CONFIG`、`AGENT_COLORS`）
- 服务层 camelCase；后端 snake_case→camelCase
- 颜色：emerald=成功/当前、sky=规划/Planner、violet=Reviewer、amber=待办/Career、rose=Research/失败
- 卡片样式：白底 + hairline 边框 + 18px 圆角 + 24px padding，无阴影（与 Apple 风格一致）
- 状态徽章：pill 形（radius 999），浅色底 + 深色字

## 设计资产
- **Ardot 画布 fileId 716776328381413**（2026-08-20 设计的完整 dashboard）
  - 27 个设计变量已通过 `apply_variables` 写入
  - 桌面端 1440 + 移动端 390 双版本
  - 验证截图存 `.workbuddy/screenshots/`（desktop-full / mobile-full / radar-card /
    quick-actions / row2-tasks-projects / agent-activity）

## 关键经验（避坑）
- **Ardot SVG 解析器对退化几何敏感**：纯水平/垂直直线段会因包围盒为 0×N 或 N×0 报
  "degenerate geometry" 错误。**修复：给所有轴线加 1px 偏移**（如 `M180 180L181 40`）。
- 设计变量已就位，下次实现代码时直接引用 `var(--color-canvas)` 等 token，不要再硬编码 hex。
