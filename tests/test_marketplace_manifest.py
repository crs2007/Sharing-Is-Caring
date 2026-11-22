"""Validate Home Assistant Marketplace (2026.11+) and Hassfest structural compliance."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
INTEGRATION_DIR = REPO_ROOT / "custom_components" / "sharing_is_caring"


def test_hacs_json_valid_for_marketplace() -> None:
    hacs_path = REPO_ROOT / "hacs.json"
    assert hacs_path.is_file(), "Root hacs.json is mandatory for HA 2026.11+ Marketplace"
    data = json.loads(hacs_path.read_text(encoding="utf-8"))
    assert data["name"] == "Sharing Is Caring"
    assert "homeassistant" in data
    assert data.get("render_readme") is True


def test_manifest_json_hassfest_ordering_and_required_keys() -> None:
    manifest_path = INTEGRATION_DIR / "manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    keys = list(manifest.keys())
    # Hassfest requires `domain` first, `name` second, then remaining keys strictly alphabetical
    assert keys[0] == "domain"
    assert keys[1] == "name"
    assert keys[2:] == sorted(keys[2:]), f"manifest.json keys after domain/name must be sorted: {keys[2:]}"

    assert manifest["domain"] == "sharing_is_caring"
    assert manifest["config_flow"] is True
    assert manifest["version"]
    assert manifest["documentation"].startswith("https://")
    assert manifest["issue_tracker"].startswith("https://")
    assert isinstance(manifest["codeowners"], list) and manifest["codeowners"]
    assert isinstance(manifest["categories"], list) and 1 <= len(manifest["categories"]) <= 3


def test_strings_and_en_translations_match() -> None:
    strings = json.loads((INTEGRATION_DIR / "strings.json").read_text(encoding="utf-8"))
    en = json.loads((INTEGRATION_DIR / "translations" / "en.json").read_text(encoding="utf-8"))
    assert strings == en


def test_services_yaml_is_valid() -> None:
    services = yaml.safe_load((INTEGRATION_DIR / "services.yaml").read_text(encoding="utf-8"))
    assert "preview" in services
    assert "share" in services
    assert "preview_hash" in services["share"]["fields"]


def test_compiled_frontend_panel_asset_exists() -> None:
    panel_js = INTEGRATION_DIR / "frontend" / "sharing-is-caring-panel.js"
    assert panel_js.is_file(), "Built Lit frontend panel JS must be committed for Marketplace"
    content = panel_js.read_text(encoding="utf-8")
    assert "sharing-is-caring-panel" in content
    assert len(content) > 500
