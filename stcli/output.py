"""
Shared Rich helpers — console, theme, and utility renderers.
"""

from typing import Any

from rich.console import Console
from rich.theme import Theme

THEME = Theme({
    "title":    "bold cyan",
    "heading":  "bold white",
    "label":    "dim white",
    "value":    "white",
    "good":     "bold green",
    "warn":     "bold yellow",
    "error":    "bold red",
    "info":     "bold blue",
    "muted":    "dim",
    "id":       "bright_magenta",
    "path":     "bright_cyan",
    "number":   "bold bright_yellow",
    "paused":   "bold yellow",
    "syncing":  "bold cyan",
    "synced":   "bold green",
    "unknown":  "dim white",
})

console = Console(theme=THEME)


def fmt_bytes(n: int | float | None) -> str:
    """Human-readable byte count."""
    if n is None:
        n = 0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            if unit == "B":
                return f"{int(n)} B"
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def fmt_pct(completed: float | None) -> str:
    if completed is None:
        completed = 0.0
    pct = round(completed, 1)
    if pct >= 100:
        return "[synced]100%[/synced]"
    if pct >= 50:
        return f"[syncing]{pct}%[/syncing]"
    return f"[warn]{pct}%[/warn]"


def folder_state_style(state: str | None, paused: bool) -> str:
    if paused:
        return "[paused]⏸ paused[/paused]"
    if not state:
        state = "unknown"
    mapping = {
        "idle":     "[synced]✓ synced[/synced]",
        "syncing":  "[syncing]⟳ syncing[/syncing]",
        "scanning": "[info]⟳ scanning[/info]",
        "error":    "[error]✗ error[/error]",
        "unknown":  "[unknown]? unknown[/unknown]",
        "sync-preparing": "[syncing]⟳ preparing[/syncing]",
        "waiting-to-scan": "[muted]⏳ waiting[/muted]",
        "waiting-to-sync": "[muted]⏳ waiting[/muted]",
        "clean-waiting-to-scan": "[muted]⏳ waiting[/muted]",
    }
    return mapping.get(state, f"[unknown]{state}[/unknown]")


def device_state_style(connected: bool, paused: bool) -> str:
    if paused:
        return "[paused]⏸ paused[/paused]"
    if connected:
        return "[synced]● connected[/synced]"
    return "[muted]○ disconnected[/muted]"


def print_json(data: Any) -> None:
    """Print structured data as pretty JSON."""
    import json
    console.print_json(json.dumps(data, default=str))

