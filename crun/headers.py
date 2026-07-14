import os
import subprocess
from graphlib import TopologicalSorter


def resolve_local_headers(source_file: str, cc: str = "gcc") -> dict[str, float]:
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
    stem, _ = os.path.splitext(header_path)
    candidate = stem + ".c"
    if os.path.isfile(candidate):
        return os.path.realpath(candidate)
    return None


def resolve_all_sources(main_source: str, cc: str) -> list[str]:
    main_source = os.path.realpath(main_source)

    dep_graph: dict[str, list[str]] = {}

    def discover(node: str) -> None:
        if node in dep_graph:
            return
        dep_graph[node] = []
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
    for path, old_mtime in snapshot.items():
        try:
            if os.stat(path).st_mtime != old_mtime:
                return True
        except FileNotFoundError:
            return True
    return False
