from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def run_cmd(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=check,
    )


def best_effort_cmd(args: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    try:
        out = run_cmd(args, cwd=cwd, check=True)
        return True, out.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, (exc.stderr or exc.stdout or "").strip()


def parse_repo_url(raw: str) -> tuple[str, str, str]:
    raw = raw.strip()

    ssh_match = re.match(r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/?#]+?)(?:\.git)?$", raw)
    if ssh_match:
        owner = ssh_match.group("owner")
        repo = ssh_match.group("repo")
        return owner, repo, f"https://github.com/{owner}/{repo}"

    parsed = urlparse(raw)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError(f"Unsupported URL (GitHub required): {raw}")

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from URL: {raw}")

    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        raise ValueError(f"Cannot parse owner/repo from URL: {raw}")
    return owner, repo, f"https://github.com/{owner}/{repo}"


def match_origin(origin_url: str, owner: str, repo: str) -> bool:
    lower = origin_url.lower()
    return "github.com" in lower and f"{owner.lower()}/{repo.lower()}" in lower


def resolve_repo_dir(sources_root: Path, owner: str, repo: str) -> Path:
    local_repo_dir = sources_root / repo
    if (local_repo_dir / ".git").exists():
        ok, origin = best_effort_cmd(["git", "remote", "get-url", "origin"], cwd=local_repo_dir)
        if ok and not match_origin(origin, owner, repo):
            local_repo_dir = sources_root / f"{repo}-{owner}"
    return local_repo_dir


def github_request(
    url: str, token: str | None = None
) -> tuple[int, dict[str, str], str]:
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


def read_origin_url(repo_dir: Path) -> str:
    ok, out = best_effort_cmd(["git", "remote", "get-url", "origin"], cwd=repo_dir)
    return out.strip() if ok and out else ""


def parse_github_remote(origin_url: str) -> tuple[str, str, str]:
    if not origin_url:
        return "", "", ""

    try:
        owner, repo, canonical_url = parse_repo_url(origin_url)
        return owner, repo, canonical_url
    except ValueError:
        return "", "", ""
