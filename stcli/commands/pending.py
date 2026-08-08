"""stcli – pending command group (list, accept, dismiss)."""

import click
from rich.table import Table
from rich.panel import Panel
from rich import box

from stcli.output import console, print_json
from stcli.resolvers import resolve_device
from stcli.api import SyncthingError


def _short(did: str) -> str:
    return did[:7] + "…"


@click.group("pending")
def pending_cmd():
    """Show, accept, or dismiss pending device/folder requests."""


@pending_cmd.command("list")
@click.pass_context
def pending_list(ctx):
    """Show all pending devices and folders waiting to be accepted."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)

    try:
        pend_devs    = client.pending_devices()
        pend_folders = client.pending_folders()
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to fetch pending items: {e}[/error]")
        raise SystemExit(1)

    if json_out:
        print_json({
            "pending_devices": pend_devs,
            "pending_folders": pend_folders,
        })
        return

    if not pend_devs and not pend_folders:
        console.print("[synced]✓ No pending devices or folders.[/synced]")
        return

    if pend_devs:
        table = Table(
            title="[warn]⚠  Pending Devices[/warn]",
            box=box.ROUNDED,
            border_style="yellow",
        )
        table.add_column("Device ID",  style="id")
        table.add_column("Name",       style="value")
        table.add_column("Address",    style="path")
        table.add_column("First Seen", style="muted")

        for did, info in pend_devs.items():
            addrs = ", ".join(info.get("address", []))
            table.add_row(
                _short(did),
                info.get("name", "—"),
                addrs,
                info.get("time", "—")[:10],
            )
        console.print(table)
        console.print(
            "[muted]→ Accept:  [bold]stcli pending accept device <DEVICE-ID>[/bold][/muted]\n"
            "[muted]→ Dismiss: [bold]stcli pending dismiss device <DEVICE-ID>[/bold][/muted]"
        )

    if pend_folders:
        table = Table(
            title="[warn]⚠  Pending Folders[/warn]",
            box=box.ROUNDED,
            border_style="yellow",
        )
        table.add_column("Folder ID",  style="id")
        table.add_column("Label",      style="value")
        table.add_column("Offered By", style="path")
        table.add_column("First Seen", style="muted")

        for fid, info in pend_folders.items():
            offered_by = info.get("offeredBy", {})
            by = ", ".join(_short(d) for d in offered_by.keys())
            label = info.get("label", "—")
            table.add_row(fid, label, by, info.get("time", "—")[:10])
        console.print(table)
        console.print(
            "[muted]→ Accept:  [bold]stcli pending accept folder <FOLDER-ID> --from <DEVICE-ID> --path <PATH>[/bold][/muted]\n"
            "[muted]→ Dismiss: [bold]stcli pending dismiss folder <FOLDER-ID> --from <DEVICE-ID>[/bold][/muted]"
        )


# ── Accept sub-group ──────────────────────────────────────────────────────────

@pending_cmd.group("accept")
def accept_group():
    """Accept a pending device or folder request."""


@accept_group.command("device")
@click.argument("device_id")
@click.option("--name", default=None, help="Friendly name for the device.")
@click.option("--introducer", is_flag=True, default=False,
              help="Trust as an introducer.")
@click.pass_obj
def accept_device(client, device_id, name, introducer):
    """Accept a pending device connection request."""
    pend = client.pending_devices()
    matches = {did: info for did, info in pend.items() if did.lower().startswith(device_id.lower())}
    if not matches:
        console.print(f"[error]✗ No pending device matching '[id]{device_id}[/id]'[/error]")
        console.print("[muted]Run [bold]stcli pending list[/bold] to see pending devices.[/muted]")
        raise SystemExit(1)
    if len(matches) > 1:
        console.print(f"[warn]Ambiguous prefix – matched {len(matches)} pending devices.[/warn]")
        raise SystemExit(1)

    full_id, info = next(iter(matches.items()))
    resolved_name = name or info.get("name", "")

    cfg = {
        "deviceID":   full_id,
        "name":       resolved_name,
        "addresses":  ["dynamic"],
        "introducer": introducer,
        "autoAcceptFolders": False,
    }

    try:
        client.add_device(cfg)
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to accept device: {e}[/error]")
        raise SystemExit(1)

    console.print(Panel(
        f"[label]Device ID :[/label] [id]{full_id}[/id]\n"
        f"[label]Name      :[/label] [value]{resolved_name or '(unnamed)'}[/value]\n"
        f"[label]Introducer:[/label] [value]{introducer}[/value]",
        title="[good]✓ Device Accepted[/good]",
        border_style="green",
        expand=False,
    ))


@accept_group.command("folder")
@click.argument("folder_id")
@click.option("--from",  "from_device", required=True,
              help="Device ID that offered this folder.")
@click.option("--path",  "local_path",  required=True,
              type=click.Path(resolve_path=True),
              help="Local path where the folder should be stored.")
@click.option("--label", default=None, help="Override folder label.")
@click.option("--type",  "folder_type",
              type=click.Choice(["sendreceive", "sendonly", "receiveonly"]),
              default="sendreceive", show_default=True)
@click.pass_obj
def accept_folder(client, folder_id, from_device, local_path, label, folder_type):
    """Accept a pending folder offered by another device."""
    import os
    pend = client.pending_folders()
    matches = {fid: info for fid, info in pend.items() if fid.lower().startswith(folder_id.lower())}
    if not matches:
        console.print(f"[error]✗ No pending folder matching '[id]{folder_id}[/id]'[/error]")
        console.print("[muted]Run [bold]stcli pending list[/bold] to see pending folders.[/muted]")
        raise SystemExit(1)
    if len(matches) > 1:
        console.print(f"[warn]Ambiguous prefix – matched {len(matches)} pending folders.[/warn]")
        raise SystemExit(1)

    full_fid, info = next(iter(matches.items()))
    resolved_label = label or info.get("label") or os.path.basename(local_path)

    # Resolve from_device to full device ID if possible
    offered_by = info.get("offeredBy", {})
    from_matches = [d for d in offered_by.keys() if d.lower().startswith(from_device.lower())]
    if from_matches:
        full_from_device = from_matches[0]
    else:
        # Fallback to resolve_device or raw string
        try:
            dev = resolve_device(client, from_device)
            full_from_device = dev["deviceID"]
        except Exception:
            full_from_device = from_device

    my_id = client.system_status().get("myID", "")
    devices = [{"deviceID": my_id}, {"deviceID": full_from_device}]

    cfg = {
        "id":    full_fid,
        "label": resolved_label,
        "path":  local_path,
        "type":  folder_type,
        "devices": devices,
        "fsWatcherEnabled": True,
        "rescanIntervalS":  3600,
    }

    try:
        client.add_folder(cfg)
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to accept folder: {e}[/error]")
        raise SystemExit(1)

    console.print(Panel(
        f"[label]Folder ID :[/label] [id]{full_fid}[/id]\n"
        f"[label]Label     :[/label] [value]{resolved_label}[/value]\n"
        f"[label]Path      :[/label] [path]{local_path}[/path]\n"
        f"[label]Type      :[/label] [value]{folder_type}[/value]\n"
        f"[label]From      :[/label] [id]{_short(full_from_device)}[/id]",
        title="[good]✓ Folder Accepted[/good]",
        border_style="green",
        expand=False,
    ))


# ── Dismiss sub-group ─────────────────────────────────────────────────────────

@pending_cmd.group("dismiss")
def dismiss_group():
    """Dismiss (ignore) a pending device or folder request."""


@dismiss_group.command("device")
@click.argument("device_id")
@click.pass_obj
def dismiss_device(client, device_id):
    """Dismiss a pending device request."""
    pend = client.pending_devices()
    matches = {did: info for did, info in pend.items() if did.lower().startswith(device_id.lower())}
    if not matches:
        console.print(f"[error]✗ No pending device matching '[id]{device_id}[/id]'[/error]")
        raise SystemExit(1)

    for full_id in matches:
        try:
            client.dismiss_pending_device(full_id)
            console.print(f"[muted]✓ Dismissed device [id]{_short(full_id)}[/id][/muted]")
        except SyncthingError as e:
            console.print(f"[error]✗ Failed to dismiss [id]{_short(full_id)}[/id]: {e}[/error]")


@dismiss_group.command("folder")
@click.argument("folder_id")
@click.option("--from", "from_device", required=True,
              help="Device ID that offered the folder.")
@click.pass_obj
def dismiss_folder(client, folder_id, from_device):
    """Dismiss a pending folder offer."""
    pend = client.pending_folders()
    matches = {fid: info for fid, info in pend.items() if fid.lower().startswith(folder_id.lower())}
    if matches:
        if len(matches) > 1:
            console.print(f"[warn]Ambiguous prefix – matched {len(matches)} pending folders.[/warn]")
            raise SystemExit(1)
        full_fid = next(iter(matches.keys()))
    else:
        full_fid = folder_id

    try:
        dev = resolve_device(client, from_device)
        full_from = dev["deviceID"]
    except Exception:
        full_from = from_device

    try:
        client.dismiss_pending_folder(full_fid, full_from)
        console.print(f"[muted]✓ Dismissed folder [id]{full_fid}[/id] from [id]{_short(full_from)}[/id][/muted]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to dismiss folder: {e}[/error]")
        raise SystemExit(1)
