"""stcli – connect / profile management commands."""

import click
from rich.table import Table
from rich.panel import Panel
from rich import box

from stcli.config import (
    ConnectionProfile, detect_profile,
    save_profile, load_profiles, delete_profile, get_profile, set_default_profile,
)
from stcli.api import SyncthingClient, SyncthingError
from stcli.output import console, print_json


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
@click.pass_context
def connect_list(ctx):
    """Show all saved connection profiles."""
    json_out = ctx.find_root().params.get("json_output", False)
    profiles = load_profiles()

    if json_out:
        print_json({n: p.to_dict() for n, p in profiles.items()})
        return

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


@connect_group.command("show")
@click.argument("name", default="default")
@click.pass_context
def connect_show(ctx, name):
    """Show detailed settings of a profile (or auto-detected fallback)."""
    json_out = ctx.find_root().params.get("json_output", False)
    profile = get_profile(name) or detect_profile()

    if not profile:
        console.print(f"[error]Profile '[value]{name}[/value]' not found and auto-detection failed.[/error]")
        raise SystemExit(1)

    if json_out:
        print_json(profile.to_dict())
        return

    lines = [
        f"[label]Profile Name :[/label] [value]{profile.name}[/value]",
        f"[label]Base URL     :[/label] [path]{profile.base_url}[/path]",
        f"[label]Host         :[/label] [value]{profile.host}[/value]",
        f"[label]Port         :[/label] [number]{profile.port}[/number]",
        f"[label]TLS / HTTPS  :[/label] [value]{profile.tls}[/value]",
        f"[label]Verify TLS   :[/label] [value]{profile.verify_tls}[/value]",
        f"[label]API Key      :[/label] [muted]{profile.api_key[:8]}… ({len(profile.api_key)} chars)[/muted]" if profile.api_key else "[warn]No API Key[/warn]",
    ]

    console.print(Panel(
        "\n".join(lines),
        title=f"[title]🔌 Profile: {name}[/title]",
        border_style="cyan",
        expand=False,
    ))


@connect_group.command("default")
@click.argument("name")
def connect_default(name):
    """Set a profile as the default connection profile."""
    if set_default_profile(name):
        console.print(f"[good]✓ Profile '[value]{name}[/value]' is now the default profile.[/good]")
    else:
        console.print(f"[error]Profile '[value]{name}[/value]' not found.[/error]")
        raise SystemExit(1)


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
def connect_test(profile_name):
    """Test connectivity for a profile (or auto-detected if default)."""
    profile = get_profile(profile_name)
    if not profile and profile_name == "default":
        profile = detect_profile()

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
