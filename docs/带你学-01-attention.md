# 带你学 · 第 1 课：Attention 的 QKV 从哪来

> 入口：第 0 课停在 `x = emb(ids)`，shape 是 `[seq_len, d_model]` 的一串向量。
> 定位：30 天计划 Day 1「Transformer 总体结构」的核心齿轮。吃透这课，"Q/K/V 维度吓人"的错觉就破了。
> 格式：**概念 → 数学直觉 → PyTorch 代码 → HF 代码 → 面试题 → 小实验**。

---

## 1. 概念

第 0 课那串向量 `x` 有个致命缺陷：**每个 token 是孤立的**。第 3 个位置的向量不知道第 1、第 5 个位置是什么。但语言是关系的——"它"指代谁、"把 A 写进 B"里 A/B 谁主谁宾，都靠 token 之间互相"看"。

Self-Attention 干的事就一句话：**让每个 token 去和序列里所有 token 交换信息，按相关度加权揉成一串新向量**。

那么"怎么看、看谁、看多少"由谁决定？——由 **Q / K / V** 三个角色决定。先建立隐喻（后面会拆穿它只是隐喻）：

- **Q（Query，查询）**："我想找什么样的信息？"
- **K（Key，键）**："我能提供什么标签，供别人检索我？"
- **V（Value，值）**："我被检索到时，实际贡献的内容是什么？"

一个 token 拿自己的 Q 去和所有 token 的 K 比相似度 → 相似度高的，就多拿一点对方的 V。

**先停一下想：**如果 Q/K/V 是三个"独立学出来的东西"，那参数量岂不是爆炸？而且它们和输入 `x` 什么关系？——这是本课要拆穿的核心错觉。

---

## 2. 数学直觉

**QKV 到底从哪来？**

答案最反直觉也最省参数量：**它们都来自同一个输入 `x`，各过一道可学习线性变换**（本质和第 0 课的 `nn.Embedding` 一样，是线性投影，不是魔法）：

```
Q = x · W_Q        # W_Q ∈ R^{d × d_k}
K = x · W_K        # W_K ∈ R^{d × d_k}
V = x · W_V        # W_V ∈ R^{d × d_k}
```

也就是说：**没有"三套独立语义"，只有"同一份向量被三种方式重新表达"**。Q/K 同源，所以"每个 token 既是提问者，又是对别人开放的被检索键"——这正是 self-attention 里 "self" 的意思。

**打分与加权（单头）：**

```
scores = Q · Kᵀ / √d_k        # [T, T]，每个格子 = "token i 对 token j 的关注分"
attn   = softmax(scores, dim=-1)   # 每行和=1，变成"注意力分配比例"
out    = attn · V              # [T, d_k]，按分配比例把 V 揉起来
```

**为什么要除以 √d_k？**

Q·K 的每一项是一个长度为 `d_k` 的点积，是 `d_k` 个 ~1 方差项相加 → 方差随 `d_k` 放大。`d_k` 一大，分数动辄几十上百，softmax 直接"饱和"（某项≈1、其余≈0）→ 梯度≈0，学不动。除以 √d_k 把方差拉回 O(1)，softmax 才有区分度。**这是面试高频题，记住"为防止 softmax 饱和、保持梯度"就够。**

**多头（Multi-Head）在干什么？**

把 `d` 切成 `h` 个头，每头只看 `d_k = d/h` 维的 subspace，各自算一遍上面的流程，再把 `h` 个结果拼起来过一道 `W_O` 投影回 `d`。直觉：让不同头关注不同关系（头 A 管语法、头 B 管指代、头 C 管远距离依赖）。**头数 h 不影响总维度 d，只把 d 平分。**

**因果掩码（causal mask）：**

Decoder-only 模型（Qwen 等）生成时是"从左到右"的，第 i 个 token 不能偷看第 i+1 个之后的。实现：把 `scores` 里 `j > i` 的位置填 `-inf`，softmax 后那些位置权重=0。这就是为什么你打印注意力矩阵会看到上三角全 0。

---

## 3. PyTorch 代码（手写单头 + 因果掩码）

```python
import torch, torch.nn as nn, torch.nn.functional as F

# x：假设已过 embedding，shape [batch=1, seq=T, d]
T, d = 5, 16
x = torch.randn(1, T, d)

# QKV 从哪来？—— 三个独立的可学习线性投影，输入都是同一个 x（bias=False 更纯粹）
W_Q = nn.Linear(d, d, bias=False)
W_K = nn.Linear(d, d, bias=False)
W_V = nn.Linear(d, d, bias=False)

Q = W_Q(x)   # [1, T, d]
K = W_K(x)   # [1, T, d]
V = W_V(x)   # [1, T, d]
print(Q.shape, K.shape, V.shape)   # 都是 torch.Size([1, 5, 16])

# 打分：每个 token 的 Q 和所有 token 的 K 做点积
scores = Q @ K.transpose(-2, -1) / (d ** 0.5)   # [1, T, T]
print("原始分数矩阵（上三角也有值，还没遮）：")
print(scores[0].detach().round(2))

# 因果掩码：只看自己及左边（上三角填 -inf）
mask = torch.triu(torch.ones(T, T), diagonal=1).bool()
scores = scores.masked_fill(mask, float('-inf'))

attn = F.softmax(scores, dim=-1)   # 每行和=1，上三角=0
out  = attn @ V                    # [1, T, d]
print("注意力权重（每行和=1，上三角=0）：")
print(attn[0].detach().round(2))
print("输出 shape:", out.shape)    # torch.Size([1, 5, 16]) —— 和第 0 课的 x 同形！
```

