# crun

Compile and run a C file in one command, like `go run` but for C.

```
crun hello.c
crun args.c foo bar baz
crun --clean
```

It leaves no binaries next to your source and never writes an `a.out`. Compiler warnings are on by default.

---

## How it works

1. It finds the local dependencies of your `.c` file with `gcc -MM`, using `include/`, `src/` and the project root as include paths.
2. It sorts the `.c` files it found so dependencies come first.
3. Each source file is compiled to its own object file (`.o`), then everything is linked into one binary. If several files need compiling, they are compiled in parallel (up to one job per CPU core).
4. On a rebuild, only sources whose content or headers changed are recompiled. The other `.o` files are reused.
5. The binary is named after the main source file, so `hello.c` gives `hello`.
6. It runs the binary and passes along any arguments you gave.
7. Object files and the binary are cached in `~/.cache/crun/`. Each source is tracked by its SHA256 hash and by the modification times of the headers it includes.
8. The path of the main source file is saved in `source_origin.txt` so `--clean` can tell when an entry is orphaned.
9. The program's exit code is passed back to the shell.
10. If the program dies from a signal (for example SIGSEGV), crun says so.

---

## Requirements

| Dependency | Minimum version |
|---|---|
| Python | 3.12+ |
| GCC / cc / clang | any modern version |

---

## Installation

### One-liner

```bash
curl -fsSL https://raw.githubusercontent.com/Sameer-521/utils/main/crun/install.sh | bash
```
If the one-liner doesn't work, use one of the manual methods below.

It clones the repo, copies `crun/` into `~/.crun/`, and symlinks `~/.local/bin/crun` to the entry point.

### Manual (any platform)

```bash
git clone --depth 1 https://github.com/Sameer-521/utils.git /tmp/crun-install
cp -r /tmp/crun-install/crun ~/.crun
ln -sf ~/.crun/__main__.py ~/.local/bin/crun
rm -rf /tmp/crun-install
```

Make sure `~/.local/bin` is on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc or ~/.zshrc
```

### Termux (Android)

```bash
pkg install python gcc git
git clone --depth 1 https://github.com/Sameer-521/utils.git "$PREFIX/tmp/crun-install"
mkdir -p ~/.local/bin
cp -r "$PREFIX/tmp/crun-install/crun" ~/.crun
ln -sf ~/.crun/__main__.py ~/.local/bin/crun
rm -rf "$PREFIX/tmp/crun-install"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

Termux doesn't allow writing to `/tmp` without root, so these steps use `$PREFIX/tmp` instead. The one-liner also works on Termux, since `install.sh` picks `$TMPDIR` or `$PREFIX/tmp` on its own.

### Fish shell

```fish
git clone --depth 1 https://github.com/Sameer-521/utils.git /tmp/crun-install
cp -r /tmp/crun-install/crun ~/.crun
ln -sf ~/.crun/__main__.py ~/.local/bin/crun
rm -rf /tmp/crun-install
fish_add_path ~/.local/bin
```

### Check it works

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

Your program gets these through `argc` and `argv` as usual.

### Linking the math library

Use `--lm` to link `libm`:

```bash
crun --lm math_demo.c
```

### Linking other libraries

Use `--lib NAME` to link any library (`-lNAME`). You can repeat it:

```bash
crun --lib readline shell.c
crun --lib readline --lib ncurses shell.c
```

Put crun's options before the source file. Anything after it goes to your program.

### Short options

| Short | Long |
|---|---|
| `-c` | `--clean` |
| `-n` | `--dry-run` |
| `-F` | `--force-clear-cache` |
| `-k` | `--keep` |
| `-d` | `--debug` |
| `-g` | `--graph` |
| `-m` | `--lm` |
| `-l NAME` | `--lib NAME` |

Short flags can be combined (`-dk`). `-l` takes a value, so put it last or give it separately (`-l readline`).

### Debug mode

`--debug` always recompiles (no cache), adds `-O0`, and prints the binary path instead of running the program. That makes it easy to hand to a debugger:

```bash
crun --debug program.c
# → /home/user/.cache/crun/program-a1b2c3d4/program

gdb $(crun --debug program.c)
```

