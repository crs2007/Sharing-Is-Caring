"""Layers 1 & 3: Structural stripping and deterministic entity/Jinja2 anonymizer."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from ..const import SEVERITY_AUTO_REDACTED, SEVERITY_NEEDS_REVIEW
from ..models import (
    AbilityGraph,
    AuditFinding,
    AuditReport,
    ExternalRole,
    HelperDefinition,
    IncludeRef,
    SanitizedAbility,
    SecretRef,
    ShareableDefinition,
)
from .pii_dictionary import InstancePIIDictionary

# Keys stripped unconditionally from any exported YAML mapping (Layer 1)
_STRIP_STRUCTURAL_KEYS: frozenset[str] = frozenset(
    {
        "id",
        "unique_id",
        "device_id",
        "area_id",
        "floor_id",
        "label_id",
        "entry_id",
        "context",
    }
)

# Keys whose string values should be flagged for user review if non-empty
_FREE_TEXT_REVIEW_KEYS: frozenset[str] = frozenset(
    {"message", "title", "tts_text", "caption", "subtitle"}
)

# Keys representing sensitive credentials/codes that must be redacted immediately
_SENSITIVE_VALUE_KEYS: frozenset[str] = frozenset(
    {
        "code",
        "pin",
        "password",
        "passcode",
        "token",
        "api_key",
        "apikey",
        "secret",
        "authorization",
        "webhook_id",
        "chat_id",
        "phone",
        "phone_number",
        "recipient",
        "email",
    }
)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")
    return slug or "shared_ability"


def _domain_role_label(domain: str, index: int) -> str:
    pretty = domain.replace("_", " ").title()
    return f"{pretty} {index}"


class EntityAnonymizer:
    """Deterministically maps external entities and PII-bearing helpers to clean generic names."""

    def __init__(
        self,
        graph: AbilityGraph,
        pii_dict: InstancePIIDictionary,
        audit: AuditReport,
    ) -> None:
        self._graph = graph
        self._pii = pii_dict
        self._audit = audit
        self.entity_map: dict[str, str] = {}
        self.external_roles: list[ExternalRole] = []
        self._domain_counters: dict[str, int] = {}
        self._used_helper_slugs: set[str] = set()
        self._build_mappings()

    def _next_index(self, domain: str) -> int:
        count = self._domain_counters.get(domain, 0) + 1
        self._domain_counters[domain] = count
        return count

    def _build_mappings(self) -> None:
        # 1. Bundled helpers: preserve semantic slug, stripping only personal PII tokens
        for helper in self._graph.helpers:
            cleaned_slug, changed = self._pii.strip_from_slug(helper.object_id)
            candidate = cleaned_slug
            suffix = 2
            while f"{helper.domain}.{candidate}" in self._used_helper_slugs:
                candidate = f"{cleaned_slug}_{suffix}"
                suffix += 1
            new_eid = f"{helper.domain}.{candidate}"
            self._used_helper_slugs.add(new_eid)
            self.entity_map[helper.entity_id] = new_eid
            if changed:
                self._audit.add(
                    AuditFinding(
                        severity=SEVERITY_AUTO_REDACTED,
                        category="helper_slug_pii",
                        location=helper.entity_id,
                        message="Removed personal term from bundled helper slug.",
                        replacement=new_eid,
                    )
                )

        # 2. Companion scripts: preserve semantic slug, stripping personal PII tokens
        for script in self._graph.companion_scripts:
            cleaned_slug, changed = self._pii.strip_from_slug(script.object_id)
            new_eid = f"script.{cleaned_slug}"
            self.entity_map[script.entity_id] = new_eid
            if changed:
                self._audit.add(
                    AuditFinding(
                        severity=SEVERITY_AUTO_REDACTED,
                        category="script_slug_pii",
                        location=script.entity_id,
                        message="Removed personal term from companion script slug.",
                        replacement=new_eid,
                    )
                )

        # 3. External entities: ALWAYS anonymize into generic role placeholders
        for ext_eid in self._graph.external_entities:
            if "." not in ext_eid:
                continue
            domain, _obj_id = ext_eid.split(".", 1)
            idx = self._next_index(domain)
            if domain == "notify":
                placeholder = f"notify.mobile_app_your_device_{idx}" if idx > 1 else "notify.mobile_app_your_device"
                input_key = f"notify_service_{idx}" if idx > 1 else "notify_service"
            else:
                placeholder = f"{domain}.example_{domain}_{idx}"
                input_key = f"target_{domain}_{idx}"

            self.entity_map[ext_eid] = placeholder
            self.external_roles.append(
                ExternalRole(
                    placeholder_entity_id=placeholder,
                    blueprint_input_key=input_key,
                    domain=domain,
                    label=_domain_role_label(domain, idx),
                )
            )
            self._audit.add(
                AuditFinding(
                    severity=SEVERITY_AUTO_REDACTED,
                    category="external_entity_anonymized",
                    location=ext_eid,
                    message=f"Anonymized external {domain} entity into generic placeholder.",
                    replacement=placeholder,
                )
            )

    def rewrite_string(self, text: str, location: str, *, key_name: str = "") -> str:
        """Rewrite entity IDs (including in Jinja2 templates) and strip Instance PII."""
        result = text

        # Rewrite entity references (longest entity_id first to prevent partial prefix collisions)
        for old_eid in sorted(self.entity_map.keys(), key=len, reverse=True):
            new_eid = self.entity_map[old_eid]
            if old_eid == new_eid:
                continue
            # Direct entity_id match
            pattern = re.compile(rf"(?<![a-zA-Z0-9_]){re.escape(old_eid)}(?![a-zA-Z0-9_])")
            result = pattern.sub(new_eid, result)
            # Jinja2 states.domain.object_id syntax
            old_dom, old_obj = old_eid.split(".", 1)
            new_dom, new_obj = new_eid.split(".", 1)
            attr_pattern = re.compile(
                rf"\bstates\.{re.escape(old_dom)}\.{re.escape(old_obj)}(?![a-zA-Z0-9_])"
            )
            result = attr_pattern.sub(f"states.{new_dom}.{new_obj}", result)

        # Strip instance PII terms & URLs
        result, pii_hits = self._pii.redact_text(result)
        for hit_cat in set(pii_hits):
            self._audit.add(
                AuditFinding(
                    severity=SEVERITY_AUTO_REDACTED,
                    category=hit_cat,
                    location=location,
                    message=f"Redacted Home Assistant instance personal data ({hit_cat}).",
                    replacement="<REDACTED_PERSONAL>",
                )
            )

        # Flag free-text notification/TTS messages for user review
        if key_name in _FREE_TEXT_REVIEW_KEYS and result.strip():
            preview_snippet = result if len(result) <= 80 else f"{result[:77]}..."
            self._audit.add(
                AuditFinding(
                    severity=SEVERITY_NEEDS_REVIEW,
                    category="free_text_message",
                    location=location,
                    message="Review free-text message/title to ensure it contains no personal details.",
                    snippet=preview_snippet,
                )
            )

        return result

    def sanitize_structure(
        self,
        obj: Any,
        location: str,
        *,
        text_overrides: dict[str, str] | None = None,
    ) -> Any:
        """Recursively strip Layer 1 structural metadata and rewrite Layer 2/3 references."""
        if isinstance(obj, SecretRef):
            placeholder = obj.placeholder()
            self._audit.add(
                AuditFinding(
                    severity=SEVERITY_AUTO_REDACTED,
                    category="secret_reference",
                    location=location,
                    message="Replaced !secret reference with placeholder without reading secrets.yaml.",
                    replacement=placeholder,
                )
            )
            return placeholder

        if isinstance(obj, IncludeRef):
            placeholder = f"<REMOVED_{obj.tag.lstrip('!').upper()}>"
            self._audit.add(
                AuditFinding(
                    severity=SEVERITY_NEEDS_REVIEW,
                    category="include_reference",
                    location=location,
                    message=f"Removed external YAML directive '{obj.tag}'. Verify exported logic is complete.",
                    replacement=placeholder,
                )
            )
            return placeholder

        if isinstance(obj, dict):
            cleaned_dict: dict[str, Any] = {}

            # Detect hardware-bound device triggers/conditions/actions
            is_device_block = (
                obj.get("platform") == "device"
                or obj.get("trigger") == "device"
                or obj.get("condition") == "device"
                or ("device_id" in obj and "type" in obj and "domain" in obj)
            )
            if is_device_block:
                self._audit.add(
                    AuditFinding(
                        severity=SEVERITY_NEEDS_REVIEW,
                        category="hardware_device_block",
                        location=location,
                        message=(
                            "Stripped hardware-specific device_id from device trigger/condition/action. "
                            "Replace with a state/action trigger or update the placeholder on import."
                        ),
                        replacement="<YOUR_DEVICE_ID>",
                    )
                )

            for raw_key, raw_val in obj.items():
                key = str(raw_key)
                key_lower = key.lower()
                child_loc = f"{location}.{key}"

                if key_lower in _STRIP_STRUCTURAL_KEYS:
                    if key_lower == "device_id" and is_device_block:
                        cleaned_dict[key] = "<YOUR_DEVICE_ID>"
                    elif key_lower in ("area_id", "floor_id", "label_id"):
                        cleaned_dict[key] = f"<YOUR_{key_lower.upper()}>"
                        self._audit.add(
                            AuditFinding(
                                severity=SEVERITY_AUTO_REDACTED,
                                category="ha_registry_id",
                                location=child_loc,
                                message=f"Replaced local Home Assistant {key_lower} with placeholder.",
                                replacement=f"<YOUR_{key_lower.upper()}>",
                            )
                        )
                    else:
                        self._audit.add(
                            AuditFinding(
                                severity=SEVERITY_AUTO_REDACTED,
                                category="internal_ha_id",
                                location=child_loc,
                                message=f"Stripped internal Home Assistant metadata key '{key}'.",
                            )
                        )
                    continue

                if key_lower in _SENSITIVE_VALUE_KEYS and raw_val not in (None, ""):
                    placeholder = f"<YOUR_{key_lower.upper()}>"
                    cleaned_dict[key] = placeholder
                    self._audit.add(
                        AuditFinding(
                            severity=SEVERITY_AUTO_REDACTED,
                            category="sensitive_field",
                            location=child_loc,
                            message=f"Redacted sensitive field '{key}'.",
                            replacement=placeholder,
                        )
                    )
                    continue

                # Apply inline user override for reviewable free-text fields before rewriting
                if (
                    text_overrides
                    and child_loc in text_overrides
                    and isinstance(raw_val, str)
                ):
                    raw_val = text_overrides[child_loc]

                if isinstance(raw_val, str):
                    cleaned_dict[key] = self.rewrite_string(
                        raw_val, child_loc, key_name=key_lower
                    )
                else:
                    cleaned_dict[key] = self.sanitize_structure(
                        raw_val, child_loc, text_overrides=text_overrides
                    )

            return cleaned_dict

        if isinstance(obj, list):
            return [
                self.sanitize_structure(
                    item, f"{location}[{idx}]", text_overrides=text_overrides
                )
                for idx, item in enumerate(obj)
            ]

        if isinstance(obj, str):
            return self.rewrite_string(obj, location)

        return deepcopy(obj)


def sanitize_ability_graph(
    graph: AbilityGraph,
    pii_dict: InstancePIIDictionary,
    audit: AuditReport,
    *,
    title_override: str | None = None,
    description_override: str | None = None,
    text_overrides: dict[str, str] | None = None,
) -> SanitizedAbility:
    """Run Layers 1-3 across the root automation/script, helpers, and companion scripts."""
    anonymizer = EntityAnonymizer(graph, pii_dict, audit)

    sanitized_root = anonymizer.sanitize_structure(
        graph.root.config,
        graph.root.domain,
        text_overrides=text_overrides,
    )

    raw_title = (title_override or graph.root.alias or graph.root.object_id).strip()
    clean_title = anonymizer.rewrite_string(raw_title, f"{graph.root.domain}.alias")
    if isinstance(sanitized_root, dict):
        sanitized_root["alias"] = clean_title

    raw_desc = (
        description_override
        if description_override is not None
        else graph.root.description
    ).strip()
    clean_desc = (
        anonymizer.rewrite_string(raw_desc, f"{graph.root.domain}.description")
        if raw_desc
        else ""
    )
    if isinstance(sanitized_root, dict) and clean_desc:
        sanitized_root["description"] = clean_desc

    # Sanitize bundled helpers
    sanitized_helpers: list[HelperDefinition] = []
    for helper in graph.helpers:
        new_eid = anonymizer.entity_map.get(helper.entity_id, helper.entity_id)
        new_dom, new_obj = new_eid.split(".", 1)
        helper_cfg = deepcopy(helper.config)
        # Layer 1 extra guard: NEVER keep initial value on input_text (could hold PIN/password/message)
        if helper.domain == "input_text":
            if "initial" in helper_cfg:
                helper_cfg.pop("initial", None)
                audit.add(
                    AuditFinding(
                        severity=SEVERITY_AUTO_REDACTED,
                        category="input_text_initial",
                        location=f"helper.{new_eid}.initial",
                        message="Stripped initial value from input_text helper to prevent data leakage.",
                    )
                )
            if helper_cfg.get("mode") == "password":
                audit.add(
                    AuditFinding(
                        severity=SEVERITY_NEEDS_REVIEW,
                        category="password_helper",
                        location=f"helper.{new_eid}",
                        message="Bundled input_text helper uses password mode (value stripped; schema only).",
                    )
                )

        sanitized_cfg = anonymizer.sanitize_structure(
            helper_cfg,
            f"helper.{new_eid}",
            text_overrides=text_overrides,
        )
        sanitized_helpers.append(
            HelperDefinition(
                entity_id=new_eid,
                domain=new_dom,
                object_id=new_obj,
                source_type=helper.source_type,
                config=sanitized_cfg,
                name=str(sanitized_cfg.get("name")) if sanitized_cfg.get("name") else None,
            )
        )

    # Sanitize companion scripts
    sanitized_scripts: list[ShareableDefinition] = []
    for script in graph.companion_scripts:
        new_eid = anonymizer.entity_map.get(script.entity_id, script.entity_id)
        _, new_obj = new_eid.split(".", 1)
        sanitized_cfg = anonymizer.sanitize_structure(
            script.config,
            f"script.{new_obj}",
            text_overrides=text_overrides,
        )
        sanitized_alias = anonymizer.rewrite_string(script.alias, f"script.{new_obj}.alias")
        if isinstance(sanitized_cfg, dict):
            sanitized_cfg["alias"] = sanitized_alias
        sanitized_scripts.append(
            ShareableDefinition(
                entity_id=new_eid,
                domain="script",
                object_id=new_obj,
                alias=sanitized_alias,
                description=str(sanitized_cfg.get("description", ""))
                if isinstance(sanitized_cfg, dict)
                else "",
                config=sanitized_cfg,
            )
        )

    # Blueprint eligibility: single automation or script (no companion scripts required)
    blueprint_eligible = graph.root.domain in ("automation", "script")

    slug = _slugify(clean_title)
    return SanitizedAbility(
        slug=slug,
        title=clean_title,
        description=clean_desc,
        root_domain=graph.root.domain,
        root_config=sanitized_root,
        helpers=sanitized_helpers,
        companion_scripts=sanitized_scripts,
        external_roles=anonymizer.external_roles,
        entity_map=anonymizer.entity_map,
        blueprint_eligible=blueprint_eligible,
        audit=audit,
    )