**关键直觉（回应第 0 课钩子）：** 维度吓人，是因为第一次见 `Q = x @ W_Q` 还不习惯。但它和第 0 课的 `emb(ids)` 是**同类操作**——都是"向量 × 可学习矩阵"。`out` 的 shape 和输入 `x` 一模一样，Transformer 才能一层层叠上去。QKV 不是新维度怪物，是 `x` 的三次线性变身。

---

## 4. Hugging Face 代码（看真实模型的注意力）

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B")
# output_attentions=True 才会返回每一层的注意力矩阵
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen3-0.6B", output_attentions=True, torch_dtype="auto"
)

ids = tok("猫坐在垫子上，它很舒服", return_tensors="pt")
out = model(**ids, output_attentions=True)

# out.attentions 是 tuple：每层一个 [batch, heads, T, T]
print("层数:", len(out.attentions))
print("第 0 层注意力 shape:", out.attentions[0].shape)   # [1, n_heads, T, T]
```

打印出来你会看到：
- 第 1 维是 **头数**（Qwen3-0.6B 是 16 头），每头一份 `[T, T]` 矩阵。
- 同一个词（如"它"）在不同头上注意的对象**不一样**——这正是多头存在的证据。
- 上三角恒为 0（因果掩码生效）。

> 注：0.6B 在 CPU 也能跑，只是慢；有卡就 `model.to("cuda")`。这步是"看见真实注意力"，可选，但强烈建议做一次——抽象和具象对上了，后面看 VLM 的多模态注意力才不会慌。

---

## 5. 面试题（闭卷能答）

1. **Q/K/V 从哪来？** 答：同一个输入 `x` 过三道独立可学习线性投影，不是三套独立语义。
2. **为什么除以 √d_k？** 答：把点积方差拉回 O(1)，防止 softmax 饱和、梯度消失。
3. **Multi-Head 的作用？头数 h 改变总维度 d 吗？** 答：让不同头关注不同关系子空间；h 只把 d 平分，不改总维度。
4. **因果掩码解决什么？** 答：Decoder-only 生成时不能偷看未来 token；把 `j>i` 填 -inf。
5. **Self-Attention 和 Cross-Attention 区别？** 答：self 的 Q/K/V 都来自同一 `x`；cross 的 Q 来自解码侧、`K/V` 来自编码侧（VLM 里文本-图像对齐就是这种，Day 3 讲）。
6. **Attention 的输出 shape 和输入一样吗？为什么这很重要？** 答：一样（经 W_O 投影回 d），所以能堆叠成深层网络。

---

## 6. 小实验（今天就能做完）

- [ ] 跑第 3 节代码，把 `attn[0]` 打印出来，指给"自己"看：第 0 行只能 attend 第 0 列（因果），最后一行能 attend 全部——**直观感受因果掩码**。
- [ ] 把 `scores = Q @ K.transpose(-2,-1) / (d**0.5)` 的 `/ (d**0.5)` 去掉（或改成 `/ 1`），重跑，观察 softmax 是不是变得"非 0 即 1"、梯度信息丢失——**亲手验证 √d_k 的必要性**。
- [ ] 把 `T, d = 5, 16` 改成 `T=8`，看 `scores` 从 5×5 变成 8×8，确认维度随序列长度走、不随 d_k 卡死。
- [ ] 跑第 4 节 HF 代码，挑一句含代词的中文（"小明给了小红一本书，她很高兴"），看"她"那个位置的注意力是不是明显偏向"小红"——**看模型真的在"指代消解"**。

> 完成后，Day 1 数据流 `Token → Embedding → Attention → ...` 的前三段全通了。剩下 Position（位置怎么进向量）、FFN、Residual/Norm、LM Head，下一课接着拆。

---

## 反思（Socratic）

你第 0 课卡的是"文本怎么变向量"，这课拆的是"向量怎么互相看"。现在问自己一个更深的：**Attention 让 token 交换了信息，但它知道"顺序"吗？** 把 `x` 里第 1 和第 4 个位置调换，Attention 算出来的 `out` 会变吗？——如果会变，是为什么变的；如果不变，那"顺序"这路信号，Transformer 到底靠谁补上？想清楚这个，下一课（位置编码 RoPE：位置怎么真正进向量）你就知道为什么第 0 课说"位置是另一路信号"了。
