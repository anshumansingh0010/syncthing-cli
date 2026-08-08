"""stcli – devices commands."""

import time
import click
from rich.table import Table
from rich.panel import Panel
from rich import box
from datetime import datetime, timezone

from stcli.output import console, fmt_bytes, device_state_style, print_json
from stcli.resolvers import resolve_device
from stcli.api import SyncthingError


def _short_id(device_id: str) -> str:
    return device_id[:7] + "…"


def _parse_time(ts: str | None) -> str:
    if not ts or ts.startswith("0001"):
        return "never"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        s = int(delta.total_seconds())
        if s < 60:      return f"{s}s ago"
        if s < 3600:    return f"{s // 60}m ago"
        if s < 86400:   return f"{s // 3600}h ago"
        return f"{s // 86400}d ago"
    except Exception:
        return ts[:10]


@click.group("devices")
def devices_group():
    """List, inspect, add, remove, edit, pause, resume, and ping devices."""


@devices_group.command("list")
@click.pass_context
def devices_list(ctx):
    """List all configured devices."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)

    try:
        devices     = client.devices()
        conns_resp  = client.system_connections()
        connections = conns_resp.get("connections", {}) if isinstance(conns_resp, dict) else {}
        stats       = client.stats_devices()
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to fetch devices: {e}[/error]")
        raise SystemExit(1)

    if json_out:
        print_json({
            "devices": devices,
            "connections": connections,
            "stats": stats,
        })
        return

    table = Table(
        title="[title]Syncthing Devices[/title]",
        box=box.ROUNDED,
        header_style="heading",
        border_style="dim white",
        expand=True,
    )
    table.add_column("Short ID", style="id",    no_wrap=True)
    table.add_column("Name",     style="value",  no_wrap=True)
    table.add_column("State",    no_wrap=True)
    table.add_column("Address",  style="path",   overflow="fold")
    table.add_column("Last Seen",style="muted",  no_wrap=True)
    table.add_column("In / Out", style="number", no_wrap=True)

    for dev in devices:
        did    = dev["deviceID"]
        name   = dev.get("name") or _short_id(did)
        paused = dev.get("paused", False)
        conn   = connections.get(did, {}) if isinstance(connections, dict) else {}
        stat   = stats.get(did, {}) if isinstance(stats, dict) else {}

        connected = conn.get("connected", False) if isinstance(conn, dict) else False
        addr      = conn.get("address", "—") if connected and isinstance(conn, dict) else "—"
        last_seen = _parse_time(stat.get("lastSeen") if isinstance(stat, dict) else None)
        inb       = fmt_bytes(conn.get("inBytesTotal", 0)) if isinstance(conn, dict) else "0 B"
        outb      = fmt_bytes(conn.get("outBytesTotal", 0)) if isinstance(conn, dict) else "0 B"

        table.add_row(
            _short_id(did), name,
            device_state_style(connected, paused),
            addr, last_seen,
            f"{inb} / {outb}",
        )

    console.print(table)


@devices_group.command("info")
@click.argument("device_id")
@click.pass_context
def device_info(ctx, device_id):
    """Show detailed info for a specific device (full ID, short ID, or name)."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)

    dev = resolve_device(client, device_id)
    did = dev["deviceID"]

    conns_resp  = client.system_connections()
    connections = conns_resp.get("connections", {}) if isinstance(conns_resp, dict) else {}
    conn        = connections.get(did, {}) if isinstance(connections, dict) else {}
    stats       = client.stats_devices()
    stat        = stats.get(did, {}) if isinstance(stats, dict) else {}

    if json_out:
        print_json({
            "config": dev,
            "connection": conn,
            "stats": stat,
        })
        return

    lines = [
        f"[label]Device ID   :[/label] [id]{did}[/id]",
        f"[label]Name        :[/label] [value]{dev.get('name') or '(unnamed)'}[/value]",
        f"[label]Paused      :[/label] [value]{dev.get('paused', False)}[/value]",
        f"[label]Introducer  :[/label] [value]{dev.get('introducer', False)}[/value]",
        f"[label]Auto Accept :[/label] [value]{dev.get('autoAcceptFolders', False)}[/value]",
        "",
        f"[label]Connected   :[/label] {device_state_style(conn.get('connected', False), dev.get('paused', False))}",
        f"[label]Address     :[/label] [path]{conn.get('address', '—')}[/path]",
        f"[label]Type        :[/label] [value]{conn.get('type', '—')}[/value]",
        f"[label]Client      :[/label] [value]{conn.get('clientVersion', '—')}[/value]",
        f"[label]In / Out    :[/label] [number]{fmt_bytes(conn.get('inBytesTotal', 0))} / {fmt_bytes(conn.get('outBytesTotal', 0))}[/number]",
        "",
        f"[label]Last Seen   :[/label] [value]{_parse_time(stat.get('lastSeen'))}[/value]",
    ]

    addresses = dev.get("addresses", [])
    if addresses:
        lines.append(f"\n[label]Configured addresses:[/label]")
        for a in addresses:
            lines.append(f"  [path]{a}[/path]")

    console.print(Panel(
        "\n".join(lines),
        title=f"[title]🖥  {dev.get('name') or _short_id(did)}[/title]",
        border_style="cyan",
        expand=False,
    ))


@devices_group.command("pause")
@click.argument("device_id")
@click.pass_obj
def device_pause(client, device_id):
    """Pause syncing with a device."""
    dev = resolve_device(client, device_id)
    did = dev["deviceID"]
    try:
        client.pause_device(did)
        console.print(f"[paused]⏸  Device [id]{_short_id(did)}[/id] paused.[/paused]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to pause device: {e}[/error]")
        raise SystemExit(1)


