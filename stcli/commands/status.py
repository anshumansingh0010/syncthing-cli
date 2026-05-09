"""stcli – status command."""

import click
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.table import Table
from rich import box

from stcli.output import console, fmt_bytes, folder_state_style, device_state_style


@click.command("status")
@click.pass_obj
def status_cmd(client):
    """Show an overall snapshot of your Syncthing instance."""
    sys_status   = client.system_status()
    sys_version  = client.system_version()
    folders      = client.folders()
    devices      = client.devices()
    connections  = client.system_connections().get("connections", {})

    my_id  = sys_status.get("myID", "")
    uptime = sys_status.get("uptime", 0)
    alloc  = sys_status.get("alloc", 0)
    sys_mb = sys_status.get("sys", 0)

    # Uptime formatting
    h, rem = divmod(uptime, 3600)
    m, s   = divmod(rem, 60)
    uptime_str = f"{h}h {m}m {s}s"

    connected_devs = sum(1 for c in connections.values() if c.get("connected"))

    # ── Header panel ─────────────────────────────────────────────────────────
    header_lines = [
        f"[label]Version   :[/label] [value]{sys_version.get('version', '—')}[/value]"
        f"  ([value]{sys_version.get('os', '')} / {sys_version.get('arch', '')}[/value])",
        f"[label]Device ID :[/label] [id]{my_id}[/id]",
        f"[label]Uptime    :[/label] [number]{uptime_str}[/number]",
        f"[label]Memory    :[/label] [number]{fmt_bytes(alloc)}[/number]"
        f"  [label](sys: {fmt_bytes(sys_mb)})[/label]",
        f"[label]Folders   :[/label] [number]{len(folders)}[/number]"
        f"  [label]Devices:[/label] [number]{len(devices)}[/number]"
        f"  [label]Connected:[/label] [number]{connected_devs}[/number]",
    ]
    console.print(Panel(
        "\n".join(header_lines),
        title="[title]⚡ Syncthing Status[/title]",
        border_style="cyan",
    ))

    # ── Folders summary ───────────────────────────────────────────────────────
    ftable = Table(
        title="[heading]Folders[/heading]",
        box=box.SIMPLE_HEAD,
        header_style="heading",
        border_style="dim",
        expand=True,
    )
    ftable.add_column("ID",     style="id",   no_wrap=True)
    ftable.add_column("Label",  style="value")
    ftable.add_column("State",  no_wrap=True)
    ftable.add_column("Size",   style="number", justify="right")

    for folder in folders:
        fid    = folder["id"]
        label  = folder.get("label") or fid
        paused = folder.get("paused", False)
        try:
            st = client.folder_status(fid)
            state = st.get("state", "unknown")
            size  = fmt_bytes(st.get("localBytes", 0))
        except Exception:
            state, size = "unknown", "—"

        ftable.add_row(fid, label, folder_state_style(state, paused), size)

    console.print(ftable)

    # ── Devices summary ───────────────────────────────────────────────────────
    dtable = Table(
        title="[heading]Devices[/heading]",
        box=box.SIMPLE_HEAD,
        header_style="heading",
        border_style="dim",
        expand=True,
    )
    dtable.add_column("ID",    style="id",   no_wrap=True)
    dtable.add_column("Name",  style="value")
    dtable.add_column("State", no_wrap=True)
    dtable.add_column("Traffic", style="number", justify="right")

    for dev in devices:
        did    = dev["deviceID"]
        name   = dev.get("name") or did[:7] + "…"
        paused = dev.get("paused", False)
        conn   = connections.get(did, {})
        connected = conn.get("connected", False)
        traffic   = (
            f"↓{fmt_bytes(conn.get('inBytesTotal',0))} ↑{fmt_bytes(conn.get('outBytesTotal',0))}"
            if connected else "—"
        )
        dtable.add_row(did[:7] + "…", name, device_state_style(connected, paused), traffic)

    console.print(dtable)

    # ── Pending ───────────────────────────────────────────────────────────────
    try:
        pend_devs    = client.pending_devices()
        pend_folders = client.pending_folders()

        if pend_devs:
            console.print(f"\n[warn]⚠  {len(pend_devs)} pending device(s) want to connect — run [bold]stcli pending[/bold] to review.[/warn]")
        if pend_folders:
            console.print(f"[warn]⚠  {len(pend_folders)} pending folder(s) are being offered — run [bold]stcli pending[/bold] to review.[/warn]")
    except Exception:
        pass
