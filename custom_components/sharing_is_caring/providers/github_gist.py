"""GitHub Gist share provider using the user's own GitHub Personal Access Token."""

from __future__ import annotations

import logging
from urllib.parse import quote

import aiohttp

from ..const import (
    GITHUB_API_BASE,
    GITHUB_API_VERSION,
    PROVIDER_GITHUB_GIST,
    VISIBILITY_PUBLIC,
    VISIBILITY_SECRET,
)
from ..models import AbilityBundle, ShareResult
from .base import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderError,
    ProviderScopeError,
    ShareProvider,
    TokenValidationResult,
)

_LOGGER = logging.getLogger(__name__)

_BROAD_SENSITIVE_SCOPES = frozenset(
    {"repo", "delete_repo", "admin:org", "admin:public_key", "admin:repo_hook", "workflow", "user"}
)


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "HomeAssistant-SharingIsCaring",
    }


class GitHubGistProvider(ShareProvider):
    """Publishes sanitized multi-file AbilityBundles as GitHub Gists."""

    provider_id = PROVIDER_GITHUB_GIST

    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self._session = session
        self._token = token.strip()

    @staticmethod
    async def async_validate_token(
        session: aiohttp.ClientSession,
        token: str,
    ) -> TokenValidationResult:
        """Validate a user-supplied GitHub PAT (Fine-Grained or Classic) for Gist access."""
        cleaned = token.strip()
        if not cleaned:
            raise ProviderAuthError("GitHub token is empty.")

        headers = _github_headers(cleaned)
        try:
            async with session.get(
                f"{GITHUB_API_BASE}/user",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    raise ProviderAuthError("GitHub rejected the token (401 Unauthorized).")
                if resp.status == 403:
                    raise ProviderScopeError("GitHub token lacks required access (403 Forbidden).")
                if resp.status >= 400:
                    raise ProviderError(f"GitHub API error during validation (HTTP {resp.status}).")

                data = await resp.json()
                username = str(data.get("login", "github-user"))
                raw_scopes = resp.headers.get("X-OAuth-Scopes")
        except aiohttp.ClientError as err:
            raise ProviderConnectionError(f"Could not connect to GitHub API: {err}") from err

        scopes: tuple[str, ...] = ()
        has_broad = False
        if raw_scopes is not None:
            # Classic PAT: verify explicit `gist` scope
            parsed_scopes = tuple(s.strip() for s in raw_scopes.split(",") if s.strip())
            scopes = parsed_scopes
            if "gist" not in parsed_scopes:
                raise ProviderScopeError(
                    "Classic GitHub PAT is missing the 'gist' scope."
                )
            has_broad = bool(set(parsed_scopes) & _BROAD_SENSITIVE_SCOPES)
            if has_broad:
                _LOGGER.warning(
                    "Configured GitHub PAT has broader scopes than needed (%s). "
                    "For best security, use a Fine-Grained PAT with only 'Gists: Read and write'.",
                    ", ".join(parsed_scopes),
                )
        else:
            # Fine-Grained PAT: verify Gists endpoint access explicitly
            try:
                async with session.get(
                    f"{GITHUB_API_BASE}/gists?per_page=1",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as gist_resp:
                    if gist_resp.status == 401:
                        raise ProviderAuthError("GitHub rejected the token (401 Unauthorized).")
                    if gist_resp.status == 403:
                        raise ProviderScopeError(
                            "Fine-Grained PAT does not have 'Gists: Read and write' permission."
                        )
                    if gist_resp.status >= 400:
                        raise ProviderError(
                            f"GitHub Gists permission check failed (HTTP {gist_resp.status})."
                        )
            except aiohttp.ClientError as err:
                raise ProviderConnectionError(f"Could not reach GitHub Gists API: {err}") from err

        return TokenValidationResult(
            username=username,
            has_broad_scopes=has_broad,
            scopes=scopes,
        )

    async def async_publish(
        self,
        bundle: AbilityBundle,
        *,
        visibility: str = VISIBILITY_SECRET,
    ) -> ShareResult:
        """Create a multi-file GitHub Gist from the exact sanitized bundle."""
        if not self._token:
            raise ProviderAuthError("No GitHub Personal Access Token configured.")

        is_public = visibility == VISIBILITY_PUBLIC
        payload = {
            "description": f"Home Assistant Ability: {bundle.title}",
            "public": is_public,
            "files": {
                filename: {"content": content}
                for filename, content in bundle.files.items()
            },
        }

        try:
            async with self._session.post(
                f"{GITHUB_API_BASE}/gists",
                headers=_github_headers(self._token),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status == 401:
                    raise ProviderAuthError("GitHub rejected the token (401 Unauthorized).")
                if resp.status == 403:
                    raise ProviderScopeError(
                        "GitHub token does not have permission to create Gists (403 Forbidden)."
                    )
                if resp.status >= 400:
                    raise ProviderError(f"GitHub Gist creation failed (HTTP {resp.status}).")

                data = await resp.json()
        except aiohttp.ClientError as err:
            raise ProviderConnectionError(f"Failed to publish Gist to GitHub: {err}") from err

        share_url = str(data.get("html_url", ""))
        gist_id = str(data.get("id", "")) or None
        raw_blueprint_url: str | None = None
        my_ha_import_url: str | None = None

        if bundle.blueprint_filename:
            gist_files = data.get("files", {})
            bp_info = gist_files.get(bundle.blueprint_filename)
            if isinstance(bp_info, dict) and bp_info.get("raw_url"):
                raw_blueprint_url = str(bp_info["raw_url"])
                my_ha_import_url = (
                    "https://my.home-assistant.io/redirect/blueprint_import/"
                    f"?blueprint_url={quote(raw_blueprint_url, safe='')}"
                )

        return ShareResult(
            provider=self.provider_id,
            share_url=share_url,
            visibility=VISIBILITY_PUBLIC if is_public else VISIBILITY_SECRET,
            raw_blueprint_url=raw_blueprint_url,
            my_ha_import_url=my_ha_import_url,
            gist_id=gist_id,
            files=dict(bundle.files),
        )
