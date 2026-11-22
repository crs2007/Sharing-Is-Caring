"""Generates a clean, human-readable README.md for the shared Ability Bundle."""

from __future__ import annotations

from ..models import SanitizedAbility


def build_readme_markdown(
    sanitized: SanitizedAbility,
    *,
    package_filename: str,
    blueprint_filename: str | None = None,
) -> str:
    """Build README.md summarizing the ability, required roles, bundled helpers, and install steps."""
    lines: list[str] = [
        f"# {sanitized.title}",
        "",
    ]

    if sanitized.description:
        lines.extend([sanitized.description, ""])
    else:
        lines.extend(
            [
                f"A shareable Home Assistant **{sanitized.root_domain}** ability bundle.",
                "",
            ]
        )

    lines.extend(
        [
            "## Files Included",
            "",
            f"- **`{package_filename}`** — Complete Home Assistant Package containing the {sanitized.root_domain}"
            + (
                f" and all {len(sanitized.helpers)} related helper(s)."
                if sanitized.helpers
                else "."
            ),
        ]
    )
    if blueprint_filename:
        lines.append(
            f"- **`{blueprint_filename}`** — Parameterized Home Assistant Blueprint with `!input` selectors."
        )
    lines.append("")

    # Required external entities/roles
    lines.extend(["## Required External Devices / Entities", ""])
    if sanitized.external_roles:
        lines.extend(
            [
                "| Role | Domain | Package Placeholder | Blueprint Input |",
                "| :--- | :--- | :--- | :--- |",
            ]
        )
        for role in sanitized.external_roles:
            lines.append(
                f"| {role.label} | `{role.domain}` | `{role.placeholder_entity_id}` | `{role.blueprint_input_key}` |"
            )
    else:
        lines.append("No external hardware or user entities required — this ability is self-contained.")
    lines.append("")

    # Bundled helpers
    lines.extend(["## Bundled Helpers", ""])
    if sanitized.helpers:
        lines.extend(
            [
                "| Helper Entity ID | Type | Name |",
                "| :--- | :--- | :--- |",
            ]
        )
        for helper in sanitized.helpers:
            display_name = helper.name or helper.object_id.replace("_", " ").title()
            lines.append(f"| `{helper.entity_id}` | `{helper.domain}` | {display_name} |")
    else:
        lines.append("No additional helpers required.")
    lines.append("")

    # Companion scripts
    if sanitized.companion_scripts:
        lines.extend(["## Bundled Companion Scripts", ""])
        for script in sanitized.companion_scripts:
            lines.append(f"- **`{script.entity_id}`** — {script.alias}")
        lines.append("")

    # Installation instructions
    lines.extend(
        [
            "## How to Use This Ability",
            "",
            "### Option 1: Install as a Home Assistant Package (Includes All Helpers)",
            "1. Ensure packages are enabled in your `configuration.yaml`:",
            "   ```yaml",
            "   homeassistant:",
            "     packages: !include_dir_named packages",
            "   ```",
            f"2. Save `{package_filename}` into your `config/packages/` directory.",
            "3. Replace any `example_*` or `<YOUR_*>` placeholders with your own entity IDs.",
            "4. Reload YAML configuration (or restart Home Assistant).",
            "",
        ]
    )

    if blueprint_filename:
        lines.extend(
            [
                "### Option 2: Import as a Home Assistant Blueprint",
                (
                    f"1. Copy the raw URL of `{blueprint_filename}` (or click the "
                    "**My Home Assistant** import link provided by the sharer)."
                ),
                (
                    "2. In Home Assistant, go to **Settings > Automations & Scenes > "
                    "Blueprints > Import Blueprint** and paste the URL."
                ),
            ]
        )
        if sanitized.helpers:
            lines.append(
                f"3. Create the {len(sanitized.helpers)} helper(s) listed in the "
                "**Bundled Helpers** table above (or copy their definitions from "
                f"`{package_filename}`)."
            )
        lines.append("")

    lines.extend(
        [
            "---",
            (
                "*Exported and sanitized with **Sharing Is Caring** — personal data, "
                "secrets, and local IDs were stripped automatically before sharing.*"
            ),
            "",
        ]
    )

    return "\n".join(lines)
