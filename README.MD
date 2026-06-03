# utils

Personal utilities, terminal configurations, and helper scripts.

## subdirectories

### crun

A Python script that compiles, runs, and cleans up a C source file in a single command -- like `go run`, but for C. It caches binaries in `~/.cache/crun/` to skip recompilation when nothing changed, forwards the program's exit code, and reports signal crashes (e.g. SIGSEGV). See `crun/README.md` for full usage and installation details.

### custom_nvim_plugins

Standalone Neovim plugin specs in Lua, intended to be sourced by a plugin manager (e.g. lazy.nvim):

- `catppuccin.lua` -- Catppuccin colorscheme for Neovim.
- `dashboard.lua` -- Dashboard (start screen) configuration via `folke/snacks.nvim`.

### terminal

Backups of terminal-related dotfiles, synced from their live locations by `backup_configs.py`:

- `fish/` -- Fish shell configuration (`config.fish`, completions, functions, conf.d snippets).
- `ghostty/` -- Ghostty terminal emulator configuration.
- `starship.toml` -- Starship cross-shell prompt configuration.

## scripts

### backup_configs.py

Copies live registered configurations from their various sources into the corresponding backup destinations and optionally commits and pushes the changes to this repository. Run it after making changes to your registered configs e.g your terminal setup to keep the repo in sync.
