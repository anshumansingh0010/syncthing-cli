"""stcli – watch dashboard & events commands."""

import time
import click
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.layout import Layout

from stcli.output import console, fmt_bytes, folder_state_style, device_state_style, print_json
from stcli.api import SyncthingError


@click.command("watch")
@click.option("--interval", "-i", default=2.0, type=float, show_default=True, help="Refresh interval in seconds.")
@click.pass_obj
def watch_cmd(client, interval):
    """Live-updating dashboard monitoring your Syncthing node.

    Press Ctrl+C to exit.
    """
    def generate_dashboard() -> Panel:
        try:
            sys_status  = client.system_status()
            sys_version = client.system_version()
            folders     = client.folders()
            devices     = client.devices()
            connections = client.system_connections().get("connections", {})
        except Exception as e:
            return Panel(f"[error]Error polling Syncthing: {e}[/error]", title="[error]Connection Error[/error]")

        uptime = sys_status.get("uptime", 0)
        h, rem = divmod(uptime, 3600)
        m, s   = divmod(rem, 60)

        # Header string
        hdr = (
            f"[label]Version:[/label] [value]{sys_version.get('version', '—')}[/value] | "
            f"[label]Uptime:[/label] [number]{h}h {m}m {s}s[/number] | "
            f"[label]RAM:[/label] [number]{fmt_bytes(sys_status.get('alloc', 0))}[/number] | "
            f"[label]Folders:[/label] [number]{len(folders)}[/number] | "
            f"[label]Devices:[/label] [number]{len(devices)}[/number]"
        )

        # Folders Table
        ftable = Table(box=box.SIMPLE_HEAD, header_style="heading", expand=True)
        ftable.add_column("Folder", style="value")
        ftable.add_column("State")
        ftable.add_column("Size", style="number", justify="right")

        for f in folders:
            fid = f["id"]
            lbl = f.get("label") or fid
            paused = f.get("paused", False)
            try:
                st = client.folder_status(fid)
                state = st.get("state", "unknown")
                size = fmt_bytes(st.get("localBytes", 0))
            except Exception:
                state, size = "unknown", "—"
            ftable.add_row(lbl[:25], folder_state_style(state, paused), size)

        # Devices Table
        dtable = Table(box=box.SIMPLE_HEAD, header_style="heading", expand=True)
        dtable.add_column("Device", style="value")
        dtable.add_column("State")
        dtable.add_column("Traffic", style="number", justify="right")

        for d in devices:
            did = d["deviceID"]
            name = d.get("name") or did[:7] + "…"
            paused = d.get("paused", False)
            conn = connections.get(did, {})
            connected = conn.get("connected", False)
            traffic = (
                f"↓{fmt_bytes(conn.get('inBytesTotal',0))} ↑{fmt_bytes(conn.get('outBytesTotal',0))}"
                if connected else "—"
            )
            dtable.add_row(name[:20], device_state_style(connected, paused), traffic)

        layout = Layout()
        layout.split_column(
            Layout(Panel(hdr, border_style="cyan", title="[title]⚡ Syncthing Live Watch[/title]")),
            Layout(ftable, name="folders"),
            Layout(dtable, name="devices"),
        )
        return layout

    console.print("[info]Starting live dashboard (press Ctrl+C to stop)…[/info]")
    try:
        with Live(generate_dashboard(), refresh_per_second=1.0/interval, console=console) as live:
            while True:
                time.sleep(interval)
                live.update(generate_dashboard())
    except KeyboardInterrupt:
        console.print("\n[muted]Dashboard stopped.[/muted]")


@click.command("events")
@click.option("--limit", "-n", default=10, type=int, show_default=True, help="Number of events to display.")
@click.option("--since", default=0, type=int, show_default=True, help="Event ID offset to start from.")
@click.option("--follow", "-f", is_flag=True, help="Continuously listen and print new events.")
@click.pass_context
def events_cmd(ctx, limit, since, follow):
    """Stream or display real-time events from Syncthing."""
    client = ctx.obj
    json_out = ctx.find_root().params.get("json_output", False)

    if follow:
        console.print(f"[info]Listening for Syncthing events (since event ID {since})… Press Ctrl+C to stop.[/info]")
        last_id = since
        try:
            while True:
                evs = client.events(since=last_id, limit=limit)
                for ev in evs:
                    last_id = max(last_id, ev.get("id", last_id))
                    if json_out:
                        print_json(ev)
                    else:
                        etype = ev.get("type", "Event")
                        t = ev.get("time", "")[:19].replace("T", " ")
                        data_summary = str(ev.get("data", {}))
                        if len(data_summary) > 80:
                            data_summary = data_summary[:77] + "..."
                        console.print(f"[muted]{t}[/muted] [id]#{ev.get('id')}[/id] [info]{etype}[/info]: {data_summary}")
                time.sleep(1.0)
        except KeyboardInterrupt:
            console.print("\n[muted]Event stream stopped.[/muted]")
        return

    try:
        evs = client.events(since=since, limit=limit)
    except SyncthingError as e:
        console.print(f"[error]✗ Failed to fetch events: {e}[/error]")
        raise SystemExit(1)

    if json_out:
        print_json(evs)
        return

    table = Table(title=f"[title]Syncthing Events (Limit: {limit})[/title]", box=box.SIMPLE)
    table.add_column("ID", style="id", no_wrap=True)
    table.add_column("Time", style="muted", no_wrap=True)
    table.add_column("Type", style="info")
    table.add_column("Summary", style="value")

    for ev in evs:
        eid = str(ev.get("id", ""))
        t = ev.get("time", "")[:19].replace("T", " ")
        etype = ev.get("type", "")
        summary = str(ev.get("data", {}))
        table.add_row(eid, t, etype, summary[:60])

    console.print(table)
