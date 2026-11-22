"""Dependency discovery engine for Home Assistant automations, scripts, and helpers."""

from __future__ import annotations

import logging
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from jinja2 import Environment, TemplateSyntaxError

from .const import (
    ALL_HELPER_DOMAINS,
    MAX_COMPANION_SCRIPTS,
    MAX_DEPENDENCY_DEPTH,
    SHAREABLE_DOMAINS,
)
from .helpers_extractor import extract_helpers_sync
from .models import AbilityGraph, HelperDefinition, ShareableDefinition
from .yaml_loader import load_yaml_file_no_secrets

_LOGGER = logging.getLogger(__name__)

# Matches valid Home Assistant entity IDs: domain.object_id
_ENTITY_ID_RE = re.compile(r"\b([a-z][a-z0-9_]{1,31})\.([a-z0-9][a-z0-9_]{0,127})\b")

# Matches Jinja2 state accessors: states('a.b'), is_state("a.b", ...), states.a.b
_JINJA_ENTITY_FUNC_RE = re.compile(
    r"""(?:states|is_state|state_attr|is_state_attr|expand|device_id|area_id|area_name)\(\s*['"]([a-z][a-z0-9_]*\.[a-z0-9_]+)['"]""",
)
_JINJA_STATES_ATTR_RE = re.compile(
    r"""\bstates\.([a-z][a-z0-9_]+)\.([a-z0-9_]+)\b""",
)

# Known Home Assistant domains to avoid false-positive entity_id matches on filenames/floats/etc.
_KNOWN_ENTITY_DOMAINS: frozenset[str] = (
    ALL_HELPER_DOMAINS
    | SHAREABLE_DOMAINS
    | frozenset(
        {
            "alarm_control_panel",
            "binary_sensor",
            "button",
            "calendar",
            "camera",
            "climate",
            "cover",
            "device_tracker",
            "event",
            "fan",
            "humidifier",
            "lawn_mower",
            "light",
            "lock",
            "media_player",
            "notify",
            "number",
            "person",
            "remote",
            "scene",
            "select",
            "sensor",
            "siren",
            "sun",
            "switch",
            "text",
            "time",
            "todo",
            "tts",
            "update",
            "vacuum",
            "valve",
            "water_heater",
            "weather",
            "zone",
        }
    )
)

# Standard service verbs that should NOT be mistaken for script/entity IDs when under service/action
_STANDARD_SCRIPT_SERVICES: frozenset[str] = frozenset(
    {"turn_on", "turn_off", "toggle", "reload"}
)

_JINJA_ENV = Environment(autoescape=False)  # noqa: S701


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_") or "ability"


def extract_entity_references_from_template(template_str: str) -> set[str]:
    """Extract Home Assistant entity IDs referenced inside a Jinja2 template string."""
    refs: set[str] = set()
    if "{{" not in template_str and "{%" not in template_str:
        return refs

    # Validate syntax via Jinja2 parser when possible, then extract patterns safely
    try:
        _JINJA_ENV.parse(template_str)
    except TemplateSyntaxError:
        _LOGGER.debug("Template syntax warning during static reference scan; falling back to regex")

    for match in _JINJA_ENTITY_FUNC_RE.finditer(template_str):
        candidate = match.group(1)
        domain = candidate.split(".", 1)[0]
        if domain in _KNOWN_ENTITY_DOMAINS:
            refs.add(candidate)

    for match in _JINJA_STATES_ATTR_RE.finditer(template_str):
        domain, obj_id = match.group(1), match.group(2)
        if domain in _KNOWN_ENTITY_DOMAINS:
            refs.add(f"{domain}.{obj_id}")

    # Also catch quoted entity_ids inside arrays like expand(['light.a', 'light.b'])
    for match in re.finditer(r"""['"]([a-z][a-z0-9_]*\.[a-z0-9_]+)['"]""", template_str):
        candidate = match.group(1)
        domain = candidate.split(".", 1)[0]
        if domain in _KNOWN_ENTITY_DOMAINS:
            refs.add(candidate)

    return refs


