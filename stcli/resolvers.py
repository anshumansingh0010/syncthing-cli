"""
Identifier resolution helpers for Syncthing devices and folders.
Supports exact match, prefix match, and label/name match.
"""

from stcli.output import console
from stcli.api import SyncthingClient


def resolve_device(client: SyncthingClient, identifier: str) -> dict:
    """Resolve a device identifier (full ID, prefix, or name) to a device dictionary."""
    devices = client.devices()
    if not devices:
        console.print(f"[error]✗ No configured devices found.[/error]")
        raise SystemExit(1)

    ident_lower = identifier.strip().lower()

    # 1. Exact ID match
    for dev in devices:
        if dev["deviceID"].lower() == ident_lower:
            return dev

    # 2. Exact Name match (case-insensitive)
    name_matches = [d for d in devices if (d.get("name") or "").lower() == ident_lower]
    if len(name_matches) == 1:
        return name_matches[0]

    # 3. ID Prefix match
    prefix_matches = [d for d in devices if d["deviceID"].lower().startswith(ident_lower)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    # 4. Name substring match
    sub_matches = [d for d in devices if ident_lower in (d.get("name") or "").lower()]
    if len(sub_matches) == 1:
        return sub_matches[0]

    # Handle multiple or zero matches
    candidates = prefix_matches or name_matches or sub_matches
    if len(candidates) > 1:
        match_info = ", ".join(f"'{d.get('name') or d['deviceID'][:7]}' ({d['deviceID'][:7]}…)" for d in candidates)
        console.print(f"[warn]Ambiguous device identifier '{identifier}' matches {len(candidates)} devices: {match_info}[/warn]")
        raise SystemExit(1)

    console.print(f"[error]✗ Device '[id]{identifier}[/id]' not found.[/error]")
    raise SystemExit(1)


def resolve_folder(client: SyncthingClient, identifier: str) -> dict:
    """Resolve a folder identifier (full ID, prefix, or label) to a folder dictionary."""
    folders = client.folders()
    if not folders:
        console.print(f"[error]✗ No configured folders found.[/error]")
        raise SystemExit(1)

    ident_lower = identifier.strip().lower()

    # 1. Exact ID match
    for folder in folders:
        if folder["id"].lower() == ident_lower:
            return folder

    # 2. Exact Label match (case-insensitive)
    label_matches = [f for f in folders if (f.get("label") or "").lower() == ident_lower]
    if len(label_matches) == 1:
        return label_matches[0]

    # 3. ID Prefix match
    prefix_matches = [f for f in folders if f["id"].lower().startswith(ident_lower)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    # 4. Label substring match
    sub_matches = [f for f in folders if ident_lower in (f.get("label") or "").lower()]
    if len(sub_matches) == 1:
        return sub_matches[0]

    # Handle multiple or zero matches
    candidates = prefix_matches or label_matches or sub_matches
    if len(candidates) > 1:
        match_info = ", ".join(f"'{f.get('label') or f['id']}' ({f['id']})" for f in candidates)
        console.print(f"[warn]Ambiguous folder identifier '{identifier}' matches {len(candidates)} folders: {match_info}[/warn]")
        raise SystemExit(1)

    console.print(f"[error]✗ Folder '[id]{identifier}[/id]' not found.[/error]")
    raise SystemExit(1)
