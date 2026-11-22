"""High-level coordinator orchestrating discovery, sanitization, bundling, and publishing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiohttp

from .bundler import build_ability_files
from .const import (
    AUDIT_STATUS_BLOCKED,
    AUDIT_STATUS_NEEDS_REVIEW,
    CONF_DEFAULT_VISIBILITY,
    CONF_GITHUB_TOKEN,
    PROVIDER_GITHUB_GIST,
    PROVIDER_LOCAL,
    SHAREABLE_DOMAINS,
    VISIBILITY_SECRET,
)
from .discovery import discover_ability_sync
from .models import AbilityBundle, ShareResult
from .providers import (
    GitHubGistProvider,
    LocalExportProvider,
    ProviderAuthError,
    ProviderError,
    ShareProvider,
)
from .sanitizer import PreviewCache, SanitizationPipeline, SanitizeOptions


class PublishBlockedError(Exception):
    """Raised when a publish attempt fails the fail-closed security gate."""


class SharingCoordinator:
    """Coordinates discovery, zero-leak sanitization, preview caching, and provider publishing."""

    def __init__(
        self,
        hass: Any,
        config_dir: Path,
        *,
        github_token: str = "",
        default_visibility: str = VISIBILITY_SECRET,
        session: aiohttp.ClientSession | None = None,
        cache: PreviewCache | None = None,
    ) -> None:
        self._hass = hass
        self._config_dir = config_dir
        self._github_token = github_token.strip()
        self._default_visibility = default_visibility
        self._session = session
        self.pipeline = SanitizationPipeline(cache=cache)

    @property
    def github_configured(self) -> bool:
        return bool(self._github_token)

    @property
    def default_visibility(self) -> str:
        return self._default_visibility

    def update_config(
        self,
        *,
        github_token: str | None = None,
        default_visibility: str | None = None,
    ) -> None:
        if github_token is not None:
            self._github_token = github_token.strip()
        if default_visibility is not None:
            self._default_visibility = default_visibility

    def get_status(self) -> dict[str, Any]:
        """Return safe integration capability status for the UI (never exposes the token!)."""
        return {
            "github_configured": self.github_configured,
            "default_visibility": self._default_visibility,
            "available_providers": [
                {
                    "id": PROVIDER_GITHUB_GIST,
                    "name": "GitHub Gist",
                    "configured": self.github_configured,
                    "supports_visibility": True,
                },
                {
                    "id": PROVIDER_LOCAL,
                    "name": "Local Copy / Download",
                    "configured": True,
                    "supports_visibility": False,
                },
            ],
        }

    def list_shareables(self) -> list[dict[str, Any]]:
        """List automations and scripts available for sharing in the local HA instance."""
        items: list[dict[str, Any]] = []
        states = getattr(self._hass, "states", None)
        if states is None or not hasattr(states, "async_all"):
            return items

        for state in states.async_all():
            eid = str(getattr(state, "entity_id", ""))
            if "." not in eid:
                continue
            domain, obj_id = eid.split(".", 1)
            if domain not in SHAREABLE_DOMAINS:
                continue
            attrs = getattr(state, "attributes", {}) or {}
            items.append(
                {
                    "entity_id": eid,
                    "domain": domain,
                    "name": str(attrs.get("friendly_name") or obj_id.replace("_", " ").title()),
                }
            )

        return sorted(items, key=lambda item: (item["domain"], item["name"].lower()))

    async def async_preview(
        self,
        entity_id: str,
        options: SanitizeOptions | None = None,
    ) -> AbilityBundle:
        """Discover, sanitize, bundle, and cache a shareable ability without making outbound calls."""
        opts = options or SanitizeOptions()

        if hasattr(self._hass, "async_add_executor_job"):
            graph = await self._hass.async_add_executor_job(
                lambda: discover_ability_sync(
                    self._hass,
                    self._config_dir,
                    entity_id,
                    include_companion_scripts=opts.include_companion_scripts,
                )
            )
        else:
            graph = discover_ability_sync(
                self._hass,
                self._config_dir,
                entity_id,
                include_companion_scripts=opts.include_companion_scripts,
            )

        sanitized, pii_dict = self.pipeline.sanitize_graph(self._hass, graph, opts)
        raw_files, package_filename, blueprint_filename = build_ability_files(
            sanitized,
            generate_blueprint=opts.generate_blueprint,
        )
        return self.pipeline.finalize_bundle(
            sanitized,
            pii_dict,
            raw_files,
            package_filename=package_filename,
            blueprint_filename=blueprint_filename,
        )

    def _get_provider(self, provider_id: str) -> ShareProvider:
        if provider_id == PROVIDER_LOCAL:
            return LocalExportProvider()

        if provider_id == PROVIDER_GITHUB_GIST:
            if not self._github_token:
                raise ProviderAuthError(
                    "GitHub Gist is not configured. Add your own GitHub Personal Access Token "
                    "under Settings > Devices & Services > Sharing Is Caring > Reconfigure."
                )
            session = self._session
            if session is None:
                from homeassistant.helpers.aiohttp_client import async_get_clientsession

                session = async_get_clientsession(self._hass)
            return GitHubGistProvider(session=session, token=self._github_token)

        raise ProviderError(f"Unsupported share provider: {provider_id}")

    async def async_publish(
        self,
        *,
        preview_hash: str,
        provider_id: str = PROVIDER_GITHUB_GIST,
        visibility: str | None = None,
        confirm_review_items: bool = False,
    ) -> ShareResult:
        """Publish ONLY a previously previewed, hash-verified, blocker-free bundle."""
        bundle = self.pipeline.cache.get(preview_hash)
        if bundle is None:
            raise PublishBlockedError(
                "Preview hash is invalid or expired. Run preview again before publishing."
            )

        if bundle.audit.status == AUDIT_STATUS_BLOCKED or not bundle.audit.can_publish:
            raise PublishBlockedError(
                f"Publish blocked: {len(bundle.audit.blocked)} security blocker(s) detected. "
                "Remove or redact all blocked items and generate a fresh preview."
            )

        if bundle.audit.status == AUDIT_STATUS_NEEDS_REVIEW and not confirm_review_items:
            raise PublishBlockedError(
                f"Publish requires explicit confirmation: {len(bundle.audit.needs_review)} "
                "item(s) need review before publishing."
            )

        provider = self._get_provider(provider_id)
        chosen_visibility = visibility or self._default_visibility
        return await provider.async_publish(bundle, visibility=chosen_visibility)


def build_coordinator_from_entry(hass: Any, entry: Any) -> SharingCoordinator:
    """Create a SharingCoordinator from a Home Assistant ConfigEntry."""
    data = getattr(entry, "data", {}) or {}
    options = getattr(entry, "options", {}) or {}
    token = str(data.get(CONF_GITHUB_TOKEN, ""))
    visibility = str(
        options.get(
            CONF_DEFAULT_VISIBILITY,
            data.get(CONF_DEFAULT_VISIBILITY, VISIBILITY_SECRET),
        )
    )
    config_dir = Path(hass.config.config_dir)
    return SharingCoordinator(
        hass,
        config_dir,
        github_token=token,
        default_visibility=visibility,
    )
