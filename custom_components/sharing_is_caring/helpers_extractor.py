"""Extract Home Assistant helper definitions (schema only, zero runtime state)."""

from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .const import CONFIG_ENTRY_HELPER_DOMAINS, STORAGE_HELPER_DOMAINS
from .models import HelperDefinition
from .yaml_loader import load_yaml_file_no_secrets

_LOGGER = logging.getLogger(__name__)

# Fields allowed per storage helper domain (allowlist-first: never copy internal IDs or live state)
_STORAGE_HELPER_ALLOWED_FIELDS: dict[str, frozenset[str]] = {
    "input_boolean": frozenset({"name", "icon", "initial"}),
    "input_button": frozenset({"name", "icon"}),
    "input_datetime": frozenset({"name", "icon", "has_date", "has_time"}),
    "input_number": frozenset(
        {"name", "icon", "min", "max", "step", "mode", "unit_of_measurement", "initial"}
    ),
    "input_select": frozenset({"name", "icon", "options", "initial"}),
    "input_text": frozenset({"name", "icon", "min", "max", "pattern", "mode"}),  # initial stripped!
    "counter": frozenset({"name", "icon", "initial", "minimum", "maximum", "step", "restore"}),
    "timer": frozenset({"name", "icon", "duration", "restore"}),
    "schedule": frozenset(
        {
            "name",
            "icon",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }
    ),
}

# Config-entry helper keys that are safe schema fields (never copy entry_id, unique_id, device_id)
_CONFIG_ENTRY_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "entry_id",
        "unique_id",
        "device_id",
        "area_id",
        "floor_id",
        "label_id",
        "token",
        "api_key",
        "password",
        "username",
        "secret",
        "webhook_id",
    }
)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")
    return slug or "helper"


def _read_json_file(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError) as err:
        _LOGGER.debug("Could not read storage file %s: %s", path.name, err)
        return None


def _filter_storage_helper_config(domain: str, raw: dict[str, Any]) -> dict[str, Any]:
    allowed = _STORAGE_HELPER_ALLOWED_FIELDS.get(domain, frozenset({"name", "icon"}))
    return {k: deepcopy(v) for k, v in raw.items() if k in allowed and v is not None}


