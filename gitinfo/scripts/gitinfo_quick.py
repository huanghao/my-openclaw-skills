#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass
class RepoTarget:
    owner: str
    repo: str
    canonical_url: str


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_cmd(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=check)


def best_effort_cmd(args: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    try:
        out = run_cmd(args, cwd=cwd, check=True)
        return True, out.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, (exc.stderr or exc.stdout or "").strip()


def parse_repo_target(raw: str) -> RepoTarget:
    raw = raw.strip()

    ssh_match = re.match(
        r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/?#]+?)(?:\.git)?$", raw
    )
    if ssh_match:
        owner = ssh_match.group("owner")
        repo = ssh_match.group("repo")
        return RepoTarget(
            owner=owner, repo=repo, canonical_url=f"https://github.com/{owner}/{repo}"
        )

    parsed = urlparse(raw)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError(f"Unsupported URL (GitHub required): {raw}")

    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from URL: {raw}")

    owner, repo = path_parts[0], path_parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    if not owner or not repo:
        raise ValueError(f"Cannot parse owner/repo from URL: {raw}")

    return RepoTarget(owner=owner, repo=repo, canonical_url=f"https://github.com/{owner}/{repo}")


def github_request(url: str, token: str | None = None) -> tuple[int, dict[str, str], str]:
    headers = {
        "User-Agent": "gitinfo-skill/2.0",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, dict(resp.headers.items()), body
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, dict(exc.headers.items()) if exc.headers else {}, body
    except URLError:
        return 0, {}, ""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_json_load(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def maybe_int(value: Any) -> Any:
    return value if isinstance(value, int) else "n/a"


def match_origin(origin_url: str, owner: str, repo: str) -> bool:
    lower = origin_url.lower()
    return "github.com" in lower and f"{owner.lower()}/{repo.lower()}" in lower


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

    # Add shallow key files under src/app/cmd if present.
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


def count_tracked_files(repo_dir: Path) -> int:
    ok, out = best_effort_cmd(["git", "ls-files"], cwd=repo_dir)
    if ok and out:
        return len([line for line in out.splitlines() if line.strip()])
    return sum(1 for p in repo_dir.rglob("*") if p.is_file() and ".git" not in p.parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="gitinfo quick collector")
    parser.add_argument("--repo-url", required=True, help="GitHub repository URL")
    parser.add_argument("--sources-root", default="~/workspace/sources")
    parser.add_argument("--output-root", default="~/workspace/sources/gitinfo-outputs")
    parser.add_argument("--ref", default="")
    parser.add_argument("--draft-report-file", default="report.stage-a.md")
    parser.add_argument("--final-report-file", default="report.md")
    args = parser.parse_args()

    try:
        target = parse_repo_target(args.repo_url)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    sources_root = Path(args.sources_root).expanduser()
    output_root = Path(args.output_root).expanduser()
    sources_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    local_repo_dir = sources_root / target.repo
    if (local_repo_dir / ".git").exists():
        ok, origin = best_effort_cmd(["git", "remote", "get-url", "origin"], cwd=local_repo_dir)
        if ok and not match_origin(origin, target.owner, target.repo):
            local_repo_dir = sources_root / f"{target.repo}-{target.owner}"

    if not (local_repo_dir / ".git").exists():
        try:
            subprocess.run(["git", "clone", target.canonical_url, str(local_repo_dir)], check=True)
        except subprocess.CalledProcessError:
            print(f"Clone failed for {target.canonical_url}", file=sys.stderr)
            return 1
    else:
        ok, err = best_effort_cmd(["git", "fetch", "--all", "--tags", "--prune"], cwd=local_repo_dir)
        if not ok:
            print(f"Warning: fetch failed, continue with local state: {local_repo_dir}", file=sys.stderr)
            if err:
                print(err, file=sys.stderr)

    if args.ref:
        ok, err = best_effort_cmd(["git", "checkout", args.ref], cwd=local_repo_dir)
        if not ok:
            print(f"Warning: checkout failed for ref {args.ref}, continue with current HEAD", file=sys.stderr)
            if err:
                print(err, file=sys.stderr)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_root / f"{timestamp}-{target.repo}"
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    github_token = os.environ.get("GITHUB_TOKEN")
    repo_api = f"https://api.github.com/repos/{target.owner}/{target.repo}"
    release_api = f"{repo_api}/releases/latest"
    contrib_api = f"{repo_api}/contributors?per_page=100&anon=true"
    deepwiki_url = f"https://deepwiki.com/{target.owner}/{target.repo}"

    status, headers, body = github_request(repo_api, token=github_token)
    write_text(raw_dir / "repo.json", body)
    write_json(raw_dir / "repo.http.json", {"status": status, "headers": headers})

    status, headers, body = github_request(release_api, token=github_token)
    write_text(raw_dir / "release.json", body)
    write_json(raw_dir / "release.http.json", {"status": status, "headers": headers})

    status, headers, body = github_request(contrib_api, token=github_token)
    write_text(raw_dir / "contributors.json", body)
    write_json(raw_dir / "contributors.http.json", {"status": status, "headers": headers})

    status, headers, body = github_request(deepwiki_url)
    write_text(raw_dir / "deepwiki.html", body)
    write_json(raw_dir / "deepwiki.http.json", {"status": status, "headers": headers})

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
    description = repo_json.get("description") or "n/a"
    latest_release_tag = release_json.get("tag_name") or "n/a"
    latest_release_date = release_json.get("published_at") or "n/a"

    contributor_count: int | str = "n/a"
    if isinstance(contrib_json, list):
        contributor_count = len(contrib_json)

    ok, commits_30d = best_effort_cmd(["git", "rev-list", "--count", "--since=30 days ago", "HEAD"], cwd=local_repo_dir)
    commits_30d = commits_30d if ok and commits_30d else "0"

    ok, commits_90d = best_effort_cmd(["git", "rev-list", "--count", "--since=90 days ago", "HEAD"], cwd=local_repo_dir)
    commits_90d = commits_90d if ok and commits_90d else "0"

    ok, last_commit_hash = best_effort_cmd(["git", "rev-parse", "--short", "HEAD"], cwd=local_repo_dir)
    last_commit_hash = last_commit_hash if ok and last_commit_hash else "n/a"

    ok, last_commit_date = best_effort_cmd(["git", "log", "-1", "--format=%cI"], cwd=local_repo_dir)
    last_commit_date = last_commit_date if ok and last_commit_date else "n/a"

    ok, last_commit_author = best_effort_cmd(["git", "log", "-1", "--format=%an"], cwd=local_repo_dir)
    last_commit_author = last_commit_author if ok and last_commit_author else "n/a"

    code_stats_source = "file-count"
    if shutil.which("scc"):
        ok, out = best_effort_cmd(["scc", str(local_repo_dir)])
        if ok:
            write_text(raw_dir / "scc.txt", out + "\n")
            code_stats_source = "scc"
    elif shutil.which("cloc"):
        ok, out = best_effort_cmd(["cloc", str(local_repo_dir)])
        if ok:
            write_text(raw_dir / "cloc.txt", out + "\n")
            code_stats_source = "cloc"

    tracked_files_count = count_tracked_files(local_repo_dir)
    if code_stats_source == "file-count":
        write_text(raw_dir / "file-count.txt", f"{tracked_files_count}\n")

    tree_entries = collect_tree(local_repo_dir, max_depth=3, max_items=400)
    write_text(
        raw_dir / "tree-depth3.txt",
        "\n".join(tree_entries) + ("\n" if tree_entries else ""),
    )

    key_files = collect_key_files(local_repo_dir)
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

    facts = {
        "repo": f"{target.owner}/{target.repo}",
        "repoUrl": target.canonical_url,
        "localRepoPath": str(local_repo_dir),
        "outputPath": str(run_dir),
        "generatedAtUtc": now_utc_iso(),
        "stats": {
            "stars": stars,
            "forks": forks,
            "watchers": watchers,
            "openIssues": open_issues,
            "license": license_spdx,
            "defaultBranch": default_branch,
            "lastPush": pushed_at,
            "latestReleaseTag": latest_release_tag,
            "latestReleaseDate": latest_release_date,
            "contributorsSampleCount": contributor_count,
            "commits30d": commits_30d,
            "commits90d": commits_90d,
            "lastCommitHash": last_commit_hash,
            "lastCommitDate": last_commit_date,
            "lastCommitAuthor": last_commit_author,
            "trackedFilesCount": tracked_files_count,
            "codeStatsSource": code_stats_source,
            "deepwikiStatus": deepwiki_status,
        },
        "materialFiles": {
            "repoJson": "raw/repo.json",
            "releaseJson": "raw/release.json",
            "contributorsJson": "raw/contributors.json",
            "deepwikiHtml": "raw/deepwiki.html",
            "tree": "raw/tree-depth3.txt",
            "keyFiles": "raw/key-files.txt",
            "codeStats": f"raw/{'scc.txt' if code_stats_source == 'scc' else ('cloc.txt' if code_stats_source == 'cloc' else 'file-count.txt')}",
        },
    }
    write_json(run_dir / "facts.json", facts)

    collector_summary = f"""# gitinfo 素材采集结果（仅客观信息）

此文件仅记录采集结果，不包含架构结论。

- 仓库：{target.owner}/{target.repo}
- 规范化 URL：{target.canonical_url}
- 本地仓库：{local_repo_dir}
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
- 近30天提交数：{commits_30d}
- 近90天提交数：{commits_90d}
- 最新提交：{last_commit_hash}，作者 {last_commit_author}，时间 {last_commit_date}
- 跟踪文件数：{tracked_files_count}
- 代码统计来源：{code_stats_source}
- DeepWiki 状态：{deepwiki_status}

## 素材文件

- facts.json
- raw/repo.json
- raw/release.json
- raw/contributors.json
- raw/deepwiki.html
- raw/tree-depth3.txt
- raw/key-files.txt
"""
    write_text(run_dir / "collector-summary.md", collector_summary)

    draft_report_name = Path(args.draft_report_file).name or "report.stage-a.md"

    context_draft = f"""# gitinfo 报告（Stage A 草稿，待补全）

## 一、项目定位（待补全）

- 仓库：{target.owner}/{target.repo}
- 项目描述（GitHub）：{description}
- 目标：请结合 README 与关键源码，补全“这个项目做什么、解决什么问题、面向谁”。

## 二、客观数据快照

- Stars：{stars}
- Forks：{forks}
- Watchers：{watchers}
- Open issues：{open_issues}
- License：{license_spdx}
- 默认分支：{default_branch}
- 最近推送：{pushed_at}
- 最新发布：{latest_release_tag}（{latest_release_date}）
- 贡献者数量（API样本）：{contributor_count}
- 近30天提交数：{commits_30d}
- 近90天提交数：{commits_90d}
- 最新提交：{last_commit_hash}，作者 {last_commit_author}，时间 {last_commit_date}
- 跟踪文件数：{tracked_files_count}
- 代码统计来源：{code_stats_source}
- DeepWiki 状态：{deepwiki_status}

## 三、状态判断（待补全）

- 请基于“客观数据快照”补充 3-5 条简评：
- 规模（大/中/小）
- 热度（高/中/低）
- 活跃度（高/中/低）
- 维护风险（低/中/高）

## 四、业务架构概要（待补全）

- 请基于 README + `raw/tree-depth3.txt` + `raw/key-files.txt` + 关键源码补全：
1. 核心功能
2. 业务模块分工
3. 关键技术与依赖
4. 功能如何被模块与技术支撑

## 五、关键流程（待补全）

- 用 6-10 步描述核心业务流程（业务视角，不展开实现细节）。

## 六、风险与边界（待补全）

- 维护风险、耦合风险、扩展边界，各给出 1-3 条。

## 七、证据索引

- 采集摘要：`collector-summary.md`
- 结构化数据：`facts.json`
- 仓库元信息：`raw/repo.json`
- 发布信息：`raw/release.json`
- 贡献者：`raw/contributors.json`
- DeepWiki 原文：`raw/deepwiki.html`
- 目录树：`raw/tree-depth3.txt`
- 关键文件清单：`raw/key-files.txt`
- 代码统计：`{facts["materialFiles"]["codeStats"]}`
"""
    write_text(run_dir / draft_report_name, context_draft)

    print("gitinfo collection complete")
    print(f"RUN_DIR={run_dir}")
    print(f"FACTS_FILE={run_dir / 'facts.json'}")
    print(f"COLLECTOR_SUMMARY={run_dir / 'collector-summary.md'}")
    print(f"DRAFT_REPORT_FILE={run_dir / draft_report_name}")
    print(f"FINAL_REPORT_FILE={run_dir / (Path(args.final_report_file).name or 'report.md')}")
    print(f"SANITIZED_REPO_URL={target.canonical_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
