"""Sanitization pipeline orchestrator and byte-exact preview_hash TTL cache."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from ..const import PREVIEW_CACHE_MAX_ENTRIES, PREVIEW_CACHE_TTL_SECONDS
from ..models import AbilityBundle, AbilityGraph, AuditReport, SanitizedAbility
from .anonymizer import sanitize_ability_graph
from .pii_dictionary import build_instance_pii_dictionary
from .scanner import scan_and_scrub_rendered_files


@dataclass(slots=True)
class SanitizeOptions:
    """User-configurable options for previewing and sanitizing an ability."""

    title: str | None = None
    description: str | None = None
    include_companion_scripts: bool = True
    generate_blueprint: bool = True
    custom_redactions: list[str] = field(default_factory=list)
    text_overrides: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class _CachedPreview:
    bundle: AbilityBundle
    expires_at: float


class PreviewCache:
    """In-memory short-TTL cache storing exact sanitized bundles keyed by preview_hash."""

    def __init__(
        self,
        ttl_seconds: int = PREVIEW_CACHE_TTL_SECONDS,
        max_entries: int = PREVIEW_CACHE_MAX_ENTRIES,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._entries: dict[str, _CachedPreview] = {}

    def _prune(self, now: float) -> None:
        expired = [k for k, v in self._entries.items() if v.expires_at <= now]
        for k in expired:
            del self._entries[k]
        if len(self._entries) >= self._max_entries:
            oldest_keys = sorted(
                self._entries.keys(), key=lambda k: self._entries[k].expires_at
            )
            for k in oldest_keys[: max(1, len(self._entries) - self._max_entries + 1)]:
                del self._entries[k]

    def put(self, bundle: AbilityBundle) -> None:
        now = time.monotonic()
        self._prune(now)
        self._entries[bundle.preview_hash] = _CachedPreview(
            bundle=bundle,
            expires_at=now + self._ttl,
        )

    def get(self, preview_hash: str) -> AbilityBundle | None:
        now = time.monotonic()
        entry = self._entries.get(preview_hash)
        if entry is None:
            return None
        if entry.expires_at <= now:
            del self._entries[preview_hash]
            return None
        return entry.bundle

    def clear(self) -> None:
        self._entries.clear()


def compute_bundle_hash(files: dict[str, str]) -> str:
    """Compute a deterministic SHA-256 hash over the exact rendered bundle files."""
    canonical = json.dumps(files, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class SanitizationPipeline:
    """Runs Layers 1-4 and produces byte-exact, hash-verified AbilityBundles."""

    def __init__(self, cache: PreviewCache | None = None) -> None:
        self.cache = cache or PreviewCache()

    def sanitize_graph(
        self,
        hass: Any,
        graph: AbilityGraph,
        options: SanitizeOptions | None = None,
    ) -> tuple[SanitizedAbility, Any]:
        """Run Layers 1-3 on an AbilityGraph and return (SanitizedAbility, InstancePIIDictionary)."""
        opts = options or SanitizeOptions()
        audit = AuditReport()
        pii_dict = build_instance_pii_dictionary(hass, opts.custom_redactions)
        sanitized = sanitize_ability_graph(
            graph,
            pii_dict,
            audit,
            title_override=opts.title,
            description_override=opts.description,
            text_overrides=opts.text_overrides,
        )
        return sanitized, pii_dict

    def finalize_bundle(
        self,
        sanitized: SanitizedAbility,
        pii_dict: Any,
        raw_files: dict[str, str],
        *,
        package_filename: str,
        blueprint_filename: str | None,
    ) -> AbilityBundle:
        """Run Layer 4 final audit scan, compute preview_hash, and cache the exact bundle."""
        scrubbed_files = scan_and_scrub_rendered_files(raw_files, pii_dict, sanitized.audit)
        preview_hash = compute_bundle_hash(scrubbed_files)

        bundle = AbilityBundle(
            slug=sanitized.slug,
            title=sanitized.title,
            description=sanitized.description,
            files=scrubbed_files,
            audit=sanitized.audit,
            preview_hash=preview_hash,
            package_filename=package_filename,
            blueprint_filename=blueprint_filename,
            dependencies_summary={
                "helpers": [
                    {
                        "entity_id": h.entity_id,
                        "domain": h.domain,
                        "name": h.name or h.object_id,
                        "source_type": h.source_type,
                    }
                    for h in sanitized.helpers
                ],
                "companion_scripts": [
                    {"entity_id": s.entity_id, "alias": s.alias}
                    for s in sanitized.companion_scripts
                ],
                "external_roles": [r.to_dict() for r in sanitized.external_roles],
            },
        )
        self.cache.put(bundle)
        return bundle
