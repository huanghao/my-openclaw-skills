---
name: dida365-cli
description: 用 `dida365-cli` 命令行管理 Dida365（滴答清单/TickTick）个人待办：创建、查询、更新、完成、删除任务与项目。适用于“帮我管理我的 TODO 清单/待办事项”这类请求。
homepage: https://github.com/huanghao/dida365-cli
metadata: {"openclaw":{"emoji":"🗓️","requires":{"bins":["dida365-cli"]},"install":[{"id":"brew","kind":"brew","formula":"huanghao/tap/dida365-cli","bins":["dida365-cli"],"label":"Install dida365-cli (brew tap)"}]}}
user-invocable: true
---

# Dida365 CLI

Use `dida365-cli` to manage personal TODOs in Dida365 (TickTick / 滴答清单) from terminal commands.

Setup

- Ensure CLI is available: `dida365-cli version --json`
- Install (Homebrew): `brew tap huanghao/tap && brew install dida365-cli`
- Auth must be completed before task operations:
  - `dida365-cli auth status --json`
  - Required status fields: `access_token_set: true`, `client_id_set: true`, `redirect_uri_set: true`
- Config defaults:
  - `~/.config/dida365-cli/config.json`

Agent safety rules (must follow)

- Prefer JSON output for all actionable commands: add `--json`
- For every write operation, run `--dry-run` first, then run the real command after preview passes
- Read commands use local 10-second cache by default; disable with `--no-cache` or `DIDA_NO_CACHE=1`
- Repeated identical write operations are debounced within 3 seconds; avoid immediate duplicate retries

Read commands

- List projects: `dida365-cli projects list --json`
- List tasks in project: `dida365-cli list --project <project_id> --json`
- Show task detail: `dida365-cli show --project <project_id> --id <task_id> --json`
- Common fields to inspect: `title`, `content`, `status`, `completedTime`, `dueDate`, `priority`

Write commands (always dry-run first)

- Create project:
  - Preview: `dida365-cli projects create --name "Roadmap" --view-mode list --kind TASK --json --dry-run`
  - Execute: `dida365-cli projects create --name "Roadmap" --view-mode list --kind TASK --json`
- Create task:
  - Preview: `dida365-cli add --project <project_id> --title "Task title" --content "Task content" --due "2026-02-25T18:00:00+0800" --priority 3 --json --dry-run`
  - Execute: `dida365-cli add --project <project_id> --title "Task title" --content "Task content" --due "2026-02-25T18:00:00+0800" --priority 3 --json`
- Update task:
  - Preview: `dida365-cli update --project <project_id> --id <task_id> --title "New title" --content "New content" --due "2026-02-26T18:00:00+0800" --priority 5 --json --dry-run`
  - Execute: `dida365-cli update --project <project_id> --id <task_id> --title "New title" --content "New content" --due "2026-02-26T18:00:00+0800" --priority 5 --json`
- Complete task:
  - Preview: `dida365-cli done --project <project_id> --id <task_id> --json --dry-run`
  - Execute: `dida365-cli done --project <project_id> --id <task_id> --json`
- Delete task:
  - Preview: `dida365-cli delete --project <project_id> --id <task_id> --json --dry-run`
  - Execute: `dida365-cli delete --project <project_id> --id <task_id> --json`

Input limits

- `dida365-cli add` enforces `< 500` characters for `--title`, `--content`, `--desc`

Auth commands (when user asks explicitly)

- Init OAuth app: `dida365-cli auth init --client-id <client_id> --client-secret <client_secret> --redirect-uri <redirect_uri>`
- Open auth URL: `dida365-cli auth login`
- Exchange code for token: `dida365-cli auth token --code <authorization_code>`
- Refresh token: `dida365-cli auth refresh`
- Logout: `dida365-cli auth logout`
