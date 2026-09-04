"""Regression tests for the Docker Compose stack embedded in README.md.

README.md is the single source of truth for the production deployment
manifest. These tests pin the cross-service invariants that would otherwise
break only at runtime (credential drift, wiring, GPU passthrough).
"""

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"

REQUIRED_SERVICES = {"vllm-inference", "postgres-vector", "n8n-automation"}


def extract_manifest(text: str) -> str:
    """Return the yaml block containing the compose manifest."""
    blocks = re.findall(r"```(?:yaml|yml)\s*\n(.*?)```", text, re.DOTALL)
    for block in blocks:
        if "vllm-inference" in block and "services:" in block:
            return block
    raise AssertionError(
        "no compose manifest (```yaml block containing vllm-inference) found in README.md"
    )


@pytest.fixture(scope="module")
def compose() -> dict:
    text = README.read_text(encoding="utf-8")
    manifest = extract_manifest(text)
    return yaml.safe_load(manifest)


def env_map(service: dict) -> dict:
    """Normalize a service's environment to a dict regardless of list/dict form."""
    raw = service.get("environment") or {}
    if isinstance(raw, dict):
        return dict(raw)
    return dict(item.split("=", 1) for item in raw)


def published_port_pairs(service: dict) -> set[tuple[str, str]]:
    """Normalize ports to (host, container) pairs."""
    pairs = set()
    for entry in service.get("ports") or []:
        text = str(entry).split("/", 1)[0]
        if ":" in text:
            host, container = text.split(":", 1)
        else:
            host = container = text
        pairs.add((host, container))
    return pairs


def used_named_volumes(compose: dict) -> set[str]:
    used = set()
    for service in compose["services"].values():
        for entry in service.get("volumes") or []:
            name = entry.split(":", 1)[0]
            # host paths are anchored; anything else is a volume reference
            if name and not name.startswith(("/", "~", ".")):
                used.add(name)
    return used


def test_manifest_parses_with_expected_top_level_keys(compose):
    assert set(compose) == {"version", "services", "volumes"}


def test_expected_services_are_defined(compose):
    assert set(compose["services"]) == REQUIRED_SERVICES


def test_n8n_connects_with_exact_postgres_credentials(compose):
    postgres = compose["services"]["postgres-vector"]
    pg_env = env_map(postgres)
    n8n_env = env_map(compose["services"]["n8n-automation"])

    assert n8n_env["DB_POSTGRESDB_HOST"] == "postgres-vector"  # the compose service name

    pg_ports = [container for _, container in published_port_pairs(postgres)]
    assert n8n_env["DB_POSTGRESDB_PORT"] in pg_ports
    assert n8n_env["DB_POSTGRESDB_DATABASE"] == pg_env["POSTGRES_DB"]
    assert n8n_env["DB_POSTGRESDB_USER"] == pg_env["POSTGRES_USER"]
    # password drift here fails only at runtime, when n8n cannot authenticate
    assert n8n_env["DB_POSTGRESDB_PASSWORD"] == pg_env["POSTGRES_PASSWORD"]
    assert n8n_env["DB_TYPE"] == "postgresdb"


def test_service_dependencies_are_wired(compose):
    n8n = compose["services"]["n8n-automation"]
    assert "postgres-vector" in (n8n.get("depends_on") or [])

    names = set(compose["services"])
    for service in compose["services"].values():
        for dependency in service.get("depends_on") or []:
            assert dependency in names, f"depends_on references unknown service {dependency!r}"


def test_named_volumes_are_declared(compose):
    declared = set(compose.get("volumes") or {})
    used = used_named_volumes(compose)
    # undeclared named volumes silently become fresh anonymous volumes on recreate
    assert used <= declared, f"undeclared volumes: {used - declared}"
    assert {"pgdata", "n8n_data"} <= declared


def test_vllm_has_gpu_passthrough(compose):
    vllm = compose["services"]["vllm-inference"]
    devices = vllm["deploy"]["resources"]["reservations"]["devices"]
    assert any(
        device.get("driver") == "nvidia" and "gpu" in (device.get("capabilities") or [])
        for device in devices
    )
    # vLLM needs host IPC for shared-memory paged attention
    assert vllm.get("ipc") == "host"


def test_vllm_reads_hf_token_from_environment(compose):
    vllm_env = env_map(compose["services"]["vllm-inference"])
    assert vllm_env.get("HUGGING_FACE_HUB_TOKEN") == "${HF_TOKEN}"


def test_published_ports_match_documented_access(compose):
    # README documents: curl http://localhost:8000/v1/models
    assert ("8000", "8000") in published_port_pairs(compose["services"]["vllm-inference"])
    assert ("5432", "5432") in published_port_pairs(compose["services"]["postgres-vector"])
    assert ("5678", "5678") in published_port_pairs(compose["services"]["n8n-automation"])


def test_all_services_restart_on_failure(compose):
    for name, service in compose["services"].items():
        assert service.get("restart") == "unless-stopped", name
