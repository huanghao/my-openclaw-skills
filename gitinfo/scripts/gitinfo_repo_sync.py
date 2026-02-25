#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from git_common import parse_repo_url, resolve_repo_dir, best_effort_cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="Clone or update a GitHub repository locally")
    parser.add_argument("--repo-url", required=True, help="GitHub repository URL")
    parser.add_argument("--sources-root", default="~/workspace/sources")
    parser.add_argument("--ref", default="", help="Optional git ref to checkout")
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Shallow history depth (<=0 disables shallow behavior)",
    )
    args = parser.parse_args()

    try:
        owner, repo, canonical_url = parse_repo_url(args.repo_url)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    sources_root = Path(args.sources_root).expanduser()
    sources_root.mkdir(parents=True, exist_ok=True)

    local_repo_dir = resolve_repo_dir(sources_root, owner, repo)

    if not (local_repo_dir / ".git").exists():
        clone_cmd = ["git", "clone"]
        clone_cmd.extend(["--filter=blob:none", "--single-branch", "--no-tags"])
        if args.depth > 0:
            clone_cmd.extend(["--depth", str(args.depth)])
        if args.ref:
            clone_cmd.extend(["--branch", args.ref])
        clone_cmd.extend([canonical_url, str(local_repo_dir)])
        try:
            subprocess.run(clone_cmd, check=True)
        except subprocess.CalledProcessError:
            print(f"Clone failed for {canonical_url}", file=sys.stderr)
            return 1
    else:
        fetch_cmd = ["git", "fetch", "--prune", "--no-tags", "origin"]
        if args.depth > 0:
            fetch_cmd.extend(["--depth", str(args.depth)])
        ok, err = best_effort_cmd(fetch_cmd, cwd=local_repo_dir)
        if not ok:
            print(f"Warning: fetch failed, continue with local state: {local_repo_dir}", file=sys.stderr)
            if err:
                print(err, file=sys.stderr)

    if args.ref:
        ok, err = best_effort_cmd(["git", "checkout", args.ref], cwd=local_repo_dir)
        if not ok:
            ref_fetch_cmd = ["git", "fetch", "origin", args.ref]
            if args.depth > 0:
                ref_fetch_cmd.extend(["--depth", str(args.depth)])
            fetched, fetch_err = best_effort_cmd(ref_fetch_cmd, cwd=local_repo_dir)
            if fetched:
                ok, err = best_effort_cmd(["git", "checkout", "FETCH_HEAD"], cwd=local_repo_dir)
            elif fetch_err:
                err = f"{err}\n{fetch_err}".strip()
        if not ok:
            print(f"Warning: checkout failed for ref {args.ref}, continue with current HEAD", file=sys.stderr)
            if err:
                print(err, file=sys.stderr)

    ok, head_commit = best_effort_cmd(["git", "rev-parse", "--short", "HEAD"], cwd=local_repo_dir)
    print("repo sync complete")
    print(f"LOCAL_REPO_PATH={local_repo_dir}")
    print(f"SANITIZED_REPO_URL={canonical_url}")
    print(f"HEAD_COMMIT={head_commit if ok and head_commit else 'n/a'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