def collect_entity_references(obj: Any, parent_key: str = "") -> set[str]:
    """Recursively collect all entity IDs referenced in a YAML config dict/list."""
    refs: set[str] = set()

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key).lower()
            # Direct action/service calls to a script (e.g. action: script.my_custom_script)
            if key_str in ("service", "action") and isinstance(value, str):
                parts = value.strip().split(".", 1)
                if len(parts) == 2:
                    svc_domain, svc_name = parts
                    if svc_domain == "script" and svc_name not in _STANDARD_SCRIPT_SERVICES:
                        refs.add(f"script.{svc_name}")
                    elif svc_domain == "notify":
                        refs.add(f"notify.{svc_name}")
            else:
                refs.update(collect_entity_references(value, parent_key=key_str))
        return refs

    if isinstance(obj, list):
        for item in obj:
            refs.update(collect_entity_references(item, parent_key=parent_key))
        return refs

    if isinstance(obj, str):
        text = obj.strip()
        if "{{" in text or "{%" in text:
            refs.update(extract_entity_references_from_template(text))
            return refs

        # Direct entity_id field or list of entity_ids
        if parent_key in ("entity_id", "entities", "source", "entity", "source_entity"):
            for part in text.split(","):
                candidate = part.strip()
                if _ENTITY_ID_RE.fullmatch(candidate):
                    dom = candidate.split(".", 1)[0]
                    if dom in _KNOWN_ENTITY_DOMAINS:
                        refs.add(candidate)
        elif _ENTITY_ID_RE.fullmatch(text):
            dom = text.split(".", 1)[0]
            if dom in _KNOWN_ENTITY_DOMAINS and parent_key not in (
                "service",
                "action",
                "platform",
                "domain",
                "alias",
                "name",
                "description",
                "message",
                "title",
            ):
                refs.add(text)

    return refs


def _load_automations_from_disk(config_dir: Path) -> list[dict[str, Any]]:
    """Load raw automation dicts from automations.yaml and packages/*.yaml."""
    automations: list[dict[str, Any]] = []

    auto_file = config_dir / "automations.yaml"
    data = load_yaml_file_no_secrets(auto_file)
    if isinstance(data, list):
        automations.extend(item for item in data if isinstance(item, dict))

    packages_dir = config_dir / "packages"
    if packages_dir.is_dir():
        for pkg_path in sorted(packages_dir.rglob("*.yaml")):
            pkg_doc = load_yaml_file_no_secrets(pkg_path)
            if not isinstance(pkg_doc, dict):
                continue
            pkg_autos = pkg_doc.get("automation")
            if isinstance(pkg_autos, list):
                automations.extend(item for item in pkg_autos if isinstance(item, dict))
            elif isinstance(pkg_autos, dict):
                automations.append(pkg_autos)

    return automations


def _load_scripts_from_disk(config_dir: Path) -> dict[str, dict[str, Any]]:
    """Load raw script dicts keyed by object_id from scripts.yaml and packages/*.yaml."""
    scripts: dict[str, dict[str, Any]] = {}

    script_file = config_dir / "scripts.yaml"
    data = load_yaml_file_no_secrets(script_file)
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, dict):
                scripts[str(key)] = val

    packages_dir = config_dir / "packages"
    if packages_dir.is_dir():
        for pkg_path in sorted(packages_dir.rglob("*.yaml")):
            pkg_doc = load_yaml_file_no_secrets(pkg_path)
            if not isinstance(pkg_doc, dict):
                continue
            pkg_scripts = pkg_doc.get("script")
            if isinstance(pkg_scripts, dict):
                for key, val in pkg_scripts.items():
                    if isinstance(val, dict) and str(key) not in scripts:
                        scripts[str(key)] = val

    return scripts


def _find_automation_definition(
    hass: Any,
    config_dir: Path,
    entity_id: str,
) -> ShareableDefinition | None:
    """Locate the raw config dict for a specific automation entity_id."""
    _, obj_id = entity_id.split(".", 1)
    state = hass.states.get(entity_id) if getattr(hass, "states", None) else None
    state_id = str(state.attributes.get("id", "")) if state and state.attributes else ""
    friendly_name = (
        str(state.attributes.get("friendly_name", "")) if state and state.attributes else ""
    )

    for raw in _load_automations_from_disk(config_dir):
        raw_id = str(raw.get("id", ""))
        raw_alias = str(raw.get("alias", ""))
        if (
            (state_id and raw_id == state_id)
            or (raw_alias and _slugify(raw_alias) == obj_id)
            or (raw_id and _slugify(raw_id) == obj_id)
            or (friendly_name and raw_alias == friendly_name)
        ):
            return ShareableDefinition(
                entity_id=entity_id,
                domain="automation",
                object_id=obj_id,
                alias=raw_alias or friendly_name or obj_id.replace("_", " ").title(),
                description=str(raw.get("description", "")),
                config=deepcopy(raw),
            )

    # Fallback: check in-memory automation component entities (for YAML/UI loaded configs)
    auto_comp = hass.data.get("automation") if isinstance(getattr(hass, "data", None), dict) else None
    if auto_comp and hasattr(auto_comp, "get_entity"):
        ent = auto_comp.get_entity(entity_id)
        raw_cfg = getattr(ent, "raw_config", None) if ent else None
        if isinstance(raw_cfg, dict):
            alias = str(raw_cfg.get("alias", friendly_name or obj_id))
            return ShareableDefinition(
                entity_id=entity_id,
                domain="automation",
                object_id=obj_id,
                alias=alias,
                description=str(raw_cfg.get("description", "")),
                config=deepcopy(raw_cfg),
            )

    return None


