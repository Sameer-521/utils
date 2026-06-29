#!/usr/bin/env python3
"""
crun - Compile, run, and clean up a C source file (Go-style).
Usage: crun <file.c> [program args...]
"""

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
from graphlib import TopologicalSorter
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "crun"

# ANSI colours
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BOLD = "\033[1m"
RESET = "\033[0m"

DIVIDER = "─" * 40

# ── Standard flags ─────────────────────────────────────────────────────────────
CFLAGS = [
    "-std=gnu99",
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Wconversion",
    "-Wshadow",
    "-g",
]


def resolve_local_headers(source_file: str, cc: str = "gcc") -> dict[str, float]:
    """
    Use gcc -MM to discover local headers, then stat them for mtimes.
    Returns {absolute_header_path: mtime}.
    """
    source_file = os.path.realpath(source_file)
    source_dir = os.path.dirname(source_file)

    try:
        result = subprocess.run(
            [cc, "-MM", source_file],
            capture_output=True,
            text=True,
            cwd=source_dir,
        )
    except FileNotFoundError:
        return {}

    if result.returncode != 0:
        return {}

    output = result.stdout.replace("\\\n", " ")
    if ":" in output:
        _, deps = output.split(":", 1)
    else:
        deps = output

    headers: dict[str, float] = {}
    for token in deps.split():
        token = token.strip()
        if not token or token.endswith((".c", ".o")):
            continue
        abs_path = os.path.realpath(os.path.join(source_dir, token))
        if os.path.isfile(abs_path):
            headers[abs_path] = os.stat(abs_path).st_mtime

    return headers


def find_source_from_header(header_path: str) -> str | None:
    """
    Given an absolute header path, return the corresponding .c source
    file if it exists in the same directory.  Returns None otherwise.
    """
    stem, _ = os.path.splitext(header_path)
    candidate = stem + ".c"
    if os.path.isfile(candidate):
        return os.path.realpath(candidate)
    return None


def resolve_all_sources(main_source: str, cc: str) -> list[str]:
    """
    DFS through local #include chains (via gcc -MM) to find every
    reachable .c file.  Returns sources in topological order (deps first).
    """
    main_source = os.path.realpath(main_source)

    dep_graph: dict[str, list[str]] = {}

    def discover(node: str) -> None:
        if node in dep_graph:
            return
        dep_graph[node] = []  # mark as being processed to prevent re-entry
        headers = resolve_local_headers(node, cc)
        deps: list[str] = []
        for header_path in headers:
            src = find_source_from_header(header_path)
            if src and src != node:
                deps.append(src)
                discover(src)
        dep_graph[node] = deps

    discover(main_source)

    ts = TopologicalSorter(dep_graph)
    return list(ts.static_order())


def headers_changed(snapshot: dict[str, float]) -> bool:
    """
    Returns True if any header in the snapshot has a different mtime.
    """
    for path, old_mtime in snapshot.items():
        try:
            if os.stat(path).st_mtime != old_mtime:
                return True
        except FileNotFoundError:
            return True  # deleted = changed
    return False


def clear_cache():
    if not CACHE_DIR.is_dir():
        return

    print(f"{BOLD}[cleanup --force-clear-cache]{RESET}")
    for entry in CACHE_DIR.iterdir():
        if entry.is_dir():
            print(f"Purging {entry}")
            shutil.rmtree(entry)

    print("Cache cleared")


def cleanup_orphans(dry_run: bool = False) -> None:
    to_purge = []

    if not CACHE_DIR.is_dir():
        return

    if dry_run:
        print(f"{BOLD}[cleanup --dry-run]{RESET}")
    else:
        print(f"{BOLD}[cleanup]{RESET}")

    for entry in CACHE_DIR.iterdir():
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
                        p_dict["msg"] = p_dict["msg"].replace("Purging", "Found")

                    to_purge.append(p_dict)

            else:
                p_dict = {
                    "entry": entry,
                    "msg": f"Purging potential corrupted entry: {entry.name} (Missing source_origin.txt)",
                }
                if dry_run:
                    p_dict["msg"] = p_dict["msg"].replace("Purging", "Found")

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


def write_cache_manifest(sources: list[str], binary: Path, cc: str) -> None:
    cache_dir = binary.parent
    manifest_file = cache_dir / "cache_manifest.json"

    sources_hashes: dict[str, str] = {}
    all_headers: dict[str, float] = {}

    for src in sources:
        try:
            with open(src, "rb") as f:
                sources_hashes[src] = hashlib.file_digest(f, "sha256").hexdigest()
        except FileNotFoundError:
            continue
        hdrs = resolve_local_headers(src, cc)
        all_headers.update(hdrs)

    manifest_contents = {
        "sources": sources_hashes,
        "headers": all_headers,
    }

    with open(manifest_file, "w") as file:
        json.dump(manifest_contents, file, indent=4)


