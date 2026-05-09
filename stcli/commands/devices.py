"""stcli – devices commands."""

import click
from rich.table import Table
from rich.panel import Panel
from rich import box
from datetime import datetime, timezone

from stcli.output import console, fmt_bytes, device_state_style


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
    """List, inspect, add, remove, pause, and resume connected devices."""


@devices_group.command("list")
@click.pass_obj
def devices_list(client):
    """List all configured devices."""
    devices     = client.devices()
    connections = client.system_connections().get("connections", {})
    stats       = client.stats_devices()

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
        conn   = connections.get(did, {})
        stat   = stats.get(did, {})

        connected = conn.get("connected", False)
        addr      = conn.get("address", "—") if connected else "—"
        last_seen = _parse_time(stat.get("lastSeen"))
        inb       = fmt_bytes(conn.get("inBytesTotal", 0))
        outb      = fmt_bytes(conn.get("outBytesTotal", 0))

        table.add_row(
            _short_id(did), name,
            device_state_style(connected, paused),
            addr, last_seen,
            f"{inb} / {outb}",
        )

    console.print(table)


@devices_group.command("info")
@click.argument("device_id")
@click.pass_obj
def device_info(client, device_id):
    """Show detailed info for a specific device (full or short ID)."""
    devices = client.devices()
    # Support prefix matching
    match = [d for d in devices if d["deviceID"].startswith(device_id)]
    if not match:
        console.print(f"[error]No device found matching '[id]{device_id}[/id]'[/error]")
        raise SystemExit(1)
    if len(match) > 1:
        console.print(f"[warn]Ambiguous prefix – matched {len(match)} devices.[/warn]")
        raise SystemExit(1)

    dev  = match[0]
    did  = dev["deviceID"]
    conn = client.system_connections().get("connections", {}).get(did, {})
    stat = client.stats_devices().get(did, {})

    lines = [
        f"[label]Device ID   :[/label] [id]{did}[/id]",
        f"[label]Name        :[/label] [value]{dev.get('name') or '(unnamed)'}[/value]",
        f"[label]Paused      :[/label] [value]{dev.get('paused', False)}[/value]",
        f"[label]Introducer  :[/label] [value]{dev.get('introducer', False)}[/value]",
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
    client.pause_device(device_id)
    console.print(f"[paused]⏸  Device [id]{device_id}[/id] paused.[/paused]")


@devices_group.command("resume")
@click.argument("device_id")
@click.pass_obj
def device_resume(client, device_id):
    """Resume syncing with a device."""
    client.resume_device(device_id)
    console.print(f"[synced]▶  Device [id]{device_id}[/id] resumed.[/synced]")


@devices_group.command("add")
@click.argument("device_id")
@click.option("--name",      default=None, help="Friendly name for the device.")
@click.option("--address",   "addresses", multiple=True,
              help="Address hint, e.g. tcp://192.168.1.5:22000 (repeat for multiple). Defaults to 'dynamic'.")
@click.option("--introducer", is_flag=True, default=False,
              help="Trust this device as an introducer.")
@click.pass_obj
def device_add(client, device_id, name, addresses, introducer):
    """Add a new device to Syncthing.

    \b
    Examples:
      stcli devices add DEVICE7-ABCDEF-...
      stcli devices add DEVICE7-ABCDEF-... --name laptop --address tcp://192.168.1.10:22000
    """
    cfg = {
        "deviceID":    device_id,
        "name":        name or "",
        "addresses":   list(addresses) if addresses else ["dynamic"],
        "introducer":  introducer,
        "autoAcceptFolders": False,
    }

    try:
        client.add_device(cfg)
    except Exception as e:
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
    """Remove a device from Syncthing.

    \b
    Example:
      stcli devices remove DEVICE7-ABCDEF-...
      stcli devices remove DEVICE7-ABCDEF-... --yes
    """
    devices = client.devices()
    # Support prefix matching
    match = [d for d in devices if d["deviceID"].startswith(device_id)]
    if not match:
        console.print(f"[error]✗ No device found matching '[id]{device_id}[/id]'[/error]")
        raise SystemExit(1)
    if len(match) > 1:
        console.print(f"[warn]Ambiguous prefix – matched {len(match)} devices.[/warn]")
        raise SystemExit(1)

    dev  = match[0]
    did  = dev["deviceID"]
    name = dev.get("name") or _short_id(did)

    if not yes:
        console.print(
            f"[warn]⚠  Remove device [id]{_short_id(did)}[/id] ([value]{name}[/value])?[/warn]"
        )
        click.confirm("Continue?", abort=True)

    try:
        client.remove_device(did)
    except Exception as e:
        console.print(f"[error]✗ Failed: {e}[/error]")
        raise SystemExit(1)

    console.print(f"[good]✓ Device [id]{_short_id(did)}[/id] ([value]{name}[/value]) removed.[/good]")
