import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path

from config import CFLAGS, YELLOW, BOLD, RED, RESET, DIVIDER
from compiler import find_compiler, die
from headers import resolve_all_sources
from cache import (
    get_cache_binary_path,
    get_stale_sources,
    obj_path,
    write_cache_manifest,
    clear_cache,
    cleanup_orphans,
)


def compile_sources(
    stale_sources: list[str],
    all_sources: list[str],
    cc: str,
    binary: Path,
    compile_flags: list[str],
    lm: bool,
    label: str = "",
) -> None:
    tag = f"{cc} {label}".strip()
    for src in stale_sources:
        obj = obj_path(src, binary)
        cmd = [cc, *compile_flags, "-c", src, "-o", str(obj)]
        print(f"{BOLD}[{tag}]{RESET} compiling {src} → {obj}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            die("compilation failed", result.returncode)

    all_objects = [obj_path(src, binary) for src in all_sources]
    link_cmd = [cc, *compile_flags, "-o", str(binary), *[str(o) for o in all_objects]]
    if lm:
        link_cmd.append("-lm")
    print(f"{BOLD}[{tag}]{RESET} linking → {binary}")
    result = subprocess.run(link_cmd)
    if result.returncode != 0:
        die("linking failed", result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile, run, and clean up C source files."
    )

    parser.add_argument("source", nargs="?", help="The C source file to run")

    parser.add_argument(
        "--clean", action="store_true", help="Remove orphaned cache entries"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check for orphaned and corrupted cache entries",
    )

    parser.add_argument(
        "--force-clear-cache", action="store_true", help="Force clear cache"
    )

    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep copy of the binary in the source code directory",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Compile with debug flags and output the binary path for a debugger",
    )

    parser.add_argument("--lm", action="store_true", help="Link libm")

    parser.add_argument(
        "prog_args", nargs=argparse.REMAINDER, help="Arguments passed to the C program"
    )

    args = parser.parse_args()

    if args.force_clear_cache:
        clear_cache()
        sys.exit(0)

    if args.clean:
        cleanup_orphans(dry_run=True) if args.dry_run else cleanup_orphans()
        sys.exit(0)

    if not args.source:
        parser.print_help()
        sys.exit(1)

    source = args.source
    prog_args = args.prog_args

    try:
        if not os.path.isfile(source):
            die(f"file '{source}' not found")

        if not source.endswith(".c"):
            print(
                f"{YELLOW}warning:{RESET} '{source}' does not have a .c extension, proceeding anyway"
            )

        binary = get_cache_binary_path(source)
        cc = find_compiler()
        assert cc is not None
        all_sources = resolve_all_sources(source, cc)

        if args.debug:
            binary.parent.mkdir(parents=True, exist_ok=True)
            compile_sources(
                all_sources,
                all_sources,
                cc,
                binary,
                list(CFLAGS) + ["-O0"],
                args.lm,
                "debug",
            )
            print(str(binary))
            sys.exit(0)

        stale = (
            get_stale_sources(all_sources, binary, cc)
            if binary.exists()
            else all_sources
        )

        if not stale and binary.exists():
            print(f"{BOLD}[cache]{RESET} {source} — skipping compilation")
        else:
            binary.parent.mkdir(parents=True, exist_ok=True)
            compile_sources(stale, all_sources, cc, binary, CFLAGS, args.lm)

            src_origin = binary.parent / "source_origin.txt"
            if not src_origin.exists():
                with open(src_origin, "w", encoding="utf-8") as f:
                    f.write(os.path.abspath(source))

            write_cache_manifest(all_sources, binary, cc)

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
            if exit_code < 0:
                sig_name = signal.Signals(-exit_code).name
                print(f"{RED}[crashed with {sig_name}]{RESET}")
            else:
                print(f"{YELLOW}[exit {exit_code}]{RESET}")
                sys.exit(exit_code)

    except KeyboardInterrupt:
        sys.exit(1)