def read_stored_headers(binary: Path) -> tuple[dict[str, str], dict[str, float]]:
    cache_dir = binary.parent
    cache_manifest_file = cache_dir / "cache_manifest.json"

    try:
        with open(cache_manifest_file, "r") as f:
            contents = json.load(f)
            return contents.get("sources", {}), contents.get("headers", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}, {}


def is_source_cached(sources: list[str], binary: Path) -> bool:
    cache_dir = binary.parent
    cache_manifest_file = cache_dir / "cache_manifest.json"

    if not binary.exists() or not cache_manifest_file.exists():
        return False

    try:
        with open(cache_manifest_file, "r") as f:
            contents = json.load(f)
            stored_sources = contents.get("sources", {})
            stored_headers = contents.get("headers", {})
    except (json.JSONDecodeError, KeyError):
        return False

    if len(stored_sources) != len(sources):
        return False

    for src in sources:
        if src not in stored_sources:
            return False
        try:
            with open(src, "rb") as f:
                current_hash = hashlib.file_digest(f, "sha256").hexdigest()
        except FileNotFoundError:
            return False
        if stored_sources[src] != current_hash:
            return False

    for path, old_mtime in stored_headers.items():
        try:
            if Path(path).stat().st_mtime != old_mtime:
                return False
        except FileNotFoundError:
            return False

    return True


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

    # force-clear cache
    parser.add_argument(
        "--force-clear-cache", action="store_true", help="Force clear cache"
    )

    # keep binary in source code directory
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep copy of the binary in the source code directory",
    )

    # debug mode
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Compile with debug flags and output the binary path for a debugger",
    )

    # link math.h
    parser.add_argument("--lm", action="store_true", help="Link libm")

    # remaining args
    parser.add_argument(
        "prog_args", nargs=argparse.REMAINDER, help="Arguments passed to the C program"
    )

    args = parser.parse_args()

    if args.force_clear_cache:
        clear_cache()
        sys.exit(0)

    # cleanup
    if args.clean:
        cleanup_orphans(dry_run=True) if args.dry_run else cleanup_orphans()
        sys.exit(0)

    if not args.source:
        parser.print_help()
        sys.exit(1)

    source = args.source
    prog_args = args.prog_args
    try:
        # ── Validate source ────────────────────────────────────────────────────────
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

        # ── Compile ────────────────────────────────────────────────────────────────
        if args.debug:
            binary.parent.mkdir(parents=True, exist_ok=True)
            compile_flags = list(CFLAGS) + ["-O0"]
            object_files = []
            for src in all_sources:
                obj = binary.parent / (
                    Path(src).stem
                    + "."
                    + hashlib.sha256(src.encode()).hexdigest()[:8]
                    + ".o"
                )
                object_files.append(obj)
                cmd = [cc, *compile_flags, "-c", src, "-o", str(obj)]
                print(
                    f"{BOLD}[{cc} debug]{RESET} compiling {src} → {obj}",
                    file=sys.stderr,
                )
                result = subprocess.run(cmd)
                if result.returncode != 0:
                    die("compilation failed", result.returncode)

            link_cmd = [
                cc,
                *compile_flags,
                "-o",
                str(binary),
                *[str(o) for o in object_files],
            ]
            if args.lm:
                link_cmd.append("-lm")
            print(f"{BOLD}[{cc} debug]{RESET} linking → {binary}", file=sys.stderr)
            result = subprocess.run(link_cmd)
            if result.returncode != 0:
                die("linking failed", result.returncode)

            print(str(binary))
            sys.exit(0)

        elif is_source_cached(all_sources, binary):
            print(f"{BOLD}[cache]{RESET} {source} — skipping compilation")
        else:
            binary.parent.mkdir(parents=True, exist_ok=True)
            object_files = []
            for src in all_sources:
                obj = binary.parent / (
                    Path(src).stem
                    + "."
                    + hashlib.sha256(src.encode()).hexdigest()[:8]
                    + ".o"
                )
                object_files.append(obj)
                cmd = [cc, *CFLAGS, "-c", src, "-o", str(obj)]
                print(f"{BOLD}[{cc}]{RESET} compiling {src} → {obj}")
                result = subprocess.run(cmd)
                if result.returncode != 0:
                    die("compilation failed", result.returncode)

            link_cmd = [
                cc,
                *CFLAGS,
                "-o",
                str(binary),
                *[str(o) for o in object_files],
            ]
            if args.lm:
                link_cmd.append("-lm")
            print(f"{BOLD}[{cc}]{RESET} linking → {binary}")
            result = subprocess.run(link_cmd)
            if result.returncode != 0:
                die("linking failed", result.returncode)

            src_origin = binary.parent / "source_origin.txt"
            if not src_origin.exists():
                with open(src_origin, "w", encoding="utf-8") as f:
                    f.write(os.path.abspath(source))

            write_cache_manifest(all_sources, binary, cc)

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

    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
