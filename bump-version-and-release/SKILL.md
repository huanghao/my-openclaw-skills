---
name: bump-version-and-release
description: 在任意仓库执行一次发布闭环：升级版本、更新 CHANGELOG、构建打包、更新 Homebrew tap Formula，并给出可执行的发布结果清单。
---

# Bump Version And Release

当用户要求“发布新版本 / 升级版本并发版 / 更新 Homebrew Formula”时使用本 skill。

## 输入约定

开始前先确认或自动识别以下信息：
- 当前仓库的版本来源（如 `package.json`、`pyproject.toml`、`Cargo.toml`、`VERSION` 文件）。
- 目标版本号与升级类型（patch/minor/major）。
- Homebrew tap 仓库地址、Formula 文件路径、Formula 名称。
- 构建产物名称、下载 URL（或发布附件 URL）以及对应 SHA256。

若关键信息缺失：先在仓库内搜索并推断；仍无法确定时再向用户提 1 个最小问题。

## 执行流程

1. 读取仓库当前状态。
- 检查 `git status --short`，识别未提交改动。
- 识别版本文件与 changelog 文件路径。

2. 升级版本号。
- 使用仓库已有方式优先（如 `npm version`、`poetry version`、`cargo set-version`、项目脚本）。
- 若无统一命令，再做定点文件修改。
- 避免同时修改无关文件。

3. 更新 `CHANGELOG.md`。
- 在新版本标题下写入本次变更摘要与日期。
- 若项目已有 changelog 规范（Keep a Changelog / Conventional Commits），遵循原规范。

4. 构建并产出发布包。
- 运行项目既有构建命令。
- 记录产物路径、文件名、大小、校验值（SHA256）。
- 构建失败时输出最小复现命令和关键报错。

5. 更新 Homebrew tap Formula。
- 在 tap 仓库对应 Formula 中更新 `url` 与 `sha256`，必要时更新 `version`。
- 保持原有 Ruby 风格与缩进。
- 如仓库存在校验命令（如 `brew audit --strict` / `brew test`），尽量执行并记录结果。

6. 自检与结果汇总。
- 列出修改文件清单。
- 给出可直接执行的提交命令、打 tag 命令、推送命令。
- 明确哪些步骤已完成，哪些因环境限制未执行。

## 输出模板

最终回复按以下结构：

- `版本变更`：`old -> new`
- `已修改文件`：逐个文件列出关键变更点
- `构建产物`：文件名、路径、SHA256
- `Formula 更新`：Formula 路径、旧值 -> 新值
- `验证结果`：执行过的校验命令与结果
- `发布命令清单`：按顺序给出命令（commit/tag/push/release）
- `未完成项`：需要用户补充或手动执行的事项

## 约束

- 不回滚或覆盖用户已有未提交改动。
- 不使用破坏性 git 命令（如 `git reset --hard`）。
- 若检测到与发布无关的大范围脏改动，先提示风险再继续。
