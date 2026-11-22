"""Constants for the Sharing Is Caring integration."""

from __future__ import annotations

DOMAIN = "sharing_is_caring"
VERSION = "0.1.0"

# Config entry keys
CONF_GITHUB_TOKEN = "github_token"  # noqa: S105
CONF_DEFAULT_VISIBILITY = "default_visibility"
CONF_SHOW_IN_SIDEBAR = "show_in_sidebar"

# Visibility options
VISIBILITY_SECRET = "secret"  # noqa: S105
VISIBILITY_PUBLIC = "public"
VALID_VISIBILITIES = (VISIBILITY_SECRET, VISIBILITY_PUBLIC)

# Provider identifiers
PROVIDER_GITHUB_GIST = "github_gist"
PROVIDER_LOCAL = "local"
VALID_PROVIDERS = (PROVIDER_GITHUB_GIST, PROVIDER_LOCAL)

# Panel constants
PANEL_URL_PATH = "sharing-is-caring"
PANEL_TITLE = "Sharing Is Caring"
PANEL_ICON = "mdi:share-variant"
PANEL_MODULE_URL = f"/api/{DOMAIN}/static/sharing-is-caring-panel.js"
PANEL_STATIC_BASE_URL = f"/api/{DOMAIN}/static"

# Preview cache settings
PREVIEW_CACHE_TTL_SECONDS = 900  # 15 minutes
PREVIEW_CACHE_MAX_ENTRIES = 32

# Discovery bounds
MAX_DEPENDENCY_DEPTH = 4
MAX_COMPANION_SCRIPTS = 10

# Shareable root domains
SHAREABLE_DOMAINS: frozenset[str] = frozenset({"automation", "script"})

# Storage-collection helper domains (stored in .storage/<domain>)
STORAGE_HELPER_DOMAINS: frozenset[str] = frozenset(
    {
        "input_boolean",
        "input_button",
        "input_datetime",
        "input_number",
        "input_select",
        "input_text",
        "counter",
        "timer",
        "schedule",
    }
)

# Config-entry helper domains (stored as ConfigEntry items in HA)
CONFIG_ENTRY_HELPER_DOMAINS: frozenset[str] = frozenset(
    {
        "template",
        "group",
        "utility_meter",
        "threshold",
        "derivative",
        "integration",
        "min_max",
        "statistics",
        "tod",
        "trend",
        "random",
        "generic_thermostat",
        "generic_hygrostat",
        "switch_as_x",
    }
)

ALL_HELPER_DOMAINS: frozenset[str] = STORAGE_HELPER_DOMAINS | CONFIG_ENTRY_HELPER_DOMAINS

# Domains representing sensitive/personal or hardware-bound external entities (never bundled)
PERSONAL_DOMAINS: frozenset[str] = frozenset(
    {
        "person",
        "device_tracker",
        "zone",
        "calendar",
        "notify",
        "camera",
        "lock",
        "alarm_control_panel",
    }
)

# Services / Actions
SERVICE_PREVIEW = "preview"
SERVICE_SHARE = "share"

# Audit severities
SEVERITY_AUTO_REDACTED = "auto_redacted"
SEVERITY_NEEDS_REVIEW = "needs_review"
SEVERITY_BLOCKED = "blocked"

AUDIT_STATUS_CLEAN = "clean"
AUDIT_STATUS_NEEDS_REVIEW = "needs_review"
AUDIT_STATUS_BLOCKED = "blocked"

# GitHub API
GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
