---
name: hn-daily-feishu-digest
description: Heartbeat-driven Hacker News daily briefing for OpenClaw. Use when you need recurring HN monitoring with a 6-hour collect cadence and a single 11:30 daily Feishu summary, based only on HN API metadata.
metadata: {"openclaw":{"always":true}}
---

# HN Daily Feishu Digest

Run this skill from OpenClaw heartbeat or cron. This skill is not self-starting.

## Driver Model

Use one periodic trigger (recommended: heartbeat every 1 hour), then gate execution by state.

Execution gates:

- Run `collect` only if at least 6 hours have passed since `last_collect_at`.
- Run `digest` only if local time is 11:00 or later and `digest_sent_date` is not today.
- If neither gate passes, return `HEARTBEAT_OK`.

Timezone default: `Asia/Shanghai`.

## Data Source Constraints

Use HN API metadata only:

- `https://hacker-news.firebaseio.com/v0/topstories.json`
- `https://hacker-news.firebaseio.com/v0/item/<id>.json`

Rules:

- In each collect run, fetch only Top 10 story ids.
- Keep `type=story` items only.
- Do not open article URLs and do not scrape page content.

## Minimal State

Track these keys in skill state:

- `last_collect_at` (ISO datetime)
- `digest_sent_date` (YYYY-MM-DD in local timezone)
- `daily_candidates[date][hn_id]`
- `daily_usage[date]`

Per candidate item:

- `id`, `title`, `url`, `score`, `descendants`, `by`, `time`
- `first_seen_at`, `last_seen_at`, `seen_count`
- `max_score`, `max_descendants`
- `category`
- `days_seen` (for multi-day hot handling)

Per day usage:

- `model`
- `input_tokens`, `output_tokens`, `total_tokens`
- `collect_duration_ms_total`, `digest_duration_ms_total`, `duration_ms_total`

## Collect Action

When collect gate passes:

1. Fetch Top 10 ids.
2. Fetch each item metadata.
3. Upsert into today's candidate pool by `id`.
4. Update seen counters and max fields.
5. Assign one primary category:
   - `AI/ML`, `DevTools`, `Security`, `Infra/Cloud`, `Startup/Business`, `Science`, `Policy`, `Other`
6. Update usage metrics and `last_collect_at`.

## Digest Action

When digest gate passes:

1. Load today's unique candidates.
2. Rank and pick Top 15.
3. Send one Feishu digest message.
4. Set `digest_sent_date` to today.

If candidates are fewer than 15, send available items and mark partial list.

## Ranking Rules

Main list score:

`daily_score = 0.5*norm(score) + 0.3*norm(descendants) + 0.2*freshness - repeat_penalty`

- `freshness`: newer stories in the same day get higher value.
- `repeat_penalty`: `0.05 * max(0, days_seen - 1)`.

Multi-day hot handling:

- Keep repeated stories eligible in Top 15 with penalty.
- Add a short `Sustained Heat` block (up to 3 items) for stories that stay hot across days.

## Feishu Message Contract

Always include these sections in order:

1. `Top 15` (each item: rank/title/HN link/url/score/comments/first_seen/seen_count/category/1-2 sentence metadata summary)
2. `Category Summary` (counts + percentages for all daily unique candidates)
3. `Runtime Usage Summary` (model + input/output/total tokens + durations)
4. `Sustained Heat` (optional, up to 3)

## Failure Rules

- Partial HN fetch failures: continue with successful items.
- Send failure: keep digest content for retry; do not mark sent.
- No candidates by digest time: send a short no-data notice instead of skipping.
