---
name: gitinfo
description: Clone a GitHub repository and generate a quick architecture-oriented project context pack. Use when user sends `/gitinfo <url>` or asks for a fast project introduction with code stats, recency signals, high-level architecture, and ecosystem context.
metadata:
  {"openclaw":{"emoji":"🧭","requires":{"bins":["git","python3"]}},"tags":["github","architecture","research"]}
user-invocable: true
---

# gitinfo

Generate a quick project context pack from a GitHub URL.

## Invocation

- Command: `/gitinfo <url>`
- Example: `/gitinfo https://github.com/openclaw/openclaw`

## Output location

- Root: `~/workspace/sources/gitinfo-outputs`
- Run folder: `<repo>-<timestamp>/`
- Main context file for follow-up analysis: `context.md`

## Workflow

1. Parse `owner/repo` from the URL.
2. Clone or update repository under `~/workspace/sources`.
3. Collect quick signals:
   - stars/forks/open issues/license/default branch
   - latest push/release timestamps
   - 30/90 day commit counts
   - contributor count (best effort)
   - code stats (`scc`, fallback to `cloc`, fallback to file count)
4. Read DeepWiki (`https://deepwiki.com/<owner>/<repo>`) when available.
5. Build high-level architecture overview:
   - entry points
   - runtime flow
   - top-level components/boundaries
   - extension points
6. Write output files to run folder.

## Files written

- `context.md` (primary context for deeper follow-up; merged final report)
- `facts.json` (structured facts)
- `raw/` (raw API and command outputs)
- Final report language: Chinese (`context.md`)

## Execute

Run this script:

```bash
python3 "{baseDir}/scripts/gitinfo_quick.py" --repo-url "<url>"
```

If the user provides only `/gitinfo <url>`, use default output root and quick settings.
