# stcli — Syncthing CLI

A beautiful, batteries-included command-line interface for [Syncthing](https://syncthing.net).

```
╔══════════════════════════════╗
║   stcli  –  Syncthing CLI    ║
╚══════════════════════════════╝
```

## Features

- **Auto-detects** your local Syncthing instance (reads `~/.config/syncthing/config.xml`)
- **Named profiles** — manage multiple Syncthing instances (`stcli connect default/show/list/add/remove/test`)
- **Rich terminal output** & **JSON output** (`--json` / `-j` for machine automation)
- Full **folder management**: list, inspect, add, edit, remove, pause, resume, rescan, override, revert, ignore, share, unshare
- Full **device management**: list, inspect, add, edit, remove, pause, resume, ping with ID/prefix/name resolvers
- **System controls**: server info, global/folder rescan, restart, shutdown, log viewer, debug facilities
- **Live monitoring**: real-time dashboard (`stcli watch`) & event streaming (`stcli events -f`)
- **Pending** devices/folders dashboard and acceptance workflows

## Install

### Arch Linux (AUR)

```bash
yay -S stcli
```

### Python (pip)

To install directly from GitHub without cloning the repository manually:

```bash
pip install git+https://github.com/anshumansingh0010/syncthing-cli.git
# or to install globally/system-wide:
pip install git+https://github.com/anshumansingh0010/syncthing-cli.git --break-system-packages
```

*(If you have already cloned the repository locally, you can simply run `pip install .` from inside the folder).*

`stcli` is placed in `~/.local/bin/stcli`. Add that to your `$PATH` if needed.

## Quick Start

```bash
# Auto-detect Syncthing and test the connection
stcli connect auto

# Save the auto-detected connection as a profile
stcli connect auto --save default

# See overall status
stcli status

# Output status in JSON format
stcli --json status

# Live monitoring dashboard
stcli watch

# List all synced folders
stcli folders list

# Inspect a folder (by ID, label, or prefix)
stcli folders info "My Documents"

# Trigger a rescan of a folder
stcli folders rescan <folder-id>

# Manage ignore patterns
stcli folders ignore <folder-id> --add "*.tmp"

# List all devices
stcli devices list

# Inspect a device (by prefix or name)
stcli devices info J4U5N7

# Ping a device connection
stcli devices ping laptop

# System management
stcli system info
stcli system logs -n 50
stcli system rescan
```

## Command Reference

| Command | Description |
|---|---|
| `stcli status` | Overall snapshot (version, uptime, folders, devices) |
| `stcli watch` | Interactive live-updating status dashboard |
| `stcli events` | Stream or view Syncthing system events (`-f` to follow) |
| `stcli folders list` | Table of all folders + sync state |
| `stcli folders info <id>` | Detailed folder stats (ID, prefix, or label) |
| `stcli folders add <path>` | Add a new synced folder |
| `stcli folders edit <id>` | Update label, sync type, or rescan interval |
| `stcli folders rescan <id>` | Trigger immediate rescan for a folder |
| `stcli folders override <id>` | Override remote changes for sendonly folder |
| `stcli folders revert <id>` | Revert local changes for receiveonly folder |
| `stcli folders ignore <id>` | View or add ignore patterns (`.stignore`) |
| `stcli folders share/unshare` | Manage folder sharing with remote devices |
| `stcli folders pause/resume` | Pause or resume folder syncing |
| `stcli folders remove <id>` | Remove folder configuration |
| `stcli devices list` | Table of all devices + connection state |
| `stcli devices info <id>` | Detailed device info (ID, prefix, or name) |
| `stcli devices add <id>` | Add a new device |
| `stcli devices edit <id>` | Update device name, addresses, introducer |
| `stcli devices ping <id>` | Check device connection details & crypto |
| `stcli devices pause/resume` | Pause or resume device syncing |
| `stcli devices remove <id>` | Remove device configuration |
| `stcli system info` | Show detailed server & memory metrics |
| `stcli system rescan` | Rescan all folders (or specific subfolder) |
| `stcli system restart/shutdown` | Restart or shutdown Syncthing service |
| `stcli system logs` | View recent server log messages |
| `stcli system debug` | Inspect active debug facilities |
| `stcli pending list/accept/dismiss` | Pending devices/folders workflow |
| `stcli connect auto` | Auto-detect Syncthing and test connection |
| `stcli connect add` | Add/update a named profile |
| `stcli connect show [name]` | Show profile settings |
| `stcli connect default <name>` | Set default profile |
| `stcli connect list` | List saved profiles |
| `stcli connect remove <name>` | Delete a profile |
| `stcli connect test` | Test connectivity of a profile |

## Connection Options & Flags

Flags can be set globally before any subcommand:

```bash
stcli --json status
stcli --host 192.168.1.5 --port 8384 --api-key YOUR_KEY status
stcli --profile office folders list
```

Or via environment variables:

| Variable | Default |
|---|---|
| `SYNCTHING_API_KEY` | — |
| `SYNCTHING_HOST` | `127.0.0.1` |
| `SYNCTHING_PORT` | `8384` |
| `SYNCTHING_TLS` | `false` |
| `STCLI_PROFILE` | `default` |

Profiles are saved to `~/.stcli.json`.
