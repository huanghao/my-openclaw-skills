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

当用户只需要对已提供文本做一次性摘要时，不使用本 skill。

## 输入参数

收集并确认以下输入：
1. `goal`：要完成的信息目标。
2. `seedUrls`：初始链接列表。
3. `workspaceRoot`：任务工作目录（默认 `/Users/huanghao/workspace/learning/research/reading-workspace`）。

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
      plan-changes.md
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


## 每轮执行协议

每一轮都执行：
1. 计划：生成 `plan.vN.json` 和 `human/plan.vN.md`，包含优先级与理由。
2. 执行：按计划读取页面（先校验登录态），严格遵守“先查缓存、后请求远端”规则，抽取证据并更新读取文件。
3. 评估：计算覆盖度变化，给出 `continue | stop | blocked | ask_user`。
4. 记录：
   - 更新 `human/plan-changes.md`
   - 写入 `round-XX-summary.json`和`human/round-XX-summary.md`（资源消耗与收益）
   - 追加结构化事件到 `timeline.jsonl`
5. 更新 `human/reading-inventory.md`，至少包含：
   - 当前累计轮次与每轮阅读链接数量；
   - 本轮新增链接清单（URL + 标题 + 一句话总结）。

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

## ASK_USER 策略

默认自动推进。仅在以下条件暂停：
1. 目标存在歧义或出现重大策略分叉。
2. 出现阻塞状态（登录失败/重复失败）。
3. 连续多轮新增收益过低。

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
1. 目标覆盖度达到要求，且结论有证据支撑。
2. 用户显式要求停止。

最终报告要求：
1. 默认生成完整版总结，不少于 1000 字（中文）。
2. 报告必须覆盖：使用方式、授权机制、能力边界、调用流程、未解决问题。
3. 报告中的关键结论必须可回溯到已读链接与证据文件。

结束时必须返回：
1. 最终状态（`completed/blocked/stopped`）
2. 关键产物路径
3. 未解决问题列表
