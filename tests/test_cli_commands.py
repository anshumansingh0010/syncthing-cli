import json
import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from stcli.cli import cli
from stcli.config import ConnectionProfile


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.system_status.return_value = {
        "myID": "LOCAL-DEVICE-ID-12345",
        "uptime": 7200,
        "alloc": 10485760,
        "sys": 20971520,
        "goroutines": 45,
        "cpuPercent": 1.5,
        "discoveryEnabled": True,
        "relaysEnabled": True,
    }
    client.system_version.return_value = {
        "version": "v1.27.0",
        "os": "linux",
        "arch": "amd64",
    }
    client.system_connections.return_value = {
        "connections": {
            "DEV1-ABCDEFG": {"connected": True, "address": "192.168.1.10:22000", "inBytesTotal": 1000, "outBytesTotal": 2000}
        }
    }
    client.folders.return_value = [
        {"id": "folder-1", "label": "Documents", "path": "/home/user/Documents", "type": "sendreceive", "paused": False, "devices": [{"deviceID": "LOCAL-DEVICE-ID-12345"}]},
    ]
    client.devices.return_value = [
        {"deviceID": "DEV1-ABCDEFG-1234567-8901234", "name": "Laptop", "paused": False, "addresses": ["dynamic"]},
    ]
    client.folder_status.return_value = {
        "state": "idle",
        "localFiles": 100,
        "localDirectories": 10,
        "localBytes": 5000000,
        "globalFiles": 100,
        "globalDirectories": 10,
        "globalBytes": 5000000,
        "needFiles": 0,
        "needBytes": 0,
    }
    client.folder_completion.return_value = {"completion": 100.0}
    client.folder_errors.return_value = {"errors": []}
    client.stats_devices.return_value = {"DEV1-ABCDEFG-1234567-8901234": {"lastSeen": "2026-08-08T08:00:00Z"}}
    client.stats_folders.return_value = {}
    client.pending_devices.return_value = {}
    client.pending_folders.return_value = {}
    client.system_logs.return_value = {"messages": [{"when": "2026-08-08T08:00:00Z", "message": "Started Syncthing"}]}
    client.system_debug.return_value = {"enabled": ["db"], "facilities": {"db": "Database debugging"}}
    client.events.return_value = [{"id": 1, "time": "2026-08-08T08:00:00Z", "type": "StateChanged", "data": {}}]
    client.get_folder.return_value = {"id": "folder-1", "label": "Documents", "path": "/home/user/Documents", "devices": []}
    client.get_device.return_value = {"deviceID": "DEV1-ABCDEFG-1234567-8901234", "name": "Laptop", "addresses": ["dynamic"]}
    return client


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.1.0" in result.output


def test_status_command(mock_client):
    runner = CliRunner()
    with patch("stcli.cli._build_client", return_value=mock_client):
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "Syncthing Status" in result.output
        assert "Documents" in result.output


def test_status_command_json(mock_client):
    runner = CliRunner()
    with patch("stcli.cli._build_client", return_value=mock_client):
        result = runner.invoke(cli, ["--json", "status"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["system"]["myID"] == "LOCAL-DEVICE-ID-12345"


def test_folders_list(mock_client):
    runner = CliRunner()
    with patch("stcli.cli._build_client", return_value=mock_client):
        result = runner.invoke(cli, ["folders", "list"])
        assert result.exit_code == 0
        assert "folder-1" in result.output
        assert "Documents" in result.output


def test_folders_info(mock_client):
    runner = CliRunner()
    with patch("stcli.cli._build_client", return_value=mock_client):
        result = runner.invoke(cli, ["folders", "info", "Documents"])
        assert result.exit_code == 0
        assert "folder-1" in result.output


def test_folders_pause_and_resume(mock_client):
    runner = CliRunner()
    with patch("stcli.cli._build_client", return_value=mock_client):
        res1 = runner.invoke(cli, ["folders", "pause", "folder-1"])
        assert res1.exit_code == 0
        mock_client.pause_folder.assert_called_with("folder-1")

        res2 = runner.invoke(cli, ["folders", "resume", "folder-1"])
        assert res2.exit_code == 0
        mock_client.resume_folder.assert_called_with("folder-1")


def test_folders_rescan_override_revert_ignore_edit(mock_client):
    runner = CliRunner()
    with patch("stcli.cli._build_client", return_value=mock_client):
        r1 = runner.invoke(cli, ["folders", "rescan", "folder-1"])
        assert r1.exit_code == 0

        r2 = runner.invoke(cli, ["folders", "override", "folder-1"])
        assert r2.exit_code == 0

        r3 = runner.invoke(cli, ["folders", "revert", "folder-1"])
        assert r3.exit_code == 0

        r4 = runner.invoke(cli, ["folders", "ignore", "folder-1"])
        assert r4.exit_code == 0

        r5 = runner.invoke(cli, ["folders", "edit", "folder-1", "--label", "New Label"])
        assert r5.exit_code == 0
        mock_client.update_folder.assert_called()


def test_devices_list_and_info(mock_client):
    runner = CliRunner()
    with patch("stcli.cli._build_client", return_value=mock_client):
        res1 = runner.invoke(cli, ["devices", "list"])
        assert res1.exit_code == 0
        assert "Laptop" in res1.output

        res2 = runner.invoke(cli, ["devices", "info", "Laptop"])
        assert res2.exit_code == 0
        assert "DEV1-ABCDEFG" in res2.output


def test_devices_edit_and_ping(mock_client):
    runner = CliRunner()
    with patch("stcli.cli._build_client", return_value=mock_client):
        res1 = runner.invoke(cli, ["devices", "ping", "Laptop"])
        assert res1.exit_code == 0

        res2 = runner.invoke(cli, ["devices", "edit", "Laptop", "--name", "Laptop Pro"])
        assert res2.exit_code == 0
        mock_client.update_device.assert_called()


def test_system_commands(mock_client):
    runner = CliRunner()
    with patch("stcli.cli._build_client", return_value=mock_client):
        res1 = runner.invoke(cli, ["system", "info"])
        assert res1.exit_code == 0
        assert "v1.27.0" in res1.output

        res2 = runner.invoke(cli, ["system", "logs", "-n", "5"])
        assert res2.exit_code == 0
        assert "Started Syncthing" in res2.output

        res3 = runner.invoke(cli, ["system", "debug"])
        assert res3.exit_code == 0
        assert "Active facilities" in res3.output


def test_pending_list(mock_client):
    runner = CliRunner()
    with patch("stcli.cli._build_client", return_value=mock_client):
        res = runner.invoke(cli, ["pending", "list"])
        assert res.exit_code == 0
        assert "No pending devices" in res.output


def test_connect_list_and_show(tmp_path, monkeypatch):
    profile_file = tmp_path / ".stcli.json"
    monkeypatch.setattr("stcli.config.PROFILE_PATH", profile_file)

    runner = CliRunner()
    p = ConnectionProfile(name="testprof", host="127.0.0.1", port=8384, api_key="KEY123")
    from stcli.config import save_profile
    save_profile(p)

    res1 = runner.invoke(cli, ["connect", "list"])
    assert res1.exit_code == 0
    assert "testprof" in res1.output

    res2 = runner.invoke(cli, ["connect", "show", "testprof"])
    assert res2.exit_code == 0
    assert "testprof" in res2.output
