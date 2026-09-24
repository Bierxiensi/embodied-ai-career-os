# UI 设计系统重设计规范

> 日期：2026-09-24
> 状态：设计完成，待实施
> 范围：主题系统 + 组件库 + 信息架构 + 视觉语言

---

## 1. 主题系统架构

### 1.1 Token 分层

三层 token 架构，主题切换只覆盖第二层：

```
Layer 1: Primitive Tokens（原始值，不随主题变化）
  └── gray-50 ~ gray-900, blue-50 ~ blue-900, radius-sm/md/lg/xl ...

Layer 2: Semantic Tokens（语义映射，主题切换层）
  └── surface-canvas, surface-card, surface-elevated
  └── text-primary, text-secondary, text-muted
  └── border-default, border-subtle
  └── accent-primary, accent-success, accent-warning, accent-danger

Layer 3: Component Tokens（组件级，引用 semantic）
  └── button-bg, button-bg-hover, card-shadow, nav-height ...
```

切换机制：`<html data-theme="ardot-light">`，CSS 选择器覆盖 semantic tokens。每个主题定义 Layer 2 映射，Layer 3 自动继承。

### 1.2 三套主题

| 主题 | data-theme 值 | 调性 | 画布色 | 卡片色 | 强调色 |
|------|--------------|------|--------|--------|--------|
| Ardot Light | `ardot-light` | 克制精致，Apple 风 | `#F5F5F7` | 纯白 + 微阴影 | `#0066CC` 蓝 |
| Ardot Dark | `ardot-dark` | 沉稳专业，Linear 风 | `#0A0A0C` | `#18181B` + 微光边 | `#3B82F6` 亮蓝 |
| Ardot Neon | `ardot-neon` | 品牌驱动，Stripe 风 | `#0F0F14` | 半透明 + 渐变边 | 紫→蓝渐变 |

### 1.3 Semantic Token 清单

```typescript
// 表面（背景）
surface.canvas          // 页面底色
surface.card            // 卡片背景
surface.elevated        // 弹出层背景（Modal、Popover）
surface.overlay         // 遮罩层
surface.sidebar         // 侧边栏背景

// 文本
text.primary            // 主要文字（标题、正文）
text.secondary          // 次要文字（说明、标签）
text.muted              // 最弱文字（时间戳、辅助）
text.inverse            // 反色文字（深色按钮上）
text.link               // 链接色

// 边框
border.default          // 常规边框（卡片、输入框）
border.subtle           // 弱边框（分隔线）
border.focus            // 聚焦态边框
border.error            // 错误态边框

// 强调色
accent.primary          // 主色调（按钮、链接）
accent.primary.hover    // 主色悬停
accent.primary.soft     // 主色软背景（Badge、Tag）
accent.success          // 成功色
accent.success.soft     // 成功软背景
accent.warning          // 警告色
accent.warning.soft     // 警告软背景
accent.danger           // 危险色
accent.danger.soft      // 危险软背景

// 特殊
shadow.card             // 卡片阴影
shadow.elevated         // 弹出层阴影
shadow.glow             // 光晕（仅 Neon）
gradient.accent         // 强调渐变（仅 Neon）
gradient.subtle         // 背景渐变（仅 Neon）
backdrop.blur           // 毛玻璃（仅 Neon）
```

### 1.4 文件结构

```
src/
  tokens/
    primitives.ts        # 原始值
    semantic.ts          # SemanticToken 类型接口
    themes/
      light.ts           # Light 主题映射
      dark.ts            # Dark 主题映射
      neon.ts            # Neon 主题映射
    index.ts             # 统一导出
  theme/
    ThemeProvider.tsx     # React Context + data-theme 管理
    useTheme.ts          # hook: currentTheme, setTheme, themes
    ThemeSwitcher.tsx     # 切换 UI 组件
    applyTheme.ts        # 将 token 映射注入 CSS 变量
  app/
    globals.css          # 重写：@import 生成 CSS 变量
```

### 1.5 ThemeProvider API

