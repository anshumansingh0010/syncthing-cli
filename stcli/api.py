"""
Thin wrapper around the Syncthing REST API.
All methods raise SyncthingError on non-2xx responses.
"""

import requests
import urllib3
from urllib.parse import quote
from typing import Any, Optional

from stcli.config import ConnectionProfile

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SyncthingError(Exception):
    pass


class SyncthingClient:
    def __init__(self, profile: ConnectionProfile):
        self.profile = profile
        self._session = requests.Session()
        self._session.headers.update({
            "X-API-Key": profile.api_key,
            "Content-Type": "application/json",
        })
        self._verify = profile.verify_tls if profile.tls else False

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _url(self, path: str) -> str:
        return f"{self.profile.base_url}/rest/{path.lstrip('/')}"

    def _get(self, path: str, **params) -> Any:
        resp = self._session.get(self._url(path), params=params, verify=self._verify, timeout=10)
        self._raise(resp)
        return resp.json()

    def _post(self, path: str, json_body: Any = None, **params) -> Any:
        resp = self._session.post(self._url(path), json=json_body, params=params,
                                  verify=self._verify, timeout=10)
        self._raise(resp)
        return resp.json() if resp.text else {}

    def _patch(self, path: str, json_body: Any = None) -> Any:
        resp = self._session.patch(self._url(path), json=json_body, verify=self._verify, timeout=10)
        self._raise(resp)
        return resp.json() if resp.text else {}

    @staticmethod
    def _raise(resp: requests.Response) -> None:
        if not resp.ok:
            try:
                msg = resp.json().get("error", resp.text)
            except Exception:
                msg = resp.text or resp.reason
            raise SyncthingError(f"HTTP {resp.status_code}: {msg}")

    # ── Health / Ping ─────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Return True if Syncthing is reachable (no auth needed)."""
        try:
            resp = self._session.get(
                f"{self.profile.base_url}/rest/noauth/health",
                verify=self._verify, timeout=5,
            )
            return resp.ok
        except Exception:
            return False

    # ── System ────────────────────────────────────────────────────────────────

    def system_status(self) -> dict:
        return self._get("system/status")

    def system_version(self) -> dict:
        return self._get("system/version")

    def system_connections(self) -> dict:
        return self._get("system/connections")

    def system_ping(self) -> dict:
        return self._get("system/ping")

    def system_restart(self) -> None:
        self._post("system/restart")

    def system_shutdown(self) -> None:
        self._post("system/shutdown")

    def system_logs(self) -> dict:
        return self._get("system/logs")

    def system_debug(self) -> dict:
        return self._get("system/debug")

    # ── Config ────────────────────────────────────────────────────────────────

    def config(self) -> dict:
        return self._get("config")

    def folders(self) -> list[dict]:
        return self._get("config/folders")

    def devices(self) -> list[dict]:
        return self._get("config/devices")

    # ── Database / Folder status ──────────────────────────────────────────────

    def folder_status(self, folder_id: str) -> dict:
        return self._get("db/status", folder=folder_id)

    def folder_completion(self, folder_id: str, device_id: Optional[str] = None) -> dict:
        params: dict = {"folder": folder_id}
        if device_id:
            params["device"] = device_id
        return self._get("db/completion", **params)

    def folder_errors(self, folder_id: str) -> dict:
        return self._get("db/folder/errors", folder=folder_id)

    def db_scan(self, folder_id: Optional[str] = None, sub: Optional[str] = None) -> None:
        params = {}
        if folder_id:
            params["folder"] = folder_id
        if sub:
            params["sub"] = sub
        self._post("db/scan", **params)

    def db_override(self, folder_id: str) -> None:
        self._post("db/override", folder=folder_id)

    def db_revert(self, folder_id: str) -> None:
        self._post("db/revert", folder=folder_id)

    def db_ignores(self, folder_id: str) -> dict:
        return self._get("db/ignores", folder=folder_id)

    def update_db_ignores(self, folder_id: str, ignore_patterns: list[str]) -> dict:
        return self._post("db/ignores", json_body={"ignore": ignore_patterns}, folder=folder_id)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats_devices(self) -> dict:
        return self._get("stats/device")

    def stats_folders(self) -> dict:
        return self._get("stats/folder")

    # ── Pause / Resume ────────────────────────────────────────────────────────

    def pause_folder(self, folder_id: str) -> None:
        q_id = quote(folder_id, safe='')
        self._patch(f"config/folders/{q_id}", {"paused": True})

    def resume_folder(self, folder_id: str) -> None:
        q_id = quote(folder_id, safe='')
        self._patch(f"config/folders/{q_id}", {"paused": False})

    def pause_device(self, device_id: str) -> None:
        q_id = quote(device_id, safe='')
        self._patch(f"config/devices/{q_id}", {"paused": True})

    def resume_device(self, device_id: str) -> None:
        q_id = quote(device_id, safe='')
        self._patch(f"config/devices/{device_id}", {"paused": False})

    # ── Folder CRUD ───────────────────────────────────────────────────────────

    def add_folder(self, folder_cfg: dict) -> dict:
        """POST a new folder config. Returns the created config."""
        return self._post("config/folders", folder_cfg)

    def get_folder(self, folder_id: str) -> dict:
        """GET a single folder's full config."""
        q_id = quote(folder_id, safe='')
        return self._get(f"config/folders/{q_id}")

    def update_folder(self, folder_id: str, folder_cfg: dict) -> dict:
        """PUT (full replace) a folder's config."""
        q_id = quote(folder_id, safe='')
        resp = self._session.put(
            self._url(f"config/folders/{q_id}"),
            json=folder_cfg,
            verify=self._verify, timeout=10,
        )
        self._raise(resp)
        return resp.json() if resp.text else {}

    def remove_folder(self, folder_id: str) -> None:
        """DELETE a folder from the config."""
        q_id = quote(folder_id, safe='')
        resp = self._session.delete(
            self._url(f"config/folders/{q_id}"),
            verify=self._verify, timeout=10,
        )
        self._raise(resp)

    # ── Device CRUD ───────────────────────────────────────────────────────────

    def add_device(self, device_cfg: dict) -> dict:
        """POST a new device config. Returns the created config."""
        return self._post("config/devices", device_cfg)

    def get_device(self, device_id: str) -> dict:
        """GET a single device's full config."""
        q_id = quote(device_id, safe='')
        return self._get(f"config/devices/{q_id}")

    def update_device(self, device_id: str, device_cfg: dict) -> dict:
        """PUT (full replace) a device's config."""
        q_id = quote(device_id, safe='')
        resp = self._session.put(
            self._url(f"config/devices/{q_id}"),
            json=device_cfg,
            verify=self._verify, timeout=10,
        )
        self._raise(resp)
        return resp.json() if resp.text else {}

    def remove_device(self, device_id: str) -> None:
        """DELETE a device from the config."""
        q_id = quote(device_id, safe='')
        resp = self._session.delete(
            self._url(f"config/devices/{q_id}"),
            verify=self._verify, timeout=10,
        )
        self._raise(resp)

    # ── Cluster / Pending ─────────────────────────────────────────────────────

    def pending_devices(self) -> dict:
        return self._get("cluster/pending/devices")

    def pending_folders(self) -> dict:
        return self._get("cluster/pending/folders")

    def dismiss_pending_device(self, device_id: str) -> None:
        resp = self._session.delete(
            self._url("cluster/pending/devices"),
            params={"device": device_id},
            verify=self._verify, timeout=10,
        )
        self._raise(resp)

    def dismiss_pending_folder(self, folder_id: str, device_id: str) -> None:
        resp = self._session.delete(
            self._url("cluster/pending/folders"),
            params={"folder": folder_id, "device": device_id},
            verify=self._verify, timeout=10,
        )
        self._raise(resp)

    # ── Events (single poll) ──────────────────────────────────────────────────

    def events(self, since: int = 0, limit: int = 10) -> list[dict]:
        return self._get("events", since=since, limit=limit)
