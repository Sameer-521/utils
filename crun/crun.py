#!/usr/bin/env python3
"""
crun - Compile, run, and clean up a C source file (Go-style).
Usage: crun <file.c> [program args...]
"""

import sys
import os
import subprocess
import shutil
import re

# ANSI colours
RED    = '\033[0;31m'
GREEN  = '\033[0;32m'
YELLOW = '\033[0;33m'
BOLD   = '\033[1m'
RESET  = '\033[0m'

DIVIDER = '─' * 40

# ── Standard flags ─────────────────────────────────────────────────────────────
CFLAGS = [
    '-std=c99',
    '-Wall',
    '-Wextra',
    '-Wpedantic',
    '-Wconversion',
    '-Wshadow',
    '-g',
]


def die(msg: str, code: int = 1) -> None:
    print(f"{RED}error:{RESET} {msg}", file=sys.stderr)
    sys.exit(code)


def find_compiler() -> str:
    for cc in ('gcc', 'cc', 'clang'):
        if shutil.which(cc):
            return cc
    die("no C compiler found (looked for gcc, cc, clang)")


def derive_binary(source: str) -> str:
    """Strip the file extension to get the binary name."""
    binary = re.sub(r'\.[^.]+$', '', source)
    if binary == source:          # no extension — avoid clobbering source
        binary = source + '.out'
    return binary


def main() -> None:
    if len(sys.argv) < 2:
        print(f"{BOLD}Usage:{RESET} crun <file.c> [program args...]")
        sys.exit(1)

    source    = sys.argv[1]
    prog_args = sys.argv[2:]

    # ── Validate source ────────────────────────────────────────────────────────
    if not os.path.isfile(source):
        die(f"file '{source}' not found")

    if not source.endswith('.c'):
        print(f"{YELLOW}warning:{RESET} '{source}' does not have a .c extension, proceeding anyway")

    binary = derive_binary(source)
    cc     = find_compiler()

    # ── Compile ────────────────────────────────────────────────────────────────
    compile_cmd = [cc, *CFLAGS, '-o', binary, source]
    print(f"{BOLD}[{cc}]{RESET} compiling {source} → {binary}")

    result = subprocess.run(compile_cmd)
    if result.returncode != 0:
        die("compilation failed", result.returncode)

    # ── Run ────────────────────────────────────────────────────────────────────
    run_display = ' '.join([binary, *prog_args]) if prog_args else binary
    print(f"{BOLD}[run]{RESET} {run_display}")
    print(DIVIDER)

    exe = binary if os.path.isabs(binary) else f'./{binary}'
    run_result = subprocess.run([exe, *prog_args])
    exit_code  = run_result.returncode

    print(DIVIDER)

    # ── Clean up ───────────────────────────────────────────────────────────────
    try:
        os.remove(binary)
    except OSError as e:
        print(f"{YELLOW}warning:{RESET} could not remove binary '{binary}': {e}", file=sys.stderr)

    if exit_code != 0:
        print(f"{YELLOW}[exit {exit_code}]{RESET}")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
