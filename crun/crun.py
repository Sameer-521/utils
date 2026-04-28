#!/usr/bin/env python3
"""
crun - Compile, run, and clean up a C source file (Go-style).
Usage: crun <file.c> [program args...]
"""

import sys
import os
import subprocess
import shutil
import hashlib
from pathlib import Path

# ANSI colours
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BOLD = "\033[1m"
RESET = "\033[0m"

DIVIDER = "─" * 40

# ── Standard flags ─────────────────────────────────────────────────────────────
CFLAGS = [
    "-std=c99",
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Wconversion",
    "-Wshadow",
    "-g",
]


def die(msg: str, code: int = 1) -> None:
    print(f"{RED}error:{RESET} {msg}", file=sys.stderr)
    sys.exit(code)


def find_compiler() -> str | None:
    for cc in ("gcc", "cc", "clang"):
        if shutil.which(cc):
            return cc
    die("no C compiler found (looked for gcc, cc, clang)")


def cache_binary_path(source: str) -> Path:
    abs_src = os.path.abspath(source)
    key = hashlib.sha256(abs_src.encode()).hexdigest()[:16]
    stem = Path(source).stem
    return Path.home() / ".cache" / "crun" / key / stem


def is_cached(source: str, binary: Path) -> bool:
    if not binary.exists():
        return False
    return binary.stat().st_mtime >= os.path.getmtime(source)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"{BOLD}Usage:{RESET} crun <file.c> [program args...]")
        sys.exit(1)

    source = sys.argv[1]
    prog_args = sys.argv[2:]

    # ── Validate source ────────────────────────────────────────────────────────
    if not os.path.isfile(source):
        die(f"file '{source}' not found")

    if not source.endswith(".c"):
        print(
            f"{YELLOW}warning:{RESET} '{source}' does not have a .c extension, proceeding anyway"
        )

    binary = cache_binary_path(source)
    cc = find_compiler()

    # ── Compile ────────────────────────────────────────────────────────────────
    if is_cached(source, binary):
        print(f"{BOLD}[cache]{RESET} {source} — skipping compilation")
    else:
        binary.parent.mkdir(parents=True, exist_ok=True)
        compile_cmd = [cc, *CFLAGS, "-o", str(binary), source]
        print(f"{BOLD}[{cc}]{RESET} compiling {source} → {binary}")

        result = subprocess.run(compile_cmd)
        if result.returncode != 0:
            die("compilation failed", result.returncode)

    # ── Run ────────────────────────────────────────────────────────────────────
    if len(prog_args) > 3:
        run_display = " ".join(
            [str(binary), *prog_args[:3], f"...({len(prog_args) - 3} more)"]
        )
    else:
        run_display = " ".join([str(binary), *prog_args])

    print(f"{BOLD}[run]{RESET} {run_display}")
    print(DIVIDER)

    run_result = subprocess.run([str(binary), *prog_args])
    exit_code = run_result.returncode

    print(f"\n{DIVIDER}")

    if exit_code != 0:
        print(f"{YELLOW}[exit {exit_code}]{RESET}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
