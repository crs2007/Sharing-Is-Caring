"""Dual-artifact Ability Bundler (README.md + package.yaml + blueprint.yaml)."""

from __future__ import annotations

from ..models import SanitizedAbility
from .blueprint_builder import build_blueprint_yaml
from .package_builder import build_package_yaml
from .readme_builder import build_readme_markdown


def build_ability_files(
    sanitized: SanitizedAbility,
    *,
    generate_blueprint: bool = True,
) -> tuple[dict[str, str], str, str | None]:
    """Build all output files for a sanitized ability.

    Returns (files_dict, package_filename, blueprint_filename).
    """
    package_filename = f"{sanitized.slug}_package.yaml"
    blueprint_filename: str | None = None

    files: dict[str, str] = {}
    package_yaml = build_package_yaml(sanitized)

    blueprint_yaml: str | None = None
    if generate_blueprint and sanitized.blueprint_eligible:
        blueprint_yaml = build_blueprint_yaml(sanitized)
        if blueprint_yaml is not None:
            blueprint_filename = f"{sanitized.slug}_blueprint.yaml"

    readme_md = build_readme_markdown(
        sanitized,
        package_filename=package_filename,
        blueprint_filename=blueprint_filename,
    )

    # Order: README.md first so GitHub Gist displays it at the top
    files["README.md"] = readme_md
    files[package_filename] = package_yaml
    if blueprint_filename and blueprint_yaml is not None:
        files[blueprint_filename] = blueprint_yaml

    return files, package_filename, blueprint_filename


__all__ = [
    "build_ability_files",
    "build_blueprint_yaml",
    "build_package_yaml",
    "build_readme_markdown",
]
