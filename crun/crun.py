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


def cleanup_orphans(dry_run: bool = False):
    cache_dir = Path.home() / ".cache" / "crun"
    to_purge = []

    if not cache_dir.is_dir():
        return

    if dry_run:
        print(f"{BOLD}[cleanup --dry-run]{RESET}")
    else:
        print(f"{BOLD}[cleanup]{RESET}")

    for entry in cache_dir.iterdir():
        if entry.is_dir():
            origin_file = entry / "source_origin.txt"

            if origin_file.exists():
                source_path_str = origin_file.read_text().strip()
                source_path = Path(source_path_str)

                if not source_path.exists():
                    p_dict = {
                        "entry": entry,
                        "msg": f"Purging orphaned cache entry: {entry.name} (Source missing: {source_path_str})",
                    }
                    if dry_run:
                        p_dict["msg"] = (
                            f"Found orphaned cache entry: {entry.name} (Source missing: {source_path_str})"
                        )
                    to_purge.append(p_dict)

            else:
                p_dict = {
                    "entry": entry,
                    "msg": f"Purging potential corrupted entry: {entry.name} (Missing source_origin.txt)",
                }
                if dry_run:
                    p_dict["msg"] = (
                        f"Found potential corrupted entry: {entry.name} (Missing source_origin.txt)"
                    )
                to_purge.append(p_dict)

    if not to_purge:
        print("Nothing to cleanup")
    else:
        for item in to_purge:
            print(item["msg"])
            if not dry_run:
                shutil.rmtree(item["entry"])


def die(msg: str, code: int = 1) -> None:
    print(f"{RED}error:{RESET} {msg}", file=sys.stderr)
    sys.exit(code)


def find_compiler() -> str | None:
    for cc in ("gcc", "cc", "clang"):
        if shutil.which(cc):
            return cc
    die("no C compiler found (looked for gcc, cc, clang)")


def get_cache_binary_path(source: str) -> Path:
    abs_src = os.path.abspath(source)
    key = hashlib.sha256(abs_src.encode()).hexdigest()[:8]
    stem = Path(source).stem
    folder_name = f"{stem}-{key}"
    return Path.home() / ".cache" / "crun" / folder_name / stem


def cache_source(source: str, binary: Path):
    cache_dir = binary.parent
    source_hash_file = cache_dir / "source_hash.txt"

    with open(source, "rb") as f:
        src_hash = hashlib.file_digest(f, "sha256").hexdigest()

    with open(source_hash_file, "w") as f:
        f.write(src_hash)


def is_source_cached(source: str, binary: Path) -> bool:
    cache_dir = binary.parent
    source_hash_file = cache_dir / "source_hash.txt"

    if not binary.exists() or not source_hash_file.exists():
        return False

    with open(source_hash_file, "r") as f:
        stored_hash = f.read().strip()

    with open(source, "rb") as f:
        src_hash = hashlib.file_digest(f, "sha256").hexdigest()

    return stored_hash == src_hash


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

    # dry run cleanup
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check for orphaned and corrupted cache entries",
    )

    # remaining args
    parser.add_argument(
        "prog_args", nargs=argparse.REMAINDER, help="Arguments passed to the C program"
    )

    args = parser.parse_args()

    # cleanup
    if args.clean:
        cleanup_orphans(dry_run=True) if args.dry_run else cleanup_orphans()
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

    binary = get_cache_binary_path(source)
    cc = find_compiler()

    # ── Compile ────────────────────────────────────────────────────────────────
    if is_source_cached(source, binary):
        print(f"{BOLD}[cache]{RESET} {source} — skipping compilation")
    else:
        binary.parent.mkdir(parents=True, exist_ok=True)
        compile_cmd = [cc, *CFLAGS, "-o", str(binary), source]
        print(f"{BOLD}[{cc}]{RESET} compiling {source} → {binary}")

        result = subprocess.run(compile_cmd)
        if result.returncode != 0:
            die("compilation failed", result.returncode)
        else:
            src_origin = binary.parent / "source_origin.txt"
            if not src_origin.exists():
                with open(src_origin, "w", encoding="utf-8") as f:
                    f.write(os.path.abspath(source))

            # update hash
            cache_source(source, binary)

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
