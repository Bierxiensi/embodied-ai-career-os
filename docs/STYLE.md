# STYLE —— 加模块前的对照门槛（2026-09-24）

> 来源：spec 5.3。不是建议，是门槛：新功能开工前逐条对照，任一不过就先改设计。

1. **SQLite 单文件**，不引入第二个数据库/向量库实例（现有 ChromaDB/向量表除外）。
2. **不新增平行权威域**：策略单一真源在 `backend/app/core/` 纯函数层（skill_profile /
   target_roles / plan_30d / capacity / evidence）；改口径改这里，不在业务层各存一份。
3. **加端点前先问**：能否并入三类 intake（学习回收 / 半自动事实 / 主动登记）？
   能并就并。活跃写端点预算 **≤25**（口径=OpenAPI 文档面），同口径内只减不增
   （`test_active_write_endpoints.py` 守）。**隐藏但 UI 仍调用**的写端点不再挂
   「撤表单」支线清偿账：同一文件的 `HIDDEN_BUT_LIVE` 显式清单逐条登记
   （端点 → 一行为什么留着），并有测试钉死清单键集——以后要多一个 schema 外
   且前端还在打的写口，必须同时改清单与该键集断言；撤表单后按该文件 docstring
   的 grep 配方重算键集（撤 UI 但留数据的 service 函数零 importer，不算 live）。
4. **写死在前端文案里的数字是负债**：写"资源均来自资源锁"，不写"这 N 类"。
5. **降级必须可见**：LLM/嵌入/生成任一降级，UI 必须有徽标（answer_mode / generation_mode 同款）。
6. **拒绝线**（明文不做）：自动投递/爬虫反指纹、Gmail 全量授权、AGPL 代码复制、
   第五条产品线、未经人审的 AI 直写事实。
7. **AI 改码契约**：`docs/superpowers/specs/*.md` 中标"契约"的接口签名不得静默变更；
   prompt 变更跑 `test_persona_prompts.py`。
8. **提交纪律**：`git add` 显式路径，禁止 `git add -A`；工作区有他人改动时只提交自己的文件。
9. **口径登记**：同一语义允许两套口径并存，前提是**命名各自如实**：
   server 聚合窗口 = 滚动 24h（naive-UTC-safe，`GET /api/today` 的 `learning_logs_24h`）；
   UI「今日」= 本地日历日（frontend `isToday`）。二者不得互相当对方用，
   新增消费端点/组件前先在这里登记窗口口径。
