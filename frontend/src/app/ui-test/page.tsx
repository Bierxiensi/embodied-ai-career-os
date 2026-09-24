"use client";

import {
  Button, Badge, Tag, Input, Select, Checkbox, Radio, Toggle, Tooltip,
  Card, EmptyState, Stat, ProgressBar, StepIndicator,
  Breadcrumb, Tabs, Accordion, Modal, Drawer, Popover, Sidebar, CommandPalette,
} from "@/components/ui";
import { useState } from "react";

export default function UITestPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [checkboxVal, setCheckboxVal] = useState(false);
  const [radioVal, setRadioVal] = useState("a");
  const [toggleVal, setToggleVal] = useState(false);
  const [selectVal, setSelectVal] = useState("");

  return (
    <main style={{ padding: 40, maxWidth: 900, margin: "0 auto" }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 32 }}>UI 组件测试</h1>
      <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 24, padding: "8px 12px", background: "var(--surface-card)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)" }}>
        💡 使用顶栏的 ThemeSwitcher 切换 3 套主题（Light / Dark / Neon）验证所有组件表现。
      </p>

      {/* Button */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Button</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="primary" size="sm">Small</Button>
          <Button variant="primary" size="lg">Large</Button>
          <Button variant="primary" loading>Loading</Button>
        </div>
      </section>

      {/* Badge & Tag */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Badge & Tag</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Badge variant="success">成功</Badge>
          <Badge variant="warning">警告</Badge>
          <Badge variant="danger">危险</Badge>
          <Badge variant="primary">主色</Badge>
          <Badge variant="success" dot>带点</Badge>
          <Tag closable onClose={() => {}}>可关闭</Tag>
        </div>
      </section>

      {/* Input */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Input</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 320 }}>
          <Input placeholder="默认输入框" />
          <Input placeholder="带前缀" prefix="🔍" />
          <Input placeholder="错误态" error="此项必填" />
          <Input placeholder="禁用" disabled />
        </div>
      </section>

      {/* Select */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Select</h2>
        <div style={{ maxWidth: 320 }}>
          <Select
            options={[
              { value: "a", label: "选项 A" },
              { value: "b", label: "选项 B" },
              { value: "c", label: "选项 C" },
            ]}
            searchable
            value={selectVal}
            onChange={setSelectVal}
          />
        </div>
      </section>

      {/* Checkbox, Radio, Toggle */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Form Controls</h2>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <Checkbox label="复选框" checked={checkboxVal} onChange={(e) => setCheckboxVal(e.target.checked)} />
          <Radio label="选项 A" name="test" value="a" checked={radioVal === "a"} onChange={() => setRadioVal("a")} />
          <Radio label="选项 B" name="test" value="b" checked={radioVal === "b"} onChange={() => setRadioVal("b")} />
          <Toggle checked={toggleVal} onChange={setToggleVal} />
        </div>
      </section>

      {/* Tooltip */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Tooltip</h2>
        <Tooltip content="这是提示内容">
          <Button variant="secondary">Hover me</Button>
        </Tooltip>
      </section>

      {/* Card */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Card</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
          <Card variant="default" hoverable>
            <p style={{ margin: 0 }}>Default Card</p>
          </Card>
          <Card variant="elevated">
            <p style={{ margin: 0 }}>Elevated Card</p>
          </Card>
          <Card variant="outlined">
            <p style={{ margin: 0 }}>Outlined Card</p>
          </Card>
          <Card variant="ghost">
            <p style={{ margin: 0 }}>Ghost Card</p>
          </Card>
        </div>
      </section>

      {/* EmptyState */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>EmptyState</h2>
        <Card>
          <EmptyState icon="📭" title="暂无数据" description="这里什么都没有" action={{ label: "刷新", onClick: () => {} }} />
        </Card>
      </section>

      {/* Stat */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Stat</h2>
        <div style={{ display: "flex", gap: 32 }}>
          <Stat label="就绪度" value="85%" change={{ value: 12, direction: "up" }} />
          <Stat label="投递数" value={42} change={{ value: 5, direction: "down" }} />
        </div>
      </section>

      {/* ProgressBar */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>ProgressBar</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 400 }}>
          <ProgressBar value={65} showLabel />
          <ProgressBar value={90} variant="success" />
          <ProgressBar value={30} variant="danger" size="sm" />
        </div>
      </section>

      {/* StepIndicator */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>StepIndicator</h2>
        <StepIndicator
          steps={[
            { title: "已完成", status: "done" },
            { title: "进行中", status: "current" },
            { title: "待处理", status: "pending" },
          ]}
        />
      </section>

      {/* Breadcrumb */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Breadcrumb</h2>
        <Breadcrumb items={[{ href: "/", label: "首页" }, { href: "/jobs", label: "求职" }, { label: "岗位池" }]} />
      </section>

      {/* Tabs */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Tabs</h2>
        <Tabs
          items={[
            { key: "a", label: "标签 A", content: <p>内容 A</p> },
            { key: "b", label: "标签 B", content: <p>内容 B</p> },
          ]}
        />
      </section>

      {/* Accordion */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Accordion</h2>
        <Accordion
          items={[
            { key: "1", title: "展开项 1", content: <p>内容 1</p> },
            { key: "2", title: "展开项 2", content: <p>内容 2</p> },
          ]}
        />
      </section>

      {/* Modal, Drawer, CommandPalette */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>Overlay Components</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <Button variant="primary" onClick={() => setModalOpen(true)}>打开 Modal</Button>
          <Button variant="secondary" onClick={() => setDrawerOpen(true)}>打开 Drawer</Button>
          <Button variant="ghost" onClick={() => setCmdOpen(true)}>打开 CommandPalette</Button>
        </div>

        <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="示例弹窗">
          <p>Modal 内容</p>
        </Modal>

        <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="示例抽屉">
          <p>Drawer 内容</p>
        </Drawer>

        <CommandPalette
          open={cmdOpen}
          onClose={() => setCmdOpen(false)}
          groups={[
            {
              label: "页面",
              items: [
                { id: "1", label: "今日", icon: "📋", action: () => {} },
                { id: "2", label: "求职", icon: "💼", action: () => {} },
              ],
            },
          ]}
        />
      </section>
    </main>
  );
}
