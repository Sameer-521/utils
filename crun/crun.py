#!/usr/bin/env python3
"""
crun - Compile, run, and clean up a C source file (Go-style).
Usage: crun <file.c> [program args...]
"""

import argparse
import sys
import os
import signal
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


def cleanup_orphans():
    cache_dir = Path.home() / ".cache" / "crun"
    purged = 0

    if not cache_dir.is_dir():
        return

    for entry in cache_dir.iterdir():
        if entry.is_dir():
            origin_file = entry / "source_origin.txt"

            if origin_file.exists():
                source_path_str = origin_file.read_text().strip()
                source_path = Path(source_path_str)

                if not source_path.exists():
                    print(
                        f"Purging orphaned cache: {entry.name} (Source missing: {source_path_str})"
                    )
                    shutil.rmtree(entry)
                    purged += 1
            else:
                print(
                    f"Purging potential corrupted entry: {entry.name} (Missing source_origin.txt)"
                )
                shutil.rmtree(entry)
                purged += 1

    if purged == 0:
        print("Nothing to cleanup")


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
    key = hashlib.sha256(abs_src.encode()).hexdigest()[:8]
    stem = Path(source).stem
    folder_name = f"{stem}-{key}"
    return Path.home() / ".cache" / "crun" / folder_name / stem


def is_cached(source: str, binary: Path) -> bool:
    if not binary.exists():
        return False
    return binary.stat().st_mtime >= os.path.getmtime(source)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile, run, and clean up C source files."
    )

    # source file (optional if cleaning)
    parser.add_argument("source", nargs="?", help="The C source file to run")

    # cleanup flag
    parser.add_argument(
        "--clean", action="store_true", help="Remove orphaned cache entries"
    )

    # remaining args
    parser.add_argument(
        "prog_args", nargs=argparse.REMAINDER, help="Arguments passed to the C program"
    )

    args = parser.parse_args()

    # cleanup
    if args.clean:
        cleanup_orphans()
        sys.exit(0)

    if not args.source:
        parser.print_help()
        sys.exit(1)

    source = args.source
    prog_args = args.prog_args

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
        else:
            with open(binary.parent / "source_origin.txt", "w", encoding="utf-8") as f:
                f.write(os.path.abspath(source))

    # ── Run ────────────────────────────────────────────────────────────────────
    if len(prog_args) > 3:
        run_display = " ".join(
            [str(binary), *prog_args[:3], f"...({len(prog_args) - 3} more)"]
        )
    else:
        run_display = " ".join([str(binary), *prog_args])

    print(f"{BOLD}[run]{RESET} {run_display}")
    print(DIVIDER)

    run_result = subprocess.run(
        [str(binary), *prog_args], capture_output=False, text=True
    )
    exit_code = run_result.returncode

    print(f"\n{DIVIDER}")

    if exit_code != 0:
        # Check for negative exit codes (which indicate signals on Unix)
        if exit_code < 0:
            sig_name = signal.Signals(-exit_code).name
            print(f"{RED}[crashed with {sig_name}]{RESET}")
        else:
            print(f"{YELLOW}[exit {exit_code}]{RESET}")
            sys.exit(exit_code)


if __name__ == "__main__":
    main()
