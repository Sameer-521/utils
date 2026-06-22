# utils

Personal utilities, terminal configurations, and helper scripts.

## subdirectories

### crun

A Python script that compiles, runs, and cleans up a C source file in a single command — like `go run`, but for C. It caches binaries in `~/.cache/crun/` to skip recompilation when nothing changed, forwards the program's exit code, and reports signal crashes (e.g. SIGSEGV). See `crun/README.md` for full usage and installation details.

### custom_nvim_plugins

Standalone Neovim plugin specs in Lua, intended to be sourced by a plugin manager (e.g. lazy.nvim):

- `astro.lua.txt` — AstroNvim community plugin example.
- `ayu.lua` — Ayu colorscheme.
- `catppuccin.txt` — Catppuccin colorscheme.
- `cmp.lua` — nvim-cmp completion framework setup.
- `dashboard.lua` — Dashboard (start screen) via `folke/snacks.nvim`.
- `example.lua` — Template for new plugin specs.
- `gruvbox.lua.txt` — Gruvbox colorscheme.
- `lsp.lua.txt` — Native LSP configuration.
- `vim-be-good.lua` — Vim practice game plugin.

### terminal

Backups of terminal-related dotfiles, synced from their live locations by `backup_configs.py`:

- `fish/` — Fish shell configuration (`config.fish`, completions, functions, conf.d snippets).
- `ghostty/` — Ghostty terminal emulator configuration.
- `nvim_plugins/` — Neovim plugin manager specs.
- `starship.toml` — Starship cross-shell prompt configuration.

## scripts

### backup_configs.py

Copies live registered configurations from their various sources into the corresponding backup destinations and optionally commits and pushes the changes to this repository. Run it after making changes to your registered configs (e.g. your terminal setup) to keep the repo in sync.

### kde-desktop-layout

Interactive REPL for saving and restoring KDE Plasma desktop layouts — panels, docks, applets, and screen/monitor arrangement.

**What gets captured:**
- `plasma-org.kde.plasma.desktop-appletsrc` — widget/applet placement
- `plasmashellrc` — panel geometry, floating, alignment, auto-hide
- `kwinoutputconfig.json` — monitor/screen layout

**Commands:**

| Command | Action |
|---------|--------|
| `save <name>` | Save current layout to `~/.local/share/desktop-layouts/<name>/` |
| `list` | List all saved layouts |
| `load <name>` | Restore a layout and refresh Plasma (auto-saves preload backup) |
| `delete <name>` | Delete a saved layout |
| `rollback` | Undo last `load` — restores config to state from preload backup |
| `clear` | Clear the screen |
| `help` | Show help |
| `exit` / `quit` | Exit |

On `load`, the current config is saved to `.preload-backup` before overwriting, so `rollback` can undo mistakes.
