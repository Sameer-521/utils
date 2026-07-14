import hashlib
import json
import os
import shutil
from pathlib import Path

from config import CACHE_DIR, BOLD, RESET
from headers import resolve_local_headers

HASH_LEN = 8


def obj_path(src: str, binary: Path) -> Path:
    stem = Path(src).stem
    key = hashlib.sha256(src.encode()).hexdigest()[:HASH_LEN]
    return binary.parent / f"{stem}.{key}.o"


def get_cache_binary_path(source: str) -> Path:
    abs_src = os.path.abspath(source)
    key = hashlib.sha256(abs_src.encode()).hexdigest()[:HASH_LEN]
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


def get_stale_sources(sources: list[str], binary: Path, cc: str) -> list[str]:
    cache_manifest_file = binary.parent / "cache_manifest.json"

    stored_sources: dict[str, str] = {}
    stored_headers: dict[str, float] = {}
    if cache_manifest_file.exists():
        try:
            with open(cache_manifest_file, "r") as f:
                contents = json.load(f)
                stored_sources = contents.get("sources", {})
                stored_headers = contents.get("headers", {})
        except (json.JSONDecodeError, KeyError):
            pass

    stale: list[str] = []
    for src in sources:
        obj = obj_path(src, binary)

        if src not in stored_sources or not obj.exists():
            stale.append(src)
            continue

        try:
            with open(src, "rb") as f:
                current_hash = hashlib.file_digest(f, "sha256").hexdigest()
        except FileNotFoundError:
            stale.append(src)
            continue

        if stored_sources[src] != current_hash:
            stale.append(src)
            continue

        headers = resolve_local_headers(src, cc)
        for hdr_path, hdr_mtime in headers.items():
            old_mtime = stored_headers.get(hdr_path)
            if old_mtime is None:
                stale.append(src)
                break
            try:
                if Path(hdr_path).stat().st_mtime != old_mtime:
                    stale.append(src)
                    break
            except FileNotFoundError:
                stale.append(src)
                break

    return stale


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
