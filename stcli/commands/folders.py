"""stcli – folders commands."""

import click
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box

from stcli.output import console, fmt_bytes, fmt_pct, folder_state_style


@click.group("folders")
def folders_group():
    """List, inspect, add, remove, pause, and resume synced folders."""


@folders_group.command("list")
@click.pass_obj
def folders_list(client):
    """List all configured folders and their sync state."""
    folders = client.folders()
    stats   = client.stats_folders()

    table = Table(
        title="[title]Syncthing Folders[/title]",
        box=box.ROUNDED,
        show_header=True,
        header_style="heading",
        border_style="dim white",
        expand=True,
    )
    table.add_column("ID",       style="id",    no_wrap=True)
    table.add_column("Label",    style="value",  no_wrap=True)
    table.add_column("Path",     style="path",   overflow="fold")
    table.add_column("Type",     style="label",  no_wrap=True)
    table.add_column("State",    no_wrap=True)
    table.add_column("Devices",  style="number", justify="right")

    for folder in folders:
        fid    = folder["id"]
        label  = folder.get("label") or fid
        path   = folder.get("path", "—")
        ftype  = folder.get("type", "sendreceive").replace("send", "↔").replace("receive", "↓").replace("only", "")
        paused = folder.get("paused", False)
        devs   = len(folder.get("devices", []))

        try:
            status = client.folder_status(fid)
            state  = status.get("state", "unknown")
        except Exception:
            state = "unknown"

        table.add_row(fid, label, path, ftype, folder_state_style(state, paused), str(devs))

    console.print(table)


@folders_group.command("info")
@click.argument("folder_id")
@click.pass_obj
def folder_info(client, folder_id):
    """Show detailed info for a specific folder."""
    folders = {f["id"]: f for f in client.folders()}
    if folder_id not in folders:
        console.print(f"[error]Folder '[id]{folder_id}[/id]' not found.[/error]")
        raise SystemExit(1)

    folder = folders[folder_id]
    status = client.folder_status(folder_id)
    try:
        completion = client.folder_completion(folder_id)
    except Exception:
        completion = {}

    label  = folder.get("label") or folder_id
    paused = folder.get("paused", False)
    state  = status.get("state", "unknown")
    pct    = completion.get("completion", 100.0)

    lines = [
        f"[label]ID       :[/label] [id]{folder_id}[/id]",
        f"[label]Label    :[/label] [value]{label}[/value]",
        f"[label]Path     :[/label] [path]{folder.get('path', '—')}[/path]",
        f"[label]Type     :[/label] [value]{folder.get('type', '—')}[/value]",
        f"[label]State    :[/label] {folder_state_style(state, paused)}",
        f"[label]Sync     :[/label] {fmt_pct(pct)}",
        "",
        f"[label]Local files  :[/label] [number]{status.get('localFiles', 0):,}[/number]"
        f"  [label]dirs:[/label] [number]{status.get('localDirectories', 0):,}[/number]"
        f"  [label]size:[/label] [number]{fmt_bytes(status.get('localBytes', 0))}[/number]",
        f"[label]Global files :[/label] [number]{status.get('globalFiles', 0):,}[/number]"
        f"  [label]dirs:[/label] [number]{status.get('globalDirectories', 0):,}[/number]"
        f"  [label]size:[/label] [number]{fmt_bytes(status.get('globalBytes', 0))}[/number]",
        f"[label]Need files   :[/label] [number]{status.get('needFiles', 0):,}[/number]"
        f"  [label]bytes:[/label] [number]{fmt_bytes(status.get('needBytes', 0))}[/number]",
    ]

    if status.get("errors", 0):
        lines.append(f"\n[error]Errors: {status['errors']}[/error]")

    # Shared devices
    devs = [d for d in folder.get("devices", []) if not d.get("introducedBy")]
    if devs:
        lines.append(f"\n[label]Shared with:[/label]")
        for d in devs:
            lines.append(f"  [id]{d['deviceID'][:7]}…[/id]")

    console.print(Panel(
        "\n".join(lines),
        title=f"[title]📁 {label}[/title]",
        border_style="cyan",
        expand=False,
    ))


