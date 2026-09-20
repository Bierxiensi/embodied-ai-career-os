# 带你学 · 第 2 课：位置编码 RoPE——位置怎么真正进向量

> 入口：第 1 课结尾的反思。"把 `x` 里第 1 和第 4 个位置调换，Attention 的 `out` 会变吗？"
> 答案（先给）：**会变。** 因为现代大模型用 **RoPE（旋转位置编码）** 把位置"拧"进了 Q/K 的旋转里——位置一旦和向量绑定，Attention 就不再是排列不变的了。这课拆 RoPE 到底怎么拧的。
> 定位：30 天计划 Day 1「Transformer 总体结构」第 3 段（Position）。Qwen / Llama 全系都用 RoPE。
> 格式：**概念 → 数学直觉 → PyTorch 代码 → HF 代码 → 面试题 → 小实验**。

---

## 1. 概念

第 0 课说过：Embedding **不含顺序**，token id 只表达"是什么词"。第 1 课的 Attention 只做"向量互相看"，它自己也**不关心顺序**——`Q @ Kᵀ` 对调换的行是对称的。如果不补位置信号，模型会把"狗咬人"和"人咬狗"当成同一句话。

补位置有两条历史路线：
- **绝对位置编码**（早期）：给第 m 个位置额外发一个向量 `p_m`，直接加到 `x_m` 上（`x_m + p_m`）。有正弦（sinusoidal）和可学习两种。问题：位置是"加"上去的，和内容的乘法交互弱，且难外推到比训练时更长的序列。
- **RoPE（旋转位置编码，现代主流）**：**不另发向量，而是把位置变成一道"旋转"**，直接作用在 Q 和 K 上。Qwen3 / Llama / Qwen2.5-VL 全是它。

**先停一下想：**为什么只转 Q 和 K，**不转 V**？V 是被聚合的"内容"，转了反而把内容语义搅乱；而 Attention 的分数只由 `Q·Kᵀ` 决定——只要分数带上相对位置，目的就达到了。记住这个，下面数学就不乱。

---

## 2. 数学直觉

**核心动作：把每个 token 的向量分成一对对维度，每对按一个角度旋转。**

设位置是 `m`，向量维度 `d` 被切成 `d/2` 对。第 `i` 对 `(x_{2i}, x_{2i+1})` 的旋转角：

```
θ_i = base^(-2i/d)          # base 通常 10000；Qwen 用 1_000_000（rope_theta）
φ(m) = m · θ_i              # 位置越靠后、维度越靠内，转得越多
```

旋转（标准 2D 旋转）：

```
x'_{2i}   = x_{2i}·cos φ(m) - x_{2i+1}·sin φ(m)
x'_{2i+1} = x_{2i}·sin φ(m) + x_{2i+1}·cos φ(m)
```

对所有对做完，得到"带位置 m 的旋转后向量" `R(m)·x`。

**RoPE 真正厉害的地方——相对位置自现：**

因为旋转矩阵是正交的、且 `R(m)ᵀ·R(n) = R(n−m)`，可以推出：

```
[R(m)·q]ᵀ · [R(n)·k]  =  qᵀ · R(n−m) · k
```

意思是：**旋转后 Q(m) 和 K(n) 的点积，只取决于 `n−m`（相对距离），不依赖绝对位置 m、n。** 这就是"相对位置编码"的本质——不是硬塞相对位置标签，而是旋转的数学性质让它自动浮现。

代价：V 不参与旋转（前面说过），所以"内容"留在原空间，只有"检索关系"带了位置。

---

## 3. PyTorch 代码（手写 RoPE + 验证"只依赖相对位置"）

```python
import torch

def rope_rotate(x, pos, base=10000.0):
    # x: [T, d]   pos: [T] 每个 token 的位置
    T, d = x.shape
    i = torch.arange(0, d, 2) / d            # [d/2]，第 i 对
    freqs = base ** (-i)                      # θ_i = base^(-2i/d)
    angles = pos[:, None] * freqs[None, :]     # [T, d/2] = m·θ_i
    cos, sin = torch.cos(angles), torch.sin(angles)

    x_even, x_odd = x[:, 0::2], x[:, 1::2]     # 偶数/奇数维
    out_even = x_even * cos - x_odd * sin
    out_odd  = x_even * sin + x_odd * cos
    out = torch.zeros_like(x)
    out[:, 0::2], out[:, 1::2] = out_even, out_odd
    return out

torch.manual_seed(0)
d = 8
q, k = torch.randn(d), torch.randn(d)

print("== 旋转后 Q(m)·K(n)，看是否只依赖 (n-m) ==")
for m in [0, 5, 10]:
    for n in [0, 5, 10]:
        qm = rope_rotate(q.unsqueeze(0), torch.tensor([m])).squeeze()
        kn = rope_rotate(k.unsqueeze(0), torch.tensor([n])).squeeze()
        print(f"  m={m:2d} n={n:2d} 差={n-m:2d}  dot={ (qm*kn).sum():.4f}")

# 你会看到：
#   (0,0) 与 (5,5) 与 (10,10) 的 dot 相等 → 差都是 0
#   (0,5) 与 (5,10) 的 dot 相等         → 差都是 5
# 证据：点积只由"相对距离"决定，与绝对位置无关。
```

