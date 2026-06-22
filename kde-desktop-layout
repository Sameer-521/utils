#!/usr/bin/env python3
"""Interactive desktop layout saver/restorer for KDE Plasma."""

import shutil
import subprocess
from pathlib import Path

# ── ANSI styling ──────────────────────────────────────────────
C = "\033[36m"  # cyan
G = "\033[32m"  # green
Y = "\033[33m"  # yellow
R = "\033[31m"  # red
B = "\033[1m"  # bold
D = "\033[2m"  # dim
E = "\033[0m"  # reset

CONFIG_DIR = Path.home() / ".config"
STORAGE_DIR = Path.home() / ".local" / "share" / "desktop-layouts"

FILES = [
    "plasma-org.kde.plasma.desktop-appletsrc",
    "plasmashellrc",
    "kwinoutputconfig.json",
]


def _layout_dir(name: str) -> Path:
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        raise ValueError(f"Invalid layout name: {name!r}")
    dest = (STORAGE_DIR / name).resolve()
    if STORAGE_DIR.resolve() not in dest.parents and dest != STORAGE_DIR.resolve():
        raise ValueError(f"Layout name escapes storage: {name!r}")
    return dest


def save(name: str) -> None:
    """Save current desktop layout under <name>."""
    if not name:
        print(f"{R}Usage: save <name>{E}")
        return
    try:
        dest = _layout_dir(name)
    except ValueError as e:
        print(f"{R}{e}{E}")
        return
    if dest.exists():
        ans = input(f"{Y}'{name}' exists. Overwrite? [y/N] {E}").strip().lower()
        if ans != "y":
            print(f"{D}Cancelled.{E}")
            return
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for fname in FILES:
        src = CONFIG_DIR / fname
        if src.exists():
            shutil.copy2(src, dest / fname)
        else:
            print(f"{Y}Warning: {src} not found, skipping.{E}")
    print(f"{G}Saved '{name}' → {D}{dest}{E}")


def list_layouts(_=None) -> None:
    """List all saved layouts."""
    if not STORAGE_DIR.is_dir():
        print(f"{D}No saved layouts.{E}")
        return
    entries = sorted(
        p for p in STORAGE_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")
    )
    if not entries:
        print(f"{D}No saved layouts.{E}")
        return
    print(f"{B}Saved layouts:{E}")
    for path in entries:
        n = sum(1 for f in FILES if (path / f).exists())
        status = f"{G}✓{E}" if n == len(FILES) else f"{Y}⚠{E}"
        print(f"  {status} {C}{path.name}{E}  {D}({n}/{len(FILES)} files){E}")


def load(name: str) -> None:
    """Restore a saved layout and refresh plasmashell."""
    if not name:
        print(f"{R}Usage: load <name>{E}")
        return
    try:
        src = _layout_dir(name)
    except ValueError as e:
        print(f"{R}{e}{E}")
        return
    if not src.is_dir():
        print(f"{R}Layout '{name}' not found.{E}")
        return

    backup_dir = STORAGE_DIR / ".preload-backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for fname in FILES:
        current = CONFIG_DIR / fname
        if current.exists():
            shutil.copy2(current, backup_dir / fname)

    for fname in FILES:
        s = src / fname
        d = CONFIG_DIR / fname
        if s.exists():
            shutil.copy2(s, d)

    print(f"{G}Restored '{name}'.{E} {D}(preload state saved to {backup_dir}){E}")
    print(f"{G}Refreshing Plasma shell...{E}")
    subprocess.Popen(
        ["plasmashell", "--replace"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def delete(name: str) -> None:
    """Delete a saved layout."""
    if not name:
        print(f"{R}Usage: delete <name>{E}")
        return
    try:
        target = _layout_dir(name)
    except ValueError as e:
        print(f"{R}{e}{E}")
        return
    if not target.is_dir():
        print(f"{R}Layout '{name}' not found.{E}")
        return
    shutil.rmtree(target)
    print(f"{G}Deleted '{name}'.{E}")


def rollback(_=None) -> None:
    """Restore config files from the preload backup."""
    backup = STORAGE_DIR / ".preload-backup"
    if not backup.is_dir():
        print(f"{Y}No preload backup found.{E}")
        return
    for fname in FILES:
        s = backup / fname
        d = CONFIG_DIR / fname
        if s.exists():
            shutil.copy2(s, d)
    print(f"{G}Rolled back to preload state.{E}")
    print(f"{G}Refreshing Plasma shell...{E}")
    subprocess.Popen(
        ["plasmashell", "--replace"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def show_help(_=None) -> None:
    print(f"""\
{B}Commands:{E}
  {C}save{E} <name>    Save current desktop layout
  {C}list{E}           List saved layouts
  {C}load{E} <name>    Restore a layout and refresh Plasma
  {C}delete{E} <name>  Delete a saved layout
  {C}rollback{E}       Restore config to state before last load
  {C}clear{E}          Clear the screen
  {C}help{E}           Show this help
  {C}exit{E} / quit    Exit""")


def clear_screen(_=None) -> None:
    print("\033[2J\033[H", end="")


COMMANDS = {
    "save": save,
    "list": list_layouts,
    "load": load,
    "delete": delete,
    "clear": clear_screen,
    "rollback": rollback,
    "help": show_help,
}


def main() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Welcome banner ────────────────────────────────────────
    print(f"{C}{B}╭──────────────────────────────────────────╮{E}")
    print(f"{C}{B}│{E}        {B}Desktop Layout Manager{E}              {C}{B}│{E}")
    print(f"{C}{B}╰──────────────────────────────────────────╯{E}")
    print(f" {D}Storage:{E} {STORAGE_DIR}")
    print()
    print(f"Type {C}help{E} for commands, {C}exit{E} to quit.")
    print()

    while True:
        try:
            raw = input(f"{C}{B}>{E} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("exit", "quit"):
            break
        if cmd in COMMANDS:
            COMMANDS[cmd](arg)
        else:
            print(f"{R}Unknown command: {cmd}.{E} Type {C}help{E}.")


if __name__ == "__main__":
    main()