@devices_group.command("resume")
@click.argument("device_id")
@click.pass_obj
def device_resume(client, device_id):
    """Resume syncing with a device."""
    dev = resolve_device(client, device_id)
    did = dev["deviceID"]
    try:
        client.resume_device(did)
        console.print(f"[synced]▶  Device [id]{_short_id(did)}[/id] resumed.[/synced]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to resume device: {e}[/error]")
        raise SystemExit(1)


@devices_group.command("edit")
@click.argument("device_id")
@click.option("--name", default=None, help="Set friendly device name.")
@click.option("--address", "addresses", multiple=True, help="Set configured address(es).")
@click.option("--introducer/--no-introducer", default=None, help="Set introducer flag.")
@click.option("--auto-accept/--no-auto-accept", default=None, help="Auto accept folders from this device.")
@click.pass_obj
def device_edit(client, device_id, name, addresses, introducer, auto_accept):
    """Edit settings of an existing device."""
    dev = resolve_device(client, device_id)
    did = dev["deviceID"]
    dev_cfg = client.get_device(did)

    updated = False
    if name is not None:
        dev_cfg["name"] = name
        updated = True
    if addresses:
        dev_cfg["addresses"] = list(addresses)
        updated = True
    if introducer is not None:
        dev_cfg["introducer"] = introducer
        updated = True
    if auto_accept is not None:
        dev_cfg["autoAcceptFolders"] = auto_accept
        updated = True

    if not updated:
        console.print("[warn]No options provided to update.[/warn]")
        return

    try:
        client.update_device(did, dev_cfg)
        console.print(f"[good]✓ Device [id]{_short_id(did)}[/id] updated successfully.[/good]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to update device: {e}[/error]")
        raise SystemExit(1)


@devices_group.command("ping")
@click.argument("device_id")
@click.pass_context
def device_ping(ctx, device_id):
    """Check connection status and details for a device."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)
    dev = resolve_device(client, device_id)
    did = dev["deviceID"]

    conns_resp  = client.system_connections()
    connections = conns_resp.get("connections", {}) if isinstance(conns_resp, dict) else {}
    conn        = connections.get(did, {}) if isinstance(connections, dict) else {}

    connected = conn.get("connected", False) if isinstance(conn, dict) else False

    if json_out:
        print_json({
            "deviceID": did,
            "name": dev.get("name"),
            "connected": connected,
            "connectionDetails": conn,
        })
        return

    if connected:
        console.print(Panel(
            f"[good]● Connected[/good]\n\n"
            f"[label]Device   :[/label] [id]{did}[/id] ([value]{dev.get('name') or '(unnamed)'}[/value])\n"
            f"[label]Address  :[/label] [path]{conn.get('address', '—')}[/path]\n"
            f"[label]Client   :[/label] [value]{conn.get('clientVersion', '—')}[/value]\n"
            f"[label]Protocol :[/label] [value]{conn.get('type', '—')}[/value]\n"
            f"[label]Crypto   :[/label] [value]{conn.get('crypto', '—')}[/value]",
            title="[good]✓ Device Ping OK[/good]",
            border_style="green",
            expand=False,
        ))
    else:
        console.print(Panel(
            f"[muted]○ Disconnected[/muted]\n\n"
            f"[label]Device   :[/label] [id]{did}[/id] ([value]{dev.get('name') or '(unnamed)'}[/value])",
            title="[warn]⚠ Device Disconnected[/warn]",
            border_style="yellow",
            expand=False,
        ))


@devices_group.command("add")
@click.argument("device_id")
@click.option("--name",      default=None, help="Friendly name for the device.")
@click.option("--address",   "addresses", multiple=True,
              help="Address hint, e.g. tcp://192.168.1.5:22000 (repeat for multiple). Defaults to 'dynamic'.")
@click.option("--introducer", is_flag=True, default=False,
              help="Trust this device as an introducer.")
@click.pass_obj
def device_add(client, device_id, name, addresses, introducer):
    """Add a new device to Syncthing."""
    cfg = {
        "deviceID":    device_id,
        "name":        name or "",
        "addresses":   list(addresses) if addresses else ["dynamic"],
        "introducer":  introducer,
        "autoAcceptFolders": False,
    }

    try:
        client.add_device(cfg)
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to add device: {e}[/error]")
        raise SystemExit(1)

    console.print(Panel(
        f"[label]Device ID  :[/label] [id]{device_id}[/id]\n"
        f"[label]Name       :[/label] [value]{name or '(none)'}[/value]\n"
        f"[label]Addresses  :[/label] [path]{', '.join(addresses) or 'dynamic'}[/path]\n"
        f"[label]Introducer :[/label] [value]{introducer}[/value]",
        title="[good]✓ Device Added[/good]",
        border_style="green",
        expand=False,
    ))


@devices_group.command("remove")
@click.argument("device_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_obj
def device_remove(client, device_id, yes):
    """Remove a device from Syncthing."""
    dev  = resolve_device(client, device_id)
    did  = dev["deviceID"]
    name = dev.get("name") or _short_id(did)

    if not yes:
        console.print(
            f"[warn]⚠  Remove device [id]{_short_id(did)}[/id] ([value]{name}[/value])?[/warn]"
        )
        click.confirm("Continue?", abort=True)

    try:
        client.remove_device(did)
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to remove device: {e}[/error]")
        raise SystemExit(1)

    console.print(f"[good]✓ Device [id]{_short_id(did)}[/id] ([value]{name}[/value]) removed.[/good]")
