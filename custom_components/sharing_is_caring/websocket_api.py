"""Admin-only WebSocket API for the Sharing Is Caring sidebar panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    PROVIDER_GITHUB_GIST,
    VALID_PROVIDERS,
    VALID_VISIBILITIES,
    VISIBILITY_SECRET,
)
from .providers import ProviderError
from .sanitizer import SanitizeOptions
from .service_layer import PublishBlockedError, SharingCoordinator


def _get_coordinator(hass: HomeAssistant) -> SharingCoordinator | None:
    domain_data = hass.data.get(DOMAIN)
    if isinstance(domain_data, dict):
        coord = domain_data.get("coordinator")
        if isinstance(coord, SharingCoordinator):
            return coord
    return None


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/get_status"})
@websocket_api.async_response
async def ws_get_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return configured share providers and default visibility (never returns secrets)."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "Sharing Is Caring is not loaded.")
        return
    connection.send_result(msg["id"], coordinator.get_status())


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list_shareables"})
@websocket_api.async_response
async def ws_list_shareables(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List local automations and scripts for the sidebar picker."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "Sharing Is Caring is not loaded.")
        return
    connection.send_result(msg["id"], {"items": coordinator.list_shareables()})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/preview",
        vol.Required("entity_id"): str,
        vol.Optional("title"): str,
        vol.Optional("description"): str,
        vol.Optional("include_companion_scripts", default=True): bool,
        vol.Optional("generate_blueprint", default=True): bool,
        vol.Optional("custom_redactions", default=[]): [str],
        vol.Optional("text_overrides", default={}): {str: str},
    }
)
@websocket_api.async_response
async def ws_preview(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Run discovery, 4-layer sanitization, and bundling; return preview + preview_hash."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "Sharing Is Caring is not loaded.")
        return

    opts = SanitizeOptions(
        title=msg.get("title"),
        description=msg.get("description"),
        include_companion_scripts=bool(msg.get("include_companion_scripts", True)),
        generate_blueprint=bool(msg.get("generate_blueprint", True)),
        custom_redactions=list(msg.get("custom_redactions", [])),
        text_overrides=dict(msg.get("text_overrides", {})),
    )

    try:
        bundle = await coordinator.async_preview(msg["entity_id"], opts)
    except (ValueError, LookupError) as err:
        connection.send_error(msg["id"], "preview_failed", str(err))
        return

    connection.send_result(msg["id"], bundle.to_preview_dict())


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/publish",
        vol.Required("preview_hash"): str,
        vol.Optional("provider", default=PROVIDER_GITHUB_GIST): vol.In(VALID_PROVIDERS),
        vol.Optional("visibility", default=VISIBILITY_SECRET): vol.In(VALID_VISIBILITIES),
        vol.Optional("confirm_review_items", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_publish(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Publish a hash-verified, blocker-free sanitized bundle."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "Sharing Is Caring is not loaded.")
        return

    try:
        result = await coordinator.async_publish(
            preview_hash=msg["preview_hash"],
            provider_id=msg["provider"],
            visibility=msg.get("visibility"),
            confirm_review_items=bool(msg.get("confirm_review_items", False)),
        )
    except PublishBlockedError as err:
        connection.send_error(msg["id"], "publish_blocked", str(err))
        return
    except ProviderError as err:
        connection.send_error(msg["id"], "provider_error", str(err))
        return

    connection.send_result(msg["id"], result.to_dict())


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register all Sharing Is Caring WebSocket commands."""
    websocket_api.async_register_command(hass, ws_get_status)
    websocket_api.async_register_command(hass, ws_list_shareables)
    websocket_api.async_register_command(hass, ws_preview)
    websocket_api.async_register_command(hass, ws_publish)
