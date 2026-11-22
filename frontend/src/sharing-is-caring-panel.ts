import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type {
  HomeAssistant,
  IntegrationStatus,
  PreviewResponse,
  ShareResult,
  ShareableItem,
} from "./types";

@customElement("sharing-is-caring-panel")
export class SharingIsCaringPanel extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property({ type: Boolean }) public narrow = false;

  @state() private _step: 1 | 2 | 3 = 1;
  @state() private _loading = false;
  @state() private _error = "";
  @state() private _copiedKey = "";

  @state() private _status: IntegrationStatus | null = null;
  @state() private _items: ShareableItem[] = [];
  @state() private _search = "";
  @state() private _domainFilter: "all" | "automation" | "script" = "all";

  // Step 1 form state
  @state() private _selectedEntityId = "";
  @state() private _titleOverride = "";
  @state() private _descriptionOverride = "";
  @state() private _includeCompanionScripts = true;
  @state() private _generateBlueprint = true;

  // Step 2 audit & preview state
  @state() private _preview: PreviewResponse | null = null;
  @state() private _activeFileTab = "";
  @state() private _customRedactionsInput = "";
  @state() private _textOverrides: Record<string, string> = {};

  // Step 3 publish state
  @state() private _selectedProvider: "github_gist" | "local" = "github_gist";
  @state() private _visibility: "secret" | "public" = "secret";
  @state() private _confirmReviewItems = false;
  @state() private _shareResult: ShareResult | null = null;

  protected firstUpdated(): void {
    void this._loadInitialData();
  }

  private async _loadInitialData(): Promise<void> {
    if (!this.hass) return;
    this._loading = true;
    this._error = "";
    try {
      const [status, listResp] = await Promise.all([
        this.hass.callWS<IntegrationStatus>({ type: "sharing_is_caring/get_status" }),
        this.hass.callWS<{ items: ShareableItem[] }>({
          type: "sharing_is_caring/list_shareables",
        }),
      ]);
      this._status = status;
      this._items = listResp.items ?? [];
      this._visibility = status.default_visibility || "secret";
      this._selectedProvider = status.github_configured ? "github_gist" : "local";
    } catch (err) {
      this._error = this._formatError(err);
    } finally {
      this._loading = false;
    }
  }

  private _formatError(err: unknown): string {
    if (err && typeof err === "object" && "message" in err) {
      return String((err as { message: unknown }).message);
    }
    return String(err ?? "Unexpected error");
  }

  private _parseCustomRedactions(): string[] {
    return this._customRedactionsInput
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length >= 2);
  }

  private async _runPreview(): Promise<void> {
    if (!this._selectedEntityId) return;
    this._loading = true;
    this._error = "";
    this._confirmReviewItems = false;
    this._shareResult = null;
    try {
      const payload: Record<string, unknown> = {
        type: "sharing_is_caring/preview",
        entity_id: this._selectedEntityId,
        include_companion_scripts: this._includeCompanionScripts,
        generate_blueprint: this._generateBlueprint,
        custom_redactions: this._parseCustomRedactions(),
        text_overrides: this._textOverrides,
      };
      if (this._titleOverride.trim()) payload.title = this._titleOverride.trim();
      if (this._descriptionOverride.trim()) {
        payload.description = this._descriptionOverride.trim();
      }

      const preview = await this.hass.callWS<PreviewResponse>(payload);
      this._preview = preview;
      const filenames = Object.keys(preview.files);
      if (!filenames.includes(this._activeFileTab)) {
        this._activeFileTab = preview.package_filename || filenames[0] || "";
      }
      this._step = 2;
    } catch (err) {
      this._error = this._formatError(err);
    } finally {
      this._loading = false;
    }
  }

  private async _publishBundle(): Promise<void> {
    if (!this._preview) return;
    this._loading = true;
    this._error = "";
    try {
      const result = await this.hass.callWS<ShareResult>({
        type: "sharing_is_caring/publish",
        preview_hash: this._preview.preview_hash,
        provider: this._selectedProvider,
        visibility: this._visibility,
        confirm_review_items: this._confirmReviewItems,
      });
      this._shareResult = result;
    } catch (err) {
      this._error = this._formatError(err);
    } finally {
      this._loading = false;
    }
  }

  private async _copyText(key: string, text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      this._copiedKey = key;
      window.setTimeout(() => {
        if (this._copiedKey === key) this._copiedKey = "";
      }, 2000);
    } catch {
      this._error = "Clipboard copy was blocked by your browser.";
    }
  }

  private _downloadFile(filename: string, content: string): void {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  private _downloadAllFiles(files: Record<string, string>): void {
    for (const [name, content] of Object.entries(files)) {
      this._downloadFile(name, content);
    }
  }

  private _resetWizard(): void {
    this._step = 1;
    this._preview = null;
    this._shareResult = null;
    this._error = "";
    this._customRedactionsInput = "";
    this._textOverrides = {};
    this._confirmReviewItems = false;
  }

  private get _filteredItems(): ShareableItem[] {
    const query = this._search.trim().toLowerCase();
    return this._items.filter((item) => {
      if (this._domainFilter !== "all" && item.domain !== this._domainFilter) {
        return false;
      }
      if (!query) return true;
      return (
        item.name.toLowerCase().includes(query) ||
        item.entity_id.toLowerCase().includes(query)
      );
    });
  }

  protected render() {
    return html`
      <div class="page">
        <header class="header">
          <div class="header-inner">
            <div>
              <h1>Sharing Is Caring</h1>
              <p class="subtitle">
                Share automations &amp; scripts with all related helpers — zero sensitive data ever leaves Home Assistant.
              </p>
            </div>
            <div class="stepper" role="tablist" aria-label="Share workflow steps">
              <span class="step-pill ${this._step === 1 ? "active" : this._step > 1 ? "done" : ""}">
                1. Pick Ability
              </span>
              <span class="step-pill ${this._step === 2 ? "active" : this._step > 2 ? "done" : ""}">
                2. Privacy Audit
              </span>
              <span class="step-pill ${this._step === 3 ? "active" : ""}">
                3. Publish
              </span>
            </div>
          </div>
        </header>

        <main class="container">
          ${this._error
            ? html`<div class="alert alert-error" role="alert">${this._error}</div>`
            : nothing}

          ${this._step === 1 ? this._renderStep1() : nothing}
          ${this._step === 2 ? this._renderStep2() : nothing}
          ${this._step === 3 ? this._renderStep3() : nothing}
        </main>
      </div>
    `;
  }

  private _renderStep1() {
    const items = this._filteredItems;
    return html`
      <section class="card">
        <div class="card-header">
          <h2>Select an Automation or Script</h2>
          <div class="filter-row">
            <input
              type="search"
              class="input"
              placeholder="Search automations & scripts..."
              .value=${this._search}
              @input=${(e: Event) => {
                this._search = (e.target as HTMLInputElement).value;
              }}
            />
            <div class="pill-group">
              ${(["all", "automation", "script"] as const).map(
                (dom) => html`
                  <button
                    class="pill-btn ${this._domainFilter === dom ? "selected" : ""}"
                    @click=${() => {
                      this._domainFilter = dom;
                    }}
                  >
                    ${dom === "all" ? "All" : dom === "automation" ? "Automations" : "Scripts"}
                  </button>
                `,
              )}
            </div>
          </div>
        </div>

        ${this._loading && items.length === 0
          ? html`<p class="muted">Loading automations and scripts...</p>`
          : items.length === 0
            ? html`<p class="muted">No matching automations or scripts found.</p>`
            : html`
                <div class="entity-grid">
                  ${items.map(
                    (item) => html`
                      <button
                        class="entity-card ${this._selectedEntityId === item.entity_id
                          ? "selected"
                          : ""}"
                        @click=${() => {
                          this._selectedEntityId = item.entity_id;
                          this._textOverrides = {};
                        }}
                      >
                        <span class="badge badge-${item.domain}">${item.domain}</span>
                        <span class="entity-name">${item.name}</span>
                        <span class="entity-id">${item.entity_id}</span>
                      </button>
                    `,
                  )}
                </div>
              `}

        <div class="options-box">
          <h3>Bundle Options</h3>
          <div class="form-grid">
            <label class="field">
              <span>Public title override (optional)</span>
              <input
                type="text"
                class="input"
                placeholder="e.g. Smart Motion Hallway Light"
                .value=${this._titleOverride}
                @input=${(e: Event) => {
                  this._titleOverride = (e.target as HTMLInputElement).value;
                }}
              />
            </label>
            <label class="field">
              <span>Short description (optional)</span>
              <input
                type="text"
                class="input"
                placeholder="Briefly describe what this ability does"
                .value=${this._descriptionOverride}
                @input=${(e: Event) => {
                  this._descriptionOverride = (e.target as HTMLInputElement).value;
                }}
              />
            </label>
          </div>
          <div class="checkbox-row">
            <label class="checkbox-label">
              <input
                type="checkbox"
                .checked=${this._includeCompanionScripts}
                @change=${(e: Event) => {
                  this._includeCompanionScripts = (e.target as HTMLInputElement).checked;
                }}
              />
              <span>Bundle referenced companion scripts</span>
            </label>
            <label class="checkbox-label">
              <input
                type="checkbox"
                .checked=${this._generateBlueprint}
                @change=${(e: Event) => {
                  this._generateBlueprint = (e.target as HTMLInputElement).checked;
                }}
              />
              <span>Also generate parameterized Blueprint YAML</span>
            </label>
          </div>
        </div>

        <div class="actions-bar">
          <span class="muted">No data is uploaded during preview.</span>
          <button
            class="btn btn-primary"
            ?disabled=${!this._selectedEntityId || this._loading}
            @click=${() => void this._runPreview()}
          >
            ${this._loading ? "Analyzing & Sanitizing..." : "Inspect & Sanitize →"}
          </button>
        </div>
      </section>
    `;
  }

  private _renderStep2() {
    if (!this._preview) return nothing;
    const { audit, dependencies, files } = this._preview;
    const filenames = Object.keys(files);
    const activeContent = files[this._activeFileTab] ?? "";

    return html`
      <section class="card">
        <div class="audit-banner audit-${audit.status}">
          <div>
            <strong>
              ${audit.status === "clean"
                ? "Privacy Check Passed — Ready to Share"
                : audit.status === "needs_review"
                  ? `Review Required (${audit.counts.needs_review} item(s))`
                  : `Publishing Blocked (${audit.counts.blocked} secret/blocker(s) detected)`}
            </strong>
            <p>
              Auto-redacted: ${audit.counts.auto_redacted} · Needs review:
              ${audit.counts.needs_review} · Blocked: ${audit.counts.blocked}
            </p>
          </div>
          <code class="hash-pill" title="Exact SHA-256 preview hash verified at publish time">
            hash: ${this._preview.preview_hash.slice(0, 12)}
          </code>
        </div>

        <div class="dep-strip">
          <div class="dep-group">
            <strong>Bundled Helpers (${dependencies.helpers.length})</strong>
            <div class="chip-list">
              ${dependencies.helpers.length === 0
                ? html`<span class="muted">None</span>`
                : dependencies.helpers.map(
                    (h) => html`<span class="chip">${h.entity_id}</span>`,
                  )}
            </div>
          </div>
          <div class="dep-group">
            <strong>Companion Scripts (${dependencies.companion_scripts.length})</strong>
            <div class="chip-list">
              ${dependencies.companion_scripts.length === 0
                ? html`<span class="muted">None</span>`
                : dependencies.companion_scripts.map(
                    (s) => html`<span class="chip">${s.entity_id}</span>`,
                  )}
            </div>
          </div>
          <div class="dep-group">
            <strong>Anonymized External Roles (${dependencies.external_roles.length})</strong>
            <div class="chip-list">
              ${dependencies.external_roles.length === 0
                ? html`<span class="muted">None</span>`
                : dependencies.external_roles.map(
                    (r) => html`<span class="chip chip-role">${r.placeholder_entity_id}</span>`,
                  )}
            </div>
          </div>
        </div>

        ${audit.blocked.length > 0
          ? html`
              <div class="findings-box findings-blocked">
                <h3>Blocked Findings (Must Resolve Before Publishing)</h3>
                <ul>
                  ${audit.blocked.map(
                    (f) => html`
                      <li>
                        <code>${f.location}</code> — ${f.message}
                      </li>
                    `,
                  )}
                </ul>
              </div>
            `
          : nothing}

        ${audit.needs_review.length > 0
          ? html`
              <div class="findings-box findings-review">
                <h3>Items to Review</h3>
                <ul>
                  ${audit.needs_review.map(
                    (f) => html`
                      <li>
                        <div>
                          <code>${f.location}</code> — ${f.message}
                          ${f.snippet ? html`<div class="snippet">"${f.snippet}"</div>` : nothing}
                        </div>
                        ${f.category === "free_text_message"
                          ? html`
                              <input
                                type="text"
                                class="input override-input"
                                placeholder="Optional replacement text (then click Re-Sanitize)"
                                .value=${this._textOverrides[f.location] ?? ""}
                                @input=${(e: Event) => {
                                  const val = (e.target as HTMLInputElement).value;
                                  this._textOverrides = {
                                    ...this._textOverrides,
                                    [f.location]: val,
                                  };
                                }}
                              />
                            `
                          : nothing}
                      </li>
                    `,
                  )}
                </ul>
              </div>
            `
          : nothing}

        <div class="redaction-bar">
          <label class="field flex-grow">
            <span>Extra custom words to redact everywhere (comma-separated)</span>
            <input
              type="text"
              class="input"
              placeholder="e.g. DogName, StreetName, MySSID"
              .value=${this._customRedactionsInput}
              @input=${(e: Event) => {
                this._customRedactionsInput = (e.target as HTMLInputElement).value;
              }}
            />
          </label>
          <button
            class="btn btn-secondary"
            ?disabled=${this._loading}
            @click=${() => void this._runPreview()}
          >
            ${this._loading ? "Re-Sanitizing..." : "Re-Sanitize"}
          </button>
        </div>

        ${audit.auto_redacted.length > 0
          ? html`
              <details class="details-box">
                <summary>View ${audit.auto_redacted.length} auto-redacted item(s)</summary>
                <ul>
                  ${audit.auto_redacted.map(
                    (f) => html`
                      <li>
                        <code>${f.location}</code> →
                        ${f.replacement ? html`<code>${f.replacement}</code>` : "stripped"}
                        (${f.message})
                      </li>
                    `,
                  )}
                </ul>
              </details>
            `
          : nothing}

        <div class="code-viewer">
          <div class="tab-bar">
            <div class="tabs">
              ${filenames.map(
                (fname) => html`
                  <button
                    class="tab-btn ${this._activeFileTab === fname ? "active" : ""}"
                    @click=${() => {
                      this._activeFileTab = fname;
                    }}
                  >
                    ${fname}
                  </button>
                `,
              )}
            </div>
            <div class="tab-actions">
              <button
                class="btn btn-small"
                @click=${() => void this._copyText(this._activeFileTab, activeContent)}
              >
                ${this._copiedKey === this._activeFileTab ? "Copied!" : "Copy"}
              </button>
              <button
                class="btn btn-small"
                @click=${() => this._downloadFile(this._activeFileTab, activeContent)}
              >
                Download
              </button>
            </div>
          </div>
          <pre class="code-pre"><code>${activeContent}</code></pre>
        </div>

        <div class="actions-bar">
          <button class="btn btn-secondary" @click=${() => (this._step = 1)}>
            ← Back
          </button>
          <button
            class="btn btn-primary"
            ?disabled=${!audit.can_publish || this._loading}
            @click=${() => (this._step = 3)}
          >
            Continue to Publish →
          </button>
        </div>
      </section>
    `;
  }

  private _renderStep3() {
    if (!this._preview) return nothing;
    const needsConfirm = this._preview.audit.status === "needs_review";
    const githubReady = Boolean(this._status?.github_configured);

    if (this._shareResult) {
      return this._renderShareSuccess(this._shareResult);
    }

    return html`
      <section class="card">
        <h2>Choose Share Destination</h2>
        <p class="muted">
          Only the exact sanitized bundle you reviewed (<code>${this._preview.preview_hash.slice(0, 12)}</code>) will be exported.
        </p>

        <div class="provider-grid">
          <button
            class="provider-card ${this._selectedProvider === "github_gist" ? "selected" : ""}"
            ?disabled=${!githubReady}
            @click=${() => {
              this._selectedProvider = "github_gist";
            }}
          >
            <h3>GitHub Gist</h3>
            <p>
              ${githubReady
                ? "Publish all bundle files to your GitHub account as a clean shareable URL."
                : "Not configured yet. Add your own GitHub PAT under Settings → Devices & Services → Sharing Is Caring → Reconfigure."}
            </p>
          </button>

          <button
            class="provider-card ${this._selectedProvider === "local" ? "selected" : ""}"
            @click=${() => {
              this._selectedProvider = "local";
            }}
          >
            <h3>Local Copy / Download</h3>
            <p>
              Zero cloud requests. Export and download all sanitized files directly to your device.
            </p>
          </button>
        </div>

        ${this._selectedProvider === "github_gist" && githubReady
          ? html`
              <div class="visibility-box">
                <label class="field">
                  <span>Gist Visibility</span>
                  <select
                    class="input"
                    .value=${this._visibility}
                    @change=${(e: Event) => {
                      this._visibility = (e.target as HTMLSelectElement).value as
                        | "secret"
                        | "public";
                    }}
                  >
                    <option value="secret">Secret (Unlisted — only people with the URL)</option>
                    <option value="public">Public (Listed on your GitHub profile)</option>
                  </select>
                </label>
              </div>
            `
          : nothing}

        ${needsConfirm
          ? html`
              <label class="checkbox-label confirm-box">
                <input
                  type="checkbox"
                  .checked=${this._confirmReviewItems}
                  @change=${(e: Event) => {
                    this._confirmReviewItems = (e.target as HTMLInputElement).checked;
                  }}
                />
                <span>
                  I have inspected the ${this._preview.audit.counts.needs_review} item(s) marked
                  <strong>Needs Review</strong> and confirmed no personal data remains.
                </span>
              </label>
            `
          : nothing}

        <div class="actions-bar">
          <button class="btn btn-secondary" @click=${() => (this._step = 2)}>
            ← Back to Preview
          </button>
          <button
            class="btn btn-primary"
            ?disabled=${this._loading || (needsConfirm && !this._confirmReviewItems)}
            @click=${() => void this._publishBundle()}
          >
            ${this._loading
              ? "Publishing..."
              : this._selectedProvider === "github_gist"
                ? "Publish Sanitized Gist"
                : "Export Locally"}
          </button>
        </div>
      </section>
    `;
  }

  private _renderShareSuccess(result: ShareResult) {
    return html`
      <section class="card">
        <div class="audit-banner audit-clean">
          <div>
            <strong>Sanitized Ability Ready!</strong>
            <p>
              ${result.share_url
                ? `Published to GitHub Gist (${result.visibility}).`
                : "Sanitized bundle exported locally (zero external requests made)."}
            </p>
          </div>
        </div>

        ${result.share_url
          ? html`
              <div class="url-row">
                <label class="field flex-grow">
                  <span>Shareable URL</span>
                  <input type="text" class="input" readonly .value=${result.share_url} />
                </label>
                <button
                  class="btn btn-primary"
                  @click=${() => void this._copyText("share_url", result.share_url ?? "")}
                >
                  ${this._copiedKey === "share_url" ? "Copied!" : "Copy URL"}
                </button>
                <a
                  class="btn btn-secondary"
                  href=${result.share_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open
                </a>
              </div>
            `
          : nothing}

        ${result.my_ha_import_url
          ? html`
              <div class="url-row">
                <label class="field flex-grow">
                  <span>1-Click My Home Assistant Blueprint Import URL</span>
                  <input type="text" class="input" readonly .value=${result.my_ha_import_url} />
                </label>
                <button
                  class="btn btn-secondary"
                  @click=${() =>
                    void this._copyText("my_ha_url", result.my_ha_import_url ?? "")}
                >
                  ${this._copiedKey === "my_ha_url" ? "Copied!" : "Copy Import Link"}
                </button>
              </div>
            `
          : nothing}

        <div class="actions-bar">
          <button
            class="btn btn-secondary"
            @click=${() => this._downloadAllFiles(result.files)}
          >
            Download All Files
          </button>
          <button class="btn btn-primary" @click=${() => this._resetWizard()}>
            Share Another Ability
          </button>
        </div>
      </section>
    `;
  }

  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--primary-background-color, #fafafa);
      color: var(--primary-text-color, #212121);
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
    }

    .header {
      background: var(--app-header-background-color, var(--primary-color, #03a9f4));
      color: var(--app-header-text-color, #ffffff);
      padding: 20px 24px;
    }

    .header-inner {
      max-width: 1120px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }

    h1 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 500;
    }

    h2 {
      margin: 0 0 12px;
      font-size: 1.2rem;
    }

    h3 {
      margin: 0 0 8px;
      font-size: 1rem;
    }

    .subtitle {
      margin: 4px 0 0;
      opacity: 0.9;
      font-size: 0.92rem;
    }

    .stepper {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .step-pill {
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.16);
      font-size: 0.85rem;
    }

    .step-pill.active {
      background: #ffffff;
      color: var(--primary-color, #03a9f4);
      font-weight: 600;
    }

    .step-pill.done {
      background: rgba(255, 255, 255, 0.32);
    }

    .container {
      max-width: 1120px;
      margin: 24px auto;
      padding: 0 16px 40px;
    }

    .card {
      background: var(--card-background-color, #ffffff);
      border-radius: var(--ha-card-border-radius, 12px);
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      padding: 20px;
      box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0, 0, 0, 0.06));
    }

    .alert {
      padding: 12px 16px;
      border-radius: 8px;
      margin-bottom: 16px;
    }

    .alert-error {
      background: rgba(219, 68, 55, 0.12);
      border: 1px solid var(--error-color, #db4437);
      color: var(--error-color, #db4437);
    }

    .filter-row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 16px;
      align-items: center;
    }

    .input {
      width: 100%;
      box-sizing: border-box;
      padding: 9px 12px;
      border-radius: 8px;
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.22));
      background: var(--primary-background-color, #ffffff);
      color: var(--primary-text-color, #212121);
      font-size: 0.95rem;
    }

    .filter-row .input {
      flex: 1 1 260px;
    }

    .pill-group {
      display: flex;
      gap: 6px;
    }

    .pill-btn {
      padding: 7px 14px;
      border-radius: 999px;
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.2));
      background: transparent;
      color: inherit;
      cursor: pointer;
    }

    .pill-btn.selected {
      background: var(--primary-color, #03a9f4);
      border-color: var(--primary-color, #03a9f4);
      color: #ffffff;
    }

    .entity-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 10px;
      max-height: 320px;
      overflow-y: auto;
      padding: 4px 2px;
    }

    .entity-card {
      text-align: left;
      padding: 12px;
      border-radius: 10px;
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.15));
      background: var(--primary-background-color, #fafafa);
      color: inherit;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .entity-card.selected {
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.25);
    }

    .badge {
      align-self: flex-start;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(3, 169, 244, 0.15);
      color: var(--primary-color, #03a9f4);
    }

    .badge-script {
      background: rgba(156, 39, 176, 0.14);
      color: #9c27b0;
    }

    .entity-name {
      font-weight: 500;
    }

    .entity-id,
    .muted {
      font-size: 0.85rem;
      color: var(--secondary-text-color, #666666);
    }

    .options-box {
      margin-top: 20px;
      padding-top: 16px;
      border-top: 1px solid var(--divider-color, rgba(0, 0, 0, 0.1));
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
      margin-bottom: 12px;
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 0.88rem;
    }

    .flex-grow {
      flex: 1 1 300px;
    }

    .checkbox-row {
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
      margin-top: 8px;
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      font-size: 0.92rem;
    }

    .audit-banner {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      border-radius: 10px;
      margin-bottom: 16px;
    }

    .audit-banner p {
      margin: 4px 0 0;
      font-size: 0.88rem;
    }

    .audit-clean {
      background: rgba(67, 160, 71, 0.14);
      border: 1px solid var(--success-color, #43a047);
    }

    .audit-needs_review {
      background: rgba(255, 152, 0, 0.15);
      border: 1px solid var(--warning-color, #ff9800);
    }

    .audit-blocked {
      background: rgba(219, 68, 55, 0.15);
      border: 1px solid var(--error-color, #db4437);
    }

    .hash-pill {
      padding: 4px 10px;
      border-radius: 6px;
      background: rgba(0, 0, 0, 0.08);
      font-size: 0.82rem;
    }

    .dep-strip {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .dep-group {
      padding: 12px;
      border-radius: 8px;
      background: var(--primary-background-color, #f5f5f5);
      font-size: 0.88rem;
    }

    .chip-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }

    .chip {
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(3, 169, 244, 0.12);
      font-family: monospace;
      font-size: 0.8rem;
    }

    .chip-role {
      background: rgba(103, 58, 183, 0.12);
    }

    .findings-box {
      padding: 12px 16px;
      border-radius: 8px;
      margin-bottom: 16px;
    }

    .findings-box ul {
      margin: 8px 0 0;
      padding-left: 20px;
    }

    .findings-box li {
      margin-bottom: 8px;
    }

    .findings-blocked {
      background: rgba(219, 68, 55, 0.1);
      border-left: 4px solid var(--error-color, #db4437);
    }

    .findings-review {
      background: rgba(255, 152, 0, 0.1);
      border-left: 4px solid var(--warning-color, #ff9800);
    }

    .snippet {
      margin-top: 4px;
      font-family: monospace;
      font-size: 0.85rem;
      opacity: 0.85;
    }

    .override-input {
      margin-top: 6px;
    }

    .redaction-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: flex-end;
      margin-bottom: 14px;
    }

    .details-box {
      margin-bottom: 16px;
      padding: 10px 12px;
      border-radius: 8px;
      background: var(--primary-background-color, #f5f5f5);
      font-size: 0.88rem;
    }

    .details-box summary {
      cursor: pointer;
      font-weight: 500;
    }

    .code-viewer {
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.15));
      border-radius: 10px;
      overflow: hidden;
      margin-bottom: 16px;
    }

    .tab-bar {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      background: var(--primary-background-color, #f0f0f0);
      padding: 6px 10px;
      border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    }

    .tabs,
    .tab-actions {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }

    .tab-btn {
      padding: 6px 12px;
      border: none;
      border-radius: 6px;
      background: transparent;
      color: inherit;
      cursor: pointer;
      font-family: monospace;
      font-size: 0.85rem;
    }

    .tab-btn.active {
      background: var(--card-background-color, #ffffff);
      font-weight: 600;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    .code-pre {
      margin: 0;
      padding: 14px;
      max-height: 420px;
      overflow: auto;
      font-size: 0.84rem;
      line-height: 1.45;
      background: var(--code-editor-background-color, #1e1e1e);
      color: #e6e6e6;
    }

    .provider-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
      margin: 16px 0;
    }

    .provider-card {
      text-align: left;
      padding: 16px;
      border-radius: 10px;
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.15));
      background: var(--primary-background-color, #fafafa);
      color: inherit;
      cursor: pointer;
    }

    .provider-card.selected {
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.25);
    }

    .provider-card:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }

    .visibility-box,
    .confirm-box {
      margin: 14px 0;
    }

    .confirm-box {
      padding: 12px;
      border-radius: 8px;
      background: rgba(255, 152, 0, 0.12);
    }

    .url-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: flex-end;
      margin-bottom: 14px;
    }

    .actions-bar {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid var(--divider-color, rgba(0, 0, 0, 0.1));
    }

    .btn {
      padding: 9px 18px;
      border-radius: 8px;
      border: none;
      font-size: 0.92rem;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn-primary {
      background: var(--primary-color, #03a9f4);
      color: #ffffff;
    }

    .btn-secondary {
      background: var(--secondary-background-color, #e0e0e0);
      color: var(--primary-text-color, #212121);
    }

    .btn-small {
      padding: 5px 10px;
      font-size: 0.8rem;
      background: var(--card-background-color, #ffffff);
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.15));
      color: inherit;
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "sharing-is-caring-panel": SharingIsCaringPanel;
  }
}
