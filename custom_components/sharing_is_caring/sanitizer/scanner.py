"""Layer 4: Final-output secret, PII, and Shannon entropy audit scanner (fail-closed)."""

from __future__ import annotations

import math
import re

from ..const import SEVERITY_AUTO_REDACTED, SEVERITY_BLOCKED
from ..models import AuditFinding, AuditReport
from .pii_dictionary import InstancePIIDictionary

# Patterns that are automatically scrubbed in final rendered output
_AUTO_REDACT_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "nabu_casa_url",
        re.compile(r"https?://[a-zA-Z0-9_-]+\.ui\.nabu\.casa(?:/[^\s'\"]*)?", re.IGNORECASE),
        "<REDACTED_NABU_CASA_URL>",
    ),
    (
        "private_ddns_url",
        re.compile(
            r"https?://[a-zA-Z0-9._-]+\.(?:duckdns\.org|dyndns\.org|no-ip\.org|local|lan|home\.arpa)(?::\d+)?(?:/[^\s'\"]*)?",
            re.IGNORECASE,
        ),
        "<REDACTED_PRIVATE_URL>",
    ),
    (
        "webhook_path",
        re.compile(r"/api/webhook/[a-zA-Z0-9_-]{6,}", re.IGNORECASE),
        "/api/webhook/<YOUR_WEBHOOK_ID>",
    ),
    (
        "email_address",
        re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
        "<REDACTED_EMAIL>",
    ),
    (
        "ipv4_address",
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"
        ),
        "<REDACTED_IP>",
    ),
    (
        "ipv6_address",
        re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}\b"),
        "<REDACTED_IP>",
    ),
    (
        "mac_address",
        re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"),
        "<REDACTED_MAC>",
    ),
    (
        "phone_number",
        re.compile(r"(?<!\d)(?:\+\d{1,3}[-.\s]?)?(?:\(\d{2,4}\)|\d{2,4})[-.\s]\d{3,4}[-.\s]\d{3,4}(?!\d)"),
        "<REDACTED_PHONE>",
    ),
    (
        "gps_coordinates",
        re.compile(r"(?<!\d)-?(?:[1-8]?\d\.\d{4,7})\s*,\s*-?(?:1?[0-7]?\d\.\d{4,7}|180\.0{4,7})(?!\d)"),
        "<REDACTED_COORDINATES>",
    ),
]

# Hard-block secret patterns: if ANY match survives into rendered files, publishing is BLOCKED
_HARD_BLOCK_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "private_key_block",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "Private cryptographic key material detected.",
    ),
    (
        "jwt_token",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "JWT / Home Assistant Long-Lived Access Token detected.",
    ),
    (
        "github_token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
        "GitHub Personal Access Token detected.",
    ),
    (
        "aws_access_key",
        re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
        "AWS Access Key ID detected.",
    ),
    (
        "openai_or_api_key",
        re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b"),
        "API secret key (sk-...) detected.",
    ),
    (
        "telegram_bot_token",
        re.compile(r"\b\d{8,11}:[A-Za-z0-9_-]{30,}\b"),
        "Telegram Bot API token detected.",
    ),
    (
        "discord_or_slack_webhook",
        re.compile(
            r"https?://(?:discord(?:app)?\.com/api/webhooks/[^\s'\"]+|hooks\.slack\.com/services/[^\s'\"]+)",
            re.IGNORECASE,
        ),
        "Discord or Slack webhook URL containing embedded secret token detected.",
    ),
    (
        "bearer_auth_header",
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}\b", re.IGNORECASE),
        "HTTP Authorization Bearer token detected.",
    ),
    (
        "slack_token",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        "Slack API token detected.",
    ),
]

# Candidate token extractor for Shannon entropy checking
_ENTROPY_CANDIDATE_RE = re.compile(r"""(?<![a-zA-Z0-9_/<])([A-Za-z0-9+/=_-]{24,})(?![a-zA-Z0-9_/>])""")

# Safe non-secret prefixes/patterns excluded from entropy false positives
_ENTROPY_SAFE_SUBSTRINGS = (
    "example_",
    "target_",
    "input_",
    "binary_sensor",
    "media_player",
    "alarm_control_panel",
    "mobile_app_your_device",
    "YOUR_SECRET_",
    "REDACTED_",
    "home-assistant",
    "blueprint_import",
)


