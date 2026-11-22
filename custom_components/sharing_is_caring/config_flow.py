"""Config flow and Options flow for Sharing Is Caring."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_DEFAULT_VISIBILITY,
    CONF_GITHUB_TOKEN,
    CONF_SHOW_IN_SIDEBAR,
    DOMAIN,
    VALID_VISIBILITIES,
    VISIBILITY_SECRET,
)
from .providers import (
    GitHubGistProvider,
    ProviderAuthError,
    ProviderConnectionError,
    ProviderError,
    ProviderScopeError,
)

_LOGGER = logging.getLogger(__name__)


def _visibility_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=list(VALID_VISIBILITIES),
            translation_key=CONF_DEFAULT_VISIBILITY,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _token_selector() -> TextSelector:
    return TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


class SharingIsCaringConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Sharing Is Caring."""

    VERSION = 1

    async def _async_validate_github_token(self, token: str) -> str | None:
        """Validate optional GitHub PAT; returns translation error key or None if valid."""
        cleaned = token.strip()
        if not cleaned:
            return None

        session = async_get_clientsession(self.hass)
        try:
            await GitHubGistProvider.async_validate_token(session, cleaned)
        except ProviderAuthError:
            return "invalid_auth"
        except ProviderScopeError:
            return "insufficient_scope"
        except ProviderConnectionError:
            return "cannot_connect"
        except ProviderError:
            _LOGGER.exception("Unexpected provider error during GitHub token validation")
            return "unknown"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            token = str(user_input.get(CONF_GITHUB_TOKEN, "")).strip()
            error_key = await self._async_validate_github_token(token)
            if error_key:
                errors["base"] = error_key
            else:
                return self.async_create_entry(
                    title="Sharing Is Caring",
                    data={
                        CONF_GITHUB_TOKEN: token,
                        CONF_DEFAULT_VISIBILITY: user_input.get(
                            CONF_DEFAULT_VISIBILITY, VISIBILITY_SECRET
                        ),
                    },
                    options={
                        CONF_DEFAULT_VISIBILITY: user_input.get(
                            CONF_DEFAULT_VISIBILITY, VISIBILITY_SECRET
                        ),
                        CONF_SHOW_IN_SIDEBAR: bool(
                            user_input.get(CONF_SHOW_IN_SIDEBAR, True)
                        ),
                    },
                )

        schema = vol.Schema(
            {
                vol.Optional(CONF_GITHUB_TOKEN, default=""): _token_selector(),
                vol.Required(
                    CONF_DEFAULT_VISIBILITY, default=VISIBILITY_SECRET
                ): _visibility_selector(),
                vol.Required(CONF_SHOW_IN_SIDEBAR, default=True): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Allow the user to add, rotate, or clear their GitHub Personal Access Token."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            token = str(user_input.get(CONF_GITHUB_TOKEN, "")).strip()
            error_key = await self._async_validate_github_token(token)
            if error_key:
                errors["base"] = error_key
            else:
                new_visibility = user_input.get(
                    CONF_DEFAULT_VISIBILITY,
                    entry.options.get(CONF_DEFAULT_VISIBILITY, VISIBILITY_SECRET),
                )
                return self.async_update_reload_and_abort(
                    entry,
                    data={
                        **entry.data,
                        CONF_GITHUB_TOKEN: token,
                        CONF_DEFAULT_VISIBILITY: new_visibility,
                    },
                    options={
                        **entry.options,
                        CONF_DEFAULT_VISIBILITY: new_visibility,
                    },
                )

        current_visibility = entry.options.get(
            CONF_DEFAULT_VISIBILITY,
            entry.data.get(CONF_DEFAULT_VISIBILITY, VISIBILITY_SECRET),
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_GITHUB_TOKEN, default=""): _token_selector(),
                vol.Required(
                    CONF_DEFAULT_VISIBILITY, default=current_visibility
                ): _visibility_selector(),
            }
        )
        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SharingIsCaringOptionsFlow:
        return SharingIsCaringOptionsFlow(config_entry)


class SharingIsCaringOptionsFlow(config_entries.OptionsFlow):
    """Handle runtime options for Sharing Is Caring (sidebar toggle & default visibility)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_visibility = self._entry.options.get(
            CONF_DEFAULT_VISIBILITY,
            self._entry.data.get(CONF_DEFAULT_VISIBILITY, VISIBILITY_SECRET),
        )
        current_sidebar = bool(self._entry.options.get(CONF_SHOW_IN_SIDEBAR, True))

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEFAULT_VISIBILITY, default=current_visibility
                ): _visibility_selector(),
                vol.Required(CONF_SHOW_IN_SIDEBAR, default=current_sidebar): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
