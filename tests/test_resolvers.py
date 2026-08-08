import pytest
from unittest.mock import MagicMock
from stcli.resolvers import resolve_device, resolve_folder


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.devices.return_value = [
        {"deviceID": "J4U5N7X-ABCDEF1-2345678-AAAAAAA", "name": "Laptop"},
        {"deviceID": "K9X8Z12-WXYZ987-6543210-BBBBBBB", "name": "Work Server"},
        {"deviceID": "M1M2M3M-0000000-1111111-CCCCCCC", "name": "Phone"},
    ]
    client.folders.return_value = [
        {"id": "docs-folder-1", "label": "My Documents"},
        {"id": "photos-folder-2", "label": "Vacation Photos"},
        {"id": "music", "label": "Music Collection"},
    ]
    return client


def test_resolve_device_exact_id(mock_client):
    dev = resolve_device(mock_client, "J4U5N7X-ABCDEF1-2345678-AAAAAAA")
    assert dev["name"] == "Laptop"


def test_resolve_device_prefix_id(mock_client):
    dev = resolve_device(mock_client, "J4U5N7X")
    assert dev["name"] == "Laptop"


def test_resolve_device_name(mock_client):
    dev = resolve_device(mock_client, "laptop")
    assert dev["deviceID"].startswith("J4U5N7X")


def test_resolve_device_not_found(mock_client):
    with pytest.raises(SystemExit):
        resolve_device(mock_client, "nonexistent-device")


def test_resolve_folder_exact_id(mock_client):
    folder = resolve_folder(mock_client, "docs-folder-1")
    assert folder["label"] == "My Documents"


def test_resolve_folder_label(mock_client):
    folder = resolve_folder(mock_client, "my documents")
    assert folder["id"] == "docs-folder-1"


def test_resolve_folder_prefix(mock_client):
    folder = resolve_folder(mock_client, "photos")
    assert folder["id"] == "photos-folder-2"


def test_resolve_folder_not_found(mock_client):
    with pytest.raises(SystemExit):
        resolve_folder(mock_client, "unknown-folder")
