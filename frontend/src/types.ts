export interface HomeAssistant {
  callWS<T = unknown>(msg: Record<string, unknown>): Promise<T>;
  user?: {
    is_admin?: boolean;
    name?: string;
  };
}

export interface ProviderInfo {
  id: string;
  name: string;
  configured: boolean;
  supports_visibility: boolean;
}

export interface IntegrationStatus {
  github_configured: boolean;
  default_visibility: "secret" | "public";
  available_providers: ProviderInfo[];
}

export interface ShareableItem {
  entity_id: string;
  domain: "automation" | "script";
  name: string;
}

export interface AuditFinding {
  severity: "auto_redacted" | "needs_review" | "blocked";
  category: string;
  location: string;
  message: string;
  replacement: string | null;
  snippet: string | null;
}

export interface AuditReport {
  status: "clean" | "needs_review" | "blocked";
  can_publish: boolean;
  counts: {
    auto_redacted: number;
    needs_review: number;
    blocked: number;
  };
  auto_redacted: AuditFinding[];
  needs_review: AuditFinding[];
  blocked: AuditFinding[];
}

export interface PreviewResponse {
  slug: string;
  title: string;
  description: string;
  files: Record<string, string>;
  package_filename: string;
  blueprint_filename: string | null;
  dependencies: {
    helpers: Array<{ entity_id: string; domain: string; name: string; source_type: string }>;
    companion_scripts: Array<{ entity_id: string; alias: string }>;
    external_roles: Array<{
      placeholder_entity_id: string;
      blueprint_input_key: string;
      domain: string;
      label: string;
    }>;
  };
  audit: AuditReport;
  preview_hash: string;
}

export interface ShareResult {
  provider: string;
  share_url: string | null;
  visibility: string;
  raw_blueprint_url: string | null;
  my_ha_import_url: string | null;
  gist_id: string | null;
  files: Record<string, string>;
}
