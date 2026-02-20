---
name: gitinfo
description: Gather objective repository materials from GitHub and DeepWiki, then produce a Chinese architecture-oriented project report. Use when user sends `/gitinfo <url>` and wants fast project understanding for further research.
metadata:
  {"openclaw":{"emoji":"🧭","requires":{"bins":["git","python3"]}},"tags":["github","architecture","research"]}
user-invocable: true
---

# gitinfo

`gitinfo` 分两步：
- Stage A：脚本采集客观素材
- Stage B：Agent 读素材和源码，产出最终报告

## Invocation

- Command: `/gitinfo <url>`
- Example: `/gitinfo https://github.com/openclaw/openclaw`

## Output location

- Root: `~/workspace/sources/gitinfo-outputs`
- Run folder: `<timestamp>-<repo>/`
- Stage A draft: `report.stage-a.md`
- Final report: `report.md`（中文）

## Stage A：运行采集脚本（只采集，不下结论）

```bash
python3 "{baseDir}/scripts/gitinfo_quick.py" \
  --repo-url "<url>" \
  --draft-report-file "report.stage-a.md"
```

产出：

- `collector-summary.md`（客观采集摘要）
- `facts.json`（结构化指标）
- `raw/*`（GitHub API、DeepWiki、目录树、关键文件清单、代码统计）
- `report.stage-a.md`（报告草稿）

## Stage B：生成最终 `report.md`

1. 读取采集物：`collector-summary.md`, `facts.json`, `raw/key-files.txt`, `raw/tree-depth3.txt`, `report.stage-a.md`
2. 阅读仓库关键源码与文档：README、核心入口文件、关键目录
3. 基于 `report.stage-a.md` 完成最终中文报告
4. 将最终内容写回 `<run_dir>/report.md`（不能只留在对话里）
5. 最终回复必须附上 `report.md` 绝对路径

## 报告原则（必须遵守）

- 先业务后技术：先解释“项目是做什么的”，再讲实现支撑。
- 事实与判断分离：客观指标后，给简短判断（规模/热度/活跃/维护面）。
- 讲“能力如何达成”：核心功能 -> 业务模块 -> 关键技术/依赖 -> 支撑关系。
- 不确定就标注“待确认”，不要硬猜。
- 避免空洞目录罗列，必须有抽象与总结。

## `report.md` 结构（建议）

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
- 最终给用户看的主文件是 `report.md`。
