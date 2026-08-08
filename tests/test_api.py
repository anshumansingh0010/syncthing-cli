import pytest
from unittest.mock import MagicMock, patch
from stcli.config import ConnectionProfile
from stcli.api import SyncthingClient, SyncthingError


@pytest.fixture
def client():
    profile = ConnectionProfile(host="127.0.0.1", port=8384, api_key="TESTKEY", name="test")
    return SyncthingClient(profile)


def test_client_headers_and_url(client):
    assert client.profile.base_url == "http://127.0.0.1:8384"
    assert client._url("system/status") == "http://127.0.0.1:8384/rest/system/status"
    assert client._url("/system/status") == "http://127.0.0.1:8384/rest/system/status"
    assert client._session.headers["X-API-Key"] == "TESTKEY"


def test_ping_success(client):
    mock_resp = MagicMock()
    mock_resp.ok = True
    with patch.object(client._session, "get", return_value=mock_resp):
        assert client.ping() is True


def test_ping_failure(client):
    with patch.object(client._session, "get", side_effect=Exception("Connection error")):
        assert client.ping() is False


def test_system_status(client):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {"myID": "DEVICE-1234", "uptime": 3600}
    with patch.object(client._session, "get", return_value=mock_resp):
        status = client.system_status()
        assert status["myID"] == "DEVICE-1234"


def test_url_quoting_in_folder_operations(client):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.text = ""

    with patch.object(client._session, "patch", return_value=mock_resp) as mock_patch:
        client.pause_folder("folder/with/slashes")
        mock_patch.assert_called_once()
        call_url = mock_patch.call_args[0][0]
        assert "folder%2Fwith%2Fslashes" in call_url


def test_url_quoting_in_device_operations(client):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.text = ""

    with patch.object(client._session, "patch", return_value=mock_resp) as mock_patch:
        client.pause_device("DEV ID WITH SPACES")
        mock_patch.assert_called_once()
        call_url = mock_patch.call_args[0][0]
        assert "DEV%20ID%20WITH%20SPACES" in call_url


def test_api_error_raising(client):
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"error": "Folder not found"}

    with patch.object(client._session, "get", return_value=mock_resp):
        with pytest.raises(SyncthingError) as exc_info:
            client.get_folder("nonexistent")
        assert "404" in str(exc_info.value)
        assert "Folder not found" in str(exc_info.value)


def test_system_logs_and_debug(client):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {"messages": [{"message": "log line 1"}]}
    with patch.object(client._session, "get", return_value=mock_resp):
        logs = client.system_logs()
        assert len(logs["messages"]) == 1

    mock_resp.json.return_value = {"enabled": ["db"], "facilities": {"db": "Database debug"}}
    with patch.object(client._session, "get", return_value=mock_resp):
        debug = client.system_debug()
        assert debug["enabled"] == ["db"]