def _find_script_definition(
    hass: Any,
    config_dir: Path,
    entity_id: str,
) -> ShareableDefinition | None:
    """Locate the raw config dict for a specific script entity_id."""
    _, obj_id = entity_id.split(".", 1)
    scripts = _load_scripts_from_disk(config_dir)
    if obj_id in scripts:
        raw = scripts[obj_id]
        alias = str(raw.get("alias", obj_id.replace("_", " ").title()))
        return ShareableDefinition(
            entity_id=entity_id,
            domain="script",
            object_id=obj_id,
            alias=alias,
            description=str(raw.get("description", "")),
            config=deepcopy(raw),
        )

    # Fallback: in-memory script component
    script_comp = hass.data.get("script") if isinstance(getattr(hass, "data", None), dict) else None
    if script_comp and hasattr(script_comp, "get_entity"):
        ent = script_comp.get_entity(entity_id)
        raw_cfg = getattr(ent, "raw_config", None) if ent else None
        if isinstance(raw_cfg, dict):
            alias = str(raw_cfg.get("alias", obj_id.replace("_", " ").title()))
            return ShareableDefinition(
                entity_id=entity_id,
                domain="script",
                object_id=obj_id,
                alias=alias,
                description=str(raw_cfg.get("description", "")),
                config=deepcopy(raw_cfg),
            )

    return None


def discover_ability_sync(
    hass: Any,
    config_dir: Path,
    entity_id: str,
    *,
    include_companion_scripts: bool = True,
) -> AbilityGraph:
    """Discover an automation/script and all its related helpers and companion scripts."""
    if "." not in entity_id:
        raise ValueError(f"Invalid entity_id: {entity_id}")

    domain, _ = entity_id.split(".", 1)
    if domain not in SHAREABLE_DOMAINS:
        raise ValueError(
            f"Unsupported domain '{domain}'. Only automations and scripts can be shared."
        )

    root = (
        _find_automation_definition(hass, config_dir, entity_id)
        if domain == "automation"
        else _find_script_definition(hass, config_dir, entity_id)
    )
    if root is None:
        raise LookupError(f"Could not locate raw configuration for '{entity_id}'.")

    discovered_helpers: dict[str, HelperDefinition] = {}
    discovered_scripts: dict[str, ShareableDefinition] = {}
    external_entities: set[str] = set()
    unresolved: set[str] = set()
    visited: set[str] = {entity_id}

    frontier: set[str] = collect_entity_references(root.config) - visited

    for _depth in range(MAX_DEPENDENCY_DEPTH):
        if not frontier:
            break

        next_frontier: set[str] = set()
        helper_candidates: set[str] = set()
        script_candidates: set[str] = set()

        for ref in sorted(frontier):
            visited.add(ref)
            ref_domain = ref.split(".", 1)[0]
            if ref_domain in ALL_HELPER_DOMAINS:
                helper_candidates.add(ref)
            elif (
                ref_domain == "script"
                and include_companion_scripts
                and len(discovered_scripts) < MAX_COMPANION_SCRIPTS
            ):
                script_candidates.add(ref)
            else:
                # Could still be a config-entry helper (e.g. sensor.* created by template/utility_meter)
                if ref_domain in ("sensor", "binary_sensor", "switch", "light", "climate", "cover"):
                    helper_candidates.add(ref)
                else:
                    external_entities.add(ref)

        # Resolve helpers (storage, config_entry, or YAML)
        if helper_candidates:
            extracted = extract_helpers_sync(hass, config_dir, helper_candidates)
            for eid, helper_def in extracted.items():
                discovered_helpers[eid] = helper_def
                for sub_ref in collect_entity_references(helper_def.config):
                    if sub_ref not in visited:
                        next_frontier.add(sub_ref)

            for eid in helper_candidates - set(extracted.keys()):
                ref_domain = eid.split(".", 1)[0]
                if ref_domain in ALL_HELPER_DOMAINS:
                    # Referenced a helper domain entity we couldn't locate on disk/storage
                    unresolved.add(eid)
                    external_entities.add(eid)
                else:
                    # Regular hardware sensor/switch/light — treat as external role
                    external_entities.add(eid)

        # Resolve companion scripts
        for script_eid in sorted(script_candidates):
            if len(discovered_scripts) >= MAX_COMPANION_SCRIPTS:
                external_entities.add(script_eid)
                continue
            script_def = _find_script_definition(hass, config_dir, script_eid)
            if script_def is not None:
                discovered_scripts[script_eid] = script_def
                for sub_ref in collect_entity_references(script_def.config):
                    if sub_ref not in visited:
                        next_frontier.add(sub_ref)
            else:
                unresolved.add(script_eid)
                external_entities.add(script_eid)

        frontier = next_frontier

    return AbilityGraph(
        root=root,
        helpers=sorted(discovered_helpers.values(), key=lambda h: h.entity_id),
        companion_scripts=sorted(discovered_scripts.values(), key=lambda s: s.entity_id),
        external_entities=sorted(external_entities),
        unresolved_references=sorted(unresolved),
    )