def _extract_from_storage_files(
    config_dir: Path,
    entity_ids: set[str],
) -> dict[str, HelperDefinition]:
    """Read storage helper definitions from .storage/<domain> files."""
    found: dict[str, HelperDefinition] = {}
    storage_dir = config_dir / ".storage"
    if not storage_dir.is_dir():
        return found

    by_domain: dict[str, set[str]] = {}
    for eid in entity_ids:
        if "." not in eid:
            continue
        domain, obj_id = eid.split(".", 1)
        if domain in STORAGE_HELPER_DOMAINS:
            by_domain.setdefault(domain, set()).add(obj_id)

    for domain, wanted_ids in by_domain.items():
        storage_data = _read_json_file(storage_dir / domain)
        if not storage_data:
            continue
        items = storage_data.get("data", {}).get("items", [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", "")).strip()
            name_slug = _slugify(str(item.get("name", ""))) if item.get("name") else ""
            matched_obj_id = None
            if item_id in wanted_ids:
                matched_obj_id = item_id
            elif name_slug in wanted_ids:
                matched_obj_id = name_slug
            if matched_obj_id is None:
                continue
            eid = f"{domain}.{matched_obj_id}"
            filtered = _filter_storage_helper_config(domain, item)
            found[eid] = HelperDefinition(
                entity_id=eid,
                domain=domain,
                object_id=matched_obj_id,
                source_type="storage",
                config=filtered,
                name=str(item["name"]) if item.get("name") else None,
            )

    return found


def _extract_from_config_entries(
    hass: Any,
    entity_ids: set[str],
) -> dict[str, HelperDefinition]:
    """Extract config-entry helpers (template, group, threshold, utility_meter, etc.)."""
    found: dict[str, HelperDefinition] = {}
    config_entries_mgr = getattr(hass, "config_entries", None)
    if config_entries_mgr is None:
        return found

    # Map entity_id -> config_entry_id via entity registry when available
    ent_reg_entry_map: dict[str, str] = {}
    try:
        from homeassistant.helpers import entity_registry as er

        ent_reg = er.async_get(hass)
        for eid in entity_ids:
            reg_entry = ent_reg.async_get(eid)
            if reg_entry and reg_entry.config_entry_id:
                ent_reg_entry_map[eid] = reg_entry.config_entry_id
    except Exception:  # noqa: BLE001
        # Running outside full HA Core (e.g. unit tests with mock hass)
        reg_map = getattr(hass, "_test_entity_config_entries", None)
        if isinstance(reg_map, dict):
            ent_reg_entry_map.update(reg_map)

    all_entries = []
    if hasattr(config_entries_mgr, "async_entries"):
        all_entries = list(config_entries_mgr.async_entries())

    entries_by_id = {getattr(e, "entry_id", None): e for e in all_entries}

    for eid in entity_ids:
        if "." not in eid:
            continue
        domain, obj_id = eid.split(".", 1)
        entry = None
        entry_id = ent_reg_entry_map.get(eid)
        if entry_id and entry_id in entries_by_id:
            entry = entries_by_id[entry_id]
        else:
            # Fallback match by title slug for config-entry helpers
            for candidate in all_entries:
                if getattr(candidate, "domain", None) in CONFIG_ENTRY_HELPER_DOMAINS:
                    title_slug = _slugify(str(getattr(candidate, "title", "")))
                    if title_slug == obj_id:
                        entry = candidate
                        break

        if entry is None:
            continue

        entry_domain = str(getattr(entry, "domain", ""))
        if entry_domain not in CONFIG_ENTRY_HELPER_DOMAINS:
            continue

        merged: dict[str, Any] = {}
        raw_options = getattr(entry, "options", None) or {}
        raw_data = getattr(entry, "data", None) or {}
        for src in (raw_data, raw_options):
            if isinstance(src, dict):
                for k, v in src.items():
                    if k.lower() not in _CONFIG_ENTRY_FORBIDDEN_KEYS:
                        merged[k] = deepcopy(v)
        title = getattr(entry, "title", None)
        if title and "name" not in merged:
            merged["name"] = str(title)

        found[eid] = HelperDefinition(
            entity_id=eid,
            domain=entry_domain,
            object_id=obj_id,
            source_type="config_entry",
            config=merged,
            name=str(title) if title else None,
        )

    return found


def _extract_from_yaml_configs(
    config_dir: Path,
    entity_ids: set[str],
) -> dict[str, HelperDefinition]:
    """Fallback extraction from YAML files (configuration.yaml and packages/*.yaml)."""
    found: dict[str, HelperDefinition] = {}
    candidate_files: list[Path] = []
    cfg_yaml = config_dir / "configuration.yaml"
    if cfg_yaml.is_file():
        candidate_files.append(cfg_yaml)
    packages_dir = config_dir / "packages"
    if packages_dir.is_dir():
        candidate_files.extend(sorted(packages_dir.rglob("*.yaml")))

    wanted_by_domain: dict[str, set[str]] = {}
    for eid in entity_ids:
        if "." in eid:
            dom, obj = eid.split(".", 1)
            if dom in STORAGE_HELPER_DOMAINS or dom in CONFIG_ENTRY_HELPER_DOMAINS:
                wanted_by_domain.setdefault(dom, set()).add(obj)

    if not wanted_by_domain:
        return found

    for yaml_path in candidate_files:
        doc = load_yaml_file_no_secrets(yaml_path)
        if not isinstance(doc, dict):
            continue
        for dom, wanted_objs in wanted_by_domain.items():
            section = doc.get(dom)
            if not isinstance(section, dict):
                continue
            for obj_id in wanted_objs:
                eid = f"{dom}.{obj_id}"
                if eid in found or obj_id not in section:
                    continue
                raw_cfg = section[obj_id]
                if not isinstance(raw_cfg, dict):
                    continue
                if dom in STORAGE_HELPER_DOMAINS:
                    cfg = _filter_storage_helper_config(dom, raw_cfg)
                else:
                    cfg = {
                        k: deepcopy(v)
                        for k, v in raw_cfg.items()
                        if k.lower() not in _CONFIG_ENTRY_FORBIDDEN_KEYS
                    }
                found[eid] = HelperDefinition(
                    entity_id=eid,
                    domain=dom,
                    object_id=obj_id,
                    source_type="yaml",
                    config=cfg,
                    name=str(raw_cfg["name"]) if raw_cfg.get("name") else None,
                )

    return found


def extract_helpers_sync(
    hass: Any,
    config_dir: Path,
    entity_ids: set[str],
) -> dict[str, HelperDefinition]:
    """Synchronously extract helper definitions (call via async_add_executor_job)."""
    found = _extract_from_storage_files(config_dir, entity_ids)

    remaining = entity_ids - set(found.keys())
    if remaining:
        found.update(_extract_from_config_entries(hass, remaining))

    remaining = entity_ids - set(found.keys())
    if remaining:
        found.update(_extract_from_yaml_configs(config_dir, remaining))

    return found
