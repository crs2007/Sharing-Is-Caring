"""Shared test fixtures for Sharing Is Caring."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest


@dataclass
class FakeState:
    entity_id: str
    state: str = "off"
    attributes: dict[str, Any] = field(default_factory=dict)


class FakeStates:
    def __init__(self, states: list[FakeState] | None = None) -> None:
        self._by_id: dict[str, FakeState] = {s.entity_id: s for s in (states or [])}

    def get(self, entity_id: str) -> FakeState | None:
        return self._by_id.get(entity_id)

    def async_all(self) -> list[FakeState]:
        return list(self._by_id.values())

    def add(self, state: FakeState) -> None:
        self._by_id[state.entity_id] = state


@dataclass
class FakeConfig:
    config_dir: str
    location_name: str = "Rimer Villa"
    external_url: str | None = "https://rimerhome.ui.nabu.casa"
    internal_url: str | None = "http://192.168.1.50:8123"
    latitude: float = 32.0853
    longitude: float = 34.7818


@dataclass
class FakeConfigEntry:
    entry_id: str
    domain: str
    title: str
    data: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


class FakeConfigEntries:
    def __init__(self, entries: list[FakeConfigEntry] | None = None) -> None:
        self._entries = list(entries or [])

    def async_entries(self, domain: str | None = None) -> list[FakeConfigEntry]:
        if domain is None:
            return list(self._entries)
        return [e for e in self._entries if e.domain == domain]


class FakeHass:
    """Lightweight Home Assistant double for fast, thorough unit & security tests."""

    def __init__(
        self,
        config_dir: Path,
        *,
        states: list[FakeState] | None = None,
        config_entries: list[FakeConfigEntry] | None = None,
        entity_config_entries: dict[str, str] | None = None,
        config_overrides: dict[str, Any] | None = None,
    ) -> None:
        cfg_kwargs: dict[str, Any] = {"config_dir": str(config_dir)}
        if config_overrides:
            cfg_kwargs.update(config_overrides)
        self.config = FakeConfig(**cfg_kwargs)
        self.states = FakeStates(states)
        self.config_entries = FakeConfigEntries(config_entries)
        self._test_entity_config_entries = dict(entity_config_entries or {})
        self.data: dict[str, Any] = {}

    async def async_add_executor_job(self, func: Any, *args: Any) -> Any:
        return func(*args)


@pytest.fixture
def ha_config_dir(tmp_path: Path) -> Path:
    """Create a realistic temporary Home Assistant config directory with trap secrets."""
    storage = tmp_path / ".storage"
    storage.mkdir()

    # Trap secrets file that MUST NEVER be read or leaked!
    (tmp_path / "secrets.yaml").write_text(
        'telegram_token: "SUPER_SECRET_TRAP_VALUE_DO_NOT_LEAK"\n'
        'alarm_pin: "998877"\n',
        encoding="utf-8",
    )

    # Storage helpers
    (storage / "input_boolean").write_text(
        json.dumps(
            {
                "version": 1,
                "data": {
                    "items": [
                        {
                            "id": "sharon_night_mode",
                            "name": "Sharon Night Mode",
                            "icon": "mdi:weather-night",
                            "initial": False,
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    (storage / "input_number").write_text(
        json.dumps(
            {
                "version": 1,
                "data": {
                    "items": [
                        {
                            "id": "hallway_timeout_minutes",
                            "name": "Hallway Timeout",
                            "min": 1,
                            "max": 30,
                            "step": 1,
                            "unit_of_measurement": "min",
                            "mode": "slider",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    (storage / "input_text").write_text(
        json.dumps(
            {
                "version": 1,
                "data": {
                    "items": [
                        {
                            "id": "door_pin_code",
                            "name": "Door PIN",
                            "min": 4,
                            "max": 8,
                            "mode": "password",
                            "initial": "432198",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    (storage / "timer").write_text(
        json.dumps(
            {
                "version": 1,
                "data": {
                    "items": [
                        {
                            "id": "hallway_light_timer",
                            "name": "Hallway Light Timer",
                            "duration": "00:05:00",
                            "restore": True,
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    # Automations YAML
    (tmp_path / "automations.yaml").write_text(
        """
- id: "1730000001"
  alias: "Sharon Smart Hallway Motion Light"
  description: "Turns on hallway light when motion is detected at Rimer Villa."
  mode: restart
  triggers:
    - trigger: state
      entity_id: binary_sensor.sharon_hallway_motion
      to: "on"
  conditions:
    - condition: state
      entity_id: input_boolean.sharon_night_mode
      state: "on"
    - condition: template
      value_template: "{{ states('sensor.hallway_lux') | float(0) < states('input_number.hallway_timeout_minutes') | float(5) }}"
  actions:
    - action: light.turn_on
      target:
        entity_id: light.master_hallway_ceiling
        area_id: area_secret_hallway_123
    - action: timer.start
      target:
        entity_id: timer.hallway_light_timer
    - action: script.fade_hallway_lights
    - action: notify.mobile_app_sharon_pixel
      data:
        title: "Motion Alert at Rimer Villa"
        message: "Hallway light turned on for Sharon"
""",
        encoding="utf-8",
    )

    # Scripts YAML
    (tmp_path / "scripts.yaml").write_text(
        """
fade_hallway_lights:
  alias: "Fade Hallway Lights"
  sequence:
    - action: light.turn_on
      target:
        entity_id: light.master_hallway_ceiling
      data:
        brightness_pct: 50
""",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def fake_hass(ha_config_dir: Path) -> FakeHass:
    """Create a FakeHass populated with personal entities and a config-entry helper."""
    states = [
        FakeState(
            "automation.sharon_smart_hallway_motion_light",
            "on",
            {"id": "1730000001", "friendly_name": "Sharon Smart Hallway Motion Light"},
        ),
        FakeState(
            "script.fade_hallway_lights",
            "off",
            {"friendly_name": "Fade Hallway Lights"},
        ),
        FakeState("person.sharon", "home", {"friendly_name": "Sharon Rimer"}),
        FakeState(
            "zone.kids_school",
            "0",
            {"friendly_name": "Kids School", "latitude": 32.0912, "longitude": 34.7901},
        ),
        FakeState("device_tracker.sharon_pixel_9", "home"),
        FakeState("notify.mobile_app_sharon_pixel", "unknown"),
    ]

    entries = [
        FakeConfigEntry(
            entry_id="ce_lux_threshold",
            domain="threshold",
            title="Hallway Lux",
            options={
                "entity_id": "sensor.raw_hallway_illuminance",
                "lower": 50,
            },
        )
    ]

    return FakeHass(
        ha_config_dir,
        states=states,
        config_entries=entries,
        entity_config_entries={"sensor.hallway_lux": "ce_lux_threshold"},
    )
