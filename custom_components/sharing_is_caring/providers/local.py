"""Local copy / download share provider (zero cloud traffic, zero credentials required)."""

from __future__ import annotations

from ..const import PROVIDER_LOCAL
from ..models import AbilityBundle, ShareResult
from .base import ShareProvider


class LocalExportProvider(ShareProvider):
    """Returns the sanitized bundle locally without making any outbound network requests."""

    provider_id = PROVIDER_LOCAL

    async def async_publish(
        self,
        bundle: AbilityBundle,
        *,
        visibility: str = "local",
    ) -> ShareResult:
        return ShareResult(
            provider=self.provider_id,
            share_url=None,
            visibility="local",
            files=dict(bundle.files),
        )