@folders_group.command("pause")
@click.argument("folder_id")
@click.pass_obj
def folder_pause(client, folder_id):
    """Pause syncing for a folder."""
    client.pause_folder(folder_id)
    console.print(f"[paused]⏸  Folder [id]{folder_id}[/id] paused.[/paused]")


@folders_group.command("resume")
@click.argument("folder_id")
@click.pass_obj
def folder_resume(client, folder_id):
    """Resume syncing for a folder."""
    client.resume_folder(folder_id)
    console.print(f"[synced]▶  Folder [id]{folder_id}[/id] resumed.[/synced]")


@folders_group.command("errors")
@click.argument("folder_id")
@click.pass_obj
def folder_errors(client, folder_id):
    """Show sync errors for a folder."""
    result = client.folder_errors(folder_id)
    errors = result.get("errors") or []
    if not errors:
        console.print(f"[synced]✓ No errors for folder [id]{folder_id}[/id][/synced]")
        return

    table = Table(title=f"[error]Errors – {folder_id}[/error]", box=box.SIMPLE)
    table.add_column("Path",  style="path")
    table.add_column("Error", style="error")
    for e in errors:
        table.add_row(e.get("path", ""), e.get("error", ""))
    console.print(table)


@folders_group.command("add")
@click.argument("path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--id",      "folder_id", default=None,
              help="Folder ID (auto-generated from path basename if omitted).")
@click.option("--label",   default=None, help="Human-readable label.")
@click.option("--type",    "folder_type",
              type=click.Choice(["sendreceive", "sendonly", "receiveonly", "receiveencrypted"]),
              default="sendreceive", show_default=True,
              help="Sync type.")
@click.option("--rescan",  default=3600, show_default=True, type=int,
              help="Rescan interval in seconds.")
@click.option("--device",  "device_ids", multiple=True,
              help="Device ID to share with (repeat for multiple).")
@click.pass_obj
def folder_add(client, path, folder_id, label, folder_type, rescan, device_ids):
    """Add a new folder to Syncthing.

    \b
    Examples:
      stcli folders add ~/Documents
      stcli folders add ~/Photos --label "My Photos" --type sendonly
      stcli folders add ~/Shared --device DEVICE-ID-1 --device DEVICE-ID-2
    """
    import os, re

    # Auto-generate ID from basename if not given
    if not folder_id:
        base = os.path.basename(path.rstrip("/"))
        folder_id = re.sub(r"[^a-z0-9\-]", "-", base.lower())[:20]

    if not label:
        label = os.path.basename(path.rstrip("/"))

    # Build device list — always include self
    my_id = client.system_status().get("myID", "")
    devices = [{"deviceID": my_id}]
    for did in device_ids:
        devices.append({"deviceID": did})

    folder_cfg = {
        "id":            folder_id,
        "label":         label,
        "path":          path,
        "type":          folder_type,
        "rescanIntervalS": rescan,
        "devices":       devices,
        "fsWatcherEnabled": True,
    }

    try:
        client.add_folder(folder_cfg)
    except Exception as e:
        console.print(f"[error]✗ Failed to add folder: {e}[/error]")
        raise SystemExit(1)

    console.print(Panel(
        f"[label]ID    :[/label] [id]{folder_id}[/id]\n"
        f"[label]Label :[/label] [value]{label}[/value]\n"
        f"[label]Path  :[/label] [path]{path}[/path]\n"
        f"[label]Type  :[/label] [value]{folder_type}[/value]\n"
        f"[label]Shared:[/label] [number]{len(devices)}[/number] device(s)",
        title="[good]✓ Folder Added[/good]",
        border_style="green",
        expand=False,
    ))


