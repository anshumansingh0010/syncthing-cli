"""stcli – connect / profile management commands."""

import click
from rich.table import Table
from rich.panel import Panel
from rich import box

from stcli.config import (
    ConnectionProfile, detect_profile,
    save_profile, load_profiles, delete_profile,
)
from stcli.api import SyncthingClient, SyncthingError
from stcli.output import console


@click.group("connect")
def connect_group():
    """Manage connection profiles for Syncthing instances."""


@connect_group.command("auto")
@click.option("--save", "save_name", default=None, help="Save as named profile.")
def connect_auto(save_name):
    """Auto-detect Syncthing from local config and test the connection."""
    profile = detect_profile()
    if not profile:
        console.print("[error]Could not auto-detect Syncthing. Is it running?[/error]")
        console.print("[muted]Hint: Set SYNCTHING_API_KEY env var, or install Syncthing.[/muted]")
        raise SystemExit(1)

    _test_and_print(profile)
    if save_name:
        profile.name = save_name
        save_profile(profile)
        console.print(f"[good]✓ Saved as profile '[value]{save_name}[/value]'[/good]")


@connect_group.command("add")
@click.option("--name",    default="default",   show_default=True)
@click.option("--host",    default="127.0.0.1", show_default=True)
@click.option("--port",    default=8384,        show_default=True, type=int)
@click.option("--api-key", required=True, help="Syncthing API key")
@click.option("--tls/--no-tls", default=False,  show_default=True)
@click.option("--no-verify", is_flag=True, help="Skip TLS certificate verification")
def connect_add(name, host, port, api_key, tls, no_verify):
    """Add or update a named connection profile."""
    profile = ConnectionProfile(
        name=name, host=host, port=port,
        api_key=api_key, tls=tls, verify_tls=not no_verify,
    )
    _test_and_print(profile)
    save_profile(profile)
    console.print(f"[good]✓ Profile '[value]{name}[/value]' saved.[/good]")


@connect_group.command("list")
def connect_list():
    """Show all saved connection profiles."""
    profiles = load_profiles()
    if not profiles:
        console.print("[muted]No saved profiles. Run [bold]stcli connect add[/bold] or [bold]stcli connect auto[/bold].[/muted]")
        return

    table = Table(title="[title]Saved Profiles[/title]", box=box.ROUNDED, border_style="dim white")
    table.add_column("Name",    style="value")
    table.add_column("Host",    style="path")
    table.add_column("Port",    style="number", justify="right")
    table.add_column("TLS",     style="muted")
    table.add_column("API Key", style="muted")

    for name, p in profiles.items():
        table.add_row(
            name, p.host, str(p.port),
            "yes" if p.tls else "no",
            p.api_key[:8] + "…" if p.api_key else "—",
        )
    console.print(table)


@connect_group.command("remove")
@click.argument("name")
def connect_remove(name):
    """Delete a saved connection profile."""
    if delete_profile(name):
        console.print(f"[good]✓ Profile '[value]{name}[/value]' removed.[/good]")
    else:
        console.print(f"[error]Profile '[value]{name}[/value]' not found.[/error]")


@connect_group.command("test")
@click.option("--profile", "profile_name", default="default", show_default=True)
@click.pass_context
def connect_test(ctx, profile_name):
    """Test connectivity for a saved profile."""
    from stcli.config import get_profile
    profile = get_profile(profile_name)
    if not profile:
        console.print(f"[error]Profile '[value]{profile_name}[/value]' not found.[/error]")
        raise SystemExit(1)
    _test_and_print(profile)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _test_and_print(profile: ConnectionProfile) -> None:
    client = SyncthingClient(profile)
    console.print(f"[info]→  Connecting to [path]{profile.base_url}[/path]…[/info]")

    if not client.ping():
        console.print("[error]✗  Syncthing is not reachable at that address.[/error]")
        raise SystemExit(1)

    try:
        v = client.system_version()
        s = client.system_status()
        console.print(Panel(
            f"[good]✓  Connected[/good]\n\n"
            f"[label]Version  :[/label] [value]{v.get('version', '—')}[/value]\n"
            f"[label]Device ID:[/label] [id]{s.get('myID', '—')}[/id]\n"
            f"[label]Platform :[/label] [value]{v.get('os', '')} / {v.get('arch', '')}[/value]",
            title="[title]Connection OK[/title]",
            border_style="green",
            expand=False,
        ))
    except SyncthingError as e:
        console.print(f"[error]✗  API error: {e}[/error]")
        raise SystemExit(1)
