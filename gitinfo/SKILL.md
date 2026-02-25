---
name: gitinfo
description: Gather objective repository materials from GitHub and DeepWiki, then produce a Chinese architecture-oriented project report. Use when user sends `/gitinfo <url>` and wants fast project understanding for further research.
metadata:
  {"openclaw":{"emoji":"🧭","requires":{"bins":["git","python3"]}},"tags":["github","architecture","research"]}
user-invocable: true
---

# gitinfo

## 变量定义

- `<url>`：用户输入的 GitHub 仓库 URL（调用格式：`/gitinfo <url>`）
- `<repo>`：从 `<url>` 解析出的仓库名（不含 owner）
- `<local_repo_path>`：Step 1 产出的本地仓库目录
- `<timestamp>`：运行时间戳，格式 `YYYYMMDD-HHMMSS`
- `<run_dir>`：Step 2 产出的本次运行目录
- `<raw_dir>`：`<run_dir>/raw`
- `<report_file>`：最终报告文件，固定为 `<run_dir>/report.md`

## 目录位置

- `<sources_root>`：`~/workspace/sources`
- `<local_repo_path>`：`<sources_root>/<repo>`
- `<output_root>`：`<sources_root>/gitinfo-outputs`
- `<run_dir>`：`<output_root>/<timestamp>-<repo>`
- `<raw_dir>`：`<run_dir>/raw`
- `<report_file>`：`<run_dir>/report.md`

## 输入/输出契约

- Step 1 输入：`<url>`；输出：`<local_repo_path>`
- Step 2 输入：`<local_repo_path>`；输出：`<run_dir>`
- Step 3 输入：`<run_dir>` 下采集物与源码；输出：`<report_file>`（中文）

## 执行路径约定（必须）

## Step 1：准备本地仓库

```bash
python3 {baseDir}/scripts/gitinfo_repo_sync.py \
  --repo-url "<url>"
```

成功后读取脚本输出中的 `LOCAL_REPO_PATH`，作为 `<local_repo_path>`。

执行要求（批量场景）：
- 单仓库超时：300 秒（5 分钟）。
- 失败后允许降级：无法完成 repo sync 时，可转为 `processed_degraded`（基于 GitHub API + README 生成报告）。
- 状态需结构化：建议每仓库落 `run-result.json`，避免仅依赖日志文本判定。

## Step 2：运行采集脚本

```bash
python3 {baseDir}/scripts/gitinfo_quick.py \
  --repo-dir "<local_repo_path>"
```

产出：

- `collector-summary.md`（客观采集摘要）
- `raw/*`（GitHub API、DeepWiki、目录树、关键文件清单、代码统计等原始/近原始材料）

## Step 3：生成最终 `report.md`

1. 读取采集物：`collector-summary.md`, `raw/key-files.txt`, `raw/tree-depth3.txt`, `raw/*`
2. 阅读仓库关键源码与文档：README、核心入口文件、关键目录
3. 将最终内容写回 `<report_file>`
4. 把最终报告发回对话，不要再针对报告内容做二次总结

状态判定规则（必须）：
- `processed`：`report.md` 存在且为完整模式（已完成 Step1/2/3）。
- `processed_degraded`：`report.md` 存在，但基于降级模式（如 repo sync 超时/失败后改走 API+README）。
- `failed`：未产出 `report.md`。

批量去重键（必须）：
- 使用完整仓库标识 `owner/repo`，不要仅用仓库名。

## 报告原则（必须遵守）

- 先业务后技术：先解释“项目是做什么的”，再讲实现支撑。
- 事实与判断分离：客观指标后，给简短判断（规模/热度/活跃/维护面）。
- 讲“能力如何达成”：核心功能 -> 业务模块 -> 关键技术/依赖 -> 支撑关系。
- 不确定就标注“待确认”，不要硬猜。
- 避免空洞目录罗列，必须有抽象与总结。
- 报告语言必须为中文。

## `report.md` 结构（建议）

1. 项目定位（一句话 + 目标用户/场景）
2. 当前状态判断（指标 + 3-5 条简评）
3. 业务架构概要（核心功能、业务模块分工、关键技术与依赖、支撑关系）
4. 关键流程（建议 3-8 步，按复杂度调整，业务视角）
5. 风险与边界（维护风险、耦合风险、扩展边界）
