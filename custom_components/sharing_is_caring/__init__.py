"""The Sharing Is Caring Home Assistant integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from .const import (
    CONF_SHOW_IN_SIDEBAR,
    DOMAIN,
    PANEL_ICON,
    PANEL_MODULE_URL,
    PANEL_STATIC_BASE_URL,
    PANEL_TITLE,
    PANEL_URL_PATH,
    PROVIDER_GITHUB_GIST,
    SERVICE_PREVIEW,
    SERVICE_SHARE,
    VALID_PROVIDERS,
    VALID_VISIBILITIES,
    VERSION,
    VISIBILITY_SECRET,
)
from .providers import ProviderError
from .sanitizer import SanitizeOptions
from .service_layer import (
    PublishBlockedError,
    SharingCoordinator,
    build_coordinator_from_entry,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse

_LOGGER = logging.getLogger(__name__)

_PREVIEW_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): str,
        vol.Optional("title"): str,
        vol.Optional("description"): str,
        vol.Optional("include_companion_scripts", default=True): bool,
        vol.Optional("generate_blueprint", default=True): bool,
        vol.Optional("custom_redactions", default=[]): [str],
    }
)

_SHARE_SCHEMA = vol.Schema(
    {
        vol.Required("preview_hash"): str,
        vol.Optional("provider", default=PROVIDER_GITHUB_GIST): vol.In(VALID_PROVIDERS),
        vol.Optional("visibility", default=VISIBILITY_SECRET): vol.In(VALID_VISIBILITIES),
        vol.Optional("confirm_review_items", default=False): bool,
    }
)


async def _async_ensure_admin_call(hass: HomeAssistant, call: ServiceCall) -> None:
    """Enforce Home Assistant Admin privileges on service calls."""
    from homeassistant.exceptions import Unauthorized

    user_id = call.context.user_id
    if user_id is None:
        return  # Internal/system automation context
    user = await hass.auth.async_get_user(user_id)
    if user is None or not user.is_admin:
        raise Unauthorized(
            context=call.context,
            user_id=user_id,
            permission="admin",
        )


async def _async_register_frontend_panel(hass: HomeAssistant, show_in_sidebar: bool) -> None:
    """Register static frontend assets and optional admin-only sidebar panel."""
    from homeassistant.components import frontend
    from homeassistant.components.http import StaticPathConfig

    domain_data = hass.data.setdefault(DOMAIN, {})
    frontend_dir = Path(__file__).parent / "frontend"

    if not domain_data.get("static_registered") and frontend_dir.is_dir():
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    PANEL_STATIC_BASE_URL,
                    str(frontend_dir),
                    cache_headers=False,
                )
            ]
        )
        domain_data["static_registered"] = True

    if show_in_sidebar:
        frontend.async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            frontend_url_path=PANEL_URL_PATH,
            require_admin=True,
            config={
                "_panel_custom": {
                    "name": "sharing-is-caring-panel",
                    "module_url": f"{PANEL_MODULE_URL}?v={VERSION}",
                    "embed_iframe": False,
                }
            },
            update=True,
        )
        domain_data["panel_registered"] = True
    elif domain_data.get("panel_registered"):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
        domain_data["panel_registered"] = False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sharing Is Caring from a config entry."""
    from homeassistant.core import SupportsResponse
    from homeassistant.exceptions import HomeAssistantError

    from .websocket_api import async_register_websocket_commands

    domain_data = hass.data.setdefault(DOMAIN, {})
    coordinator = build_coordinator_from_entry(hass, entry)
    domain_data["coordinator"] = coordinator

    if not domain_data.get("ws_registered"):
        async_register_websocket_commands(hass)
        domain_data["ws_registered"] = True

    show_in_sidebar = bool(entry.options.get(CONF_SHOW_IN_SIDEBAR, True))
    await _async_register_frontend_panel(hass, show_in_sidebar=show_in_sidebar)

    async def handle_preview(call: ServiceCall) -> ServiceResponse:
        await _async_ensure_admin_call(hass, call)
        coord: SharingCoordinator = hass.data[DOMAIN]["coordinator"]
        opts = SanitizeOptions(
            title=call.data.get("title"),
            description=call.data.get("description"),
            include_companion_scripts=bool(call.data.get("include_companion_scripts", True)),
            generate_blueprint=bool(call.data.get("generate_blueprint", True)),
            custom_redactions=list(call.data.get("custom_redactions", [])),
        )
        try:
            bundle = await coord.async_preview(call.data["entity_id"], opts)
        except (ValueError, LookupError) as err:
            raise HomeAssistantError(str(err)) from err
        return bundle.to_preview_dict()

    async def handle_share(call: ServiceCall) -> ServiceResponse:
        await _async_ensure_admin_call(hass, call)
        coord: SharingCoordinator = hass.data[DOMAIN]["coordinator"]
        try:
            result = await coord.async_publish(
                preview_hash=call.data["preview_hash"],
                provider_id=call.data["provider"],
                visibility=call.data.get("visibility"),
                confirm_review_items=bool(call.data.get("confirm_review_items", False)),
            )
        except (PublishBlockedError, ProviderError) as err:
            raise HomeAssistantError(str(err)) from err
        return result.to_dict()

    if not hass.services.has_service(DOMAIN, SERVICE_PREVIEW):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PREVIEW,
            handle_preview,
            schema=_PREVIEW_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SHARE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SHARE,
            handle_share,
            schema=_SHARE_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options or reconfigure values change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Sharing Is Caring config entry."""
    from homeassistant.components import frontend

    domain_data: dict[str, Any] = hass.data.get(DOMAIN, {})
    if domain_data.get("panel_registered"):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
        domain_data["panel_registered"] = False

    if hass.services.has_service(DOMAIN, SERVICE_PREVIEW):
        hass.services.async_remove(DOMAIN, SERVICE_PREVIEW)
    if hass.services.has_service(DOMAIN, SERVICE_SHARE):
        hass.services.async_remove(DOMAIN, SERVICE_SHARE)

    domain_data.pop("coordinator", None)
    return True