**关键直觉（回应第 1 课反思）：** 位置不是"加"在向量上的附属品，而是"拧"进了 Q/K 的坐标系。同一份内容 `q`，放在位置 0 和位置 5，它的 Q 向量指向完全不同方向——所以 Attention 算分时天然知道"谁离谁多远"。这正解释了"换两个位置的 token，out 会变"。

---

## 4. Hugging Face 代码（看真实模型的 RoPE 配置）

RoPE 藏在模型内部（`modeling_qwen2.py` 的 `RotaryEmbedding`），你一般不直接调用，但要知道去哪看参数：

```python
from transformers import AutoConfig

cfg = AutoConfig.from_pretrained("Qwen/Qwen3-0.6B")
print("rope_theta       =", cfg.rope_theta)          # Qwen3 默认 1_000_000
print("max_position_embeddings =", cfg.max_position_embeddings)  # 训练时的最大长度
print("hidden_size      =", cfg.hidden_size)         # d，RoPE 在此维度上旋转
print("head_dim         =", getattr(cfg, "head_dim", cfg.hidden_size // cfg.num_attention_heads))
```

几个实战要点：
- **`rope_theta` 越大**，低频维度转得越慢 → 长序列里远距离位置仍能区分，所以大模型爱用大 theta。
- **超出 `max_position_embeddings`**：直接 RoPE 会"转飞"（角度超出训练分布）→ 长上下文要靠 **NTK-aware 缩放 / YaRN**（Qwen 的 Long 版就是这么来的）。面试常被追问"怎么扩上下文"，根在这。
- 在模型里，RoPE **只作用在 Attention 的 Q/K 上**，V 不转——印证第 1 节结论。

---

## 5. 面试题（闭卷能答）

1. **Attention 本身知道顺序吗？不补位置会怎样？** 答：不知道；"狗咬人""人咬狗"会被当同句。
2. **绝对位置编码 vs RoPE 的区别？** 答：前者把位置向量加到 x 上，弱交互、难外推；后者把位置变成 Q/K 的旋转，相对位置自现、易外推。
3. **RoPE 为什么只转 Q/K、不转 V？** 答：分数只由 QKᵀ 决定，转 Q/K 就让分数带相对位置；V 是内容，转了搅乱语义。
4. **RoPE 怎么做到"相对位置"？** 答：旋转正交且 `R(m)ᵀR(n)=R(n−m)`，推出点积只依赖 `n−m`。
5. **`rope_theta` 什么用？超长上下文怎么扩？** 答：控制低频旋转速度，越大越利长序列；超训练长度用 NTK-aware / YaRN 缩放。
6. **为什么 Qwen 用 RoPE 而非 sinusoidal？** 答：RoPE 的相对位置性质 + 外推友好，是目前 decoder-only 主流选择。

---

## 6. 小实验（今天就能做完）

- [ ] 跑第 3 节代码，把输出抄下来：确认 `(0,0)`、`(5,5)`、`(10,10)` 三行 dot 相等，`(0,5)` 与 `(5,10)` 相等——**亲手证明"只依赖差值"**。
- [ ] 把 `base` 从 `10000` 改成 `1000000`，重跑，观察角度 `angles` 整体变小——**体会大 theta 让旋转变慢、长序列更可分**。
- [ ] 把 `d` 改成 `4`，确认 `i = arange(0,4,2)/4 = [0, 0.5]`，只有 2 对维度被旋转——**RoPE 是"成对旋转"，维度必须偶分**。
- [ ] 回到第 1 课的 `attn` 矩阵：在计算 `scores = Q@Kᵀ` **之前**，对 Q、K 各做一次 `rope_rotate`，再算注意力——看"它"对"小红"的注意力是否比不转时更准（位置帮检索定位）。

> 完成后，Day 1 数据流 `Token → Embedding → Position → Attention → ...` 的前四段全通了。每个 token 现在同时带"内容（x）"和"位置（RoPE 拧进 Q/K）"，Attention 才算真正会读句子。

---

## 反思（Socratic）

到第 2 课，一个 Transformer 层里你已经看清了三件事：Embedding 给内容、RoPE 给位置、Attention 让 token 按相关度混合。**但注意——Attention 只是"把别人的向量按权重揉进来"，它本身没有对"单个 token 的内容"做任何非线性加工。** 那模型靠什么学会"如果…那么…""否定""组合"这些需要逐点变换的逻辑？——下一课 **FFN（前馈网络）**：它不做 token 间混合，只对**每个 token 独立**做"升维→非线性→降维"。想清楚"为什么 Attention 负责混合、FFN 负责变换"，你就抓住了 Transformer block 的双引擎设计哲学。