def shannon_entropy(text: str) -> float:
    """Compute Shannon entropy in bits per character."""
    if not text:
        return 0.0
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    length = len(text)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def _is_likely_high_entropy_secret(candidate: str) -> bool:
    if any(safe in candidate for safe in _ENTROPY_SAFE_SUBSTRINGS):
        return False
    # Ignore pure snake_case entity/slug identifiers or pure hyphenated slugs
    if re.fullmatch(r"[a-z0-9_]+", candidate) or re.fullmatch(r"[a-z0-9-]+", candidate):
        return False
    # Require mixed character classes (upper + lower + digit/symbol) typical of random secrets
    has_upper = any(c.isupper() for c in candidate)
    has_lower = any(c.islower() for c in candidate)
    has_digit = any(c.isdigit() for c in candidate)
    if sum((has_upper, has_lower, has_digit)) < 3:
        return False
    return shannon_entropy(candidate) >= 4.2


def scan_and_scrub_rendered_files(
    files: dict[str, str],
    pii_dict: InstancePIIDictionary,
    audit: AuditReport,
) -> dict[str, str]:
    """Run Layer 4 scanning across every rendered output file (auto-scrub PII + hard-block secrets)."""
    cleaned_files: dict[str, str] = {}

    for filename, content in files.items():
        current = content

        # 1. Final safety sweep against dynamic Instance PII Dictionary
        current, pii_hits = pii_dict.redact_text(current)
        for hit in set(pii_hits):
            audit.add(
                AuditFinding(
                    severity=SEVERITY_AUTO_REDACTED,
                    category=f"final_sweep_{hit}",
                    location=filename,
                    message=f"Final sweep redacted instance personal data ({hit}) in {filename}.",
                    replacement="<REDACTED_PERSONAL>",
                )
            )

        # 2. Final safety sweep against exact instance coordinates
        for lat, lon in pii_dict.coordinates:
            lat_prefix = f"{lat:.3f}"
            lon_prefix = f"{lon:.3f}"
            if lat_prefix in current and lon_prefix in current:
                current = re.sub(
                    rf"{re.escape(lat_prefix)}\d*", "<REDACTED_LAT>", current
                )
                current = re.sub(
                    rf"{re.escape(lon_prefix)}\d*", "<REDACTED_LON>", current
                )
                audit.add(
                    AuditFinding(
                        severity=SEVERITY_AUTO_REDACTED,
                        category="instance_coordinates",
                        location=filename,
                        message="Redacted Home Assistant zone/home GPS coordinates.",
                        replacement="<REDACTED_COORDINATES>",
                    )
                )

        # 3. Auto-redact known PII/network patterns (IPs, MACs, emails, phones, private URLs, webhooks)
        for category, pattern, replacement in _AUTO_REDACT_PATTERNS:
            if pattern.search(current):
                current = pattern.sub(replacement, current)
                audit.add(
                    AuditFinding(
                        severity=SEVERITY_AUTO_REDACTED,
                        category=category,
                        location=filename,
                        message=f"Auto-redacted {category.replace('_', ' ')} in {filename}.",
                        replacement=replacement,
                    )
                )

        # 4. Hard-block credential/secret detection (never include the matched secret in the report!)
        for line_no, line in enumerate(current.splitlines(), start=1):
            # Skip known safe badges/links in README.md
            if "my.home-assistant.io" in line or "img.shields.io" in line:
                continue

            for category, pattern, desc in _HARD_BLOCK_PATTERNS:
                if pattern.search(line):
                    audit.add(
                        AuditFinding(
                            severity=SEVERITY_BLOCKED,
                            category=category,
                            location=f"{filename}:{line_no}",
                            message=f"{desc} Remove or add a custom redaction before publishing.",
                        )
                    )

            for match in _ENTROPY_CANDIDATE_RE.finditer(line):
                token = match.group(1)
                if _is_likely_high_entropy_secret(token):
                    audit.add(
                        AuditFinding(
                            severity=SEVERITY_BLOCKED,
                            category="high_entropy_secret",
                            location=f"{filename}:{line_no}",
                            message=(
                                "Detected high-entropy string that looks like an API key or secret. "
                                "Remove it or add it to custom redactions before publishing."
                            ),
                        )
                    )
                    break  # One entropy finding per line is sufficient

        cleaned_files[filename] = current

    return cleaned_files