```tsx
// 使用方式
const { theme, setTheme, themes } = useTheme();

// Context 值
interface ThemeContextValue {
  theme: 'ardot-light' | 'ardot-dark' | 'ardot-neon';
  setTheme: (t: ThemeContextValue['theme']) => void;
  themes: Array<{ id: string; label: string; icon: string }>;
}

// 存储：localStorage('ardot-theme')，默认 'ardot-light'
// 注入：ThemeProvider 挂载时调用 applyTheme()，设置 <html data-theme="..."> + CSS 变量
```

### 1.6 CSS 变量生成

`applyTheme(theme)` 遍历 semantic tokens，生成：

```css
:root[data-theme="ardot-light"] {
  --surface-canvas: #F5F5F7;
  --surface-card: #FFFFFF;
  --text-primary: #1D1D1F;
  /* ... */
}
```

组件通过 `var(--surface-card)` 引用，零 JS 运行时开销。

---

## 2. 组件库设计

### 2.1 设计原则

1. **Token 驱动**：组件内部不硬编码颜色/阴影/圆角，全部引用 CSS 变量
2. **变体 + 尺寸**：每个组件支持 `variant` 和 `size` 两个维度
3. **可覆盖**：所有组件接受 `className` 和 `style` prop
4. **无障碍**：键盘导航、ARIA 属性、焦点管理
5. **主题自适应**：Neon 主题下自动增强视觉效果（渐变、光晕、毛玻璃）

### 2.2 组件清单

#### 表单与基础控件（9 个）

**Button**
```tsx
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost' | 'danger';
  size: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: ReactNode;
  children: ReactNode;
}
// Light: 纯色背景 + 微阴影
// Dark: 纯色背景 + 微光边
// Neon: 渐变背景 + hover 光晕 + press 缩放
```

**Input**
```tsx
interface InputProps {
  size: 'sm' | 'md' | 'lg';
  prefix?: ReactNode;
  suffix?: ReactNode;
  error?: string;
  disabled?: boolean;
}
// 聚焦态：border-focus + ring（Neon 下 ring 有渐变）
```

**Select**
```tsx
interface SelectProps {
  size: 'sm' | 'md' | 'lg';
  options: Array<{ value: string; label: string }>;
  searchable?: boolean;
  placeholder?: string;
}
// 弹出层：surface-elevated + shadow.elevated
```

**Checkbox / Radio / Toggle**
```tsx
// Checkbox: 方框 + 勾选动画（120ms）
// Radio: 圆框 + 选中环动画
// Toggle: 滑块 + 颜色过渡（Neon 下有渐变）
// 三者共享 size: 'sm' | 'md'
```

**Badge**
```tsx
interface BadgeProps {
  variant: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info';
  size: 'sm' | 'md';
  dot?: boolean;  // 圆点指示器
}
// 使用 accent.*.soft 作为背景，accent.* 作为文字
```

**Tag**
```tsx
interface TagProps {
  variant: 'default' | 'primary' | 'success' | 'warning' | 'danger';
  closable?: boolean;
  onClose?: () => void;
}
// 与 Badge 类似，但有关闭按钮
```

**Tooltip**
```tsx
interface TooltipProps {
  content: ReactNode;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
}
// surface-elevated 背景，arrow 跟随
```

#### 容器与布局（8 个）

**Card**
```tsx
interface CardProps {
  variant?: 'default' | 'elevated' | 'outlined' | 'ghost';
  padding?: 'sm' | 'md' | 'lg';
  hoverable?: boolean;
  header?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
}
// Light: white bg + subtle shadow + border
// Dark: dark bg + subtle glow border
// Neon: glass bg + gradient border + glow shadow
// hoverable: translateY(-2px) + shadow deepen（200ms）
```

**Modal**
```tsx
interface ModalProps {
  open: boolean;
  onClose: () => void;
  size?: 'sm' | 'md' | 'lg' | 'full';
  title?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
}
// 进入动画：opacity 0→1 + scale(0.96→1)（200ms）
// 遮罩：surface.overlay（Light: rgba(0,0,0,0.4), Neon: rgba(0,0,0,0.6) + blur）
```

**Drawer**
```tsx
interface DrawerProps {
  open: boolean;
  onClose: () => void;
  placement?: 'right' | 'left' | 'bottom';
  size?: number;  // px
  title?: ReactNode;
  children: ReactNode;
}
```

