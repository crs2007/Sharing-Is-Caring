"""Generates a clean, self-contained Home Assistant Package YAML."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..const import STORAGE_HELPER_DOMAINS
from ..models import SanitizedAbility
from ..yaml_loader import dump_clean_yaml


def build_package_yaml(sanitized: SanitizedAbility) -> str:
    """Build a drop-in Home Assistant package YAML containing helpers + automation/script."""
    package: dict[str, Any] = {}

    # 1. Storage helpers grouped by domain (e.g., input_boolean:, timer:, schedule:)
    for helper in sanitized.helpers:
        if helper.domain in STORAGE_HELPER_DOMAINS:
            section = package.setdefault(helper.domain, {})
            section[helper.object_id] = deepcopy(helper.config)
        else:
            # Config-entry helpers (template, group, threshold, utility_meter, etc.)
            if helper.domain == "utility_meter":
                section = package.setdefault("utility_meter", {})
                section[helper.object_id] = deepcopy(helper.config)
            else:
                entries = package.setdefault(helper.domain, [])
                cfg = deepcopy(helper.config)
                cfg.setdefault("name", helper.name or helper.object_id.replace("_", " ").title())
                entries.append(cfg)

    # 2. Companion scripts + root script (if root is a script)
    scripts_section: dict[str, Any] = {}
    if sanitized.root_domain == "script":
        scripts_section[sanitized.slug] = deepcopy(sanitized.root_config)

    for comp in sanitized.companion_scripts:
        scripts_section[comp.object_id] = deepcopy(comp.config)

    if scripts_section:
        package["script"] = scripts_section

    # 3. Root automation (if root is an automation)
    if sanitized.root_domain == "automation":
        package["automation"] = [deepcopy(sanitized.root_config)]

    header_lines = [
        f"# Home Assistant Package: {sanitized.title}",
        "# Exported and sanitized by Sharing Is Caring (zero personal data included).",
        "#",
        "# To install: save this file in your Home Assistant 'packages/' folder,",
        "# replace any 'example_*' / '<YOUR_*>' placeholders with your own entities,",
        "# and reload YAML configuration.",
    ]
    if sanitized.external_roles:
        header_lines.append("#")
        header_lines.append("# External placeholders to customize:")
        for role in sanitized.external_roles:
            header_lines.append(f"#   - {role.placeholder_entity_id} ({role.label})")

    header = "\n".join(header_lines) + "\n\n"
    return header + dump_clean_yaml(package)
