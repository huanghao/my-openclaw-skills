#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from git_common import (
    read_origin_url,
    parse_github_remote,
    github_request,
    best_effort_cmd,
)

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def safe_json_load(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def maybe_int(value: Any) -> Any:
    return value if isinstance(value, int) else "n/a"


def collect_tree(repo_dir: Path, max_depth: int = 3, max_items: int = 400) -> list[str]:
    entries: list[str] = []
    root_depth = len(repo_dir.parts)
    for root, dirs, files in os.walk(repo_dir):
        current = Path(root)
        rel_depth = len(current.parts) - root_depth
        if ".git" in dirs:
            dirs.remove(".git")
        if rel_depth > max_depth:
            dirs[:] = []
            continue

        for name in sorted(dirs):
            rel = (current / name).relative_to(repo_dir)
            entries.append(str(rel) + "/")
        for name in sorted(files):
            rel = (current / name).relative_to(repo_dir)
            entries.append(str(rel))

        if len(entries) >= max_items:
            return entries[:max_items]
    return entries[:max_items]


def collect_key_files(repo_dir: Path) -> list[str]:
    patterns = [
        "README.md",
        "README.MD",
        "readme.md",
        "docs",
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "Makefile",
        "docker-compose.yml",
        "docker-compose.yaml",
    ]
    hits: list[str] = []
    for p in patterns:
        candidate = repo_dir / p
        if candidate.exists():
            hits.append(str(candidate.relative_to(repo_dir)))

    for root_name in ["src", "app", "cmd", "server", "api"]:
        base = repo_dir / root_name
        if not base.exists() or not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.is_file() and child.suffix in {
                ".ts",
                ".tsx",
                ".js",
                ".jsx",
                ".py",
                ".go",
                ".rs",
                ".swift",
                ".java",
            }:
                hits.append(str(child.relative_to(repo_dir)))
            if len(hits) >= 40:
                break
    return sorted(set(hits))[:60]


def count_files(repo_dir: Path) -> int:
    return sum(1 for p in repo_dir.rglob("*") if p.is_file() and ".git" not in p.parts)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect repository materials from a local directory"
    )
    parser.add_argument("--repo-dir", required=True, help="Local repository directory")
    parser.add_argument("--output-root", default="~/workspace/sources/gitinfo-outputs")
    args = parser.parse_args()

    repo_dir = Path(args.repo_dir).expanduser().resolve()
    if not repo_dir.exists() or not repo_dir.is_dir():
        print(f"Invalid --repo-dir: {repo_dir}")
        return 2

    output_root = Path(args.output_root).expanduser()
    output_root.mkdir(parents=True, exist_ok=True)

    origin_url = read_origin_url(repo_dir)
    owner, repo, canonical_url = parse_github_remote(origin_url)
    repo_slug = repo if repo else repo_dir.name

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_root / f"{timestamp}-{repo_slug}"
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    github_token = os.environ.get("GITHUB_TOKEN")
    if owner and repo:
        repo_api = f"https://api.github.com/repos/{owner}/{repo}"
        release_api = f"{repo_api}/releases/latest"
        contrib_api = f"{repo_api}/contributors?per_page=100&anon=true"
        deepwiki_url = f"https://deepwiki.com/{owner}/{repo}"

        status, headers, body = github_request(repo_api, token=github_token)
        write_text(raw_dir / "repo.json", body)
        write_json(raw_dir / "repo.http.json", {"status": status, "headers": headers})

        status, headers, body = github_request(release_api, token=github_token)
        write_text(raw_dir / "release.json", body)
        write_json(
            raw_dir / "release.http.json", {"status": status, "headers": headers}
        )

        status, headers, body = github_request(contrib_api, token=github_token)
        write_text(raw_dir / "contributors.json", body)
        write_json(
            raw_dir / "contributors.http.json", {"status": status, "headers": headers}
        )

        status, headers, body = github_request(deepwiki_url)
        write_text(raw_dir / "deepwiki.html", body)
        write_json(
            raw_dir / "deepwiki.http.json", {"status": status, "headers": headers}
        )
    else:
        write_text(raw_dir / "repo.json", "")
        write_json(raw_dir / "repo.http.json", {"status": 0, "headers": {}})
        write_text(raw_dir / "release.json", "")
        write_json(raw_dir / "release.http.json", {"status": 0, "headers": {}})
        write_text(raw_dir / "contributors.json", "")
        write_json(raw_dir / "contributors.http.json", {"status": 0, "headers": {}})
        write_text(raw_dir / "deepwiki.html", "")
        write_json(raw_dir / "deepwiki.http.json", {"status": 0, "headers": {}})

    repo_json = safe_json_load(raw_dir / "repo.json")
    release_json = safe_json_load(raw_dir / "release.json")
    contrib_json = safe_json_load(raw_dir / "contributors.json")

    stars = maybe_int(repo_json.get("stargazers_count"))
    forks = maybe_int(repo_json.get("forks_count"))
    watchers = maybe_int(repo_json.get("subscribers_count"))
    open_issues = maybe_int(repo_json.get("open_issues_count"))
    default_branch = repo_json.get("default_branch") or "n/a"
    pushed_at = repo_json.get("pushed_at") or "n/a"
    license_spdx = ((repo_json.get("license") or {}).get("spdx_id")) or "n/a"
    latest_release_tag = release_json.get("tag_name") or "n/a"
    latest_release_date = release_json.get("published_at") or "n/a"

    contributor_count: int | str = "n/a"
    if isinstance(contrib_json, list):
        contributor_count = len(contrib_json)

    code_stats_source = "file-count"
    if shutil.which("scc"):
        ok, out = best_effort_cmd(["scc", str(repo_dir)])
        if ok:
            write_text(raw_dir / "scc.txt", out + "\n")
            code_stats_source = "scc"
    elif shutil.which("cloc"):
        ok, out = best_effort_cmd(["cloc", str(repo_dir)])
        if ok:
            write_text(raw_dir / "cloc.txt", out + "\n")
            code_stats_source = "cloc"

    tracked_files_count = count_files(repo_dir)
    if code_stats_source == "file-count":
        write_text(raw_dir / "file-count.txt", f"{tracked_files_count}\n")

    tree_entries = collect_tree(repo_dir, max_depth=3, max_items=400)
    write_text(
        raw_dir / "tree-depth3.txt",
        "\n".join(tree_entries) + ("\n" if tree_entries else ""),
    )

    key_files = collect_key_files(repo_dir)
    write_text(
        raw_dir / "key-files.txt", "\n".join(key_files) + ("\n" if key_files else "")
    )

    deepwiki_status = "missing_or_blocked"
    deepwiki_http = safe_json_load(raw_dir / "deepwiki.http.json")
    deep_status_code = deepwiki_http.get("status")
    if deep_status_code == 200:
        deepwiki_status = "available"
    elif isinstance(deep_status_code, int) and 300 <= deep_status_code < 400:
        deepwiki_status = "redirect_or_partial"

    collector_summary = f"""# gitinfo 素材采集结果（仅客观信息）

此文件仅记录采集结果，不包含架构结论。

- 远程仓库：{canonical_url or "n/a"}
- 本地目录：{repo_dir}
- 输出目录：{run_dir}
- 生成时间（UTC）：{now_utc_iso()}

## 客观快照

- Stars：{stars}
- Forks：{forks}
- Watchers：{watchers}
- Open issues：{open_issues}
- License：{license_spdx}
- 默认分支：{default_branch}
- 最近推送：{pushed_at}
- 最新发布：{latest_release_tag}（{latest_release_date}）
- 贡献者数量（API样本）：{contributor_count}
- 文件数：{tracked_files_count}
- 代码统计来源：{code_stats_source}
- DeepWiki 状态：{deepwiki_status}

## 素材文件

- raw/repo.json
- raw/release.json
- raw/contributors.json
- raw/deepwiki.html
- raw/tree-depth3.txt
- raw/key-files.txt
"""
    write_text(run_dir / "collector-summary.md", collector_summary)

    print("material collection complete")
    print(f"RUN_DIR={run_dir}")
    print(f"COLLECTOR_SUMMARY={run_dir / 'collector-summary.md'}")
    print(f"SANITIZED_REPO_URL={canonical_url or 'n/a'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