**Popover**
```tsx
interface PopoverProps {
  trigger: ReactNode;
  content: ReactNode;
  placement?: 'top' | 'bottom' | 'left' | 'right';
}
// surface.elevated + shadow.elevated
```

**Tabs**
```tsx
interface TabsProps {
  items: Array<{ key: string; label: string; content: ReactNode }>;
  variant?: 'underline' | 'pill';
  activeKey?: string;
  onChange?: (key: string) => void;
}
// underline: 下划线滑动动画
// pill: 背景色过渡
```

**Accordion**
```tsx
interface AccordionProps {
  items: Array<{ key: string; title: ReactNode; content: ReactNode }>;
  multiple?: boolean;
}
// 展开动画：height auto 过渡（300ms）
```

**EmptyState**
```tsx
interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}
```

**Skeleton**
```tsx
interface SkeletonProps {
  variant?: 'text' | 'circular' | 'rectangular';
  width?: number | string;
  height?: number | string;
  lines?: number;  // text variant
}
// 闪烁渐变：从左到右（Light/Dark），Neon 下有彩虹渐变
```

#### 数据展示（6 个）

**Stat**
```tsx
interface StatProps {
  label: string;
  value: string | number;
  change?: { value: number; direction: 'up' | 'down' };
  icon?: ReactNode;
  size?: 'sm' | 'md' | 'lg';
}
// 大数字用 accent.primary，趋势用 success/danger
```

**ProgressBar**
```tsx
interface ProgressBarProps {
  value: number;  // 0-100
  variant?: 'default' | 'success' | 'warning' | 'danger';
  size?: 'sm' | 'md';
  showLabel?: boolean;
  segments?: Array<{ value: number; variant: string }>;
}
// Neon: 渐变填充 + 微光
```

**RadarChart**
```tsx
interface RadarChartProps {
  data: Array<{ label: string; value: number; max?: number }>;
  size?: number;
  showLabels?: boolean;
  fillOpacity?: number;
}
// 统一现有 RadarChart 的接口，用 theme token 替换硬编码色
```

**BarChart**
```tsx
interface BarChartProps {
  data: Array<{ label: string; value: number; color?: string }>;
  orientation?: 'horizontal' | 'vertical';
  showValues?: boolean;
}
```

**Timeline**
```tsx
interface TimelineProps {
  items: Array<{
    title: string;
    description?: string;
    time?: string;
    icon?: ReactNode;
    status?: 'done' | 'current' | 'pending';
  }>;
}
// 节点样式：done=success, current=primary(脉冲), pending=muted
```

**StepIndicator**
```tsx
interface StepIndicatorProps {
  steps: Array<{ title: string; status: 'done' | 'current' | 'pending' }>;
  orientation?: 'horizontal' | 'vertical';
}
```

#### 导航组件（5 个）

**PageHeader**
```tsx
interface PageHeaderProps {
  eyebrow?: string;      // 小标签（如 "Day 12"）
  title: string;
  subtitle?: string;
  backLink?: { href: string; label: string };
  actions?: ReactNode;
}
```

**Sidebar**
```tsx
interface SidebarProps {
  sections: Array<{
    label: string;
    items: Array<{ href: string; label: string; icon?: ReactNode; badge?: number }>;
  }>;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
}
// 宽屏：常驻，240px → 64px（折叠）
// 窄屏：抽屉式，从左侧滑出
// Neon: 半透明背景 + backdrop-filter
```

**Breadcrumb**
```tsx
interface BreadcrumbProps {
  items: Array<{ href?: string; label: string }>;
  separator?: ReactNode;
}
```

**Pagination**
```tsx
interface PaginationProps {
  current: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
}
// 按钮样式跟随 Button secondary variant
```

**CommandPalette**
```tsx
interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  groups: Array<{
    label: string;
    items: Array<{ id: string; label: string; icon?: ReactNode; action: () => void }>;
  }>;
}
// ⌘K 触发
// surface.elevated 背景 + shadow.elevated
// 搜索框 + 分组结果列表 + 键盘导航
```

---

## 3. 信息架构重构

### 3.1 页面变更

