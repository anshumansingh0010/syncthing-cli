# stcli — Syncthing CLI

A beautiful, batteries-included command-line interface for [Syncthing](https://syncthing.net).

```
╔══════════════════════════════╗
║   stcli  –  Syncthing CLI    ║
╚══════════════════════════════╝
```

## Features

- **Auto-detects** your local Syncthing instance (reads `~/.config/syncthing/config.xml`)
- **Named profiles** — manage multiple Syncthing instances
- **Rich terminal output** — tables, panels, colours, icons
- Full **folder management**: list, inspect, pause, resume, errors
- Full **device management**: list, inspect, connection stats, pause, resume
- **Pending** devices/folders dashboard
- Environment variable and flag overrides for scripting

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

# List all synced folders
stcli folders list

# Inspect a folder (use its ID)
stcli folders info <folder-id>

# List all devices
stcli devices list

# Inspect a device (prefix of ID is enough)
stcli devices info J4U5N7

# Show pending connection requests
stcli pending
```

## Commands

| Command | Description |
|---|---|
| `stcli status` | Overall snapshot (version, uptime, folders, devices) |
| `stcli folders list` | Table of all folders + sync state |
| `stcli folders info <id>` | Detailed folder stats |
| `stcli folders pause <id>` | Pause a folder |
| `stcli folders resume <id>` | Resume a folder |
| `stcli folders errors <id>` | Show sync errors |
| `stcli devices list` | Table of all devices + connection state |
| `stcli devices info <id>` | Detailed device info |
| `stcli devices pause <id>` | Pause a device |
| `stcli devices resume <id>` | Resume a device |
| `stcli pending` | Pending devices/folders awaiting acceptance |
| `stcli connect auto` | Auto-detect Syncthing and test connection |
| `stcli connect add` | Add/update a named profile |
| `stcli connect list` | List saved profiles |
| `stcli connect remove <name>` | Delete a profile |
| `stcli connect test` | Test connectivity of a saved profile |

## Connection Options

Flags can be set globally before any subcommand:

```bash
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

## Auto-Detection Logic

Priority order:
1. `SYNCTHING_API_KEY` environment variable
2. `~/.config/syncthing/config.xml`
3. `~/.local/state/syncthing/config.xml`
4. `/var/syncthing/config.xml`
