---
name: doc-reading-loop
description: 使用 Codex 驱动文档研究闭环：自动执行“计划-执行-评估”多轮探索，在关键节点条件化暂停询问用户，并沉淀结构化 JSON/Markdown 过程产物。适用于从种子链接出发、围绕目标持续探索文档且暂不构建完整 CLI 工具的场景。
---

# 文档阅读闭环

## 何时使用

当用户希望：
1. 从一个或多个种子链接出发，围绕明确目标持续探索文档。
2. 通过“计划 -> 执行 -> 评估”进行迭代探索。
3. 默认自动推进轮次，仅在关键决策点暂停。
4. 同时保留机器可读（JSON）和人类可读（Markdown）的全过程材料。
5. 输出具有可追溯证据、对比深度和可执行建议的研究报告。

当用户只需要对已提供文本做一次性摘要时，不使用本 skill。

## 输入参数

收集并确认以下输入：
1. `goal`：要完成的信息目标。
2. `seedUrls`：初始链接列表。
3. `workspaceRoot`：任务工作目录（默认 `/Users/huanghao/workspace/learning/research/reading-workspace`）。
4. `depthLevel`：深度级别（`L1|L2|L3`）。
5. `focusAxes`：关注维度列表（例如 `skills,memory,tools,governance`）。
6. `outputStyle`：输出风格（`overview|comparison|decision-brief|audit`）。

默认值：
- `depthLevel=L3`
- `focusAxes=[]`
- `outputStyle=comparison`

深度定义：
- `L1`：快速综述（事实清单 + 基础结论）。
- `L2`：结构化对比（证据支撑 + 边界条件 + 建议）。
- `L3`：研究级报告（反证、置信度、迁移方案、风险评估）。

## 运行模式

1. 在 `<workspaceRoot>` 下创建任务文件。
2. 自动执行多轮流程。
3. 仅在命中 `ASK_USER` 条件时暂停。
4. 收到用户回复后继续执行。

## 登录态处理（关键）

每次执行前先做登录态检查，规则固定如下：
1. 默认使用单一持久化浏览器目录：`<workspaceRoot>/sessions/browser-profile/`。
2. 每次执行都直接复用该目录启动浏览器上下文（包含所有已登录站点状态）。
3. 若访问种子链接仍跳登录：启动可见浏览器，让用户扫码/登录，并继续使用同一目录。
4. 用户关闭浏览器后，立刻重试种子链接；可访问则继续任务，不可访问则触发 `ASK_USER`。
5. `sessions/<domain>.json` 改为可选调试产物，不作为主路径依赖。

执行要求：
1. 登录成功/失败必须写入 `timeline.jsonl`（如 `SESSION_SAVED`、`AUTH_REDIRECT_VERIFIED`、`ASK_USER`）。
2. 若因登录阻塞，任务状态置为 `WAIT_USER`；恢复后置回 `RUNNING`。

## 产物约定

创建/更新以下文件：

```txt
<workspaceRoot>
  sessions/browser-profile/
  sessions/<domain>.json (optional)
  tasks/<taskId>/
    task.json
    human/
      README.md
      reading-inventory.md
      plan-changes.md
      report.md
      round-XX-summary.md
      citation-index.md
    plan/
      plan.vN.json
    rounds/
      round-XX-summary.json
    evidence/evidence.json
    search/search-log.json
    cache/pages/<urlHash>.json
    logs/timeline.jsonl
```

规则：
- 给人读的 Markdown 集中放在 `tasks/<taskId>/human/`。
- `human/report.md` 中关键结论必须“就地引用”原文链接，不允许只在文末集中列源。

## 每轮执行协议

每一轮都执行：
1. 计划：生成 `plan.vN.json` 和 `human/plan.vN.md`，包含优先级与理由。
2. 执行：按计划读取页面（先校验登录态），严格遵守“先查缓存、后请求远端”规则，抽取证据并更新读取文件。
3. 反证：执行一轮“冲突检索”，主动寻找与当前结论冲突/削弱的证据，并写入 `evidence/evidence.json` 的 `counterEvidence` 字段。
4. 评估：同时评估覆盖度和洞察完成度，给出 `continue | stop | blocked | ask_user`。
5. 记录：
   - 更新 `human/plan-changes.md`
   - 写入 `round-XX-summary.json`和`human/round-XX-summary.md`（资源消耗与收益）
   - 追加结构化事件到 `timeline.jsonl`
6. 更新 `human/reading-inventory.md`，至少包含：
   - 当前累计轮次与每轮阅读链接数量；
   - 本轮新增链接清单（URL + 标题 + 一句话总结）。
7. 更新 `human/citation-index.md`，记录 `claimId -> source URLs -> snippet summary`。

