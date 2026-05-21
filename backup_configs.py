#!/usr/bin/env python3
"""Backup terminal configs to ~/utils/terminal/ and optionally push to remote."""

import shutil
import subprocess
import sys
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────
UTILS_REPO = Path.home() / "utils"
TERMINAL_DIR = UTILS_REPO / "terminal"

# Directory-based configs  (rsync'ed to preserve permissions / skip unchanged)
DIR_CONFIGS = {
    "fish": {
        "src": Path.home() / ".config" / "fish",
        "dst": TERMINAL_DIR / "fish",
        "exclude": ["fish_variables"],  # runtime state, not config
    },
    "ghostty": {
        "src": Path.home() / ".config" / "ghostty",
        "dst": TERMINAL_DIR / "ghostty",
        "exclude": [],
    },
}

# Single-file configs
SINGLE_CONFIGS = {
    "starship": {
        "src": Path.home() / ".config" / "starship.toml",
        "dst": TERMINAL_DIR / "starship.toml",
    },
}

# ── helpers ────────────────────────────────────────────────────────────
BLUE = "\033[34m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"


def info(msg: str) -> None:
    print(f"{BLUE}:: {msg}{RESET}")


def ok(msg: str) -> None:
    print(f"{GREEN}✓ {msg}{RESET}")


def warn(msg: str) -> None:
    print(f"{YELLOW}⚠ {msg}{RESET}")


def die(msg: str) -> None:
    print(f"{RED}✗ {msg}{RESET}", file=sys.stderr)
    sys.exit(1)


def run(
    cmd: list[str], cwd: Path | None = None, capture: bool = True
) -> subprocess.CompletedProcess:
    """Run a command; return CompletedProcess."""
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=capture,
        text=True,
    )
    return result


# ── steps ──────────────────────────────────────────────────────────────
def check_repo() -> None:
    """Ensure ~/utils exists and is a git repo."""
    info("Checking utils repo …")

    if not UTILS_REPO.is_dir():
        die(f"{UTILS_REPO} not found.  Clone it first.")

    git_dir = UTILS_REPO / ".git"
    if not git_dir.exists():
        die(f"{UTILS_REPO} exists but is not a git repository.")

    # Make sure we're on a branch and not in detached HEAD
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=UTILS_REPO)
    if branch.stdout.strip() == "HEAD":
        warn("Repo is in detached HEAD state — push will not work.")
        if input("Continue anyway? [y/N] ").strip().lower() != "y":
            sys.exit(0)

    ok(f"Repo OK — on branch '{branch.stdout.strip()}'")


def sync_configs() -> bool:
    """Copy configs from their source locations into the repo.

    Returns True if anything changed.
    """
    changed = False

    TERMINAL_DIR.mkdir(parents=True, exist_ok=True)

    # ── directory configs ──
    for name, cfg in DIR_CONFIGS.items():
        src: Path = cfg["src"]
        dst: Path = cfg["dst"]
        exclude: list[str] = cfg["exclude"]

        if not src.is_dir():
            warn(f"Skipping {name}: source {src} does not exist")
            continue

        # Build rsync args
        args = ["rsync", "-a", "--delete"]
        for e in exclude:
            args += ["--exclude", e]
        args += [f"{src}/", f"{dst}/"]

        # Run rsync — capture output to detect actual transfers
        info(f"Syncing {name} → {dst.relative_to(UTILS_REPO)}")
        result = run(args, capture=True)

        if result.returncode != 0:
            warn(f"rsync for {name} had warnings:\n{result.stderr}")

        # rsync with -a and no -v/-i prints nothing on stdout for no-ops
        if result.stdout:
            changed = True
            ok(f"{name}: changes detected")
        else:
            ok(f"{name}: up-to-date")

    # ── single-file configs ──
    for name, cfg in SINGLE_CONFIGS.items():
        src: Path = cfg["src"]
        dst: Path = cfg["dst"]

        if not src.is_file():
            warn(f"Skipping {name}: source {src} does not exist")
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)

        # Compare content before copying
        if dst.is_file() and src.read_bytes() == dst.read_bytes():
            ok(f"{name}: up-to-date")
            continue

        info(f"Copying {name} → {dst.relative_to(UTILS_REPO)}")
        shutil.copy2(src, dst)
        ok(f"{name}: updated")
        changed = True

    return changed


def show_diff() -> None:
    """Show git diff summary + full diff."""
    info("Changes in repo:")

    result = run(["git", "diff", "--stat"], cwd=UTILS_REPO)
    if result.stdout.strip():
        print(result.stdout)
    else:
        print("  (no stat output — permissions-only or empty diff)")

    result = run(["git", "diff"], cwd=UTILS_REPO)
    if result.stdout.strip():
        print(result.stdout)
    else:
        print("  (no content changes)")


def check_pending_commits() -> bool:
    result = run(cmd=["git", "status"])
    if "Changes not staged for commit" in result.stdout:
        return True
    return False


def commit_and_push() -> None:
    """Stage all changes, commit, and optionally push."""
    info("Staging all changes …")
    run(["git", "add", "-A"], cwd=UTILS_REPO)

    # Show what will be committed
    result = run(["git", "diff", "--cached", "--stat"], cwd=UTILS_REPO)
    if not result.stdout.strip():
        warn("Nothing staged — nothing to commit.")
        return

    print(result.stdout)

    commit_msg = input(f"\n{BOLD}Commit message:{RESET} ").strip()
    if not commit_msg:
        commit_msg = "backup: update terminal configs"

    run(["git", "commit", "-m", commit_msg], cwd=UTILS_REPO, capture=False)
    ok("Committed.")

    ans = input(f"\n{BOLD}Push to remote?{RESET} [y/N] ").strip().lower()
    if ans == "y":
        info("Pushing …")
        result = run(["git", "push"], cwd=UTILS_REPO, capture=False)
        if result.returncode == 0:
            ok("Push successful.")
        else:
            die("Push failed.")


# ── main ───────────────────────────────────────────────────────────────
def main() -> None:
    print(f"{BOLD}══ config-backup ══{RESET}\n")

    check_repo()
    changed = sync_configs()

    if not changed and not check_pending_commits():
        ok("All configs already up-to-date — nothing to do.")
        return

    show_diff()

    print()
    ans = input(f"{BOLD}Commit and push these changes?{RESET} [y/N] ").strip().lower()
    if ans != "y":
        info("Aborted.")
        return

    commit_and_push()


if __name__ == "__main__":
    main()
