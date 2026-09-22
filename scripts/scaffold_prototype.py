#!/usr/bin/env python3
"""Copy the bundled static wireframe starter into a new empty folder."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a new static wireframe project from the bundled starter."
    )
    parser.add_argument("output", type=Path, help="Destination folder")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_root = Path(__file__).resolve().parents[1]
    source = skill_root / "assets" / "wireframe-starter"
    target = args.output.expanduser().resolve()

    if not source.is_dir():
        print(f"ERROR: starter not found: {source}", file=sys.stderr)
        return 2

    if target.exists() and any(target.iterdir()):
        print(
            f"ERROR: destination is not empty: {target}\n"
            "Choose a new folder or review the existing project manually.",
            file=sys.stderr,
        )
        return 2

    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)

    print(f"Created wireframe project: {target}")
    print("Next: replace every {{TOKEN}}, remove unused modules, then validate the folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