| 变更类型 | 原页面 | 新位置 | 理由 |
|----------|--------|--------|------|
| 合并 | `/today` + `/dashboard` | `/today` | 功能重叠，合并为统一入口 |
| 合并 | `/reports` | `/jobs` 的 Tab | 报告是求职附属功能 |
| 合并 | `/evidence` | `/projects/[id]` 详情页 | 证据链是项目的一部分 |
| 合并 | `/experiments` | `/projects/[id]` 详情页 | 实验记录属于项目 |
| 删除 | `/jd` | 无（已有 `/jobs/pool`） | 清理无用重定向 |
| 升级 | SectionNav 水平导航 | Sidebar 侧边栏 | 品牌驱动型需要更强导航骨架 |

### 3.2 最终页面清单（13 页）

| 路径 | 页面 | 一句话职责 |
|------|------|-----------|
| `/today` | 个人主页 | 今天做什么 + 整体如何 + KPI + 快捷入口 |
| `/jobs` | 作战看板 | 倒计时 + 目标岗位 + 技能缺口 + 里程碑 + 漏斗 + 周报 Tab |
| `/jobs/pool` | 岗位池 | JD 列表 + 匹配评分 + 详情抽屉 |
| `/jobs/applications` | 投递管理 | 看板式状态流 + 时间线 |
| `/resume` | 简历工作台 | 版本管理 + 事实锚点 + 技能线 + 反捏造诊断 |
| `/interview` | 面试准备 | 弱点排名 + 面经记录 + 题库入口 |
| `/plan` | 施工计划 | 日历视图 + 进度条 + 滑窗决策 |
| `/questions` | 题库练习 | 覆盖矩阵 + 练习统计 + Quiz 模式 |
| `/knowledge` | 知识库 | RAG 搜索 + 问答界面 |
| `/projects` | 项目总览 | 项目卡片网格 + 状态筛选 |
| `/projects/[id]` | 项目详情 | 里程碑 + 证据链 + 实验记录 + README |
| `/phd` | 博士申请 | 导师匹配 + 时间线 + 材料清单 |
| `/agents` | Agent 工作台 | 多 Agent 状态 + 执行日志 + 重试 |

### 3.3 导航结构

```
GlobalNav（顶部栏，保持）:
  今日 | 求职（求职模式）| 学习 | 博士 | 概览 → 合并到今日

Sidebar（替代 SectionNav）:
  ┌──────────────────────────────────────┐
  │  🌙/☀️/⚡ 主题切换                    │
  │  📋 模式：求职中                       │
  │──────────────────────────────────────│
  │                                      │
  │  求职                                 │
  │    ├─ 作战看板    /jobs               │
  │    ├─ 岗位池      /jobs/pool          │
  │    ├─ 投递管理    /jobs/applications   │
  │    ├─ 简历        /resume             │
  │    └─ 面试准备    /interview           │
  │                                      │
  │  学习                                 │
  │    ├─ 施工计划    /plan               │
  │    ├─ 题库练习    /questions           │
  │    ├─ 知识库      /knowledge           │
  │    └─ 项目        /projects            │
  │                                      │
  │  博士                                 │
  │    └─ 申请追踪    /phd                │
  │                                      │
  │  系统                                 │
  │    └─ Agent 工作台 /agents             │
  └──────────────────────────────────────┘

CommandPalette（⌘K）:
  全局搜索页面、任务、技能、问题
```

### 3.4 页面职责详细定义

**`/today`（合并原 /dashboard）**
- 上半区：施工单（四件套 + 今日任务 + 学习目标）
- 下半区：五区概览（职业进度、技能雷达、当前位置、学术进度、ROI 任务、风险雷达）
- KPI 卡片区：任务完成率、就绪度、Agent 运行数、投递漏斗
- 快捷入口：常用页面的一键跳转

**`/jobs`（合并原 /reports）**
- 主视图：作战看板（倒计时 + 目标岗位 + 技能缺口 + 里程碑 + 漏斗）
- Tab：周报/日报（原 /reports 内容）

**`/projects/[id]（合并原 /evidence + /experiments）`**
- 项目信息 + 里程碑时间线
- Tab：证据链（原 /evidence）| 实验记录（原 /experiments）| README

