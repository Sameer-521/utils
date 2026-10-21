import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import CFLAGS, YELLOW, BOLD, RED, RESET, DIVIDER
from compiler import find_compiler, die
from headers import resolve_all_sources, resolve_local_headers, include_dirs
from cache import (
    get_cache_binary_path,
    get_stale_sources,
    obj_path,
    write_cache_manifest,
    clear_cache,
    cleanup_orphans,
    load_header_scans,
)


def compile_sources(
    stale_sources: list[str],
    all_sources: list[str],
    cc: str,
    binary: Path,
    compile_flags: list[str],
    lm: bool,
    label: str = "",
    debug: bool = False,
    libs: tuple[str, ...] = (),
) -> None:
    out = sys.stderr if debug else sys.stdout
    tag = f"{cc} {label}".strip()
    def compile_cmd(src: str, obj: Path, extra: list[str]) -> list[str]:
        include_flags = [f"-I{d}" for d in include_dirs(src)]
        return [cc, *compile_flags, *extra, *include_flags, "-c", src, "-o", str(obj)]

    if len(stale_sources) < 2:
        # Zero or one stale source: run exactly as before, stdio inherited.
        for src in stale_sources:
            obj = obj_path(src, binary)
            cmd = compile_cmd(src, obj, [])
            print(f"{BOLD}[{tag}]{RESET} compiling {src} → {obj}", file=out)
            result = subprocess.run(cmd)
            if result.returncode != 0:
                die("compilation failed", result.returncode)
    else:
        # Two or more: compile concurrently (at most cpu_count jobs), capture
        # each job's output, and replay it in source order.
        extra = ["-fdiagnostics-color=always"] if sys.stderr.isatty() else []
        jobs = [(src, obj_path(src, binary)) for src in stale_sources]
        n = len(jobs)
        lock = threading.Lock()
        stop = False  # no new jobs may start (a job failed, or interrupted)
        kill = False  # running jobs must be killed (interrupted)
        next_idx = 0
        running: set[subprocess.Popen] = set()
        results: list = [None] * n  # (returncode, stdout, stderr) or Exception
        done = [threading.Event() for _ in range(n)]

        def worker() -> None:
            nonlocal stop, next_idx
            while True:
                # Claiming an index and checking `stop` are atomic, so a job
                # is only skipped if a job before it in order has already
                # failed: the first failure in order is always reported.
                with lock:
                    if stop or next_idx >= n:
                        return
                    i = next_idx
                    next_idx += 1
                src, obj = jobs[i]
                failed = True
                try:
                    proc = subprocess.Popen(
                        compile_cmd(src, obj, extra),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    with lock:
                        running.add(proc)
                        if kill:
                            proc.kill()
                    try:
                        so, se = proc.communicate()
                    finally:
                        with lock:
                            running.discard(proc)
                    results[i] = (proc.returncode, so, se)
                    failed = proc.returncode != 0
                except BaseException as exc:  # reported in order by the main thread
                    results[i] = exc
                finally:
                    if failed:
                        with lock:
                            stop = True
                    done[i].set()

        def emit(stream, data: bytes) -> None:
            if not data:
                return
            stream.flush()
            buf = getattr(stream, "buffer", None)
            if buf is not None:
                buf.write(data)
                buf.flush()
            else:
                stream.write(data.decode(errors="replace"))
                stream.flush()

        workers = min(os.cpu_count() or 1, n)
        pool = ThreadPoolExecutor(max_workers=workers)
        try:
            for _ in range(workers):
                pool.submit(worker)
            for i, (src, obj) in enumerate(jobs):
                done[i].wait()
                print(f"{BOLD}[{tag}]{RESET} compiling {src} → {obj}", file=out)
                res = results[i]
                if isinstance(res, BaseException):
                    raise res
                code, so, se = res
                emit(sys.stdout, so)
                emit(sys.stderr, se)
                if code != 0:
                    die("compilation failed", code)
        except KeyboardInterrupt:
            with lock:
                stop = kill = True
                for proc in running:
                    proc.kill()
            raise
        finally:
            # No new jobs start; wait for those already running.
            with lock:
                stop = True
            pool.shutdown(wait=True)

    all_objects = [obj_path(src, binary) for src in all_sources]
    link_cmd = [cc, *compile_flags, "-o", str(binary), *[str(o) for o in all_objects]]
    if lm:
        link_cmd.append("-lm")
    link_cmd.extend(f"-l{lib}" for lib in libs)
    print(f"{BOLD}[{tag}]{RESET} linking → {binary}", file=out)
    result = subprocess.run(link_cmd)
    if result.returncode != 0:
        die("linking failed", result.returncode)


def print_graph(source: str, cc: str) -> None:
    cwd = Path.cwd()

    def rel(p: str) -> str:
        return str(Path(p).relative_to(cwd, walk_up=True))

    sources = resolve_all_sources(source, cc)

    inc_dirs: list[str] = []
    for src in sources:
        for d in include_dirs(src):
            if d not in inc_dirs:
                inc_dirs.append(d)

    print(f"# crun graph for {rel(os.path.realpath(source))} (compiler: {cc})")
    print("# Link order (dependencies first):")
    for src in sources:
        print(f"#   {rel(src)}")
    print(f"# Include flags: {' '.join('-I' + rel(d) for d in inc_dirs)}")
    print()
    for src in sources:
        headers = sorted(rel(h) for h in resolve_local_headers(src, cc))
        obj = Path(rel(src)).with_suffix(".o")
        print(" ".join([f"{obj}: {rel(src)}", *headers]))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile, run, and clean up C source files."
    )

    parser.add_argument("source", nargs="?", help="The C source file to run")

    parser.add_argument(
        "-c",
        "--clean", action="store_true", help="Remove orphaned cache entries"
    )

    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Check for orphaned and corrupted cache entries",
    )

    parser.add_argument(
        "-F", "--force-clear-cache", action="store_true", help="Force clear cache"
    )

    parser.add_argument(
        "-k",
        "--keep",
        action="store_true",
        help="Keep copy of the binary in the source code directory",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Compile with debug flags and output the binary path for a debugger",
    )

    parser.add_argument(
        "-g",
        "--graph",
        action="store_true",
        help="Print the dependency graph (link order and per-file headers) and exit; ignores the cache",
    )

    parser.add_argument("-m", "--lm", action="store_true", help="Link libm")

    parser.add_argument(
        "-l",
        "--lib",
        action="append",
        default=[],
        metavar="NAME",
        help="Link an extra library (-lNAME); may be repeated",
    )

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
    cwd = Path().cwd()

    try:
        if not Path(source).is_file():
            die(f"file '{source}' not found")

        if not source.endswith(".c"):
            print(
                f"{YELLOW}warning:{RESET} '{source}' does not have a .c extension, proceeding anyway"
            )

        if args.graph:
            cc = find_compiler()
            assert cc is not None
            print_graph(source, cc)
            sys.exit(0)

        binary = get_cache_binary_path(source)
        cc = find_compiler()
        assert cc is not None
        seeded = load_header_scans(binary, cc)
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
                debug=True,
                libs=tuple(args.lib),
            )

            if args.keep:
                shutil.copy(binary, cwd)
                print(f"{BOLD}[keep]{RESET} {binary.name} → {cwd}", file=sys.stderr)

            print(str(binary))
            sys.exit(0)

        stale = (
            get_stale_sources(all_sources, binary, cc)
            if binary.exists()
            else all_sources
        )

        if not stale and binary.exists():
            print(f"{BOLD}[cache]{RESET} {source} — skipping compilation")
            if not seeded.issuperset(all_sources):
                write_cache_manifest(all_sources, binary, cc)
        else:
            binary.parent.mkdir(parents=True, exist_ok=True)
            compile_sources(
                stale,
                all_sources,
                cc,
                binary,
                CFLAGS,
                args.lm,
                libs=tuple(args.lib),
            )

            src_origin = binary.parent / "source_origin.txt"
            if not src_origin.exists():
                src_origin.write_text(os.path.abspath(source), encoding="utf-8")

            write_cache_manifest(all_sources, binary, cc)

        if len(prog_args) > 3:
            run_display = " ".join(
                [str(binary), *prog_args[:3], f"...({len(prog_args) - 3} more)"]
            )
        else:
            run_display = " ".join([str(binary), *prog_args])

        if args.keep:
            shutil.copy(binary, cwd)
            print(f"{BOLD}[keep]{RESET} {binary.name} → {cwd}")

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
