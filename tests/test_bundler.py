"""Tests for the dual-artifact Ability Bundler (README.md + package.yaml + blueprint.yaml)."""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.sharing_is_caring.sanitizer import SanitizeOptions
from custom_components.sharing_is_caring.service_layer import SharingCoordinator
from custom_components.sharing_is_caring.yaml_loader import load_yaml_safe_no_secrets
from tests.conftest import FakeHass


@pytest.mark.asyncio
async def test_dual_artifact_bundle_structure_and_valid_yaml(
    fake_hass: FakeHass,
    ha_config_dir: Path,
) -> None:
    coordinator = SharingCoordinator(fake_hass, ha_config_dir)
    bundle = await coordinator.async_preview(
        "automation.sharon_smart_hallway_motion_light",
        SanitizeOptions(title="Smart Motion Hallway Light", generate_blueprint=True),
    )

    assert "README.md" in bundle.files
    assert bundle.package_filename == "smart_motion_hallway_light_package.yaml"
    assert bundle.blueprint_filename == "smart_motion_hallway_light_blueprint.yaml"
    assert bundle.package_filename in bundle.files
    assert bundle.blueprint_filename in bundle.files

    # 1. package.yaml parses cleanly and contains bundled helpers + companion script + automation
    pkg_doc = load_yaml_safe_no_secrets(bundle.files[bundle.package_filename])
    assert isinstance(pkg_doc, dict)
    assert "input_boolean" in pkg_doc
    assert "night_mode" in pkg_doc["input_boolean"]
    assert "input_number" in pkg_doc
    assert "timer" in pkg_doc
    assert "threshold" in pkg_doc
    assert "script" in pkg_doc
    assert "fade_hallway_lights" in pkg_doc["script"]
    assert "automation" in pkg_doc
    assert len(pkg_doc["automation"]) == 1

    # 2. blueprint.yaml parses cleanly with blueprint: header, !input selectors, and template vars
    bp_text = bundle.files[bundle.blueprint_filename]
    assert "!input " in bp_text
    bp_doc = load_yaml_safe_no_secrets(bp_text)
    assert isinstance(bp_doc, dict)
    assert bp_doc["blueprint"]["domain"] == "automation"
    assert bp_doc["blueprint"]["name"] == "Smart Motion Hallway Light"
    inputs = bp_doc["blueprint"]["input"]
    assert any(k.startswith("target_light") for k in inputs)
    assert any(k.startswith("target_binary_sensor") for k in inputs)
    assert any(k.startswith("helper_") for k in inputs)
    assert "variables" in bp_doc

    # 3. README.md documents roles, bundled helpers, companion scripts, and both install methods
    readme = bundle.files["README.md"]
    assert "# Smart Motion Hallway Light" in readme
    assert "## Required External Devices / Entities" in readme
    assert "## Bundled Helpers" in readme
    assert "## Bundled Companion Scripts" in readme
    assert "input_boolean.night_mode" in readme
    assert "Option 1: Install as a Home Assistant Package" in readme
    assert "Option 2: Import as a Home Assistant Blueprint" in readme


@pytest.mark.asyncio
async def test_bundle_with_blueprint_disabled(
    fake_hass: FakeHass,
    ha_config_dir: Path,
) -> None:
    coordinator = SharingCoordinator(fake_hass, ha_config_dir)
    bundle = await coordinator.async_preview(
        "script.fade_hallway_lights",
        SanitizeOptions(generate_blueprint=False),
    )
    assert bundle.blueprint_filename is None
    assert set(bundle.files.keys()) == {"README.md", bundle.package_filename}
    pkg_doc = load_yaml_safe_no_secrets(bundle.files[bundle.package_filename])
    assert "script" in pkg_doc
