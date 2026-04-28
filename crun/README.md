# crun

Compile, run, and clean up a C source file in one command — like `go run`, but for C.

```
crun hello.c
crun args.c foo bar baz
```

No leftover binaries. No accidental `a.out` clobbers. Compiler warnings on by default.

---

## How it works

1. Compiles your `.c` file with `gcc` (falls back to `cc` or `clang`)
2. Names the binary after the source file — `hello.c` → `./hello`
3. Runs it, forwarding any arguments you pass
4. Caches the binary into the .cache directory and uses a simple mtime 
comparison between the source and binary for potential compilation skips
5. Forwards the program's exit code back to the shell

---

## Requirements

| Dependency | Minimum version |
|---|---|
| Python | 3.6+ |
| GCC / cc / clang | any modern version |

---

## Installation

### Linux (general)

```bash
mkdir -p ~/.local/bin
mv crun.py ~/.local/bin/crun
chmod +x ~/.local/bin/crun
```

Make sure `~/.local/bin` is on your `PATH`. Add this to your shell's rc file if it isn't already:

```bash
# ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

Then reload it:

```bash
source ~/.bashrc   # or source ~/.zshrc
```

### Termux (Android)

```bash
# Install dependencies if not already present
pkg install python gcc

# Install the script
mkdir -p ~/.local/bin
mv crun.py ~/.local/bin/crun
chmod +x ~/.local/bin/crun

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Fish shell (any platform)

```fish
mkdir -p ~/.local/bin
mv crun.py ~/.local/bin/crun
chmod +x ~/.local/bin/crun

# Add to PATH permanently
fish_add_path ~/.local/bin
```

### Verify the installation

```
crun
# Usage: crun <file.c> [program args...]
```

---

## Usage

```
crun <file.c> [program args...]
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

### Using the exit code

`crun` forwards your program's exit code, so it composes with shell logic:

```bash
crun myprogram.c && echo "success"
```

---

## Compiler flags

These flags are applied on every compile:

| Flag | Purpose |
|---|---|
| `-std=c99` | C99 standard — VLAs, `stdint.h`, `//` comments, designated initialisers |
| `-Wall` | All common warnings |
| `-Wextra` | Extra diagnostic warnings |
| `-Wpedantic` | Strict ISO conformance; catches GCC-specific extensions |
| `-Wconversion` | Implicit narrowing and sign conversion warnings |
| `-Wshadow` | Warns when an inner variable silently hides an outer one |
| `-g` | Embeds debug symbols (lets you attach `gdb` or `valgrind` without recompiling) |


## Error handling

| Situation | Behaviour |
|---|---|
| File not found | Prints error to stderr, exits 1 |
| No `.c` extension | Prints a warning, proceeds anyway |
| Compile error | GCC output printed directly, exits with compiler's code |
| No compiler found | Prints error to stderr, exits 1 |
| Non-zero program exit | Prints `[exit N]` and forwards the code |

---

## Notes

- The binary is always named after the source file (`prog.c` → `prog`), never `a.out`
- If the source file has no extension, the binary is named `<file>.out` to avoid clobbering it
- Works with both relative and absolute paths
- The script has no dependencies outside the Python standard library