洞察完成度（Insight Completion Score, ICS）最低项：
- 至少 8 条非显而易见结论（`L2`）/ 12 条（`L3`）。
- 每条核心结论至少 2 个来源支撑；若仅 1 个来源，必须标注“单源结论”。
- 至少 2 条边界条件与 2 条失败模式分析。
- 至少 1 组可执行落地建议（按用户场景分层）。

## 页面缓存规则（强制）

1. 缓存目录固定为：`tasks/<taskId>/cache/pages/`。
2. 每次读取 URL 前必须先查缓存（按 URL 归一化后的哈希命名缓存文件）。
3. 若缓存存在且未过期：必须直接使用缓存内容，禁止请求远端页面。
4. 仅在以下场景允许请求远端：
   - 缓存不存在；
   - 缓存已过期；
   - 用户明确要求“强制刷新缓存”。
5. 远端读取成功后必须先回写缓存，再写 `reads/*.json`。
6. 每次读取必须在 `timeline.jsonl` 记录：`cacheHit=true/false`、`cacheFile`、`remoteFetched=true/false`。
7. 每轮汇总必须包含：`remoteFetched`、`cacheHits`、`cacheHitRate`。

## 页面清洗规则（强制）

1. 读取页面后先做正文抽取，降低导航/样式噪音对分析的干扰。
2. 至少保留：主标题、段落正文、表格、代码块、章节标题、文档中的关键参数名。
3. 明确丢弃：导航菜单、页脚、样式脚本、重复 UI 元素。
4. 若正文抽取失败，必须在 `timeline.jsonl` 写入 `CONTENT_EXTRACTION_DEGRADED`。

## ASK_USER 策略

默认自动推进。仅在以下条件暂停：
1. 目标存在歧义或出现重大策略分叉。
2. 出现阻塞状态（登录失败/重复失败）。
3. 连续多轮新增收益过低。
4. 深度目标与当前产出明显不匹配（例如用户要 `L3`，但 ICS 未达标）。
5. 出现多个等价研究分支（例如“继续深挖 A 维度”或“扩展竞品 B”）。

暂停时必须写入 `ASK_USER` 事件，字段包含：
`question`、`options`、`impact`、`recommendedOption`。

## 最小指令短语

接受并执行以下用户短语：
1. `创建任务：goal=..., seedUrls=[...]`
2. `开始执行任务 <taskId>`
3. `继续任务 <taskId>`
4. `查看任务进展 <taskId>`
5. `启动登录会话 <taskId>`
6. `我已登录并关闭浏览器，继续任务 <taskId>`
7. `生成最终报告 <taskId>`

## 实现约束（会话管理）

1. 优先使用 `launchPersistentContext(browser-profile)` 作为统一会话容器。
2. 禁止在每个任务中重复创建新的 profile 目录，避免登录态分裂。
3. 仅当用户明确要求“导出会话文件”时，才生成 `sessions/<domain>.json`。

## 完成标准

满足以下任一条件即判定任务完成：
1. 目标覆盖度达到要求，且结论有证据支撑，且 ICS 达标。
2. 用户显式要求停止。

最终报告要求：
1. 默认生成完整版总结，不少于 1500 字（中文）。
2. 报告必须覆盖：使用方式、授权机制、能力边界、调用流程、未解决问题。
3. 报告中的关键结论必须可回溯到已读链接与证据文件。
4. 每个关键观点后必须紧跟原文链接引用（就地引用），禁止只在文末列参考文献。
5. 报告需显式区分：`事实`、`推断`、`建议`，并给出不确定性说明。
6. 对比型报告必须含“相同点、差异点、杀手锏能力、适用场景、迁移建议”五个章节。
7. `L3` 报告额外要求：包含反证分析、置信度分级、90 天落地路线图。

## 证据文件结构（强制）

`evidence/evidence.json` 至少包含：
- `claims[]`：
  - `id`
  - `statement`
  - `type`（`fact|inference|recommendation`）
  - `sources[]`
  - `evidenceSnippets[]`
  - `counterEvidence[]`
  - `confidence`（`low|medium|high`）
  - `openQuestions[]`

## 报告质量闸门（发布前检查）

发布前必须全部通过：
1. 引用完整性：关键结论就地引用覆盖率 100%。
2. 证据强度：核心结论中“双源支撑”占比 >= 80%（`L2`）/ >= 90%（`L3`）。
3. 深度指标：非显而易见结论数、边界条件数、失败模式数达标。
4. 行动性：至少 5 条可执行建议（`L2`）/ 8 条（`L3`）。
5. 不确定性：明确列出未解决问题与后续验证路径。

结束时必须返回：
1. 最终状态（`completed/blocked/stopped`）
2. 关键产物路径
3. 未解决问题列表
