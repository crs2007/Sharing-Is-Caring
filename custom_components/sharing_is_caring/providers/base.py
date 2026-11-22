"""Base protocol and errors for Sharing Is Caring share providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..models import AbilityBundle, ShareResult


class ProviderError(Exception):
    """Base error raised by a share provider."""


class ProviderAuthError(ProviderError):
    """Raised when provider credentials are invalid or expired (HTTP 401)."""


class ProviderScopeError(ProviderError):
    """Raised when provider credentials lack required permission/scope (HTTP 403)."""


class ProviderConnectionError(ProviderError):
    """Raised when the remote share provider cannot be reached."""


@dataclass(frozen=True, slots=True)
class TokenValidationResult:
    """Result of validating a user's share provider credentials."""

    username: str
    has_broad_scopes: bool = False
    scopes: tuple[str, ...] = ()


class ShareProvider(ABC):
    """Pluggable destination provider for publishing sanitized AbilityBundles."""

    provider_id: str

    @abstractmethod
    async def async_publish(
        self,
        bundle: AbilityBundle,
        *,
        visibility: str,
    ) -> ShareResult:
        """Publish the exact sanitized bundle and return a ShareResult."""
