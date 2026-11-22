"""Adversarial zero-leak privacy and security tests for the 4-layer sanitization pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.sharing_is_caring.const import (
    AUDIT_STATUS_BLOCKED,
    AUDIT_STATUS_NEEDS_REVIEW,
)
from custom_components.sharing_is_caring.sanitizer import SanitizeOptions
from custom_components.sharing_is_caring.service_layer import SharingCoordinator
from tests.conftest import FakeHass, FakeState


@pytest.mark.asyncio
async def test_realistic_automation_leaks_zero_personal_data(
    fake_hass: FakeHass,
    ha_config_dir: Path,
) -> None:
    coordinator = SharingCoordinator(fake_hass, ha_config_dir)
    bundle = await coordinator.async_preview("automation.sharon_smart_hallway_motion_light")

    combined = "\n".join(bundle.files.values())

    # Instance PII, personal names, internal IDs, and hardware entity names MUST NOT appear
    forbidden_substrings = [
        "sharon",
        "Sharon",
        "Rimer",
        "rimer",
        "Villa",
        "1730000001",
        "area_secret_hallway_123",
        "master_hallway_ceiling",
        "mobile_app_sharon_pixel",
        "rimerhome.ui.nabu.casa",
        "192.168.1.50",
        "SUPER_SECRET_TRAP_VALUE_DO_NOT_LEAK",
        "998877",
        "432198",
    ]
    for secret in forbidden_substrings:
        assert secret not in combined, f"Sensitive data leaked into bundle: {secret!r}"

    # Bundled helper had personal prefix stripped cleanly
    assert "input_boolean.night_mode" in combined
    assert "timer.hallway_light_timer" in combined
    # Free-text notification messages must trigger Needs Review
    assert bundle.audit.status == AUDIT_STATUS_NEEDS_REVIEW
    assert bundle.audit.can_publish is True


@pytest.mark.asyncio
async def test_toxic_automation_with_secrets_and_pii_blocks_and_scrubs(
    fake_hass: FakeHass,
    ha_config_dir: Path,
) -> None:
    """Adversarial test: inject every class of sensitive data and verify scrubbing & hard blocks."""
    toxic_yaml = """
- id: "toxic_auto_999"
  alias: "Toxic Secret Automation"
  triggers:
    - trigger: webhook
      webhook_id: "super_secret_webhook_99887766"
    - platform: device
      device_id: "deadbeef1234567890abcdef12345678"
      domain: binary_sensor
      type: motion
  actions:
    - action: alarm_control_panel.alarm_disarm
      target:
        entity_id: alarm_control_panel.home_alarm
      data:
        code: "123456"
    - action: input_text.set_value
      target:
        entity_id: input_text.door_pin_code
      data:
        value: !secret telegram_token
    - action: notify.mobile_app_sharon_pixel
      data:
        title: "Call +1-555-234-5678 or alice@example.com"
        message: >-
          Connect to https://myhouse.duckdns.org:8123/api/webhook/abc123456789
          or 10.0.0.42 MAC AA:BB:CC:DD:EE:FF at 32.0853, 34.7818
          with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U
