<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/sharing_is_caring/brand/dark_logo.png">
    <source media="(prefers-color-scheme: light)" srcset="custom_components/sharing_is_caring/brand/logo.png">
    <img alt="Sharing Is Caring" src="custom_components/sharing_is_caring/brand/logo.png" height="96">
  </picture>
</p>

# Sharing Is Caring

[![Home Assistant Marketplace](https://img.shields.io/badge/Home%20Assistant-Marketplace-41BDF5?logo=home-assistant)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Share any Home Assistant automation or script together with all its related helpers as a clean, shareable URL — without ever exposing sensitive or personal information.**

> **Core Promise — "Only the New Ability":**
> Nothing leaves your Home Assistant instance until you visually inspect and approve the sanitized output. Secrets, tokens, webhook IDs, alarm codes, IPs, URLs, GPS coordinates, personal names, device/area UUIDs, and runtime entity states are automatically stripped or anonymized before sharing.

---

## What It Exports (Dual-Artifact "Ability Bundle")

When you share an automation or script, **Sharing Is Caring** automatically discovers its related helpers (and optional companion scripts) and generates up to three clean files:

1. **`README.md`** — Human-readable overview of the ability, required external device roles (e.g., *1 motion sensor, 1 light*), a table of bundled helpers, setup instructions, and a 1-click **My Home Assistant** Blueprint import button when applicable.
2. **`<slug>_package.yaml`** — A drop-in Home Assistant Package containing the sanitized automation/script **plus all related helpers** (`input_boolean`, `input_number`, `input_text`, `input_select`, `input_datetime`, `input_button`, `timer`, `counter`, `schedule`, `template`, `group`, `utility_meter`, `threshold`, `derivative`, `integration`, `min_max`, `statistics`, `tod`, `trend`, etc.).
3. **`<slug>_blueprint.yaml`** *(when eligible)* — Automatically converts external devices/entities into typed `!input` selectors so recipients can import the core automation/script with one click via My Home Assistant.

Recipients **do not** need to have Sharing Is Caring installed to use what you share.

---

## Privacy & Security Architecture

Every export passes through a **4-layer fail-closed sanitization pipeline**:

1. **Structural & Schema Stripping (Layer 1):** Never reads `secrets.yaml` values (`!secret foo` becomes `<YOUR_SECRET_FOO>`). Never exports live entity states. Clears `initial` values on `input_text` helpers. Strips internal HA UUIDs (`id`, `unique_id`, `device_id`, `area_id`, `floor_id`, `label_id`, `entry_id`).
2. **Dynamic Instance PII Dictionary (Layer 2):** Automatically detects and redacts terms specific to your Home Assistant instance (`location_name`, `external_url`/`internal_url`, `person.*` names, `zone.*` names & coordinates, HA user names, `device_tracker.*` slugs, and `notify.mobile_app_*` slugs).
3. **Entity & Jinja2 Anonymization (Layer 3):** Rewrites external entity IDs across both YAML and Jinja2 templates into generic roles (e.g., `light.sharon_bedroom_lamp` → `light.example_light_1` or `!input target_light_1`).
4. **Secret, PII & Entropy Audit Gate (Layer 4):** Scans the final rendered files for API keys, Bearer/JWT tokens, HA Long-Lived Access Tokens, webhook IDs, alarm/lock `code:` fields, emails, phone numbers, IPv4/IPv6 addresses, `.local`/`.duckdns.org`/`.ui.nabu.casa` domains, MAC addresses, GPS coordinates, and high-entropy literals.
   - **Blocked items** hard-stop publishing until removed or redacted.
   - **Needs Review items** (such as free-text notification messages) are highlighted for you to review or edit inline.
   - **Byte-Exact Approval (`preview_hash`):** Publishing uploads strictly the exact sanitized bundle you reviewed and approved — never re-reading live HA state at publish time.
   - **Admin-Only Access:** Both the Sidebar Panel and backend WebSocket/Action endpoints require Home Assistant Administrator privileges.

---

## Installation (Home Assistant Marketplace)

**Requirements:** Home Assistant **2026.11.0** or newer.

### Option 1: Install from the Home Assistant Marketplace Catalog
1. In Home Assistant, open **Settings > Marketplace**.
2. Search for **Sharing Is Caring**.
3. Click **Download / Install**.
4. **Restart Home Assistant** when prompted.

### Option 2: Install as a Custom Repository in Marketplace
1. In Home Assistant, open **Settings > Marketplace**.
2. Open the top-right menu (**⋮**) and select **Custom repositories**.
3. Enter the repository URL:
   ```text
   https://github.com/crs2007/Sharing-Is-Caring
   ```
4. Select category **Integration** and click **Add**.
5. Find **Sharing Is Caring** in the Marketplace list, click **Download / Install**, and **restart Home Assistant**.

---

## Creating Your Own GitHub Credentials (For Shareable Gist URLs)

Each user provides **their own GitHub Personal Access Token (PAT)** so shared bundles are created as Gists under **your own GitHub account** — there is no central third-party server or shared API key.

> **Don't have a GitHub account or prefer 100% offline?**
> You can leave the GitHub token blank during setup! **Local Copy & Download** works out of the box with zero cloud credentials, and you can add a GitHub token anytime later via **Reconfigure**.

### Recommended: Create a Fine-Grained Personal Access Token (Least Privilege)
1. Sign in to GitHub and go to **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** (or open [github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new)).
2. Click **Generate new token**.
3. Give it a clear name, e.g. `Home Assistant - Sharing Is Caring`.
4. Choose an **Expiration** that suits your security policy (you can rotate it anytime in Home Assistant via **Reconfigure**).
5. Under **Repository access**, leave **Public Repositories (read-only)** / **No repositories** selected — **this integration needs ZERO repository access**.
6. Expand **Account permissions**, find **Gists**, and set it to **Read and write**. Leave every other permission set to **No access**.
7. Click **Generate token** and copy the token immediately (starts with `github_pat_...`).

### Alternative: Classic Personal Access Token
1. Go to **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**.
2. Check **only** the **`gist`** checkbox (leave `repo`, `admin`, `user`, and all other scopes unchecked).
3. Click **Generate token** and copy the token (starts with `ghp_...`).

> **How your token is stored:** Your GitHub token is stored locally inside Home Assistant's encrypted/protected config entry storage. It is validated once during setup and is **only** used when you explicitly click **Publish** to create a Gist.

---

## Setting Up the Integration in Home Assistant

1. Go to **Settings > Devices & Services**.
2. Click **+ Add Integration** (bottom right) and search for **Sharing Is Caring**.
3. In the setup dialog:
   - **GitHub Personal Access Token (optional):** Paste the PAT you created above, or leave blank to use **Local Copy / Download** mode only.
   - **Default Gist Visibility:** Defaults to **Secret (Unlisted)** so only people with the URL can view your share. You can override this per share.
   - **Show in Sidebar:** Enabled by default for admin users.
4. Click **Submit**. If you provided a GitHub token, Home Assistant verifies it immediately (and warns if a classic token has unnecessarily broad permissions).

### Updating or Rotating Your GitHub Token Later
1. Go to **Settings > Devices & Services > Sharing Is Caring**.
2. Open the menu (**⋮**) on the integration entry and choose **Reconfigure** to add, replace, or remove your GitHub token.
3. Click **Configure** (Options) to toggle Sidebar visibility or default Gist visibility.

---

## How to Use

### Via the Sidebar Panel (Recommended)
1. Click **Sharing Is Caring** in the Home Assistant sidebar (visible to Admins).
2. **Step 1 — Select Ability:** Pick an automation or script, toggle whether to include detected companion scripts or generate a Blueprint, and optionally add a short title/description.
3. **Step 2 — Privacy Audit & Preview:**
   - Review the security banner (**Clean**, **Needs Review**, or **Blocked**).
   - Inspect every auto-redacted item, add any extra custom words to redact, and review/edit any flagged notification messages inline.
   - Browse the generated `package.yaml`, `blueprint.yaml`, and `README.md` tabs.
4. **Step 3 — Share:**
   - Choose **GitHub Gist (Secret or Public)** or **Copy / Download Locally**.
   - Confirm any review items and click **Publish Sanitized Bundle**.
   - Copy the resulting **Share URL** (and the 1-click **My Home Assistant** Blueprint import link if generated).

### Via Developer Tools / HA Actions
Power users can also invoke the backend actions directly:
- `sharing_is_caring.preview` — Returns the sanitized files, dependency list, security audit report, and `preview_hash`.
- `sharing_is_caring.share` — Publishes the exact cached bundle matching `preview_hash` (fails closed if the hash doesn't match, has expired, or has unresolved blockers).

---

## Troubleshooting

- **`Invalid GitHub token (401)`:** Ensure you copied the full token without extra spaces and that it hasn't expired.
- **`Missing Gist permission (403)`:** For Fine-Grained PATs, make sure **Account permissions → Gists** is set to **Read and write**. For Classic PATs, ensure the **`gist`** scope is checked.
- **Why was my export marked `Blocked`?** The Layer 4 scanner detected a pattern matching a secret, token, private key, webhook ID, or alarm/lock `code:` that was not yet resolved. Check the Audit tab to see the exact line/field and add a custom redaction or edit the flagged string.
- **What happens to `device` triggers/actions?** Home Assistant `device_id` values are random UUIDs unique to your machine and won't work on another instance. Sharing Is Caring strips every `device_id` and flags those blocks so you know to double-check the placeholder before sharing.
- **I don't see Sharing Is Caring in the sidebar:** The panel is restricted to **Administrator** accounts. Verify your user has Admin privileges and that **Show in Sidebar** is enabled under **Settings > Devices & Services > Sharing Is Caring > Configure**.

---

## Development & Contributing

```bash
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
pip install -e ".[dev]"
pytest
ruff check .
mypy custom_components/sharing_is_caring
```

Frontend panel development:
```bash
cd frontend
npm install
npm run build
```

## License

MIT License — see [LICENSE](LICENSE).
