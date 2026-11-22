"""Tests for dependency discovery and helper extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.sharing_is_caring.discovery import (
    collect_entity_references,
    discover_ability_sync,
    extract_entity_references_from_template,
)
from custom_components.sharing_is_caring.models import SecretRef
from custom_components.sharing_is_caring.yaml_loader import load_yaml_safe_no_secrets
from tests.conftest import FakeHass


def test_non_resolving_yaml_loader_preserves_secret_without_reading() -> None:
    raw = """
    webhook: !secret my_webhook
    api_key: !secret telegram_token
    nested: !include other.yaml
    """
    parsed = load_yaml_safe_no_secrets(raw)
    assert isinstance(parsed["webhook"], SecretRef)
    assert parsed["webhook"].key == "my_webhook"
    assert parsed["webhook"].placeholder() == "<YOUR_SECRET_MY_WEBHOOK>"
    assert isinstance(parsed["api_key"], SecretRef)


def test_jinja_template_entity_extraction() -> None:
    tpl = (
        "{% if is_state('input_boolean.vacation_mode', 'on') and "
        "states.sensor.outdoor_temp.state | float > 20 %}"
        "{{ expand(['light.kitchen', 'switch.fan']) | count }}"
        "{% endif %}"
    )
    refs = extract_entity_references_from_template(tpl)
    assert "input_boolean.vacation_mode" in refs
    assert "sensor.outdoor_temp" in refs
    assert "light.kitchen" in refs
    assert "switch.fan" in refs


def test_discover_automation_helpers_and_companion_scripts(
    fake_hass: FakeHass,
    ha_config_dir: Path,
) -> None:
    graph = discover_ability_sync(
        fake_hass,
        ha_config_dir,
        "automation.sharon_smart_hallway_motion_light",
        include_companion_scripts=True,
    )

    assert graph.root.entity_id == "automation.sharon_smart_hallway_motion_light"

    helper_ids = {h.entity_id for h in graph.helpers}
    assert "input_boolean.sharon_night_mode" in helper_ids
    assert "input_number.hallway_timeout_minutes" in helper_ids
    assert "timer.hallway_light_timer" in helper_ids
    # Config-entry threshold helper discovered via Jinja2 template!
    assert "sensor.hallway_lux" in helper_ids

    script_ids = {s.entity_id for s in graph.companion_scripts}
    assert "script.fade_hallway_lights" in script_ids

    # External hardware & notify entities are NOT bundled as helpers
    assert "binary_sensor.sharon_hallway_motion" in graph.external_entities
    assert "light.master_hallway_ceiling" in graph.external_entities
    assert "notify.mobile_app_sharon_pixel" in graph.external_entities
    # Transitive entity referenced by the config-entry threshold helper
    assert "sensor.raw_hallway_illuminance" in graph.external_entities


def test_discover_without_companion_scripts(
    fake_hass: FakeHass,
    ha_config_dir: Path,
) -> None:
    graph = discover_ability_sync(
        fake_hass,
        ha_config_dir,
        "automation.sharon_smart_hallway_motion_light",
        include_companion_scripts=False,
    )
    assert graph.companion_scripts == []
    assert "script.fade_hallway_lights" in graph.external_entities


def test_discover_rejects_non_shareable_domain(
    fake_hass: FakeHass,
    ha_config_dir: Path,
) -> None:
    with pytest.raises(ValueError, match="Unsupported domain"):
        discover_ability_sync(fake_hass, ha_config_dir, "light.master_hallway_ceiling")


def test_collect_entity_references_ignores_standard_script_services() -> None:
    cfg = {
        "actions": [
            {"action": "script.turn_on", "target": {"entity_id": "script.custom_helper"}},
            {"action": "script.direct_call"},
        ]
    }
    refs = collect_entity_references(cfg)
    assert "script.turn_on" not in refs
    assert "script.custom_helper" in refs
    assert "script.direct_call" in refs
