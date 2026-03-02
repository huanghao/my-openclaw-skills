---
name: browser-network-capture
description: Launch a real browser session, capture full network traffic while the user performs manual actions, then reverse-engineer the minimal API workflow (core write + minimal reads) and produce reusable docs/evidence. Use for requests like "start browser and capture", "I will operate, you analyze APIs", or "reverse this web flow by packet capture".
---

# Browser Network Capture

## When to use

Use this skill when the user asks to:
1. Start a browser and monitor all requests.
2. Let the user perform manual UI actions while the agent captures traffic.
3. Reverse-engineer APIs, request/response schema, and execution sequence.
4. Turn capture output into stable implementation guidance.

Do not use this skill for static API docs reading without live capture.

## Inputs to confirm

Collect these first:
1. `target_goal`: what operation to reverse (for example, move doc, upload image, publish).
2. `target_site`: default `https://km.sankuai.com`.
3. `capture_name`: short slug for folder naming.
4. `need_compare`: whether same-flow variants are needed (for example same-space vs cross-space).

## Standard output locations

Use this layout:

1. Raw capture:
`docs/raw-data/YYYY-MM-DD-<capture_name>/captured_network.jsonl`

2. Raw capture note:
`docs/raw-data/YYYY-MM-DD-<capture_name>/README.md`

3. Analysis report:
`docs/research/YYYYMMDD-<topic>-capture-analysis.md`

## Start capture (default profile)

Preferred command:

```bash
USER_DATA_DIR="$HOME/.local/playwright/profile" \
LOG_FILE="<ABS_CAPTURE_JSONL_PATH>" \
node "$HOME/.config/km-cli/playwright/capture-network.mjs"
```

Fallback script path:

```bash
USER_DATA_DIR="$HOME/.local/playwright/profile" \
LOG_FILE="<ABS_CAPTURE_JSONL_PATH>" \
node "/Users/huanghao/workspace/mt-cli/tools/km-cli/scripts/capture-network.mjs"
```

Notes:
1. Keep browser visible (`headless: false`).
2. Ask user to perform exactly one target operation per capture when possible.
3. Stop capture after user says done.

## Runtime protocol

1. Announce capture is running and what action user should perform.
2. Wait for user completion signal.
3. Stop capture.
4. Immediately parse for core write endpoint(s), then required read endpoint(s).
5. If `need_compare=true`, repeat capture for the variant and compare.

## Minimal analysis workflow

1. Find candidate APIs:

```bash
rg -n '"url":"https://[^\"]+/api/' <captured_network.jsonl>
```

2. Find likely write calls:

```bash
rg -n '"method":"POST"|"method":"PUT"|"method":"DELETE"' <captured_network.jsonl>
```

3. Extract path-specific evidence around target IDs/keywords.
4. Build sequence: pre-read -> core write -> post-verify reads.
5. Mark what is confirmed vs inferred.

## Deliverables checklist

Always provide:
1. Core write API (method, path, required body fields, sample response).
2. Minimal required reads (parameter prep + verification).
3. Sequence diagram in plain steps.
4. Edge-case differences (if compared variants exist).
5. Risks and unknowns.
6. Source pointers to raw files.

## Implementation principle

For command design, prefer:
1. Core state change by one write API.
2. Minimal reads only for preparation and verification.
3. Explicitly document unavoidable reads.

## Security and hygiene

1. Captured logs may contain cookies/tokens/headers. Treat as sensitive.
2. Do not paste sensitive headers into public outputs.
3. Keep raw logs in `docs/raw-data/` with a warning note.
4. Share summarized evidence, not full sensitive payloads.

## Suggested response template

Use this structure in final answers:
1. `Result`: what was confirmed.
2. `Core API`: write + minimal reads.
3. `Evidence`: raw file paths and key lines/patterns.
4. `Design impact`: how this maps to CLI/product design.
5. `Open questions`: what still needs another capture.
