# tests/test_nodes_and_updater.py
import pytest
from app import create_app
from app.services.hardware_service import hardware_service
from app.services.updater_service import updater_service, parse_semver
from app.services.sync_service import sync_service


@pytest.fixture
def app():
    app = create_app('testing')
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_hardware_service_specs():
    specs = hardware_service.get_hardware_specs()
    assert "ram_total_gb" in specs
    assert "ram_avail_gb" in specs
    assert "gpu_name" in specs
    assert "summary" in specs
    assert isinstance(specs["summary"], str)
    assert len(specs["summary"]) > 0


def test_semver_parsing():
    assert parse_semver("v2.1.3") == (2, 1, 3)
    assert parse_semver("2.1.2") == (2, 1, 2)
    assert parse_semver("v2.1.3") > parse_semver("v2.1.2")
    assert parse_semver("v2.2.0") > parse_semver("v2.1.9")
    assert parse_semver("invalid") == (0, 0, 0)


def test_updater_asset_picker():
    assets = [
        {"name": "Notes-Workstation-Windows.exe", "size_bytes": 40000000},
        {"name": "notes-workstation_0.2.5_x64-setup.exe", "size_bytes": 5000000},
        {"name": "Notes-Workstation-Android-Universal-v2.1.0.apk", "size_bytes": 14000000},
        {"name": "notes-workstation_0.2.5_amd64.AppImage", "size_bytes": 80000000}
    ]
    grouped = updater_service._group_assets_by_platform(assets)
    assert len(grouped["windows"]) == 2
    assert len(grouped["android"]) == 1
    assert len(grouped["linux"]) == 1

    rec_win = updater_service._pick_recommended_asset(grouped, "windows")
    assert rec_win["name"] == "Notes-Workstation-Windows.exe"

    rec_android = updater_service._pick_recommended_asset(grouped, "android")
    assert "Universal" in rec_android["name"]

    rec_linux = updater_service._pick_recommended_asset(grouped, "linux")
    assert rec_linux["name"].endswith(".AppImage")


def test_nodes_cluster_api(client):
    res = client.get('/api/nodes/cluster')
    assert res.status_code == 200
    data = res.get_json()
    assert "local_node" in data
    assert "hardware" in data["local_node"]
    assert "services" in data["local_node"]
    assert "llamacpp" in data["local_node"]["services"]


def test_nodes_self_config_api(client):
    res = client.post('/api/nodes/self/config', json={
        "name": "Super Rig 4090",
        "llamacpp_enabled": True,
        "llamacpp_local_port": 8085
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["name"] == "Super Rig 4090"
    assert data["llamacpp"]["enabled"] is True
    assert data["llamacpp"]["local_port"] == 8085
    assert sync_service.get_node_name() == "Super Rig 4090"
    assert sync_service.get_llamacpp_local_port() == 8085


def test_nodes_peer_rename_api(client):
    res = client.post('/api/nodes/peers/node-sample-123/rename', json={
        "alias": "My Tablet"
    })
    assert res.status_code == 200
    assert sync_service.get_peer_alias("node-sample-123") == "My Tablet"


def test_nodes_select_llm_api(client):
    res = client.post('/api/nodes/select-llm', json={
        "endpoint": "http://192.168.0.99:5000/api/nodes/proxy/llm"
    })
    assert res.status_code == 200
    assert sync_service.get_active_llm_provider() == "http://192.168.0.99:5000/api/nodes/proxy/llm"


def test_updater_api_version(client):
    res = client.get('/api/updater/version')
    assert res.status_code == 200
    data = res.get_json()
    assert "v2.1." in data["version"]
