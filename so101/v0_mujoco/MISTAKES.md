# SO101 V0 错题集

> 记录踩过的坑、根因分析、排查思路，供回顾复盘。
> 每一条都包含：现象 → 根因 → 排查步骤 → 修复方案 → 预防口诀。

---

## 坑 1：geom 终点和子 body pos 不对齐

### 现象
```
WARNING: Nan, Inf or huge value in QACC at DOF 0. The simulation is unstable.
```
设任何非零 ctrl，8 步内仿真爆炸，qpos 全变 0°。

### 根因
[so101_arm.xml#L48](file:///d:/work/embodied-ai-career-os/so101/v0_mujoco/so101_arm.xml#L48) 中 wrist_roll 的 `pos="0 0 0.5"`，但 forearm geom 终点是 `0 0 0.24`。
**子 body 悬空在父 geom 之外 0.26m**，质量挂在远处 → 重力矩巨大 + 惯量极小 → 高频振荡 → NaN。

### 排查步骤
1. 画"接龙表"，逐行检查 `父 geom fromto 终点 == 子 body pos`
2. 打印 `data.qacc`，如果 > 1000 rad/s² 说明有问题
3. 打印 `model.body_inertia`，如果某 body 惯量 < 1e-4 说明太小

### 修复
```xml
<!-- 错: pos="0 0 0.5"  悬空 -->
<!-- 对: pos="0 0 0.24" 接上 forearm geom 终点 -->
<body name="wrist_roll" pos="0 0 0.24">
```

### 预防口诀
> **接龙表法**：每加一个 body，先检查上一个 body 的 geom 终点坐标，新 body 的 pos 必须完全一致。

---

## 坑 2：actual 永远是 0°（真正根因：kp 太猛 → Mujoco 不稳定保护复位）

### 现象
```
WARNING: Nan, Inf or huge value in QACC at DOF 3. The simulation is unstable.
Time = 0.0140.
>>> 段 1: Home → Reach out
    target=[30.0°,-30.0°, 30.0°, 60.0°]  actual=[0.00°, 0.00°, 0.00°, 0.00°]
```
打印 actual 永远是 0°，但 target 看起来是对的。

### 根因
这是 3 个 BUG 叠加的"连环炸"，最后触发了 Mujoco 的保护机制：

1. **接龙错位** [L48](file:///d:/work/embodied-ai-career-os/so101/v0_mujoco/so101_arm.xml#L48)：`pos="0 0 0.5"` 挂在 forearm 末端之外 0.26m
   → 额外重力矩
2. **惯量极小** [L51](file:///d:/work/embodied-ai-career-os/so101/v0_mujoco/so101_arm.xml#L51)：wrist geom radius=0.015m，惯量 I=3.5×10⁻⁴
3. **kp 太猛** [L69](file:///d:/work/embodied-ai-career-os/so101/v0_mujoco/so101_arm.xml#L69)：kp=40 对 I=3.5e-4 太硬
   → qacc 第一步就飙升到 9560 → -59239 → 361558 → 1,630,823 → 6,722,653 rad/s²
   → 第 5 步 qpos 飞到 998° 远超物理极限
   → Mujoco 检测到不稳定，**把 qpos/qvel 全部强行复位为 0**
   → 后续 step 不再更新，actual 永远是 0°

**容易误解的点**：actual=0° 不是"没动"，是"动太快炸了然后被复位为 0"！WARNING 信号就是证据。

### 排查步骤（按顺序）
1. **看 WARNING**：有 `Nan/Inf in QACC` 吗？如果有，说明已经爆炸保护了
2. **跑一步就查 qacc**：设小 ctrl（比如 0.1rad），跑一步 step 后看 `data.qacc`
   - qacc < 1000 → 正常
   - qacc > 1000 → 不稳定 → 找 qacc 最大的那个 DOF（通常是惯量最小的关节）
3. **打印惯量**：`print(model.body_inertia)`，看哪个 body 惯量最小
4. **画接龙表**：逐行检查 `父 geom fromto 终点 == 子 body pos`

### 修复
```xml
<!-- 修复 1: 接龙对齐 -->
<body name="wrist_roll" pos="0 0 0.24">  <!-- 从 0 0 0.5 改到 0 0 0.24 -->

<!-- 修复 2: 增大惯量（增大 geom radius） -->
<geom type="cylinder" size="0.04 0.1" .../>  <!-- 从 0.015 改到 0.04 -->

<!-- 修复 3: 降低 kp/kv（小零件配小 kp） -->
<position name="wrist_roll" joint="wrist_roll_pitch" kp="5" kv="1"/>  <!-- 从 40/3 改到 5/1 -->
```

### 预防口诀
> **惯量×10 ≈ 最大 kp，kv ≈ kp/5**。接龙表、qacc、惯量——排查三件套。

---

## 坑 3：(已合并到坑 2)

---

## 坑 4：ctrlrange 的正确认识（★修正了之前的错误理解★）

### 修正
**Mujoco 的 position actuator 不会按 ctrlrange 强行裁剪 ctrl！**

我做了 3 组对比实验：
- 显式 `ctrlrange="0 0"` → ctrl=1.0 仍然产生力矩，qpos 跑到 57° ✅ 动了
- 不写 ctrlrange（默认 [0,0]）→ 同样动了 ✅
- 显式 `ctrlrange="-1.57 1.57"` → 同样动了 ✅

**所以：actual=0° 和 ctrlrange=[0,0] 没有关系！别再被误导。**

### ctrlrange 真正的作用

ctrlrange 是**"建议范围/参考边界"**，不是硬限制：
1. 规范文档：一眼看出这个 actuator 推的范围和 joint range 对应
2. 外部控制器用：RL 策略、MPC、优化器等会自动把 ctrl 限制在 ctrlrange 内
3. 真实舵机映射：实际舵机 PWM 有限范围，ctrlrange 是它在仿真里的对应

### 为什么还要设置？
虽然 Mujoco 不硬裁，但 **ctrlrange 必须和 joint range 设成一致（弧度值）**，这是行业最佳实践：

```xml
<!-- 关节 range="-90 90" 度 → ctrlrange="-1.57 1.57" 弧度 -->
<!-- 关节 range="0 135" 度 → ctrlrange="0 2.36" 弧度 -->
```

### 预防口诀
> **ctrlrange = joint range**（弧度值，保持一致）。它是最佳实践，不是硬限制。

---

## 坑 5：(已合并到坑 4)

---

## 知识点速查表

| 概念 | 公式/属性 | 说明/稳定条件 |
|------|----------|--------------|
| 惯量 I | Mujoco 按 geom 自动算 | 圆柱 I ≈ (1/12)m(3r²+h²) |
| 角加速度 | `data.qacc` | < 1000 rad/s² 才安全 |
| 自然频率 | ω = √(kp/I) | ω·dt < 0.1（稳定条件） |
| PD 控制 | 力矩 = kp×(ctrl−qpos) − kv×qvel | 力=弹簧+刹车；kp太大→振荡 |
| ctrlrange | `model.actuator_ctrlrange` | 建议范围，不强制裁剪；要和 joint range 匹配 |
| 接龙规则 | 父 geom fromto 终点 = 子 body pos | 否则悬空 → 重力矩放大 |
| Mujoco 不稳定保护 | 出现 NaN qacc 后自动复位 qpos=0 | 实际现象是 actual 永远 0° |

---

## 调试工具箱

```python
# 一键诊断脚本
import mujoco, numpy as np

model = mujoco.MjModel.from_xml_path('so101_arm.xml')
data = mujoco.MjData(model)

print("=== 诊断 ===")
print(f"关节数: {model.njnt}")
print(f"执行器数: {model.nu}")
print(f"joint range: {np.degrees(model.jnt_range)}")
print(f"ctrlrange:  {model.actuator_ctrlrange}")
print()
print("=== 惯量 ===")
for i in range(model.nbody):
    print(f"  body {i} ({model.body(i).name}): mass={model.body_mass[i]:.4f}, inertia={model.body_inertia[i]}")
print()
print("=== 稳定性测试 ===")
data.ctrl[:] = [0.1] * model.nu
for step in range(100):
    mujoco.mj_step(model, data)
print(f"qacc: {data.qacc}")
print(f"qpos (度): {np.degrees(data.qpos)}")
print(f"稳定: {not np.any(np.isnan(data.qpos))}")
```
