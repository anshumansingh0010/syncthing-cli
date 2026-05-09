"""stcli – main Click application."""

import click
from rich.panel import Panel

from stcli.output import console
from stcli.config import detect_profile, get_profile
from stcli.api import SyncthingClient, SyncthingError
from stcli.commands.status  import status_cmd
from stcli.commands.folders import folders_group
from stcli.commands.devices import devices_group
from stcli.commands.connect import connect_group
from stcli.commands.pending import pending_cmd


# ── Context builder ───────────────────────────────────────────────────────────

def _build_client(profile_name: str, host: str, port: int, api_key: str, tls: bool) -> SyncthingClient:
    """Resolve connection: explicit flags > named profile > auto-detect."""
    if api_key:
        from stcli.config import ConnectionProfile
        profile = ConnectionProfile(host=host, port=port, api_key=api_key, tls=tls)
    elif profile_name != "default" or not api_key:
        profile = get_profile(profile_name)
        if profile is None:
            profile = detect_profile()
        if profile is None:
            console.print(
                "[error]✗  Could not connect to Syncthing.[/error]\n"
                "[muted]Run [bold]stcli connect auto[/bold] to detect automatically,\n"
                "or [bold]stcli connect add --api-key <KEY>[/bold] to configure manually.[/muted]"
            )
            raise SystemExit(1)
        # Override individual fields if provided
        if host != "127.0.0.1":
            profile.host = host
        if port != 8384:
            profile.port = port
    else:
        from stcli.config import ConnectionProfile
        profile = ConnectionProfile(host=host, port=port, api_key=api_key, tls=tls)

    return SyncthingClient(profile)


# ── Root command ──────────────────────────────────────────────────────────────

@click.group()
@click.version_option("1.0.0", prog_name="stcli")
@click.option("--profile", "profile_name", default="default",
              envvar="STCLI_PROFILE", show_default=True,
              help="Named connection profile to use.")
@click.option("--host",    default="127.0.0.1", envvar="SYNCTHING_HOST",
              help="Syncthing GUI host.")
@click.option("--port",    default=8384, type=int, envvar="SYNCTHING_PORT",
              help="Syncthing GUI port.")
@click.option("--api-key", default="", envvar="SYNCTHING_API_KEY",
              help="Syncthing API key.")
@click.option("--tls/--no-tls", default=False,
              help="Use HTTPS for connection.")
@click.pass_context
def cli(ctx, profile_name, host, port, api_key, tls):
    """
    \b
    ╔══════════════════════════════╗
    ║   stcli  –  Syncthing CLI    ║
    ╚══════════════════════════════╝

    Manage your Syncthing instance from the terminal.
    Auto-detects Syncthing from your local config on first run.

    Examples:

    \b
      stcli status
      stcli folders list
      stcli folders info my-folder-id
      stcli devices list
      stcli connect auto --save home
      stcli --profile home status
    """
    ctx.ensure_object(dict)

    # Commands that don't need a live client
    if ctx.invoked_subcommand in ("connect", None):
        return

    try:
        client = _build_client(profile_name, host, port, api_key, tls)
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[error]Failed to initialise client: {e}[/error]")
        raise SystemExit(1)

    ctx.obj = client


# ── Register sub-commands ─────────────────────────────────────────────────────

cli.add_command(status_cmd)
cli.add_command(folders_group)
cli.add_command(devices_group)
cli.add_command(connect_group)
cli.add_command(pending_cmd)


if __name__ == "__main__":
    cli()
