---
name: gitinfo
description: Gather objective repository materials from GitHub and DeepWiki, then produce a Chinese architecture-oriented project report. Use when user sends `/gitinfo <url>` and wants fast project understanding for further research.
metadata:
  {"openclaw":{"emoji":"🧭","requires":{"bins":["git","python3"]}},"tags":["github","architecture","research"]}
user-invocable: true
---

# gitinfo

`gitinfo` 分为两个阶段：

- 阶段 A：脚本只做“素材采集”（客观信息）
- 阶段 B：Agent 基于素材 + 实际代码阅读生成结论

## Invocation

- Command: `/gitinfo <url>`
- Example: `/gitinfo https://github.com/openclaw/openclaw`

## Output location

- Root: `~/workspace/sources/gitinfo-outputs`
- Run folder: `<timestamp>-<repo>/`
- Final report file: `context.md` (中文)

## Stage A: 运行采集脚本（只采集，不下结论）

```bash
python3 "{baseDir}/scripts/gitinfo_quick.py" --repo-url "<url>"
```

采集后将得到：

- `collector-summary.md`（客观采集摘要）
- `facts.json`（结构化指标）
- `raw/*`（GitHub API、DeepWiki、目录树、关键文件清单、代码统计）
- `context.md`（自动生成的分析初稿，待 Agent 补全）

## Stage B: Agent 生成最终 `context.md`

在脚本完成后，Agent 需要继续阅读并分析：

1. 先读采集物：`collector-summary.md`, `facts.json`, `raw/key-files.txt`, `raw/tree-depth3.txt`, `context.md`
2. 再读仓库关键源码与文档：README、核心入口文件、关键目录
3. 在 `context.md` 初稿上补全并覆盖为最终中文报告

## 报告原则（必须遵守）

- 先业务后技术：先解释“项目是做什么的”，再讲实现支撑。
- 事实与判断分离：客观指标后，给简短判断（规模/热度/活跃/维护面）。
- 讲“能力如何达成”：核心功能 -> 业务模块 -> 关键技术/依赖 -> 支撑关系。
- 不确定就标注“待确认”，不要硬猜。
- 避免空洞目录罗列，必须有抽象与总结。

## `context.md` 结构（建议）

1. 项目定位（一句话 + 目标用户/场景）
2. 当前状态判断（指标 + 3-5 条简评）
3. 业务架构概要
   - 核心功能
   - 业务模块分工
   - 关键技术与依赖
   - 功能是如何被这些模块/技术支撑的
4. 关键流程（6-10 步，业务视角）
5. 风险与边界（维护风险、耦合风险、扩展边界）
6. 证据索引（引用 `raw/*` 和关键代码路径）

## Notes

- 采集脚本只负责“拿素材”，不负责“输出架构结论”。
- 最终给用户看的主文件是 `context.md`。
