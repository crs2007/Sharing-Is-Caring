"""Generates a parameterized Home Assistant Blueprint YAML when eligible."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

import yaml

from ..models import ExternalRole, SanitizedAbility


class _BlueprintInputTag:
    """YAML tag wrapper that serializes as `!input <key>`."""

    def __init__(self, key: str) -> None:
        self.key = key


def _dump_blueprint_yaml(data: dict[str, Any]) -> str:
    class _BlueprintDumper(yaml.SafeDumper):
        pass

    def _represent_input(dumper: yaml.SafeDumper, value: _BlueprintInputTag) -> yaml.ScalarNode:
        return dumper.represent_scalar("!input", value.key)

    def _represent_str(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
        if "\n" in value:
            return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", value)

    _BlueprintDumper.add_representer(_BlueprintInputTag, _represent_input)
    _BlueprintDumper.add_representer(str, _represent_str)

    return yaml.dump(
        data,
        Dumper=_BlueprintDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )


def _selector_for_role(role: ExternalRole) -> dict[str, Any]:
    if role.domain == "notify":
        return {"text": {}}
    return {"entity": {"domain": role.domain}}


def _replace_placeholders_with_inputs(
    obj: Any,
    placeholder_to_input: dict[str, str],
    used_template_vars: set[str],
    parent_key: str = "",
) -> Any:
    """Replace anonymized external entity placeholders with `!input` or template vars."""
    if isinstance(obj, dict):
        return {
            k: _replace_placeholders_with_inputs(
                v, placeholder_to_input, used_template_vars, parent_key=str(k).lower()
            )
            for k, v in obj.items()
        }

    if isinstance(obj, list):
        return [
            _replace_placeholders_with_inputs(
                item, placeholder_to_input, used_template_vars, parent_key=parent_key
            )
            for item in obj
        ]

    if isinstance(obj, str):
        stripped = obj.strip()
        # Exact match on an entity_id / action target -> direct `!input` tag
        if stripped in placeholder_to_input and parent_key not in ("alias", "description"):
            input_key = placeholder_to_input[stripped]
            if parent_key in ("service", "action"):
                # Service/action names cannot take `!input` directly in HA; use template var
                used_template_vars.add(input_key)
                return f"{{{{ {input_key} }}}}"
            return _BlueprintInputTag(input_key)

        # Inside a Jinja2 template string -> bind via blueprint `variables:`
        if "{{" in obj or "{%" in obj:
            rewritten = obj
            for placeholder, input_key in placeholder_to_input.items():
                if placeholder in rewritten:
                    used_template_vars.add(input_key)
                    # Replace quoted placeholder e.g. states('light.example_light_1') -> states(target_light_1)
                    rewritten = re.sub(
                        rf"""['"]{re.escape(placeholder)}['"]""",
                        input_key,
                        rewritten,
                    )
                    # Replace states.domain.obj syntax with states(var)
                    dom, obj_id = placeholder.split(".", 1)
                    rewritten = re.sub(
                        rf"\bstates\.{re.escape(dom)}\.{re.escape(obj_id)}\b",
                        f"states({input_key})",
                        rewritten,
                    )
            return rewritten

    return obj


def build_blueprint_yaml(sanitized: SanitizedAbility) -> str | None:
    """Convert a sanitized automation or script into a Home Assistant Blueprint YAML."""
    if not sanitized.blueprint_eligible or sanitized.root_domain not in ("automation", "script"):
        return None

    placeholder_to_input: dict[str, str] = {
        role.placeholder_entity_id: role.blueprint_input_key
        for role in sanitized.external_roles
    }

    inputs_spec: dict[str, Any] = {}
    for role in sanitized.external_roles:
        inputs_spec[role.blueprint_input_key] = {
            "name": role.label,
            "description": (
                f"Select your {role.domain.replace('_', ' ')} entity "
                f"(replaces {role.placeholder_entity_id})."
            ),
            "selector": _selector_for_role(role),
        }

    # Expose bundled helpers as optional inputs with sensible default entity_ids
    for helper in sanitized.helpers:
        helper_input_key = f"helper_{helper.object_id}"
        inputs_spec[helper_input_key] = {
            "name": helper.name or helper.object_id.replace("_", " ").title(),
            "description": (
                f"Required {helper.domain} helper. Create it manually or install the companion "
                f"package file ({sanitized.slug}_package.yaml)."
            ),
            "default": helper.entity_id,
            "selector": {"entity": {"domain": helper.domain}},
        }
        placeholder_to_input[helper.entity_id] = helper_input_key

    used_template_vars: set[str] = set()
    body = deepcopy(sanitized.root_config)
    # Remove alias/description from top-level blueprint body (they live under blueprint:)
    body.pop("alias", None)
    body.pop("description", None)

    parameterized_body = _replace_placeholders_with_inputs(
        body, placeholder_to_input, used_template_vars
    )

    if used_template_vars:
        existing_vars = parameterized_body.get("variables")
        merged_vars: dict[str, Any] = (
            dict(existing_vars) if isinstance(existing_vars, dict) else {}
        )
        for var_name in sorted(used_template_vars):
            merged_vars.setdefault(var_name, _BlueprintInputTag(var_name))
        parameterized_body["variables"] = merged_vars

    desc_parts: list[str] = []
    if sanitized.description:
        desc_parts.append(sanitized.description)
    else:
        desc_parts.append(f"Reusable Home Assistant {sanitized.root_domain} blueprint.")
    if sanitized.helpers:
        helper_list = ", ".join(h.entity_id for h in sanitized.helpers)
        desc_parts.append(
            f"Companion helpers required ({len(sanitized.helpers)}): {helper_list}. "
            f"See {sanitized.slug}_package.yaml or README.md for their definitions."
        )

    blueprint_doc: dict[str, Any] = {
        "blueprint": {
            "name": sanitized.title,
            "description": " ".join(desc_parts),
            "domain": sanitized.root_domain,
            "input": inputs_spec,
        },
        **parameterized_body,
    }

    header = (
        f"# Home Assistant Blueprint: {sanitized.title}\n"
        "# Exported and sanitized by Sharing Is Caring (zero personal data included).\n\n"
    )
    return header + _dump_blueprint_yaml(blueprint_doc)
