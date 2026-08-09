"""stcli – main Click application."""

import click
import requests
from rich.panel import Panel

from stcli.output import console, print_json
from stcli.config import detect_profile, get_profile, ConnectionProfile
from stcli.api import SyncthingClient, SyncthingError
from stcli.commands.status  import status_cmd
from stcli.commands.folders import folders_group
from stcli.commands.devices import devices_group
from stcli.commands.connect import connect_group
from stcli.commands.pending import pending_cmd
from stcli.commands.system  import system_group
from stcli.commands.watch   import watch_cmd, events_cmd


class ExceptionHandlingGroup(click.Group):
    """Custom Click Group that handles connection errors and API exceptions gracefully."""

    def parse_args(self, ctx, args):
        setattr(ctx, "raw_args", list(args))
        return super().parse_args(ctx, args)

    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except (SyncthingError, requests.exceptions.RequestException) as e:
            json_out = ctx.params.get("json_output", False)
            if json_out:
                print_json({"error": str(e)})
            else:
                console.print(f"[error]✗  {e}[/error]")
                msg = str(e)
                if "Could not connect" in msg or "Connection refused" in msg or "Max retries exceeded" in msg:
                    console.print(
                        "\n[muted]Tips:\n"
                        " • Start Syncthing: [bold]stcli system start[/bold]\n"
                        " • Check status: [bold]systemctl --user status syncthing[/bold]\n"
                        " • Test connectivity: [bold]stcli connect test[/bold]\n"
                        " • Auto-detect connection: [bold]stcli connect auto[/bold][/muted]"
                    )
            raise SystemExit(1)


# ── Context builder ───────────────────────────────────────────────────────────

def _build_client(ctx: click.Context, profile_name: str, host: str, port: int, api_key: str, tls: bool) -> SyncthingClient:
    """Resolve connection: explicit flags > named profile > auto-detect."""

    # Find loaded base profile or auto-detect
    base_profile = None
    if profile_name and profile_name != "default":
        base_profile = get_profile(profile_name)

    if base_profile is None:
        base_profile = get_profile("default")

    if base_profile is None:
        base_profile = detect_profile()

    if base_profile is None:
        if api_key:
            base_profile = ConnectionProfile(host=host, port=port, api_key=api_key, tls=tls)
        else:
            console.print(
                "[error]✗  Could not connect to Syncthing.[/error]\n"
                "[muted]Run [bold]stcli connect auto[/bold] to detect automatically,\n"
                "or [bold]stcli connect add --api-key <KEY>[/bold] to configure manually.[/muted]"
            )
            raise SystemExit(1)

    # Check parameter sources for explicit overrides
    has_host_override = ctx.get_parameter_source("host") == click.core.ParameterSource.COMMANDLINE
    has_port_override = ctx.get_parameter_source("port") == click.core.ParameterSource.COMMANDLINE
    has_key_override  = ctx.get_parameter_source("api_key") == click.core.ParameterSource.COMMANDLINE or bool(api_key and not base_profile.api_key)
    has_tls_override  = ctx.get_parameter_source("tls") == click.core.ParameterSource.COMMANDLINE

    profile = ConnectionProfile(
        host=host if has_host_override else base_profile.host,
        port=port if has_port_override else base_profile.port,
        api_key=api_key if has_key_override else base_profile.api_key,
        tls=tls if has_tls_override else base_profile.tls,
        verify_tls=base_profile.verify_tls,
        name=profile_name or base_profile.name,
    )

    if not profile.api_key:
        console.print(
            "[error]✗  No API Key configured.[/error]\n"
            "[muted]Pass [bold]--api-key <KEY>[/bold] or run [bold]stcli connect auto[/bold].[/muted]"
        )
        raise SystemExit(1)

    return SyncthingClient(profile)


# ── Root command ──────────────────────────────────────────────────────────────

@click.group(cls=ExceptionHandlingGroup)
@click.version_option("1.1.2", prog_name="stcli")
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
@click.option("--json", "-j", "json_output", is_flag=True, default=False,
              help="Output raw machine-readable JSON.")
@click.pass_context
def cli(ctx, profile_name, host, port, api_key, tls, json_output):
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
      stcli system info
      stcli watch
      stcli connect auto --save home
      stcli --profile home status
    """
    ctx.ensure_object(dict)

    # Commands that don't need a live client
    if ctx.invoked_subcommand in ("connect", None):
        return

    raw_args = getattr(ctx, "raw_args", [])
    is_start_or_stop = ctx.invoked_subcommand == "system" and any(a in raw_args for a in ("start", "stop"))

    try:
        client = _build_client(ctx, profile_name, host, port, api_key, tls)
    except SystemExit:
        if is_start_or_stop:
            client = None
        else:
            raise
    except Exception as e:
        if is_start_or_stop:
            client = None
        else:
            console.print(f"[error]Failed to initialise client: {e}[/error]")
            raise SystemExit(1)

    ctx.obj = client


# ── Register sub-commands ─────────────────────────────────────────────────────

cli.add_command(status_cmd)
cli.add_command(folders_group)
cli.add_command(devices_group)
cli.add_command(connect_group)
cli.add_command(pending_cmd)
cli.add_command(system_group)
cli.add_command(watch_cmd)
cli.add_command(events_cmd)


if __name__ == "__main__":
    cli()