---

## 4. 视觉设计语言

### 4.1 间距系统

```
--space-1: 4px      # 图标与文字间距
--space-2: 8px      # 紧凑元素间距
--space-3: 12px     # 行内元素间距
--space-4: 16px     # 卡片内 padding（紧凑）
--space-5: 20px     # 卡片内 padding（默认）
--space-6: 24px     # 区块间距
--space-8: 32px     # 大区块间距
--space-10: 40px    # 页面级间距
--space-12: 48px    # 页面底部留白
```

### 4.2 字体层级

```
display:    40px / -0.02em / 700    # 页面大标题
heading:    24px / -0.01em / 600    # 区块标题
title:      17px / -0.01em / 600    # 卡片标题
body:       15px / 0 / 400          # 正文
caption:    13px / 0 / 500          # 标签、辅助文字
micro:      11px / 0.02em / 600     # 微型标签（Badge、状态）
```

### 4.3 圆角

```
--radius-sm:   6px     # 小元素（Badge、Tag）
--radius-md:   10px    # 中等元素（Input、Button）
--radius-lg:   16px    # 卡片（Light/Dark）
--radius-xl:   20px    # 卡片（Neon，更大圆角）
--radius-pill: 999px   # 胶囊形（pill）
```

### 4.4 阴影

```
Light:
  shadow.card:     0 1px 3px rgba(0,0,0,0.06)
  shadow.elevated: 0 4px 16px rgba(0,0,0,0.12)

Dark:
  shadow.card:     0 0 0 1px rgba(255,255,255,0.06)
  shadow.elevated: 0 0 0 1px rgba(255,255,255,0.08), 0 8px 24px rgba(0,0,0,0.4)

Neon:
  shadow.card:     0 0 0 1px rgba(255,255,255,0.08), 0 4px 16px rgba(0,0,0,0.3)
  shadow.elevated: 0 0 0 1px rgba(255,255,255,0.1), 0 8px 32px rgba(0,0,0,0.5)
  shadow.glow:     0 0 40px rgba(139,92,246,0.15)
```

### 4.5 动效

```
# 状态过渡
transition-fast:    120ms ease-out    # 颜色、透明度
transition-base:    200ms ease-out    # 位移、尺寸
transition-slow:    300ms ease-in-out # 弹出层、展开

# 微交互
Card hover:         translateY(-2px) + shadow 加深（200ms）
Button press:       scale(0.98)（80ms）
Modal enter:        opacity 0→1 + scale(0.96→1)（200ms）
Sidebar expand:     width 64→240px（200ms ease-out）
Badge pulse:        opacity 0.6→1 循环（仅 Neon）
```

### 4.6 渐变与装饰（Neon 主题专属）

```
accent-gradient:    linear-gradient(135deg, #8B5CF6, #3B82F6)
card-glow:          0 0 40px rgba(139,92,246,0.1)
bg-grid:            repeating-linear-gradient(90deg, rgba(255,255,255,0.02) 0, rgba(255,255,255,0.02) 1px, transparent 1px, transparent 40px)
status-bar:         linear-gradient(90deg, #8B5CF6 0%, #3B82F6 50%, #10B981 100%)
```

### 4.7 主题差异总表

| 维度 | Light | Dark | Neon |
|------|-------|------|------|
| 圆角 | 12-16px | 12-16px | 16-24px |
| 阴影 | 柔和投影 | 微光边框 | 深层投影 + 光晕 |
| 渐变 | 无 | 无 | 强调色渐变 |
| 毛玻璃 | 无 | 无 | backdrop-filter |
| 动效强度 | 轻微 | 轻微 | 明显 |
| 信息密度 | 标准 | 标准 | 稍低 |
| 装饰元素 | 无 | 无 | 网格背景、状态条 |

---

## 5. 实施路线图

### Phase 1 — 主题系统与基础 Token（Day 1-2）

```
src/tokens/primitives.ts       # 原始色值、间距、圆角、字号
src/tokens/semantic.ts         # SemanticToken 类型接口
src/tokens/themes/light.ts     # Light 主题映射
src/tokens/themes/dark.ts      # Dark 主题映射
src/tokens/themes/neon.ts      # Neon 主题映射
src/theme/ThemeProvider.tsx     # React Context + data-theme 管理
src/theme/useTheme.ts          # hook
src/theme/ThemeSwitcher.tsx     # 切换 UI
src/theme/applyTheme.ts        # 注入 CSS 变量
src/app/globals.css            # 重写
```

