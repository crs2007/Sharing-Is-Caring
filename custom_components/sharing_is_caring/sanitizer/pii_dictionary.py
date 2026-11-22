"""Layer 2: Dynamic Home Assistant Instance PII Dictionary builder."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

# Common English / Home Assistant words that must NEVER be added as generic PII redactions
_SAFE_STOPWORDS: frozenset[str] = frozenset(
    {
        "home",
        "house",
        "work",
        "office",
        "away",
        "zone",
        "person",
        "phone",
        "mobile",
        "app",
        "pixel",
        "iphone",
        "android",
        "tablet",
        "watch",
        "laptop",
        "light",
        "lights",
        "switch",
        "sensor",
        "binary",
        "script",
        "automation",
        "helper",
        "input",
        "boolean",
        "number",
        "text",
        "select",
        "timer",
        "counter",
        "schedule",
        "living",
        "bedroom",
        "kitchen",
        "bathroom",
        "garage",
        "hallway",
        "front",
        "back",
        "door",
        "window",
        "motion",
        "notify",
        "admin",
        "user",
        "guest",
        "local",
        "localhost",
        "assistant",
        "default",
        "main",
        "state",
        "true",
        "false",
        "none",
        "open",
        "closed",
        "start",
        "stop",
        "turn",
        "data",
        "message",
        "title",
    }
)


@dataclass(slots=True)
class InstancePIIDictionary:
    """In-memory redaction dictionary derived from the local HA instance and user overrides."""

    terms: list[str] = field(default_factory=list)
    exact_urls: list[str] = field(default_factory=list)
    coordinates: list[tuple[float, float]] = field(default_factory=list)
    _term_patterns: list[tuple[str, re.Pattern[str]]] = field(default_factory=list, repr=False)

    def compile(self) -> None:
        """Compile case-insensitive boundary-aware patterns (longest terms first)."""
        unique_terms = sorted(
            {t.strip() for t in self.terms if len(t.strip()) >= 3},
            key=len,
            reverse=True,
        )
        self.terms = unique_terms
        self._term_patterns = []
        for term in unique_terms:
            # Match either whole word or underscore-delimited slug segment
            escaped = re.escape(term)
            pattern = re.compile(rf"(?<![a-zA-Z0-9]){escaped}(?![a-zA-Z0-9])", re.IGNORECASE)
            self._term_patterns.append((term, pattern))

    def redact_text(self, text: str, replacement: str = "<REDACTED_PERSONAL>") -> tuple[str, list[str]]:
        """Redact any instance URLs or PII terms found in text; returns (redacted, matched_categories)."""
        matches: list[str] = []
        result = text

        for url in self.exact_urls:
            if url and url.lower() in result.lower():
                result = re.sub(re.escape(url), "<REDACTED_INSTANCE_URL>", result, flags=re.IGNORECASE)
                matches.append("instance_url")

        for _term, pattern in self._term_patterns:
            if pattern.search(result):
                result = pattern.sub(replacement, result)
                matches.append("instance_pii")

        return result, matches

    def strip_from_slug(self, slug: str) -> tuple[str, bool]:
        """Strip personal PII tokens from an entity object_id/slug while keeping it valid."""
        parts = [p for p in slug.split("_") if p]
        lowered_terms = {t.lower() for t in self.terms}
        changed = False
        kept: list[str] = []
        for part in parts:
            if part.lower() in lowered_terms:
                changed = True
                continue
            kept.append(part)
        cleaned = "_".join(kept) if kept else "helper_item"
        return cleaned, changed


def _add_candidate_term(terms: set[str], value: str) -> None:
    cleaned = value.strip()
    if len(cleaned) < 3:
        return
    if cleaned.lower() in _SAFE_STOPWORDS:
        return
    terms.add(cleaned)
    # Also add individual non-stopword tokens (e.g. "Sharon Rimer" -> "Sharon", "Rimer")
    for token in re.split(r"[\s_\-.']+", cleaned):
        if len(token) >= 3 and token.lower() not in _SAFE_STOPWORDS:
            terms.add(token)


def build_instance_pii_dictionary(
    hass: Any,
    custom_redactions: list[str] | None = None,
) -> InstancePIIDictionary:
    """Inspect local HA config & states in-memory to build a dynamic PII redaction dictionary."""
    terms: set[str] = set()
    urls: set[str] = set()
    coords: list[tuple[float, float]] = []

    config = getattr(hass, "config", None)
    if config is not None:
        loc_name = getattr(config, "location_name", None)
        if isinstance(loc_name, str) and loc_name.strip().lower() != "home":
            _add_candidate_term(terms, loc_name)

        for attr in ("external_url", "internal_url"):
            url_val = getattr(config, attr, None)
            if isinstance(url_val, str) and url_val.strip():
                urls.add(url_val.strip().rstrip("/"))
                parsed = urlparse(url_val.strip())
                if parsed.hostname and parsed.hostname not in ("localhost", "127.0.0.1"):
                    urls.add(parsed.hostname)

        lat = getattr(config, "latitude", None)
        lon = getattr(config, "longitude", None)
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            coords.append((float(lat), float(lon)))

    states = getattr(hass, "states", None)
    if states is not None and hasattr(states, "async_all"):
        for state in states.async_all():
            eid = getattr(state, "entity_id", "")
            attrs = getattr(state, "attributes", {}) or {}
            if "." not in eid:
                continue
            domain, obj_id = eid.split(".", 1)
            friendly = str(attrs.get("friendly_name", ""))

            if domain == "person":
                _add_candidate_term(terms, obj_id)
                if friendly:
                    _add_candidate_term(terms, friendly)
            elif domain == "zone":
                if obj_id != "home":
                    _add_candidate_term(terms, obj_id)
                if friendly and friendly.lower() != "home":
                    _add_candidate_term(terms, friendly)
                z_lat, z_lon = attrs.get("latitude"), attrs.get("longitude")
                if isinstance(z_lat, (int, float)) and isinstance(z_lon, (int, float)):
                    coords.append((float(z_lat), float(z_lon)))
            elif domain == "device_tracker":
                _add_candidate_term(terms, obj_id)
            elif domain == "notify" and obj_id.startswith("mobile_app_"):
                suffix = obj_id.removeprefix("mobile_app_")
                _add_candidate_term(terms, suffix)

    # Always honor explicit user-supplied custom redaction terms (even short ones >= 2 chars)
    if custom_redactions:
        for custom in custom_redactions:
            c_clean = custom.strip()
            if len(c_clean) >= 2:
                terms.add(c_clean)

    dictionary = InstancePIIDictionary(
        terms=list(terms),
        exact_urls=sorted(urls, key=len, reverse=True),
        coordinates=coords,
    )
    dictionary.compile()
    return dictionary
