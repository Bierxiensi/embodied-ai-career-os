# 带你学 · 第 0 课：Tokenizer → Embedding

> 入口：你刚问的那行 `tokenizer(sequence, return_tensors="pt")`。
> 定位：30 天计划 Day 1「Transformer 总体结构」的前置地基。先吃透这课，Day 1 的「走通数据流」才有支点。
> 格式：**概念 → 数学直觉 → PyTorch 代码 → HF 代码 → 面试题 → 小实验**。

---

## 1. 概念

模型只吃**数字**，文本必须先变成整数序列（token ids），再变成向量。整条链是：

```
文本 string
  → Tokenizer（切词 + 查表）→ token ids [int]
  → Embedding（查表）→ 向量矩阵 [seq_len, d_model]
  → Transformer 各层
```

你那行代码在做的只有前半段：

```python
tokenizer(sequence, return_tensors="pt")
#          └─文本      └─返回 PyTorch 张量（不是 list）
```

三个东西要从直觉上分清：
- **token**：模型眼里的最小单位（不一定是词，常是子词，如 `playing` → `play` + `##ing`）。
- **vocab**：所有可能的 token 集合，大小 `vocab_size`（Qwen3 约 15 万，BERT-base 约 3 万）。
- **embedding**：每个 token id 对应一行可学习的浮点向量，模型靠它把"离散符号"变成"连续语义空间里的点"。

---

## 2. 数学直觉

**为什么是子词（subword）而不是整词？**
词表若按整词，会遇到海量 OOV（未登录词）且稀疏。子词切分（BPE / WordPiece）把词拆到可控粒度：`unbelievable` → `un` + `##believ` + `##able`。好处：词表小、覆盖广、相似词共享前缀。

**Embedding 是什么运算？**
就是一个**查表**（lookup table），不是矩阵乘法：

```
embedding_matrix ∈ R^{vocab_size × d_model}
vector_i = embedding_matrix[token_id_i]      # 第 i 行
```

参数量 = `vocab_size × d_model`。例如 vocab=150000, d=1536 → 约 2.3 亿参数，占大模型权重不小一块。

**位置信息从哪来？**
Embedding 本身**不含顺序**。Transformer 靠 Position Embedding（或 RoPE，Day 3 讲）把"第几个位置"加进向量。先记住：token id 只表达"是什么词"，位置是另一路信号。

---

## 3. PyTorch 代码（手写，不调库）

```python
import torch, torch.nn as nn

vocab_size, d_model = 1000, 64
emb = nn.Embedding(vocab_size, d_model)   # 随机初始化查表

ids = torch.tensor([12, 45, 7, 12])        # 一个句子（4 个 token）
x = emb(ids)                               # shape: [4, 64]
print(x.shape)                             # torch.Size([4, 64])

# 关键直觉：同一个 id（如上面的两个 12）查出来的是同一行向量
print((x[0] == x[3]).all())                # tensor(True) → 查表，不是随机
```

这就是 Transformer 输入端的全部：一串 id → 一串向量。后面所有 Attention / FFN 都是在这个向量序列上做变换。

---

## 4. Hugging Face 代码（你那行的真实形态）

```python
from transformers import AutoTokenizer

# 用你目标体系里的模型（首次会下载 tokenizer 权重，约几 MB~几十 MB）
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B")

text = "把这张发票的投标人写进结构化字段"
out = tok(text, return_tensors="pt")       # ← 你问的这行

print(out["input_ids"].shape)              # [1, seq_len]（batch 维在前）
print(tok.convert_ids_to_tokens(out["input_ids"][0]))  # 看切成了哪些 token
print(out.keys())                          # input_ids / attention_mask（可能还有 token_type_ids）
```

三个返回字段要分清：
- `input_ids`：token 的整数 id 序列（喂给 embedding 的就是它）。
- `attention_mask`：哪些位置是真实 token（1）、哪些是 padding（0）——告诉 Attention"别看 padding"。
- `token_type_ids`：区分句子 A / B（BERT 类用；Decoder-only 的 Qwen 通常没有）。

**中英文 token 效率**（面试常考）：同样意思的中文比英文吃更多 token。跑一遍 `len(tok("你好"))` vs `len(tok("hello"))` 感受一下——这直接关系你以后做 VLM / 长上下文的成本。

---

## 5. 面试题（闭卷能答）

1. 为什么用子词（BPE/WordPiece）而不是按空格切词？OOV 怎么解？
2. Embedding 是矩阵乘法吗？参数量怎么算？
3. `[CLS]` / `[SEP]` 是干什么的？Decoder-only 模型还需要吗？
4. `attention_mask` 解决什么问题？没有它会怎样？
5. 为什么中文比英文"更费 token"？对推理成本意味着什么？
6. token id 相同 → 向量相同吗？位置信息在这一步进了向量吗？（答：没进，位置是另一路）

---

## 6. 小实验（今天就能做完）

- [ ] 用 `Qwen/Qwen3-0.6B`（或你本地已有的任意 tokenizer）跑一段中文简历片段，打印 `input_ids` 长度，和英文翻译版比 token 数，记下来。
- [ ] 手算：`vocab_size=151936, d_model=1536` 时 embedding 参数量（答案约 2.33 亿）。
- [ ] 改 `out = tok(text, padding=True, truncation=True, max_length=32, return_tensors="pt")`，观察 `attention_mask` 长什么样、padding 位是什么值。
- [ ] 把 `emb` 那段的 `x[0]==x[3]` 改成不同 id，确认"不同 id → 不同向量"。

> 完成后，Day 1 的「走通数据流 Token → Embedding → Position → Attention → FFN → ...」前两段就不再是黑箱了。

---

## 反思（Socratic）

你刚才问 `return_tensors="pt"` 时，真正卡的是哪一步——是"文本怎么变 id"，还是"id 怎么变向量"，还是"为什么非要 PyTorch 张量"？想清楚这个，下一课（Attention 的 QKV 从哪来）你就不会再被维度吓住。
