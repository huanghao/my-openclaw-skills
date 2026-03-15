---
name: mdv-comments
description: 使用 mdv 打开 Markdown 文件，并通过 comments get / comments reply / comments reply-batch 读取与回复评论；不处理其他子命令。
---

## Scope

只使用以下命令：

- `mdv <FILE>`：打开 Markdown 文件
- `mdv comments get --file <FILE>`：读取文件评论
- `mdv comments reply ...`：回复单条评论
- `mdv comments reply-batch ...`：批量回复评论

不要使用其他 `mdv` 子命令。

## Workflow

1. 先打开文件：`mdv <FILE>`。
2. 读取评论：`mdv comments get --file <FILE>`（默认读人类可读输出；自动化场景优先 `--json`）。
3. 回复评论：
   - 单条：`comments reply`
   - 批量：`comments reply-batch`

## Open File

```bash
mdv /abs/path/to/file.md
```

说明：

- 传入绝对路径，避免歧义。
- 文件不存在时会直接报错，需先修正路径。

## Get Comments

人类可读输出：

```bash
mdv comments get --file /abs/path/to/file.md
```

结构化输出（推荐给 agent 解析）：

```bash
mdv comments get --file /abs/path/to/file.md --json
```

## Reply One Comment

必须显式提供作者：`--author <NAME>`。

按序号回复（推荐）：

```bash
mdv comments reply \
  --file /abs/path/to/file.md \
  --seq 2 \
  --author codex \
  --text "我会补充这段背景。"
```

按原始 ID 回复：

```bash
mdv comments reply \
  --file /abs/path/to/file.md \
  --id ann-12345 \
  --author codex \
  --text "收到，下一版处理。"
```

约束：

- `--seq` 与 `--id` 二选一。
- `--author` 必填（可用 `codex` / `claude` / 用户名等）。
- `--text` 必填。

## Reply Batch

单作者批量回复：

```bash
mdv comments reply-batch \
  --file /abs/path/to/file.md \
  --author codex \
  --input replies.json
```

`replies.json` 格式：

```json
{
  "replies": [
    { "seq": 2, "text": "先补充术语定义" },
    { "id": "ann-12345", "text": "这里我改成一致表述" }
  ]
}
```

也支持 stdin：

```bash
cat replies.json | mdv comments reply-batch --file /abs/path/to/file.md --author codex --input -
```

## Execution Rules

- 写操作前，优先先跑一次 `comments get`，确认目标序号/ID。
- 回复后，再跑一次 `comments get` 做结果校验。
- 批量回复时，优先使用文件输入，避免长命令转义错误。
- 若命令报参数缺失，按 CLI 提示补齐，不猜测默认值。
