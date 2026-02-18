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

    # SSH-like: git@github.com:owner/repo(.git)
    ssh_match = re.match(r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/?#]+?)(?:\.git)?$", raw)
    if ssh_match:
        owner = ssh_match.group("owner")
        repo = ssh_match.group("repo")
        return RepoTarget(owner=owner, repo=repo, canonical_url=f"https://github.com/{owner}/{repo}")

    parsed = urlparse(raw)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError(f"Unsupported URL (GitHub required): {raw}")

    # Drop query/fragment by only using path.
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
        "User-Agent": "gitinfo-skill/1.0",
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


def collect_tree_top2(repo_dir: Path) -> list[str]:
    entries: list[str] = []
    root_depth = len(repo_dir.parts)
    for root, dirs, files in os.walk(repo_dir):
        current = Path(root)
        rel_depth = len(current.parts) - root_depth
        if ".git" in dirs:
            dirs.remove(".git")
        if rel_depth > 2:
            dirs[:] = []
            continue

        for name in dirs:
            p = current / name
            rel = p.relative_to(repo_dir)
            if len(rel.parts) <= 2:
                entries.append(str(rel))
        for name in files:
            p = current / name
            rel = p.relative_to(repo_dir)
            if len(rel.parts) <= 2:
                entries.append(str(rel))

    return sorted(set(entries))[:200]


def first_existing(paths: list[Path]) -> str:
    for p in paths:
        if p.exists():
            return p.name
    return "none"


def main() -> int:
    parser = argparse.ArgumentParser(description="gitinfo quick analyzer")
    parser.add_argument("--repo-url", required=True, help="GitHub repository URL")
    parser.add_argument("--sources-root", default="~/workspace/sources")
    parser.add_argument("--output-root", default="~/workspace/sources/gitinfo-outputs")
    parser.add_argument("--ref", default="")
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
        try:
            subprocess.run(["git", "checkout", args.ref], cwd=local_repo_dir, check=True)
        except subprocess.CalledProcessError:
            print(f"Warning: checkout failed for ref {args.ref}, continue with current HEAD", file=sys.stderr)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_root / f"{target.repo}-{timestamp}"
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

    contributor_count = "n/a"
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

    if code_stats_source == "file-count":
        file_count = sum(1 for p in local_repo_dir.rglob("*") if p.is_file() and ".git" not in p.parts)
        write_text(raw_dir / "file-count.txt", f"{file_count}\n")

    tree_entries = collect_tree_top2(local_repo_dir)
    write_text(raw_dir / "tree-top2.txt", "\n".join(tree_entries) + ("\n" if tree_entries else ""))

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
            "codeStatsSource": code_stats_source,
            "deepwikiStatus": deepwiki_status,
        },
    }
    write_json(run_dir / "facts.json", facts)

    context_md = f"""# gitinfo 合并报告（深入分析上下文）\n\n这是后续深入研究的主上下文文件。该文件已合并“快速摘要 + 架构概要 + 上下文指引”。\n\n## 一、仓库信息\n\n- 名称：{target.owner}/{target.repo}\n- URL：{target.canonical_url}\n- 本地路径：{local_repo_dir}\n- 输出目录：{run_dir}\n- 生成时间（UTC）：{now_utc_iso()}\n\n## 二、快速摘要\n\n- Stars：{stars}\n- Forks：{forks}\n- Watchers：{watchers}\n- Open issues：{open_issues}\n- License：{license_spdx}\n- 默认分支：{default_branch}\n- 最近推送：{pushed_at}\n- 最新发布：{latest_release_tag}（{latest_release_date}）\n- 贡献者数量（API样本）：{contributor_count}\n- 近30天提交数：{commits_30d}\n- 近90天提交数：{commits_90d}\n- 最新提交：{last_commit_hash}，作者 {last_commit_author}，时间 {last_commit_date}\n- 代码统计来源：{code_stats_source}\n- DeepWiki 状态：{deepwiki_status}\n\n## 三、架构概要（Quick）\n\n### 1) 高层观察\n- 项目描述：{description}\n- 默认分支：{default_branch}\n- 最近推送：{pushed_at}\n\n### 2) 结构轮廓\n- 请先阅读 `raw/tree-top2.txt`，它是项目边界的主视图（顶层与二级目录）。\n\n### 3) 运行与入口线索\n- package.json 的 scripts / main 字段\n- cmd/、bin/、src/main*、app*、server*、cli* 目录\n- docker-compose、Makefile、CI workflow 中的 build/run 路径\n\n### 4) 扩展点线索\n- 优先关注 plugin/provider/channel/adapter 风格目录及其注册代码。\n\n### 5) 说明\n- 这里仅提供高层架构概要，不展开具体模块实现细节。\n\n## 四、证据路径\n\n- 结构化事实：facts.json\n- 原始数据与扫描结果：raw/\n- 目录样本：raw/tree-top2.txt\n- 代码统计：raw/scc.txt 或 raw/cloc.txt 或 raw/file-count.txt\n- DeepWiki 抓取：raw/deepwiki.html 与 raw/deepwiki.http.json\n\n## 五、建议的下一步提问\n\n- “基于这份上下文，用 6-10 步解释运行时请求生命周期。”\n- “梳理最关键的 5 个子系统及其边界。”\n- “列出可能的扩展点，以及新增功能应从哪里接入。”\n"""
    write_text(run_dir / "context.md", context_md)

    print("gitinfo complete")
    print(f"RUN_DIR={run_dir}")
    print(f"CONTEXT_FILE={run_dir / 'context.md'}")
    print(f"SANITIZED_REPO_URL={target.canonical_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
