# crun

Compile, run, and clean up a C source file in one command - like `go run`, but for C.

```
crun hello.c
crun args.c foo bar baz
crun --clean
```

No leftover binaries. No accidental `a.out` clobbers. Compiler warnings on by default.

---

## How it works

1. Discovers all local dependencies of your `.c` file using `gcc -MM`, building a dependency graph via DFS
2. Topologically sorts all reachable `.c` files so that dependencies are compiled first
3. Compiles each source file to a separate object file (`.o`), then links them all into a single binary
4. Names the binary after the main source file - `hello.c` becomes `./hello`
5. Runs it, forwarding any arguments you pass
6. Caches object files and the binary into `~/.cache/crun/`, using hash comparison and local header tracking to skip recompilation when nothing has changed
7. Tracks the source file path in `source_origin.txt` for cleanup purposes
8. Forwards the program's exit code back to the shell
9. Detects and reports crashes caused by signals (e.g., SIGSEGV)

---

## Requirements

| Dependency | Minimum version |
|---|---|
| Python | 3.9+ |
| GCC / cc / clang | any modern version |

---

## Installation

### One-liner

```bash
curl -fsSL https://raw.githubusercontent.com/Sameer-521/utils/main/crun/install.sh | bash
```

Downloads `crun` into `~/.local/bin/crun` and makes it executable.

### Manual (any platform)

```bash
curl -fsSL https://raw.githubusercontent.com/Sameer-521/utils/main/crun/crun.py -o ~/.local/bin/crun
chmod +x ~/.local/bin/crun
```

Make sure `~/.local/bin` is on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc or ~/.zshrc
```

### Termux (Android)

```bash
pkg install python gcc
curl -fsSL https://raw.githubusercontent.com/Sameer-521/utils/main/crun/crun.py -o ~/.local/bin/crun
chmod +x ~/.local/bin/crun
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

### Fish shell

```fish
curl -fsSL https://raw.githubusercontent.com/Sameer-521/utils/main/crun/crun.py -o ~/.local/bin/crun
chmod +x ~/.local/bin/crun
fish_add_path ~/.local/bin
```

### Verify

```
crun
# Usage: crun <file.c> [program args...]
```

---

## Usage

```
crun <file.c> [options] [program args...]
```

### Basic

```bash
crun hello.c
```

### Passing arguments to your program

```bash
crun args.c foo bar baz
```

Your program receives these via `argc` / `argv` as normal.

### Linking the math library

Use the `--lm` flag to link `libm` during compilation:

```bash
crun --lm math_demo.c
```

### Debug mode

The `--debug` flag always recompiles (no cache), injects `-O0`, and prints the binary path instead of running the program. Useful for piping to a debugger:

```bash
crun --debug program.c
# → /home/user/.cache/crun/program-a1b2c3d4/program

gdb $(crun --debug program.c)
```

### Cleaning up the cache

*   **--clean**: Removes orphaned cache entries where the source file no longer exists.
*   **--dry-run**: Used with `--clean` to see what would be removed without actually deleting files.
*   **--force-clear-cache**: Completely purges the entire cache directory.

---

## Compiler flags

These flags are applied on every compile:

| Flag | Purpose |
|---|---|
| `-std=c99` | C99 standard - VLAs, `stdint.h`, `//` comments, designated initialisers |
| `-Wall` | All common warnings |
| `-Wextra` | Extra diagnostic warnings |
| `-Wpedantic` | Strict ISO conformance; catches GCC-specific extensions |
| `-Wconversion` | Implicit narrowing and sign conversion warnings |
| `-Wshadow` | Warns when an inner variable silently hides an outer one |
| `-g` | Embeds debug symbols |

---

## Error handling

| Situation | Behaviour |
|---|---|
| File not found | Prints error to stderr, exits 1 |
| No `.c` extension | Prints a warning, proceeds anyway |
| Compile error | GCC output printed directly, exits with compiler's code |
| No compiler found | Prints error to stderr, exits 1 |
| Non-zero program exit | Prints `[exit N]` and forwards the code |
| Program crashed with signal | Prints `[crashed with SIGNAL_NAME]` |

---

## Cache management

Binaries and object files are stored in `~/.cache/crun/` using the format `<source-name>-<hash>/`. The script uses a `cache_manifest.json` file to manage:

*   **Multi-Source Integrity**: Stores a SHA256 hash for every discovered source file, not just the main one. Automatic dependency discovery means headers with matching `.c` files are included in the build.
*   **Local Header Tracking**: Tracks modification times of all headers included via `#include "..."` across every source file to trigger recompilation if any header changes.
*   **Source Origin**: Keeps the absolute path to the main source file in `source_origin.txt` for cache validation and cleanup.

---

## Notes

*   The binary is always named after the main source file, never `a.out`.
*   Multi-file projects are automatically handled - `#include "header.h"` with a matching `header.c` in the same directory will be discovered, compiled, and linked.
*   Works with both relative and absolute paths.
*   Includes a `--keep` flag to keep a copy of the binary in the source directory.
*   Includes a `--debug` flag for debugger integration - always recompiles and outputs the binary path without running.
*   The script has no dependencies outside the Python standard library.
