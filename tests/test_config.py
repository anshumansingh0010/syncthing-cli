import os
import json
import pytest
from pathlib import Path
from stcli.config import (
    ConnectionProfile, detect_profile, save_profile, load_profiles,
    delete_profile, get_profile, set_default_profile, _parse_syncthing_config
)


def test_connection_profile_dataclass():
    p = ConnectionProfile(host="10.0.0.1", port=9000, api_key="secret", tls=True, name="test")
    assert p.base_url == "https://10.0.0.1:9000"
    d = p.to_dict()
    assert d["host"] == "10.0.0.1"
    assert d["port"] == 9000
    assert d["api_key"] == "secret"
    assert d["tls"] is True

    p2 = ConnectionProfile.from_dict(d)
    assert p2.host == p.host
    assert p2.base_url == p.base_url


def test_parse_syncthing_config(tmp_path):
    config_xml = tmp_path / "config.xml"
    config_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<configuration version="37">
    <gui enabled="true" tls="true">
        <address>127.0.0.1:8384</address>
        <apikey>MY_XML_API_KEY</apikey>
    </gui>
</configuration>
""")
    profile = _parse_syncthing_config(config_xml)
    assert profile is not None
    assert profile.host == "127.0.0.1"
    assert profile.port == 8384
    assert profile.api_key == "MY_XML_API_KEY"
    assert profile.tls is True


def test_detect_profile_env_var(monkeypatch):
    monkeypatch.setenv("SYNCTHING_API_KEY", "ENV_KEY_123")
    monkeypatch.setenv("SYNCTHING_HOST", "192.168.1.100")
    monkeypatch.setenv("SYNCTHING_PORT", "9999")
    monkeypatch.setenv("SYNCTHING_TLS", "true")

    profile = detect_profile()
    assert profile is not None
    assert profile.api_key == "ENV_KEY_123"
    assert profile.host == "192.168.1.100"
    assert profile.port == 9999
    assert profile.tls is True


def test_profile_persistence(tmp_path, monkeypatch):
    profile_file = tmp_path / ".stcli.json"
    monkeypatch.setattr("stcli.config.PROFILE_PATH", profile_file)

    assert load_profiles() == {}

    p1 = ConnectionProfile(name="home", host="1.1.1.1", api_key="k1")
    save_profile(p1)

    loaded = load_profiles()
    assert "home" in loaded
    assert loaded["home"].api_key == "k1"

    assert get_profile("home").host == "1.1.1.1"

    assert set_default_profile("home") is True
    assert get_profile("default").api_key == "k1"

    assert delete_profile("home") is True
    assert get_profile("home") is None
    assert delete_profile("nonexistent") is False
