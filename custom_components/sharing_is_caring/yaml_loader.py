"""Non-resolving YAML loader that NEVER reads secrets.yaml or environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import IncludeRef, SecretRef


class NonResolvingSafeLoader(yaml.SafeLoader):
    """YAML SafeLoader that preserves !secret and !include tags as safe sentinels."""


def _construct_secret(loader: yaml.SafeLoader, node: yaml.Node) -> SecretRef:
    key = loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else "VALUE"
    return SecretRef(key=str(key).strip())


def _make_include_constructor(tag_name: str) -> Any:
    def _constructor(loader: yaml.SafeLoader, node: yaml.Node) -> IncludeRef:
        value = loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else ""
        return IncludeRef(tag=tag_name, value=str(value).strip())

    return _constructor


NonResolvingSafeLoader.add_constructor("!secret", _construct_secret)
for _tag in (
    "!include",
    "!include_dir_list",
    "!include_dir_named",
    "!include_dir_merge_list",
    "!include_dir_merge_named",
    "!env_var",
    "!input",
):
    NonResolvingSafeLoader.add_constructor(_tag, _make_include_constructor(_tag))


def load_yaml_safe_no_secrets(content: str) -> Any:
    """Parse YAML text without resolving !secret, !include, or !env_var."""
    return yaml.load(content, Loader=NonResolvingSafeLoader)  # noqa: S506


def load_yaml_file_no_secrets(path: Path) -> Any:
    """Read and parse a YAML file without resolving secrets or includes."""
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    return load_yaml_safe_no_secrets(text)


def dump_clean_yaml(data: Any) -> str:
    """Serialize sanitized Python structures to clean, readable Home Assistant YAML."""

    class _CleanDumper(yaml.SafeDumper):
        pass

    def _represent_str(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
        if "\n" in value:
            return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", value)

    _CleanDumper.add_representer(str, _represent_str)
    return yaml.dump(
        data,
        Dumper=_CleanDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )
