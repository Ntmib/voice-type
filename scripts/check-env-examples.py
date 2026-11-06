#!/usr/bin/env python3
"""Fail when tracked env templates contain credential-like values."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

SENSITIVE_NAME = re.compile(
    r"(?:SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|PRIVATE_KEY|SERVICE_KEY|DATABASE_URL|ENCRYPTION_KEY)",
    re.IGNORECASE,
)
PLACEHOLDER = re.compile(
    r"^(?:replace-me|change-me|your[-_].*|placeholder|<[^>]+>)$",
    re.IGNORECASE,
)
ANGLE_PLACEHOLDER = re.compile(r"<[^>]+>")


def tracked_env_examples() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"], text=False)
    return [
        Path(raw.decode())
        for raw in output.split(b"\0")
        if raw and Path(raw.decode()).name == ".env.example"
    ]


def is_placeholder(value: str) -> bool:
    value = value.strip().strip('"\'')
    return not value or bool(PLACEHOLDER.fullmatch(value)) or bool(ANGLE_PLACEHOLDER.search(value))


def main() -> int:
    failures: list[tuple[Path, int, str]] = []
    for path in tracked_env_examples():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, value = stripped.split("=", 1)
            name = name.strip()
            if SENSITIVE_NAME.search(name) and not is_placeholder(value):
                failures.append((path, line_number, name))

    if failures:
        print("Credential-like values found in tracked env templates:")
        for path, line_number, name in failures:
            print(f"- {path}:{line_number}: {name}")
        return 1

    print("Tracked env templates contain placeholders only for secret-like fields.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
