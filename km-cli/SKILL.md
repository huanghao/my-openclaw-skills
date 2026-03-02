---
name: km-cli
description: "使用km-cli和学城文档交互，包括搜索、新建与评论操作（edit 暂不支持）"
---


## Workflow

Collect required inputs first:

- `content_id` for existing doc operations
- `parent_id` and `title` for doc creation
- `keyword` for search operations
- comment text / reply text

Default to `--json` and parse structured fields instead of regex parsing plain text.
For `doc get-content`, do not use `--format`; read JSON and parse `data.body`.

`edit` 相关命令目前不稳定，默认不支持；仅处理 `auth/doc/search/comment`。

## Create Document

Prefer `--markdown-file` for long markdown body:

```bash
km-cli doc create \
  --parent-id "$PARENT_ID" \
  --title "$TITLE" \
  --markdown-file "$MD_FILE" \
  --json
```

Fallback for short markdown text:

```bash
km-cli doc create --parent-id "$PARENT_ID" --title "$TITLE" --markdown "$MD_TEXT" --json
```

Legacy fallback (plain text -> body JSON) when markdown is not required:

```bash
km-cli doc create --parent-id "$PARENT_ID" --title "$TITLE" --content "$TEXT" --json
```

Do not mix `--content*` and `--markdown*` in the same call.
Capture and reuse `contentId` from output.

没有明确指定父文档时用 2747778972 当parent_id

## Search Content

Search KM documents with keyword:

```bash
km-cli search content --keyword "$KEYWORD" --limit 20 --json
```

Pagination with offset:

```bash
km-cli search content --keyword "$KEYWORD" --offset 20 --limit 10 --json
```

Search in title only:

```bash
km-cli search content --keyword "$KEYWORD" --search-title --json
```

Filter by space type (-1=all, 0=team space, 1=personal space):

```bash
km-cli search content --keyword "$KEYWORD" --space-type 0 --json
```

Get search history:

```bash
km-cli search history --json
```

## Get Document Content

Fetch content JSON for reading/parsing:

```bash
km-cli doc get-content --content-id "$CONTENT_ID" --json
```

Write JSON to file when diagnostics are needed:

```bash
km-cli doc get-content --content-id "$CONTENT_ID" --json --output "$OUT_FILE"
```

Extract title/heading outline from body JSON:

```bash
km-cli doc get-content --content-id "$CONTENT_ID" --json | jq '
  .data as $d
  | {
      contentId: $d.contentId,
      title: $d.title,
      headings: [
        ($d.body | (fromjson? // {}) | .. | objects
          | select(.type? == "title" or .type? == "heading")
          | {
              type: .type,
              level: (.attrs.level // 1),
              text: ([.content[]?.text // empty] | join(""))
            })
      ]
    }'
```

## Get Comments

Use both APIs based on task type:

- Full comment totals and flat list:

```bash
km-cli comment get --content-id "$CONTENT_ID" --limit 50 --offset 0 --json
```

- Discussion threads (for reply workflow):

```bash
km-cli comment list --content-id "$CONTENT_ID" --page-no 1 --page-size 100 --json
```

## Add Comments

Add full-page comment:

```bash
km-cli comment add --content-id "$CONTENT_ID" --text "$COMMENT_TEXT" --json
```

Reply in thread:

```bash
km-cli comment reply \
  --content-id "$CONTENT_ID" \
  --discussion-id "$DISCUSSION_ID" \
  --quote-id "$QUOTE_ID" \
  --text "$REPLY_TEXT" \
  --json
```

Use empty `--quote-id` to reply to the thread root.

## Execution Rules

- Confirm target identifiers (`content_id`, `discussion_id`, `quote_id`) before writes.
- For destructive or ambiguous edits, fetch current content first and summarize planned change.
- After any write (`doc create`, `comment add/reply`), return key IDs and a concise result summary.
- If command returns auth/session errors, refresh login and retry once.

## Reference

Prefer the latest man pages in the repo:

- `/Users/huanghao/workspace/mt-cli/man/km-cli.1`
- `/Users/huanghao/workspace/mt-cli/man/km-cli.config.5`
