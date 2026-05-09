"""
Auto-detect Syncthing connection settings from the local config.xml,
environment variables, or an explicit ~/.stcli.json profile file.
"""

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


PROFILE_PATH = Path.home() / ".stcli.json"

SYNCTHING_CONFIG_CANDIDATES = [
    Path.home() / ".config" / "syncthing" / "config.xml",
    Path.home() / ".local" / "state" / "syncthing" / "config.xml",
    Path("/var/syncthing/config.xml"),
]


@dataclass
class ConnectionProfile:
    host: str = "127.0.0.1"
    port: int = 8384
    api_key: str = ""
    tls: bool = False
    verify_tls: bool = True
    name: str = "default"

    @property
    def base_url(self) -> str:
        scheme = "https" if self.tls else "http"
        return f"{scheme}://{self.host}:{self.port}"

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "api_key": self.api_key,
            "tls": self.tls,
            "verify_tls": self.verify_tls,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ConnectionProfile":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def _parse_syncthing_config(path: Path) -> Optional[ConnectionProfile]:
    """Parse Syncthing's config.xml and extract GUI settings."""
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        gui = root.find("gui")
        if gui is None:
            return None

        address = gui.findtext("address", "127.0.0.1:8384")
        api_key = gui.findtext("apikey", "")
        tls = gui.get("tls", "false").lower() == "true"

        if ":" in address:
            host, port_str = address.rsplit(":", 1)
            port = int(port_str)
        else:
            host, port = address, 8384

        # Syncthing binds 0.0.0.0 — use localhost for CLI
        if host in ("0.0.0.0", "::"):
            host = "127.0.0.1"

        return ConnectionProfile(host=host, port=port, api_key=api_key, tls=tls)
    except Exception:
        return None


def detect_profile() -> Optional[ConnectionProfile]:
    """Try every known source to build a connection profile."""
    # 1. Environment variables (highest priority)
    env_key = os.environ.get("SYNCTHING_API_KEY", "")
    if env_key:
        host = os.environ.get("SYNCTHING_HOST", "127.0.0.1")
        port = int(os.environ.get("SYNCTHING_PORT", "8384"))
        tls  = os.environ.get("SYNCTHING_TLS", "false").lower() == "true"
        return ConnectionProfile(host=host, port=port, api_key=env_key, tls=tls)

    # 2. Auto-detect from Syncthing config.xml
    for candidate in SYNCTHING_CONFIG_CANDIDATES:
        if candidate.exists():
            profile = _parse_syncthing_config(candidate)
            if profile:
                return profile

    return None


# ── Saved profiles ────────────────────────────────────────────────────────────

def load_profiles() -> dict[str, ConnectionProfile]:
    if not PROFILE_PATH.exists():
        return {}
    try:
        data = json.loads(PROFILE_PATH.read_text())
        return {name: ConnectionProfile.from_dict(d) for name, d in data.items()}
    except Exception:
        return {}


def save_profile(profile: ConnectionProfile) -> None:
    profiles = load_profiles()
    profiles[profile.name] = profile
    PROFILE_PATH.write_text(
        json.dumps({n: p.to_dict() for n, p in profiles.items()}, indent=2)
    )


def delete_profile(name: str) -> bool:
    profiles = load_profiles()
    if name not in profiles:
        return False
    del profiles[name]
    PROFILE_PATH.write_text(
        json.dumps({n: p.to_dict() for n, p in profiles.items()}, indent=2)
    )
    return True


def get_profile(name: str = "default") -> Optional[ConnectionProfile]:
    profiles = load_profiles()
    return profiles.get(name)