验收：切换主题后所有页面颜色/阴影/圆角即时变化，无闪烁。

### Phase 2 — 原子组件（Day 3-6）

```
Day 3: Button, Badge, Tag, Tooltip
Day 4: Input, Select, Checkbox, Radio, Toggle
Day 5: Card, EmptyState, Skeleton
Day 6: Stat, ProgressBar, StepIndicator
```

### Phase 3 — 布局与导航组件（Day 7-9）

```
Day 7: Sidebar + Breadcrumb
Day 8: Tabs, Accordion, Modal, Drawer, Popover
Day 9: CommandPalette
```

验收：Sidebar 替代 SectionNav，所有页面在新导航下正常运行。

### Phase 4 — 数据可视化组件（Day 10-11）

```
Day 10: RadarChart（统一接口）, BarChart
Day 11: Timeline
```

### Phase 5 — 信息架构迁移（Day 12-15）

```
Day 12: 合并 /today + /dashboard → 新 /today
Day 13: 合并 /reports → /jobs Tab，合并 /evidence + /experiments → /projects/[id]
Day 14: Sidebar 替换 SectionNav，全局导航更新
Day 15: 删除 /jd 重定向，清理路由
```

### Phase 6 — 页面迁移（Day 16-22）

```
Day 16-17: /today
Day 18-19: /questions + /interview
Day 20-21: /jobs + /jobs/pool + /jobs/applications
Day 22:    /plan, /knowledge, /projects, /phd, /agents
```

### Phase 7 — 收尾（Day 23-25）

```
Day 23: 动效打磨
Day 24: 响应式验证（手机、平板、桌面）
Day 25: 暗色/Neon 主题全面验证 + 旧代码清理
```

总周期：~25 个工作日。

---

## 附录 A：现有组件迁移映射

| 旧组件 | 新组件 | 迁移方式 |
|--------|--------|----------|
| `ui/card.ts` (cardShell) | `Card` 组件 | 替换所有 `style={cardShell}` |
| `ui/status-pill.ts` | `Badge` variant | 替换所有 `pillStyle()` |
| `ui/page-shell.tsx` | 保留，内部用新组件 | 渐进替换 |
| `ui/skeleton.tsx` | `Skeleton` 组件 | 直接替换 |
| `ui/error-card.tsx` | `Card` variant="outlined" + accent.danger | 替换 |
| `SectionNav` | `Sidebar` | Phase 5 替换 |
| `Pill` (QuestionBoard) | `Badge` | Phase 6 替换 |
| `Bar` (QuestionBoard) | `ProgressBar` | Phase 6 替换 |

## 附录 B：CSS 变量迁移清单

现有 `globals.css` 中的 27+ 变量需要映射到新 token 系统：

| 现有变量 | 新 Token | 说明 |
|----------|----------|------|
| `--color-canvas` | `--surface-canvas` | 语义重命名 |
| `--color-card` | `--surface-card` | 语义重命名 |
| `--color-ink` | `--text-primary` | 语义重命名 |
| `--color-ink-80` | `--text-secondary` | 语义重命名 |
| `--color-ink-48` | `--text-muted` | 语义重命名 |
| `--color-hairline` | `--border-default` | 语义重命名 |
| `--color-primary` | `--accent-primary` | 语义重命名 |
| `--color-emerald` | `--accent-success` | 语义重命名 |
| `--color-amber` | `--accent-warning` | 语义重命名 |
| `--color-rose` | `--accent-danger` | 语义重命名 |
| `--radius-card-lg` | `--radius-lg` | 简化命名 |
| `--radius-item-md` | `--radius-md` | 简化命名 |
| `--radius-item-sm` | `--radius-sm` | 简化命名 |

迁移策略：Phase 1 保留旧变量作为别名（`--color-canvas: var(--surface-canvas)`），Phase 6 页面迁移时逐步替换引用，最后删除别名。
