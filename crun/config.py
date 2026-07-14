from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "crun"

CFLAGS = [
    "-std=gnu99",
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Wconversion",
    "-Wshadow",
    "-g",
]

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BOLD = "\033[1m"
RESET = "\033[0m"

DIVIDER = "─" * 40
