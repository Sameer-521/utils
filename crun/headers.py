import os
import subprocess
import sys
from graphlib import TopologicalSorter
from pathlib import Path

from config import YELLOW, RESET


def include_dirs(source_file: str) -> list[str]:
    source_dir = Path(os.path.realpath(source_file)).parent

    root = source_dir
    for probe in (source_dir, *source_dir.parents):
        if probe.name == "src":
            root = probe.parent
            break

    candidates = [
        source_dir,
        root / "include",
        root / "src",
        root,
    ]
    dirs: list[str] = []
    for d in candidates:
        if d.is_dir() and str(d) not in dirs:
            dirs.append(str(d))
    return dirs


_header_cache: dict[tuple[str, str], dict[str, float]] = {}


def resolve_local_headers(source_file: str, cc: str = "gcc") -> dict[str, float]:
    source_file = os.path.realpath(source_file)
    key = (source_file, cc)
    if key not in _header_cache:
        _header_cache[key] = _scan_local_headers(source_file, cc)
    return dict(_header_cache[key])


def seed_header_cache(source_file: str, cc: str, headers: dict[str, float]) -> None:
    _header_cache[(os.path.realpath(source_file), cc)] = dict(headers)


def _scan_local_headers(source_file: str, cc: str) -> dict[str, float]:
    source_dir = os.path.dirname(source_file)
    include_flags = [f"-I{d}" for d in include_dirs(source_file)]

    try:
        result = subprocess.run(
            [cc, "-MM", "-MG", *include_flags, source_file],
            capture_output=True,
            text=True,
            cwd=source_dir,
        )
    except FileNotFoundError:
        print(
            f"{YELLOW}warning:{RESET} compiler '{cc}' not found, "
            f"header dependencies of {source_file} not tracked",
            file=sys.stderr,
        )
        return {}

    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        print(
            f"{YELLOW}warning:{RESET} could not resolve headers of {source_file}"
            + (f": {detail[0]}" if detail else ""),
            file=sys.stderr,
        )
        return {}

    output = result.stdout.replace("\\\n", " ")
    if ":" in output:
        _, deps = output.split(":", 1)
    else:
        deps = output

    headers: dict[str, float] = {}
    for token in deps.split():
        token = token.strip()
        if not token or token.endswith(".o"):
            continue
        abs_path = os.path.realpath(os.path.join(source_dir, token))
        if abs_path == source_file:
            continue
        if os.path.isfile(abs_path):
            headers[abs_path] = os.stat(abs_path).st_mtime

    return headers


def find_source_from_header(header_path: str) -> str | None:
    stem, ext = os.path.splitext(header_path)
    if ext == ".c":
        return None
    candidate = stem + ".c"
    if os.path.isfile(candidate):
        return os.path.realpath(candidate)

    parts = os.path.realpath(header_path).split(os.sep)
    for i in range(len(parts) - 2, -1, -1):
        if parts[i] == "include":
            root = os.sep.join(parts[:i])
            rel = os.sep.join(parts[i + 1 :])
            mirrored = os.path.join(root, "src", os.path.splitext(rel)[0] + ".c")
            if os.path.isfile(mirrored):
                return os.path.realpath(mirrored)
            break
    return None


def resolve_all_sources(main_source: str, cc: str) -> list[str]:
    main_source = os.path.realpath(main_source)

    dep_graph: dict[str, list[str]] = {}

    def direct_deps(node: str) -> list[str]:
        deps: list[str] = []
        for header in resolve_local_headers(node, cc):
            src = find_source_from_header(header)
            if src and src != node:
                deps.append(src)

        return deps

    def discover(node: str) -> None:
        if node in dep_graph:
            return

        dep_graph[node] = []  # mark as visiting
        deps = direct_deps(node)
        dep_graph[node] = deps
        for dep in deps:
            discover(dep)

    discover(main_source)

    ts = TopologicalSorter(dep_graph)
    return list(ts.static_order())


def headers_changed(snapshot: dict[str, float]) -> bool:
    for path, old_mtime in snapshot.items():
        try:
            if Path(path).stat().st_mtime != old_mtime:
                return True
        except FileNotFoundError:
            return True
    return False
