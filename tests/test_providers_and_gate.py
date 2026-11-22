"""Tests for ShareProviders (GitHub Gist + Local) and the fail-closed preview_hash publish gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from custom_components.sharing_is_caring.const import (
    PROVIDER_GITHUB_GIST,
    PROVIDER_LOCAL,
    VISIBILITY_PUBLIC,
    VISIBILITY_SECRET,
)
from custom_components.sharing_is_caring.providers import (
    GitHubGistProvider,
    ProviderAuthError,
    ProviderScopeError,
)
from custom_components.sharing_is_caring.sanitizer import PreviewCache, SanitizeOptions
from custom_components.sharing_is_caring.service_layer import (
    PublishBlockedError,
    SharingCoordinator,
)
from tests.conftest import FakeHass, FakeState


class _MockResponse:
    def __init__(
        self,
        status: int,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._json = json_data or {}
        self.headers = headers or {}

    async def json(self) -> dict[str, Any]:
        return self._json

    async def __aenter__(self) -> _MockResponse:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None


class _MockSession:
    def __init__(self, responses: list[_MockResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def get(self, url: str, **kwargs: Any) -> _MockResponse:
        self.calls.append(("GET", url, None))
        return self._responses.pop(0)

    def post(self, url: str, **kwargs: Any) -> _MockResponse:
        self.calls.append(("POST", url, kwargs.get("json")))
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_github_validate_fine_grained_pat_success() -> None:
    session = _MockSession(
        [
            _MockResponse(200, {"login": "octocat"}, headers={}),  # No X-OAuth-Scopes -> fine-grained
            _MockResponse(200, [], headers={}),  # GET /gists?per_page=1 succeeds
        ]
    )
    result = await GitHubGistProvider.async_validate_token(session, "github_pat_test")  # type: ignore[arg-type]
    assert result.username == "octocat"
    assert result.has_broad_scopes is False
    assert len(session.calls) == 2


@pytest.mark.asyncio
async def test_github_validate_classic_pat_missing_gist_scope_fails() -> None:
    session = _MockSession(
        [_MockResponse(200, {"login": "octocat"}, headers={"X-OAuth-Scopes": "repo, read:user"})]
    )
    with pytest.raises(ProviderScopeError):
        await GitHubGistProvider.async_validate_token(session, "ghp_test")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_github_validate_classic_pat_broad_scope_flagged() -> None:
    session = _MockSession(
        [_MockResponse(200, {"login": "octocat"}, headers={"X-OAuth-Scopes": "gist, repo"})]
    )
    result = await GitHubGistProvider.async_validate_token(session, "ghp_test")  # type: ignore[arg-type]
    assert result.has_broad_scopes is True
    assert "gist" in result.scopes


@pytest.mark.asyncio
async def test_github_validate_401_raises_auth_error() -> None:
    session = _MockSession([_MockResponse(401, {"message": "Bad credentials"})])
    with pytest.raises(ProviderAuthError):
        await GitHubGistProvider.async_validate_token(session, "bad_token")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_publish_gate_blocks_unreviewed_expired_and_blocked_bundles(
    fake_hass: FakeHass,
    ha_config_dir: Path,
) -> None:
    coordinator = SharingCoordinator(fake_hass, ha_config_dir)

    # 1. Unknown/expired preview_hash MUST fail closed
    with pytest.raises(PublishBlockedError, match="invalid or expired"):
        await coordinator.async_publish(
            preview_hash="nonexistent_hash",
            provider_id=PROVIDER_LOCAL,
        )

    # 2. Bundle with Needs Review MUST fail unless confirm_review_items=True
    bundle = await coordinator.async_preview("automation.sharon_smart_hallway_motion_light")
    with pytest.raises(PublishBlockedError, match="requires explicit confirmation"):
        await coordinator.async_publish(
            preview_hash=bundle.preview_hash,
            provider_id=PROVIDER_LOCAL,
            confirm_review_items=False,
        )

    # 3. With confirm_review_items=True, local export succeeds with zero cloud calls
    local_res = await coordinator.async_publish(
        preview_hash=bundle.preview_hash,
        provider_id=PROVIDER_LOCAL,
        confirm_review_items=True,
    )
    assert local_res.provider == PROVIDER_LOCAL
    assert local_res.share_url is None
    assert local_res.files == bundle.files

    # 4. Bundle with a hard-blocked secret CANNOT be published even with confirm_review_items=True
    blocked = await coordinator.async_preview(
        "automation.sharon_smart_hallway_motion_light",
        SanitizeOptions(
            text_overrides={
                "automation.actions[3].data.message": "Key sk-proj-abc1234567890XYZdefghijklmnop"
            }
        ),
    )
    with pytest.raises(PublishBlockedError, match="security blocker"):
        await coordinator.async_publish(
            preview_hash=blocked.preview_hash,
            provider_id=PROVIDER_LOCAL,
            confirm_review_items=True,
        )


@pytest.mark.asyncio
async def test_github_gist_publish_uses_exact_cached_bytes_and_returns_my_ha_url(
    fake_hass: FakeHass,
    ha_config_dir: Path,
) -> None:
    # Clean script with no free-text review items
    mock_session = _MockSession(
        [
            _MockResponse(
                201,
                {
                    "id": "abc123gist",
                    "html_url": "https://gist.github.com/octocat/abc123gist",
                    "files": {
                        "fade_hallway_lights_blueprint.yaml": {
                            "raw_url": "https://gist.githubusercontent.com/octocat/abc123gist/raw/fade_hallway_lights_blueprint.yaml"
                        }
                    },
                },
            )
        ]
    )

    coordinator = SharingCoordinator(
        fake_hass,
        ha_config_dir,
        github_token="github_pat_valid",
        default_visibility=VISIBILITY_SECRET,
        session=mock_session,  # type: ignore[arg-type]
        cache=PreviewCache(),
    )

    bundle = await coordinator.async_preview("script.fade_hallway_lights")

    # Mutate disk file AFTER preview to verify TOCTOU protection (must upload cached bytes!)
    (ha_config_dir / "scripts.yaml").write_text(
        "fade_hallway_lights:\n  alias: 'INJECTED_SECRET_AFTER_PREVIEW'\n  sequence: []\n",
        encoding="utf-8",
    )

    result = await coordinator.async_publish(
        preview_hash=bundle.preview_hash,
        provider_id=PROVIDER_GITHUB_GIST,
        visibility=VISIBILITY_PUBLIC,
    )

    assert result.share_url == "https://gist.github.com/octocat/abc123gist"
    assert result.visibility == VISIBILITY_PUBLIC
    assert result.my_ha_import_url is not None
    assert "my.home-assistant.io/redirect/blueprint_import" in result.my_ha_import_url

    # Verify uploaded payload never saw post-preview mutation
    method, url, posted_json = mock_session.calls[0]
    assert method == "POST"
    assert url.endswith("/gists")
    assert posted_json is not None
    assert posted_json["public"] is True
    assert "INJECTED_SECRET_AFTER_PREVIEW" not in str(posted_json)


@pytest.mark.asyncio
async def test_coordinator_status_never_exposes_token(
    fake_hass: FakeHass,
    ha_config_dir: Path,
) -> None:
    secret_tok = "github_pat_SUPER_SECRET_USER_TOKEN_12345"
    coordinator = SharingCoordinator(fake_hass, ha_config_dir, github_token=secret_tok)
    status = coordinator.get_status()
    assert status["github_configured"] is True
    assert secret_tok not in str(status)

    # Also verify list_shareables only returns automations & scripts
    fake_hass.states.add(FakeState("light.kitchen", "on"))
    shareables = coordinator.list_shareables()
    domains = {s["domain"] for s in shareables}
    assert domains <= {"automation", "script"}
    assert len(shareables) == 2