### Dependency graph

`--graph` (`-g`) prints every source file the program needs, in link order (dependencies first), plus the headers each one includes. Nothing is compiled or run, and nothing is written to the cache. It never reads the cache either, so no file is left out because it is "unchanged". Use it to write a Makefile by hand:

```bash
crun --graph src/main.c
```

```
# crun graph for src/main.c (compiler: gcc)
# Link order (dependencies first):
#   src/a/b.c
#   src/main.c
# Include flags: -Isrc/a -Iinclude -Isrc -I.

src/a/b.o: src/a/b.c include/a/b.h
src/main.o: src/main.c include/a/b.h
```

### Cleaning up the cache

* `--clean` (`-c`): removes cache entries whose source file no longer exists.
* `--dry-run` (`-n`): use with `--clean` to see what would be removed without deleting anything.
* `--force-clear-cache` (`-F`): deletes the whole cache. `-cF` also works, since it is just `-c -F` and the full purge wins.

---

## Project layouts

These layouts work without any configuration:

```
flat/                 src-only/              include-src/
  main.c                src/                   include/
  util.h                  main.c                 a/b.h
  util.c                  util.h               src/
                          util.c                 main.c
                                                 a/b.c
```

* Flat: everything in one directory.
* `src/`: headers sit next to their sources.
* `include/` and `src/`: flat or mirrored, so `include/a/b.h` pairs with `src/a/b.c`.

A header is paired with a source by location only: the same directory first (`x/b.h` with `x/b.c`), then the mirrored `src/` path. File names are never matched on their own.

The project root is the parent of the nearest `src/` directory above your source file. If there is none, it is the source's own directory. `include/`, `src/` and the root are passed to the compiler as `-I` paths, so `#include "a/b.h"` works from any source file.

A `.c` file that is pulled in with `#include` is tracked for rebuilds but not compiled on its own.

---

## Compiler flags

These flags are used on every compile:

| Flag | What it does |
|---|---|
| `-std=gnu99` | GNU C99: VLAs, `stdint.h`, `//` comments, designated initialisers, plus GNU extensions |
| `-Wall` | Common warnings |
| `-Wextra` | Extra warnings |
| `-Wpedantic` | Strict ISO conformance, flags GCC-specific extensions |
| `-Wconversion` | Warns about implicit narrowing and sign conversions |
| `-Wshadow` | Warns when an inner variable hides an outer one |
| `-g` | Adds debug symbols |
| `-pipe` | Uses pipes instead of temp files between compiler stages, which is faster on slow storage like Android |

---

## Error handling

| Situation | What happens |
|---|---|
| File not found | Prints an error to stderr, exits 1 |
| No `.c` extension | Prints a warning and carries on |
| Compile error | Prints the compiler output and exits with the compiler's exit code |
| No compiler found | Prints an error to stderr, exits 1 |
| Header scan fails | Prints a warning to stderr and treats the file as having no header dependencies |
| Program exits non-zero | Prints `[exit N]` and exits with the same code |
| Program crashes with a signal | Prints `[crashed with SIGNAL_NAME]` |

---

## Cache

Binaries and object files live in `~/.cache/crun/`, in folders named `<source-name>-<hash>/`. A `cache_manifest.json` file in each folder records:

* The SHA256 hash of every source file, not just the main one, so a change in any of them triggers a recompile of that file.
* The modification times of the headers each source includes. Touching a shared header only recompiles the sources that include it.
* The path of the main source file (kept separately in `source_origin.txt`), used by `--clean`.

On a rebuild, unchanged `.o` files are reused and only the link step runs again.

---

## Notes

* The binary is always named after the main source file, never `a.out`.
* Multi-file projects work automatically. If `header.h` has a matching `header.c` in the same directory or in the mirrored `src/` directory, it is found, compiled and linked. See [Project layouts](#project-layouts).
* Relative and absolute paths both work.
* `--keep` (`-k`) copies the binary into the source directory.
* `--debug` (`-d`) always recompiles and prints the binary path without running it.
* Nothing outside the Python standard library is needed.
