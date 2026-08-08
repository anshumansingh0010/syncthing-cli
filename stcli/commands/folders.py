"""stcli – folders commands."""

import click
from rich.table import Table
from rich.panel import Panel
from rich import box

from stcli.output import console, fmt_bytes, fmt_pct, folder_state_style, print_json
from stcli.resolvers import resolve_folder, resolve_device
from stcli.api import SyncthingError


@click.group("folders")
def folders_group():
    """List, inspect, add, remove, edit, pause, resume, and manage synced folders."""


@folders_group.command("list")
@click.pass_context
def folders_list(ctx):
    """List all configured folders and their sync state."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)

    try:
        folders = client.folders()
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to fetch folders: {e}[/error]")
        raise SystemExit(1)

    if json_out:
        print_json(folders)
        return

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
@click.pass_context
def folder_info(ctx, folder_id):
    """Show detailed info for a specific folder (ID, label, or prefix)."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)

    folder = resolve_folder(client, folder_id)
    fid = folder["id"]

    try:
        status = client.folder_status(fid)
    except Exception:
        status = {}

    try:
        completion = client.folder_completion(fid)
    except Exception:
        completion = {}

    if json_out:
        print_json({
            "config": folder,
            "status": status,
            "completion": completion,
        })
        return

    label  = folder.get("label") or fid
    paused = folder.get("paused", False)
    state  = status.get("state", "unknown")
    pct    = completion.get("completion", 100.0)

    lines = [
        f"[label]ID       :[/label] [id]{fid}[/id]",
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
    folder = resolve_folder(client, folder_id)
    fid = folder["id"]
    try:
        client.pause_folder(fid)
        console.print(f"[paused]⏸  Folder [id]{fid}[/id] paused.[/paused]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to pause folder: {e}[/error]")
        raise SystemExit(1)


@folders_group.command("resume")
@click.argument("folder_id")
@click.pass_obj
def folder_resume(client, folder_id):
    """Resume syncing for a folder."""
    folder = resolve_folder(client, folder_id)
    fid = folder["id"]
    try:
        client.resume_folder(fid)
        console.print(f"[synced]▶  Folder [id]{fid}[/id] resumed.[/synced]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to resume folder: {e}[/error]")
        raise SystemExit(1)


@folders_group.command("rescan")
@click.argument("folder_id")
@click.option("--sub", default=None, help="Subdirectory relative to folder root.")
@click.pass_obj
def folder_rescan(client, folder_id, sub):
    """Trigger an immediate rescan of a folder."""
    folder = resolve_folder(client, folder_id)
    fid = folder["id"]
    try:
        client.db_scan(folder_id=fid, sub=sub)
        msg = f"[good]✓ Rescan triggered for folder [id]{fid}[/id][/good]"
        if sub:
            msg += f" (sub: {sub})"
        console.print(msg)
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to rescan folder: {e}[/error]")
        raise SystemExit(1)


@folders_group.command("override")
@click.argument("folder_id")
@click.pass_obj
def folder_override(client, folder_id):
    """Override remote changes for a Send Only folder."""
    folder = resolve_folder(client, folder_id)
    fid = folder["id"]
    try:
        client.db_override(fid)
        console.print(f"[good]✓ Sent override command for folder [id]{fid}[/id].[/good]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to override folder: {e}[/error]")
        raise SystemExit(1)


@folders_group.command("revert")
@click.argument("folder_id")
@click.pass_obj
def folder_revert(client, folder_id):
    """Revert local changes for a Receive Only folder."""
    folder = resolve_folder(client, folder_id)
    fid = folder["id"]
    try:
        client.db_revert(fid)
        console.print(f"[good]✓ Sent revert command for folder [id]{fid}[/id].[/good]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to revert folder: {e}[/error]")
        raise SystemExit(1)


@folders_group.command("ignore")
@click.argument("folder_id")
@click.option("--add", "add_pattern", multiple=True, help="Add ignore pattern(s).")
@click.pass_context
def folder_ignore(ctx, folder_id, add_pattern):
    """View or manage ignore patterns (.stignore) for a folder."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)
    folder = resolve_folder(client, folder_id)
    fid = folder["id"]

    try:
        data = client.db_ignores(fid)
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to fetch ignores: {e}[/error]")
        raise SystemExit(1)

    patterns = data.get("ignore") or []

    if add_pattern:
        new_patterns = patterns + list(add_pattern)
        try:
            res = client.update_db_ignores(fid, new_patterns)
            patterns = res.get("ignore", new_patterns)
            console.print(f"[good]✓ Added {len(add_pattern)} ignore pattern(s) to folder [id]{fid}[/id].[/good]")
        except SyncthingError as e:
            console.print(f"[error]✗ Failed to update ignores: {e}[/error]")
            raise SystemExit(1)

    if json_out:
        print_json({"folder": fid, "ignore": patterns})
        return

    table = Table(title=f"[title]Ignore Patterns – {fid}[/title]", box=box.SIMPLE)
    table.add_column("Pattern", style="value")
    for p in patterns:
        table.add_row(p)

    console.print(table)


@folders_group.command("edit")
@click.argument("folder_id")
@click.option("--label", default=None, help="Set new human-readable label.")
@click.option("--type", "folder_type", type=click.Choice(["sendreceive", "sendonly", "receiveonly", "receiveencrypted"]), default=None)
@click.option("--rescan", type=int, default=None, help="Rescan interval in seconds.")
@click.pass_obj
def folder_edit(client, folder_id, label, folder_type, rescan):
    """Update settings of an existing folder."""
    folder = resolve_folder(client, folder_id)
    fid = folder["id"]

    updated = False
    if label is not None:
        folder["label"] = label
        updated = True
    if folder_type is not None:
        folder["type"] = folder_type
        updated = True
    if rescan is not None:
        folder["rescanIntervalS"] = rescan
        updated = True

    if not updated:
        console.print("[warn]No options provided to update.[/warn]")
        return

    try:
        client.update_folder(fid, folder)
        console.print(f"[good]✓ Folder [id]{fid}[/id] updated successfully.[/good]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to update folder: {e}[/error]")
        raise SystemExit(1)


@folders_group.command("errors")
@click.argument("folder_id")
@click.pass_context
def folder_errors(ctx, folder_id):
    """Show sync errors for a folder."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)
    folder = resolve_folder(client, folder_id)
    fid = folder["id"]

    try:
        result = client.folder_errors(fid)
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to fetch folder errors: {e}[/error]")
        raise SystemExit(1)

    errors = result.get("errors") or []
    if json_out:
        print_json({"folder": fid, "errors": errors})
        return

    if not errors:
        console.print(f"[synced]✓ No errors for folder [id]{fid}[/id][/synced]")
        return

    table = Table(title=f"[error]Errors – {fid}[/error]", box=box.SIMPLE)
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
    """Add a new folder to Syncthing."""
    import os, re

    if not folder_id:
        base = os.path.basename(path.rstrip("/"))
        folder_id = re.sub(r"[^a-z0-9\-]", "-", base.lower())[:20]

    if not label:
        label = os.path.basename(path.rstrip("/"))

    my_id = client.system_status().get("myID", "")
    devices = [{"deviceID": my_id}]
    for did in device_ids:
        dev = resolve_device(client, did)
        devices.append({"deviceID": dev["deviceID"]})

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
    except SyncthingError as e:
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
    """Remove a folder from Syncthing (does NOT delete local files)."""
    folder = resolve_folder(client, folder_id)
    fid    = folder["id"]
    label  = folder.get("label") or fid
    path   = folder.get("path", "—")

    if not yes:
        console.print(
            f"[warn]⚠  Remove folder [id]{fid}[/id] ([value]{label}[/value]) "
            f"at [path]{path}[/path]?[/warn]\n"
            f"[muted]Local files will NOT be deleted.[/muted]"
        )
        click.confirm("Continue?", abort=True)

    try:
        client.remove_folder(fid)
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to remove folder: {e}[/error]")
        raise SystemExit(1)

    console.print(f"[good]✓ Folder [id]{fid}[/id] removed from Syncthing.[/good]")


@folders_group.command("share")
@click.argument("folder_id")
@click.argument("device_id")
@click.option("--encryption-password", default=None,
              help="Encrypt data for this device (receiveencrypted mode).")
@click.pass_obj
def folder_share(client, folder_id, device_id, encryption_password):
    """Share an existing folder with a device."""
    folder = resolve_folder(client, folder_id)
    fid    = folder["id"]
    device = resolve_device(client, device_id)
    did    = device["deviceID"]
    device_name = device.get("name") or did[:7] + "…"

    folder_cfg = client.get_folder(fid)
    existing_ids = {d["deviceID"] for d in folder_cfg.get("devices", [])}
    if did in existing_ids:
        console.print(
            f"[warn]⚠  Device [id]{did[:7]}…[/id] ([value]{device_name}[/value]) "
            f"is already sharing folder [id]{fid}[/id].[/warn]"
        )
        return

    new_device_entry: dict = {"deviceID": did}
    if encryption_password:
        new_device_entry["encryptionPassword"] = encryption_password

    folder_cfg["devices"] = folder_cfg.get("devices", []) + [new_device_entry]

    try:
        client.update_folder(fid, folder_cfg)
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to share folder: {e}[/error]")
        raise SystemExit(1)

    label = folder_cfg.get("label") or fid
    console.print(Panel(
        f"[label]Folder :[/label] [id]{fid}[/id] ([value]{label}[/value])\n"
        f"[label]Device :[/label] [id]{did[:7]}…[/id] ([value]{device_name}[/value])\n"
        f"[label]Encrypt:[/label] [value]{'yes' if encryption_password else 'no'}[/value]\n\n"
        f"[muted]The remote device will receive a folder offer.[/muted]",
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
    """Stop sharing a folder with a device."""
    folder = resolve_folder(client, folder_id)
    fid    = folder["id"]
    device = resolve_device(client, device_id)
    did    = device["deviceID"]
    device_name = device.get("name") or did[:7] + "…"

    folder_cfg = client.get_folder(fid)
    existing = folder_cfg.get("devices", [])
    new_list = [d for d in existing if d["deviceID"] != did]

    if len(new_list) == len(existing):
        console.print(
            f"[warn]⚠  Device [id]{did[:7]}…[/id] is not sharing "
            f"folder [id]{fid}[/id].[/warn]"
        )
        return

    if not yes:
        console.print(
            f"[warn]⚠  Stop sharing folder [id]{fid}[/id] with "
            f"[id]{did[:7]}…[/id] ([value]{device_name}[/value])?[/warn]"
        )
        click.confirm("Continue?", abort=True)

    folder_cfg["devices"] = new_list
    try:
        client.update_folder(fid, folder_cfg)
    except SyncthingError as e:
        console.print(f"[error]✗ Failed: {e}[/error]")
        raise SystemExit(1)

    console.print(
        f"[good]✓ Stopped sharing [id]{fid}[/id] with "
        f"[id]{did[:7]}…[/id] ([value]{device_name}[/value]).[/good]"
    )


@folders_group.command("shares")
@click.argument("folder_id")
@click.pass_context
def folder_shares(ctx, folder_id):
    """List all devices a folder is currently shared with."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)
    folder = resolve_folder(client, folder_id)
    fid = folder["id"]
    folder_cfg = client.get_folder(fid)

    label   = folder_cfg.get("label") or fid
    devices = folder_cfg.get("devices", [])

    all_devices = {d["deviceID"]: d.get("name", "") for d in client.devices()}
    my_id = client.system_status().get("myID", "")
    connections = client.system_connections().get("connections", {})

    if json_out:
        print_json({"folder": fid, "shares": devices})
        return

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
        connected = connections.get(did, {}).get("connected", False) if isinstance(connections, dict) else False
        conn_str  = "[synced]● yes[/synced]" if connected else "[muted]○ no[/muted]"
        encrypted = "🔒 yes" if entry.get("encryptionPassword") else "no"
        table.add_row(did[:7] + "…", name or "(unnamed)", role, conn_str, encrypted)

    console.print(table)
