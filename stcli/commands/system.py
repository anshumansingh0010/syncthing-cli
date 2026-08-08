"""stcli – system commands (info, rescan, restart, shutdown, logs, debug)."""

import click
from rich.table import Table
from rich.panel import Panel
from rich import box

from stcli.output import console, fmt_bytes, print_json
from stcli.resolvers import resolve_folder
from stcli.api import SyncthingError


@click.group("system")
def system_group():
    """System operations: info, rescan, restart, shutdown, logs, debug."""


@system_group.command("info")
@click.pass_context
def system_info(ctx):
    """Show detailed system information and server status."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)

    try:
        status  = client.system_status()
        version = client.system_version()
        conns   = client.system_connections()
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to get system info: {e}[/error]")
        raise SystemExit(1)

    if json_out:
        print_json({
            "status": status,
            "version": version,
            "connections": conns,
        })
        return

    uptime = status.get("uptime", 0)
    h, rem = divmod(uptime, 3600)
    m, s   = divmod(rem, 60)
    uptime_str = f"{h}h {m}m {s}s"

    lines = [
        f"[label]Version      :[/label] [value]{version.get('version', '—')}[/value]",
        f"[label]OS / Arch    :[/label] [value]{version.get('os', '')} / {version.get('arch', '')}[/value]",
        f"[label]Device ID    :[/label] [id]{status.get('myID', '—')}[/id]",
        f"[label]Uptime       :[/label] [number]{uptime_str}[/number]",
        f"[label]Alloc Memory :[/label] [number]{fmt_bytes(status.get('alloc', 0))}[/number]",
        f"[label]Sys Memory   :[/label] [number]{fmt_bytes(status.get('sys', 0))}[/number]",
        f"[label]Goroutines   :[/label] [number]{status.get('goroutines', 0)}[/number]",
        f"[label]CPU Usage    :[/label] [number]{status.get('cpuPercent', 0):.1f}%[/number]",
        f"[label]Discovery    :[/label] [value]{status.get('discoveryEnabled', False)}[/value]",
        f"[label]Relays       :[/label] [value]{status.get('relaysEnabled', False)}[/value]",
    ]

    console.print(Panel(
        "\n".join(lines),
        title="[title]⚙  Syncthing System Information[/title]",
        border_style="cyan",
        expand=False,
    ))


@system_group.command("rescan")
@click.argument("folder_id", required=False, default=None)
@click.option("--sub", default=None, help="Subdirectory path relative to folder root.")
@click.pass_obj
def system_rescan(client, folder_id, sub):
    """Trigger a rescan for all folders or a specific folder.

    \b
    Examples:
      stcli system rescan
      stcli system rescan my-folder
      stcli system rescan my-folder --sub photos/2026
    """
    try:
        resolved_id = None
        if folder_id:
            folder = resolve_folder(client, folder_id)
            resolved_id = folder["id"]

        client.db_scan(folder_id=resolved_id, sub=sub)
        target = f"folder '[id]{resolved_id}[/id]'" if resolved_id else "all folders"
        if sub:
            target += f" (sub: {sub})"
        console.print(f"[good]✓ Rescan triggered for {target}.[/good]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to trigger rescan: {e}[/error]")
        raise SystemExit(1)


@system_group.command("restart")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_obj
def system_restart(client, yes):
    """Restart the Syncthing service."""
    if not yes:
        click.confirm("Are you sure you want to restart Syncthing?", abort=True)
    try:
        client.system_restart()
        console.print("[good]✓ Sent restart request to Syncthing.[/good]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to restart: {e}[/error]")
        raise SystemExit(1)


@system_group.command("shutdown")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_obj
def system_shutdown(client, yes):
    """Shutdown the Syncthing service."""
    if not yes:
        click.confirm("Are you sure you want to shutdown Syncthing?", abort=True)
    try:
        client.system_shutdown()
        console.print("[good]✓ Sent shutdown request to Syncthing.[/good]")
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to shutdown: {e}[/error]")
        raise SystemExit(1)


@system_group.command("logs")
@click.option("--limit", "-n", default=20, type=int, show_default=True, help="Number of recent log lines to show.")
@click.pass_context
def system_logs(ctx, limit):
    """View recent system log messages from Syncthing."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)

    try:
        logs_data = client.system_logs()
        messages = logs_data.get("messages", [])
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to fetch logs: {e}[/error]")
        raise SystemExit(1)

    if json_out:
        print_json(messages[-limit:] if limit > 0 else messages)
        return

    table = Table(title="[title]Recent System Logs[/title]", box=box.SIMPLE, border_style="dim white")
    table.add_column("Time", style="muted", no_wrap=True)
    table.add_column("Message", style="value")

    for msg in messages[-limit:]:
        t = msg.get("when", "")[:19].replace("T", " ")
        table.add_row(t, msg.get("message", ""))

    console.print(table)


@system_group.command("debug")
@click.pass_context
def system_debug(ctx):
    """Show active debug facilities in Syncthing."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)

    try:
        debug_data = client.system_debug()
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to fetch debug state: {e}[/error]")
        raise SystemExit(1)

    if json_out:
        print_json(debug_data)
        return

    enabled = debug_data.get("enabled", [])
    facilities = debug_data.get("facilities", {})

    console.print(Panel(
        f"[label]Active facilities:[/label] [good]{', '.join(enabled) or 'None'}[/good]\n\n" +
        "\n".join(f"[label]{k}:[/label] [value]{v}[/value]" for k, v in facilities.items()),
        title="[title]🐛 System Debug Facilities[/title]",
        border_style="cyan",
        expand=False,
    ))
