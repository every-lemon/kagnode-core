#!/usr/bin/env python3
"""Check the committed source inventory without modifying the worktree."""

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def check():
    entries = json.loads((ROOT / "packaging/source-files.json").read_text())
    if not isinstance(entries, list) or not all(isinstance(x, str) for x in entries):
        raise ValueError("Source inventory must be a list of paths")
    tracked = sorted(
        x
        for x in subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
        if x
    )
    if entries != sorted(set(entries)) or entries != tracked:
        missing = sorted(set(tracked) - set(entries))
        extra = sorted(set(entries) - set(tracked))
        raise ValueError(
            f"Source inventory differs: missing={missing}, extra={extra}; require sorted unique paths"
        )
    print(f"Source inventory matches all {len(entries)} tracked files")


if __name__ == "__main__":
    check()
