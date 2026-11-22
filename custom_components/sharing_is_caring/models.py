"""Data models for Sharing Is Caring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import (
    AUDIT_STATUS_BLOCKED,
    AUDIT_STATUS_CLEAN,
    AUDIT_STATUS_NEEDS_REVIEW,
    SEVERITY_AUTO_REDACTED,
    SEVERITY_BLOCKED,
    SEVERITY_NEEDS_REVIEW,
)


@dataclass(frozen=True, slots=True)
class SecretRef:
    """Sentinel representing an unresolved YAML `!secret` tag."""

    key: str

    def placeholder(self) -> str:
        """Return safe placeholder string for export."""
        safe_key = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in self.key).upper()
        return f"<YOUR_SECRET_{safe_key or 'VALUE'}>"


@dataclass(frozen=True, slots=True)
class IncludeRef:
    """Sentinel representing an unresolved YAML `!include*` or `!env_var` tag."""

    tag: str
    value: str


@dataclass(slots=True)
class HelperDefinition:
    """Extracted definition of a Home Assistant helper (schema only, no runtime state)."""

    entity_id: str
    domain: str
    object_id: str
    source_type: str  # "storage", "config_entry", or "yaml"
    config: dict[str, Any]
    name: str | None = None


@dataclass(slots=True)
class ShareableDefinition:
    """Extracted raw definition of an automation or script."""

    entity_id: str
    domain: str  # "automation" or "script"
    object_id: str
    alias: str
    config: dict[str, Any]
    description: str = ""


@dataclass(slots=True)
class AbilityGraph:
    """Full dependency graph for a shareable automation or script."""

    root: ShareableDefinition
    helpers: list[HelperDefinition] = field(default_factory=list)
    companion_scripts: list[ShareableDefinition] = field(default_factory=list)
    external_entities: list[str] = field(default_factory=list)
    unresolved_references: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AuditFinding:
    """Single privacy/security finding produced during sanitization."""

    severity: str  # auto_redacted | needs_review | blocked
    category: str
    location: str
    message: str
    replacement: str | None = None
    snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize finding for API responses (never containing raw secrets)."""
        return {
            "severity": self.severity,
            "category": self.category,
            "location": self.location,
            "message": self.message,
            "replacement": self.replacement,
            "snippet": self.snippet,
        }


@dataclass(slots=True)
class AuditReport:
    """Aggregated security audit report for a sanitized bundle."""

    findings: list[AuditFinding] = field(default_factory=list)

    @property
    def auto_redacted(self) -> list[AuditFinding]:
        return [f for f in self.findings if f.severity == SEVERITY_AUTO_REDACTED]

    @property
    def needs_review(self) -> list[AuditFinding]:
        return [f for f in self.findings if f.severity == SEVERITY_NEEDS_REVIEW]

    @property
    def blocked(self) -> list[AuditFinding]:
        return [f for f in self.findings if f.severity == SEVERITY_BLOCKED]

    @property
    def status(self) -> str:
        if self.blocked:
            return AUDIT_STATUS_BLOCKED
        if self.needs_review:
            return AUDIT_STATUS_NEEDS_REVIEW
        return AUDIT_STATUS_CLEAN

    @property
    def can_publish(self) -> bool:
        return not self.blocked

    def add(self, finding: AuditFinding) -> None:
        self.findings.append(finding)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "can_publish": self.can_publish,
            "counts": {
                "auto_redacted": len(self.auto_redacted),
                "needs_review": len(self.needs_review),
                "blocked": len(self.blocked),
            },
            "auto_redacted": [f.to_dict() for f in self.auto_redacted],
            "needs_review": [f.to_dict() for f in self.needs_review],
            "blocked": [f.to_dict() for f in self.blocked],
        }


@dataclass(slots=True)
class ExternalRole:
    """Anonymized external entity role exposed to recipients."""

    placeholder_entity_id: str
    blueprint_input_key: str
    domain: str
    label: str
    usage_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "placeholder_entity_id": self.placeholder_entity_id,
            "blueprint_input_key": self.blueprint_input_key,
            "domain": self.domain,
            "label": self.label,
            "usage_count": self.usage_count,
        }


@dataclass(slots=True)
class SanitizedAbility:
    """Result of sanitizing an AbilityGraph (contains zero sensitive data)."""

    slug: str
    title: str
    description: str
    root_domain: str
    root_config: dict[str, Any]
    helpers: list[HelperDefinition]
    companion_scripts: list[ShareableDefinition]
    external_roles: list[ExternalRole]
    entity_map: dict[str, str]  # Internal only (never serialized to shared output!)
    blueprint_eligible: bool
    audit: AuditReport


@dataclass(slots=True)
class AbilityBundle:
    """Final multi-file sanitized bundle ready for preview and publishing."""

    slug: str
    title: str
    description: str
    files: dict[str, str]  # filename -> UTF-8 content
    audit: AuditReport
    preview_hash: str
    blueprint_filename: str | None = None
    package_filename: str = ""
    dependencies_summary: dict[str, Any] = field(default_factory=dict)

    def to_preview_dict(self) -> dict[str, Any]:
        """Serialize bundle for preview API responses."""
        return {
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "files": self.files,
            "package_filename": self.package_filename,
            "blueprint_filename": self.blueprint_filename,
            "dependencies": self.dependencies_summary,
            "audit": self.audit.to_dict(),
            "preview_hash": self.preview_hash,
        }


@dataclass(frozen=True, slots=True)
class ShareResult:
    """Outcome of publishing an AbilityBundle via a ShareProvider."""

    provider: str
    share_url: str | None
    visibility: str
    files: dict[str, str]
    raw_blueprint_url: str | None = None
    my_ha_import_url: str | None = None
    gist_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "share_url": self.share_url,
            "visibility": self.visibility,
            "raw_blueprint_url": self.raw_blueprint_url,
            "my_ha_import_url": self.my_ha_import_url,
            "gist_id": self.gist_id,
            "files": self.files,
        }
