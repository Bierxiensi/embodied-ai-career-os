# Tailwind CSS 迁移设计

> 日期：2026-09-17
> 状态：已批准

## 目标

引入 Tailwind CSS，统一设计 token，降低样式维护成本。渐进式迁移，不破坏现有功能。

## 现状

- 全站纯 inline style（`style={{...}}`）
- `globals.css` 定义了 CSS 变量（`--color-primary`、`--color-ink`、`--radius-card-lg` 等）
- 无 UI 框架，无设计系统
- 暗色模式部分支持（`[data-theme="dark"]`）

## 方案

### 步骤 1：安装 Tailwind + 配置

```bash
npm install -D tailwindcss @tailwindcss/postcss
```

`tailwind.config.ts` 映射现有 CSS 变量到 Tailwind 主题：
- `colors.primary` → `var(--color-primary)`
- `colors.ink` → `var(--color-ink)`
- `colors.card` → `var(--color-card)`
- `colors.hairline` → `var(--color-hairline)`
- `colors.emerald` → `var(--color-emerald)`
- `colors.amber` → `var(--color-amber)`
- `colors.rose` → `var(--color-rose)`
- `colors.zinc-100` → `var(--color-zinc-100)`
- `borderRadius.card` → `var(--radius-card-lg)`
- `borderRadius.item` → `var(--radius-item-md)`
- `borderRadius.pill` → `var(--radius-pill)`

### 步骤 2：globals.css 注入 Tailwind

```css
@import "tailwindcss";
```

保留现有 CSS 变量定义（`:root` 和 `[data-theme="dark"]`）。

### 步骤 3：新组件全部用 Tailwind

新组件用 Tailwind 类名，不再写 inline style。颜色用自定义 token：
```tsx
// 旧
<div style={{ background: "var(--color-card)", borderRadius: "var(--radius-card-lg)" }}>

// 新
<div className="bg-card rounded-card">
```

### 步骤 4：旧组件渐进迁移

按优先级迁移（高频改动的组件先改）：
1. QuestionBoard.tsx（刚改过，改动频繁）
2. TodayBoard.tsx
3. Dashboard.tsx
4. JobsBoard.tsx
5. 其他组件

迁移时不改功能，只改样式写法。

## 设计 Token 映射表

| Tailwind 名 | CSS 变量 | 用途 |
|---|---|---|
| `bg-card` | `--color-card` | 卡片背景 |
| `bg-page` | `--color-page` | 页面背景 |
| `text-ink` | `--color-ink` | 主文字 |
| `text-ink-80` | `--color-ink-80` | 次文字 |
| `text-ink-48` | `--color-ink-48` | 辅助文字 |
| `border-hairline` | `--color-hairline` | 边框 |
| `text-primary` | `--color-primary` | 主色调 |
| `bg-emerald` | `--color-emerald` | 绿色 |
| `bg-amber` | `--color-amber` | 琥珀色 |
| `bg-rose` | `--color-rose` | 玫瑰色 |
| `rounded-card` | `--radius-card-lg` | 大圆角 |
| `rounded-item` | `--radius-item-md` | 中圆角 |
| `rounded-pill` | `--radius-pill` | 胶囊圆角 |

## 不做的事

- 不引入 Shadcn/ui（保持轻量）
- 不引入 Tailwind UI（付费）
- 不一次性迁移所有组件（风险太大）
- 不改功能逻辑（只改样式写法）