"""
    (ha_config_dir / "automations.yaml").write_text(toxic_yaml, encoding="utf-8")
    fake_hass.states.add(
        FakeState(
            "automation.toxic_secret_automation",
            "on",
            {"id": "toxic_auto_999", "friendly_name": "Toxic Secret Automation"},
        )
    )

    coordinator = SharingCoordinator(fake_hass, ha_config_dir)
    bundle = await coordinator.async_preview("automation.toxic_secret_automation")
    combined = "\n".join(bundle.files.values())

    # 1. Layer 1 & 4 MUST scrub every PII, network, credential field, and trap secret
    must_not_appear = [
        "toxic_auto_999",
        "super_secret_webhook_99887766",
        "deadbeef1234567890abcdef12345678",
        "123456",
        "432198",  # input_text initial value from .storage/input_text!
        "SUPER_SECRET_TRAP_VALUE_DO_NOT_LEAK",
        "alice@example.com",
        "+1-555-234-5678",
        "myhouse.duckdns.org",
        "abc123456789",
        "10.0.0.42",
        "AA:BB:CC:DD:EE:FF",
        "32.0853",
        "34.7818",
    ]
    for leaked in must_not_appear:
        assert leaked not in combined, f"Leaked sensitive value: {leaked!r}"

    # 2. Raw JWT / Bearer token inside free-text message MUST trigger HARD BLOCK
    assert bundle.audit.status == AUDIT_STATUS_BLOCKED
    assert bundle.audit.can_publish is False
    blocked_categories = {f.category for f in bundle.audit.blocked}
    assert "jwt_token" in blocked_categories or "bearer_auth_header" in blocked_categories

    # 3. Audit report itself must NEVER echo the raw secret token
    audit_json = str(bundle.audit.to_dict())
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in audit_json
    assert "SUPER_SECRET_TRAP_VALUE_DO_NOT_LEAK" not in audit_json


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("secret_payload", "expected_category"),
    [
        ("ghp_1234567890abcdefghij1234567890abcdef", "github_token"),
        ("github_pat_11AAAAAA0123456789_abcdefghij1234567890ABCDEF", "github_token"),
        ("AKIAIOSFODNN7EXAMPLE", "aws_access_key"),
        ("sk-proj-abc1234567890XYZdefghijklmnop", "openai_or_api_key"),
        ("123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw", "telegram_bot_token"),
        ("https://discord.com/api/webhooks/123456789/abcdef123456", "discord_or_slack_webhook"),
        ("-----BEGIN RSA PRIVATE KEY-----", "private_key_block"),
        ("xK9mP2vQ7nR4tW8yB3cF6hJ5zL1dG0sA9eN", "high_entropy_secret"),
    ],
)
async def test_layer4_hard_blocks_every_secret_class(
    fake_hass: FakeHass,
    ha_config_dir: Path,
    secret_payload: str,
    expected_category: str,
) -> None:
    (ha_config_dir / "automations.yaml").write_text(
        f"""
- id: "sec_test"
  alias: "Secret Leak Test"
  triggers:
    - trigger: state
      entity_id: binary_sensor.door
      to: "on"
  actions:
    - action: persistent_notification.create
      data:
        message: "Leaked value: {secret_payload}"
""",
        encoding="utf-8",
    )
    fake_hass.states.add(
        FakeState(
            "automation.secret_leak_test",
            "on",
            {"id": "sec_test", "friendly_name": "Secret Leak Test"},
        )
    )

    coordinator = SharingCoordinator(fake_hass, ha_config_dir)
    bundle = await coordinator.async_preview("automation.secret_leak_test")

    assert bundle.audit.status == AUDIT_STATUS_BLOCKED
    assert bundle.audit.can_publish is False
    categories = {f.category for f in bundle.audit.blocked}
    assert expected_category in categories


@pytest.mark.asyncio
async def test_custom_redactions_and_inline_override_cannot_bypass_blocker(
    fake_hass: FakeHass,
    ha_config_dir: Path,
) -> None:
    coordinator = SharingCoordinator(fake_hass, ha_config_dir)

    # Custom redaction strips arbitrary extra word everywhere
    bundle = await coordinator.async_preview(
        "automation.sharon_smart_hallway_motion_light",
        SanitizeOptions(custom_redactions=["Hallway"]),
    )
    combined = "\n".join(bundle.files.values())
    assert "Hallway" not in combined

    # Trying to inject a GitHub PAT via inline text override MUST still get hard-blocked!
    blocked_bundle = await coordinator.async_preview(
        "automation.sharon_smart_hallway_motion_light",
        SanitizeOptions(
            text_overrides={
                "automation.actions[3].data.message": "Token ghp_1234567890abcdefghij1234567890abcdef"
            }
        ),
    )
    assert blocked_bundle.audit.status == AUDIT_STATUS_BLOCKED
    assert blocked_bundle.audit.can_publish is False