@folders_group.command("remove")
@click.argument("folder_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_obj
def folder_remove(client, folder_id, yes):
    """Remove a folder from Syncthing (does NOT delete local files).

    \b
    Example:
      stcli folders remove my-folder-id
      stcli folders remove my-folder-id --yes
    """
    # Verify it exists
    folders = {f["id"]: f for f in client.folders()}
    if folder_id not in folders:
        console.print(f"[error]✗ Folder '[id]{folder_id}[/id]' not found.[/error]")
        raise SystemExit(1)

    folder = folders[folder_id]
    label  = folder.get("label") or folder_id
    path   = folder.get("path", "—")

    if not yes:
        console.print(
            f"[warn]⚠  Remove folder [id]{folder_id}[/id] ([value]{label}[/value]) "
            f"at [path]{path}[/path]?[/warn]\n"
            f"[muted]Local files will NOT be deleted.[/muted]"
        )
        click.confirm("Continue?", abort=True)

    try:
        client.remove_folder(folder_id)
    except Exception as e:
        console.print(f"[error]✗ Failed: {e}[/error]")
        raise SystemExit(1)

    console.print(f"[good]✓ Folder [id]{folder_id}[/id] removed from Syncthing.[/good]")


@folders_group.command("share")
@click.argument("folder_id")
@click.argument("device_id")
@click.option("--encryption-password", default=None,
              help="Encrypt data for this device (receiveencrypted mode).")
@click.pass_obj
def folder_share(client, folder_id, device_id, encryption_password):
    """Share an existing folder with a device.

    \b
    The device must already be added to Syncthing.
    The folder will appear as a pending offer on the remote device.

    \b
    Examples:
      stcli folders share my-docs LBKP247-...
      stcli folders share my-docs LBKP247-... --encryption-password secret
    """
    # Resolve full device ID via prefix matching
    all_devices = client.devices()
    dev_matches = [d for d in all_devices if d["deviceID"].startswith(device_id)]
    if not dev_matches:
        console.print(
            f"[error]✗ Device '[id]{device_id}[/id]' not found.[/error]\n"
            f"[muted]Run [bold]stcli devices list[/bold] to see available devices,\n"
            f"or [bold]stcli devices add <ID>[/bold] to add it first.[/muted]"
        )
        raise SystemExit(1)
    if len(dev_matches) > 1:
        console.print(f"[warn]Ambiguous prefix – matched {len(dev_matches)} devices.[/warn]")
        raise SystemExit(1)
    full_device_id = dev_matches[0]["deviceID"]
    device_name    = dev_matches[0].get("name") or full_device_id[:7] + "…"

    # Get the current folder config
    try:
        folder = client.get_folder(folder_id)
    except Exception:
        console.print(f"[error]✗ Folder '[id]{folder_id}[/id]' not found.[/error]")
        raise SystemExit(1)

    existing_ids = {d["deviceID"] for d in folder.get("devices", [])}
    if full_device_id in existing_ids:
        console.print(
            f"[warn]⚠  Device [id]{full_device_id[:7]}…[/id] ([value]{device_name}[/value]) "
            f"is already sharing folder [id]{folder_id}[/id].[/warn]"
        )
        return

    # Append the new device entry
    new_device_entry: dict = {"deviceID": full_device_id}
    if encryption_password:
        new_device_entry["encryptionPassword"] = encryption_password

    folder["devices"] = folder.get("devices", []) + [new_device_entry]

    try:
        client.update_folder(folder_id, folder)
    except Exception as e:
        console.print(f"[error]✗ Failed to share folder: {e}[/error]")
        raise SystemExit(1)

    label = folder.get("label") or folder_id
    console.print(Panel(
        f"[label]Folder :[/label] [id]{folder_id}[/id] ([value]{label}[/value])\n"
        f"[label]Device :[/label] [id]{full_device_id[:7]}…[/id] ([value]{device_name}[/value])\n"
        f"[label]Encrypt:[/label] [value]{'yes' if encryption_password else 'no'}[/value]\n\n"
        f"[muted]The remote device will receive a folder offer.\n"
        f"They must accept it via their Syncthing UI or:\n"
        f"  stcli pending accept folder {folder_id} --from <their-device-id> --path <path>[/muted]",
        title="[good]✓ Folder Shared[/good]",
        border_style="green",
        expand=False,
    ))


@folders_group.command("unshare")
@click.argument("folder_id")
@click.argument("device_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_obj
def folder_unshare(client, folder_id, device_id, yes):
    """Stop sharing a folder with a device.

    \b
    Examples:
      stcli folders unshare my-docs LBKP247-...
      stcli folders unshare my-docs LBKP247-... --yes
    """
    # Resolve full device ID via prefix
    all_devices = client.devices()
    dev_matches = [d for d in all_devices if d["deviceID"].startswith(device_id)]
    if not dev_matches:
        console.print(f"[error]✗ Device '[id]{device_id}[/id]' not found.[/error]")
        raise SystemExit(1)
    if len(dev_matches) > 1:
        console.print(f"[warn]Ambiguous prefix – matched {len(dev_matches)} devices.[/warn]")
        raise SystemExit(1)
    full_device_id = dev_matches[0]["deviceID"]
    device_name    = dev_matches[0].get("name") or full_device_id[:7] + "…"

    # Get folder config
    try:
        folder = client.get_folder(folder_id)
    except Exception:
        console.print(f"[error]✗ Folder '[id]{folder_id}[/id]' not found.[/error]")
        raise SystemExit(1)

    existing = folder.get("devices", [])
    new_list  = [d for d in existing if d["deviceID"] != full_device_id]

    if len(new_list) == len(existing):
        console.print(
            f"[warn]⚠  Device [id]{full_device_id[:7]}…[/id] is not sharing "
            f"folder [id]{folder_id}[/id].[/warn]"
        )
        return

    if not yes:
        console.print(
            f"[warn]⚠  Stop sharing folder [id]{folder_id}[/id] with "
            f"[id]{full_device_id[:7]}…[/id] ([value]{device_name}[/value])?[/warn]"
        )
        click.confirm("Continue?", abort=True)

    folder["devices"] = new_list
    try:
        client.update_folder(folder_id, folder)
    except Exception as e:
        console.print(f"[error]✗ Failed: {e}[/error]")
        raise SystemExit(1)

    console.print(
        f"[good]✓ Stopped sharing [id]{folder_id}[/id] with "
        f"[id]{full_device_id[:7]}…[/id] ([value]{device_name}[/value]).[/good]"
    )


@folders_group.command("shares")
@click.argument("folder_id")
@click.pass_obj
def folder_shares(client, folder_id):
    """List all devices a folder is currently shared with.

    \b
    Example:
      stcli folders shares my-docs
    """
    try:
        folder = client.get_folder(folder_id)
    except Exception:
        console.print(f"[error]✗ Folder '[id]{folder_id}[/id]' not found.[/error]")
        raise SystemExit(1)

    label   = folder.get("label") or folder_id
    devices = folder.get("devices", [])

    # Get known device names
    all_devices = {d["deviceID"]: d.get("name", "") for d in client.devices()}
    my_id = client.system_status().get("myID", "")
    connections = client.system_connections().get("connections", {})

    table = Table(
        title=f"[title]Shares for 📁 {label}[/title]",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="heading",
        expand=False,
    )
    table.add_column("Device ID",  style="id",    no_wrap=True)
    table.add_column("Name",       style="value")
    table.add_column("Role",       style="label")
    table.add_column("Connected",  no_wrap=True)
    table.add_column("Encrypted",  style="muted")

    for entry in devices:
        did       = entry["deviceID"]
        name      = all_devices.get(did, "(unknown)")
        role      = "[synced]self[/synced]" if did == my_id else "peer"
        connected = connections.get(did, {}).get("connected", False)
        conn_str  = "[synced]● yes[/synced]" if connected else "[muted]○ no[/muted]"
        encrypted = "🔒 yes" if entry.get("encryptionPassword") else "no"
        table.add_row(did[:7] + "…", name or "(unnamed)", role, conn_str, encrypted)

    console.print(table)
    console.print(
        f"\n[muted]To share with another device: [bold]stcli folders share {folder_id} <DEVICE-ID>[/bold][/muted]"
    )
