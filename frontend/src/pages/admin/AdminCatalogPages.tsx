import { Badge, Button, Card, Typography } from "../../lib/watercolor";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import adminApi from "../../api/adminClient";
import { AdminPageIntro } from "./adminCommon";
import { formatPricingSummary } from "../../shared/pricing";
import { useI18n } from "../../i18n";

type CatalogKey =
  | "brands"
  | "providers"
  | "provider-endpoints"
  | "provider-credentials"
  | "public-models"
  | "upstream-models"
  | "model-routes";

type CatalogItem = Record<string, any> & { id: string; enabled?: boolean };
type CatalogState = Record<CatalogKey, CatalogItem[]>;
type TranslateFn = (key: string, params?: Record<string, string | number>) => string;

type CatalogConfig = {
  key: CatalogKey;
  path: string;
  titleKey: string;
  descriptionKey: string;
  singularKey: string;
  primary: (item: CatalogItem, state: CatalogState) => string;
  secondary: (item: CatalogItem, state: CatalogState, t: TranslateFn) => string;
  meta: (item: CatalogItem, state: CatalogState, t: TranslateFn) => Array<[string, string]>;
};

type CreateField = {
  name: string;
  labelKey: string;
  type: "text" | "number" | "boolean" | "select" | "json" | "secret" | "textarea";
  required?: boolean;
  placeholder?: string;
  helper?: string;
  options?: Array<{ value: string; label: string }>;
  optionsFrom?: CatalogKey;
  optionLabel?: (item: CatalogItem, state: CatalogState) => string;
  defaultValue?: unknown;
};

const emptyState: CatalogState = {
  brands: [],
  providers: [],
  "provider-endpoints": [],
  "provider-credentials": [],
  "public-models": [],
  "upstream-models": [],
  "model-routes": [],
};

const catalogKeys = Object.keys(emptyState) as CatalogKey[];

const byId = (items: CatalogItem[], id: string | null | undefined) => items.find((item) => item.id === id);

const jsonSummary = (value: unknown) => {
  if (!value || typeof value !== "object") return "-";
  return JSON.stringify(value);
};

const EnabledBadge = ({ enabled }: { enabled?: boolean }) => {
  const { t } = useI18n();
  if (typeof enabled !== "boolean") return null;
  return <Badge variant={enabled ? "primary" : "warning"}>{t(enabled ? "common.enabled" : "common.disabled")}</Badge>;
};

const configs: Record<CatalogKey, CatalogConfig> = {
  brands: {
    key: "brands",
    path: "/admin/brands",
    titleKey: "catalog.brands.title",
    descriptionKey: "catalog.brands.desc",
    singularKey: "catalog.brands.singular",
    primary: (item) => item.name || item.slug,
    secondary: (item) => item.slug,
    meta: (item) => [
      ["catalog.meta.id", item.id],
      ["catalog.meta.icon", item.icon_url || item.icon_slug || "-"],
      ["catalog.meta.created", item.created_at || "-"],
    ],
  },
  providers: {
    key: "providers",
    path: "/admin/providers",
    titleKey: "catalog.providers.title",
    descriptionKey: "catalog.providers.desc",
    singularKey: "catalog.providers.singular",
    primary: (item) => item.name || item.slug,
    secondary: (item) => item.slug,
    meta: (item, state) => [
      ["catalog.meta.id", item.id],
      ["catalog.meta.endpoints", String(state["provider-endpoints"].filter((endpoint) => endpoint.provider_id === item.id).length)],
      ["catalog.meta.upstreamModels", String(state["upstream-models"].filter((model) => model.provider_id === item.id).length)],
    ],
  },
  "provider-endpoints": {
    key: "provider-endpoints",
    path: "/admin/provider-endpoints",
    titleKey: "catalog.providerEndpoints.title",
    descriptionKey: "catalog.providerEndpoints.desc",
    singularKey: "catalog.providerEndpoints.singular",
    primary: (item) => item.display_name || item.slug,
    secondary: (item, state) => `${byId(state.providers, item.provider_id)?.name || item.provider_id} / ${item.slug}`,
    meta: (item, state) => [
      ["catalog.meta.provider", byId(state.providers, item.provider_id)?.name || item.provider_id],
      ["catalog.meta.baseUrl", item.base_url || "-"],
      ["catalog.meta.health", item.health_state || "-"],
      ["catalog.meta.credentials", String(state["provider-credentials"].filter((credential) => credential.provider_endpoint_id === item.id).length)],
    ],
  },
  "provider-credentials": {
    key: "provider-credentials",
    path: "/admin/provider-credentials",
    titleKey: "catalog.providerCredentials.title",
    descriptionKey: "catalog.providerCredentials.desc",
    singularKey: "catalog.providerCredentials.singular",
    primary: (item) => item.display_name || item.id,
    secondary: (item, state, t) => {
      const endpoint = byId(state["provider-endpoints"], item.provider_endpoint_id);
      const provider = byId(state.providers, endpoint?.provider_id);
      return `${provider?.name || t("catalog.meta.provider")} / ${endpoint?.display_name || item.provider_endpoint_id}`;
    },
    meta: (item, state, t) => {
      const endpoint = byId(state["provider-endpoints"], item.provider_endpoint_id);
      const secretValue = item.has_secret
        ? item.secret_last4
          ? t("catalog.savedLast4", { last4: item.secret_last4 })
          : t("catalog.saved")
        : t("catalog.missing");
      return [
        ["catalog.meta.endpoint", endpoint?.display_name || item.provider_endpoint_id],
        ["catalog.meta.secret", secretValue],
        ["catalog.meta.health", item.health_state || "-"],
        ["catalog.meta.cooldown", item.cooldown_until || "-"],
      ];
    },
  },
  "public-models": {
    key: "public-models",
    path: "/admin/public-models",
    titleKey: "catalog.publicModels.title",
    descriptionKey: "catalog.publicModels.desc",
    singularKey: "catalog.publicModels.singular",
    primary: (item) => item.display_name || item.slug,
    secondary: (item, state, t) => `${item.slug} / ${byId(state.brands, item.brand_id)?.name || t("catalog.noBrand")}`,
    meta: (item, state) => [
      ["catalog.meta.brand", byId(state.brands, item.brand_id)?.name || item.brand_id || "-"],
      ["catalog.meta.category", item.category || "-"],
      ["catalog.meta.multiplier", `x${item.multiplier ?? 1}`],
      ["catalog.meta.routes", String(state["model-routes"].filter((route) => route.public_model_id === item.id).length)],
    ],
  },
  "upstream-models": {
    key: "upstream-models",
    path: "/admin/upstream-models",
    titleKey: "catalog.upstreamModels.title",
    descriptionKey: "catalog.upstreamModels.desc",
    singularKey: "catalog.upstreamModels.singular",
    primary: (item) => item.display_name || item.upstream_name,
    secondary: (item, state) => `${byId(state.providers, item.provider_id)?.name || item.provider_id} / ${item.upstream_name}`,
    meta: (item, state) => [
      ["catalog.meta.provider", byId(state.providers, item.provider_id)?.name || item.provider_id],
      ["catalog.meta.context", item.context_window ? String(item.context_window) : "-"],
      ["catalog.meta.capabilities", jsonSummary(item.capabilities)],
      ["catalog.meta.routes", String(state["model-routes"].filter((route) => route.upstream_model_id === item.id).length)],
    ],
  },
  "model-routes": {
    key: "model-routes",
    path: "/admin/model-routes",
    titleKey: "catalog.modelRoutes.title",
    descriptionKey: "catalog.modelRoutes.desc",
    singularKey: "catalog.modelRoutes.singular",
    primary: (item, state) => byId(state["public-models"], item.public_model_id)?.slug || item.public_model_id,
    secondary: (item, state, t) => {
      const upstream = byId(state["upstream-models"], item.upstream_model_id);
      const provider = byId(state.providers, upstream?.provider_id);
      return `${provider?.slug || t("catalog.meta.provider")} / ${upstream?.upstream_name || item.upstream_model_id}`;
    },
    meta: (item, state) => [
      ["catalog.meta.publicModel", byId(state["public-models"], item.public_model_id)?.slug || item.public_model_id],
      ["catalog.meta.upstream", byId(state["upstream-models"], item.upstream_model_id)?.upstream_name || item.upstream_model_id],
      ["catalog.meta.credential", byId(state["provider-credentials"], item.provider_credential_id)?.display_name || item.provider_credential_id || "-"],
      ["catalog.meta.priorityWeight", `${item.priority ?? "-"} / ${item.weight ?? "-"}`],
    ],
  },
};

const upsertTemplates: Record<CatalogKey, Record<string, unknown>> = {
  brands: { name: "Brave Search", slug: "brave-search", icon_slug: "brave", icon_url: "", enabled: true },
  providers: { name: "Brave Search", slug: "brave-search", icon_slug: "brave", icon_url: "", enabled: true },
  "provider-endpoints": {
    provider_id: "provider-id",
    slug: "web",
    display_name: "Brave Web Search",
    base_url: "https://api.search.brave.com/res/v1",
    enabled: true,
    health_state: "healthy",
  },
  "provider-credentials": {
    provider_endpoint_id: "endpoint-id",
    display_name: "Brave Search main key",
    api_key: "BSAL...",
    enabled: true,
    health_state: "healthy",
  },
  "public-models": {
    slug: "brave-web-search",
    display_name: "Brave Web Search",
    description: "Search product model exposed as APICred tool capacity.",
    brand_id: "brand-id",
    category: "search",
    enabled: true,
    pricing: { mode: "request", unit: "request", price: 0 },
    multiplier: 1,
  },
  "upstream-models": {
    provider_id: "provider-id",
    upstream_name: "web-search",
    display_name: "Brave Web Search",
    context_window: null,
    capabilities: { search: true, web: true },
    default_pricing: { mode: "request", unit: "request" },
    enabled: true,
  },
  "model-routes": {
    public_model_id: "public-model-id",
    upstream_model_id: "upstream-model-id",
    provider_credential_id: "credential-id",
    priority: 1,
    weight: 1,
    enabled: true,
    quota_unit: "requests",
    quota_rules: { day: 2000 },
  },
};

const createFields: Record<CatalogKey, CreateField[]> = {
  brands: [
    { name: "name", labelKey: "catalog.field.name", type: "text", required: true, placeholder: "OpenAI" },
    { name: "slug", labelKey: "catalog.field.slug", type: "text", required: true, placeholder: "openai" },
    { name: "icon_slug", labelKey: "catalog.field.iconSlug", type: "text", placeholder: "openai" },
    { name: "icon_url", labelKey: "catalog.field.iconUrl", type: "text", placeholder: "https://..." },
    { name: "enabled", labelKey: "catalog.field.enabled", type: "boolean", defaultValue: true },
  ],
  providers: [
    { name: "name", labelKey: "catalog.field.name", type: "text", required: true, placeholder: "OpenAI" },
    { name: "slug", labelKey: "catalog.field.slug", type: "text", required: true, placeholder: "openai" },
    { name: "icon_slug", labelKey: "catalog.field.iconSlug", type: "text", placeholder: "openai" },
    { name: "icon_url", labelKey: "catalog.field.iconUrl", type: "text", placeholder: "https://..." },
    { name: "enabled", labelKey: "catalog.field.enabled", type: "boolean", defaultValue: true },
  ],
  "provider-endpoints": [
    {
      name: "provider_id",
      labelKey: "catalog.field.provider",
      type: "select",
      required: true,
      optionsFrom: "providers",
      optionLabel: (item) => `${item.name || item.slug} (${item.slug})`,
    },
    { name: "slug", labelKey: "catalog.field.slug", type: "text", required: true, placeholder: "default" },
    { name: "display_name", labelKey: "catalog.field.displayName", type: "text", required: true, placeholder: "OpenAI Default" },
    { name: "base_url", labelKey: "catalog.field.baseUrl", type: "text", required: true, placeholder: "https://api.openai.com/v1" },
    {
      name: "health_state",
      labelKey: "catalog.field.healthState",
      type: "select",
      defaultValue: "healthy",
      options: [
        { value: "healthy", label: "catalog.field.healthHealthy" },
        { value: "disabled", label: "catalog.field.healthDisabled" },
        { value: "cooldown", label: "catalog.field.healthCooldown" },
      ],
    },
    { name: "cooldown_until", labelKey: "catalog.field.cooldownUntil", type: "text", placeholder: "2026-07-04T12:00:00Z" },
    { name: "enabled", labelKey: "catalog.field.enabled", type: "boolean", defaultValue: true },
  ],
  "provider-credentials": [
    {
      name: "provider_endpoint_id",
      labelKey: "catalog.field.endpoint",
      type: "select",
      required: true,
      optionsFrom: "provider-endpoints",
      optionLabel: (item, state) => {
        const provider = byId(state.providers, item.provider_id);
        return `${provider?.slug || item.provider_id} / ${item.display_name || item.slug}`;
      },
    },
    { name: "display_name", labelKey: "catalog.field.displayName", type: "text", required: true, placeholder: "OpenAI production key" },
    { name: "api_key", labelKey: "catalog.field.apiKey", type: "secret", required: true, placeholder: "sk-..." },
    {
      name: "health_state",
      labelKey: "catalog.field.healthState",
      type: "select",
      defaultValue: "healthy",
      options: [
        { value: "healthy", label: "catalog.field.healthHealthy" },
        { value: "disabled", label: "catalog.field.healthDisabled" },
        { value: "cooldown", label: "catalog.field.healthCooldown" },
      ],
    },
    { name: "cooldown_until", labelKey: "catalog.field.cooldownUntil", type: "text", placeholder: "2026-07-04T12:00:00Z" },
    { name: "enabled", labelKey: "catalog.field.enabled", type: "boolean", defaultValue: true },
  ],
  "public-models": [
    { name: "slug", labelKey: "catalog.field.slug", type: "text", required: true, placeholder: "gpt-4o-mini" },
    { name: "display_name", labelKey: "catalog.field.displayName", type: "text", required: true, placeholder: "GPT-4o mini" },
    { name: "description", labelKey: "catalog.field.description", type: "textarea", placeholder: "面向用户展示的模型说明" },
    {
      name: "brand_id",
      labelKey: "catalog.field.brand",
      type: "select",
      optionsFrom: "brands",
      optionLabel: (item) => `${item.name || item.slug} (${item.slug})`,
    },
    {
      name: "category",
      labelKey: "catalog.field.category",
      type: "select",
      defaultValue: "llm",
      options: ["llm", "image", "embedding", "audio", "moderation", "realtime", "search", "agent", "robotics"].map((value) => ({ value, label: value })),
    },
    { name: "pricing", labelKey: "catalog.field.pricingJson", type: "json", required: true, defaultValue: { mode: "request", unit: "request", price: 0 } },
    { name: "multiplier", labelKey: "catalog.field.multiplier", type: "number", defaultValue: 1 },
    { name: "enabled", labelKey: "catalog.field.enabled", type: "boolean", defaultValue: true },
  ],
  "upstream-models": [
    {
      name: "provider_id",
      labelKey: "catalog.field.provider",
      type: "select",
      required: true,
      optionsFrom: "providers",
      optionLabel: (item) => `${item.name || item.slug} (${item.slug})`,
    },
    { name: "upstream_name", labelKey: "catalog.field.upstreamName", type: "text", required: true, placeholder: "gpt-4o-mini" },
    { name: "display_name", labelKey: "catalog.field.displayName", type: "text", required: true, placeholder: "GPT-4o mini" },
    { name: "context_window", labelKey: "catalog.field.contextWindow", type: "number", placeholder: "128000" },
    { name: "capabilities", labelKey: "catalog.field.capabilitiesJson", type: "json", required: true, defaultValue: { chat: true } },
    { name: "default_pricing", labelKey: "catalog.field.defaultPricingJson", type: "json", required: true, defaultValue: { mode: "token", unit: "1M tokens" } },
    { name: "enabled", labelKey: "catalog.field.enabled", type: "boolean", defaultValue: true },
  ],
  "model-routes": [
    {
      name: "public_model_id",
      labelKey: "catalog.field.publicModel",
      type: "select",
      required: true,
      optionsFrom: "public-models",
      optionLabel: (item) => `${item.display_name || item.slug} (${item.slug})`,
    },
    {
      name: "upstream_model_id",
      labelKey: "catalog.field.upstreamModel",
      type: "select",
      required: true,
      optionsFrom: "upstream-models",
      optionLabel: (item, state) => `${byId(state.providers, item.provider_id)?.slug || item.provider_id} / ${item.upstream_name}`,
    },
    {
      name: "provider_credential_id",
      labelKey: "catalog.field.credential",
      type: "select",
      optionsFrom: "provider-credentials",
      optionLabel: (item, state) => {
        const endpoint = byId(state["provider-endpoints"], item.provider_endpoint_id);
        const provider = byId(state.providers, endpoint?.provider_id);
        return `${provider?.slug || "provider"} / ${item.display_name || item.id}`;
      },
    },
    { name: "base_url_override", labelKey: "catalog.field.baseUrlOverride", type: "text", placeholder: "可选" },
    { name: "priority", labelKey: "catalog.field.priority", type: "number", defaultValue: 1 },
    { name: "weight", labelKey: "catalog.field.weight", type: "number", defaultValue: 1 },
    {
      name: "quota_unit",
      labelKey: "catalog.field.quotaUnit",
      type: "select",
      defaultValue: "tokens",
      options: [
        { value: "tokens", label: "tokens" },
        { value: "requests", label: "requests" },
      ],
    },
    { name: "quota_rules", labelKey: "catalog.field.quotaRulesJson", type: "json", required: true, defaultValue: { day: 2000 } },
    { name: "enabled", labelKey: "catalog.field.enabled", type: "boolean", defaultValue: true },
  ],
};

async function loadCatalogState(): Promise<CatalogState> {
  const responses = await Promise.all(catalogKeys.map((key) => adminApi.get(`/admin/${key}`)));
  return catalogKeys.reduce((next, key, index) => {
    next[key] = Array.isArray(responses[index].data) ? responses[index].data : [];
    return next;
  }, { ...emptyState });
}

const MetaGrid = ({ rows }: { rows: Array<[string, string]> }) => {
  const { t } = useI18n();
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {rows.map(([label, value]) => (
        <div key={label} className="min-w-0 border border-slate-200 bg-slate-50 px-3 py-2">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{t(label)}</div>
          <div className="mt-1 break-words text-sm text-slate-800">{value || "-"}</div>
        </div>
      ))}
    </div>
  );
};

const CatalogCard = ({ config, item, state }: { config: CatalogConfig; item: CatalogItem; state: CatalogState }) => {
  const navigate = useNavigate();
  const { t } = useI18n();
  return (
    <button
      type="button"
      onClick={() => navigate(`${config.path}/${item.id}`)}
      className="block w-full border border-slate-200 bg-white p-4 text-left transition hover:border-slate-400 hover:bg-slate-50"
    >
      <div className="flex min-h-10 items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-900">{config.primary(item, state)}</div>
          <div className="mt-1 truncate text-xs text-slate-500">{config.secondary(item, state, t)}</div>
        </div>
        <EnabledBadge enabled={item.enabled} />
      </div>
      <div className="mt-4 space-y-2">
        {config.meta(item, state, t).slice(0, 3).map(([label, value]) => (
          <div key={label} className="flex gap-3 text-xs">
            <span className="w-24 shrink-0 text-slate-400">{t(label)}</span>
            <span className="min-w-0 truncate text-slate-700">{value || "-"}</span>
          </div>
        ))}
      </div>
    </button>
  );
};

const RelatedLinks = ({ item, state, catalogKey }: { item: CatalogItem; state: CatalogState; catalogKey: CatalogKey }) => {
  const { t } = useI18n();
  const links: Array<{ label: string; path: string; name: string }> = [];
  const push = (labelKey: string, configKey: CatalogKey, related: CatalogItem | undefined, name?: string) => {
    if (!related) return;
    links.push({ label: t(labelKey), path: `${configs[configKey].path}/${related.id}`, name: name || configs[configKey].primary(related, state) });
  };

  if (catalogKey === "provider-endpoints") push("catalog.meta.provider", "providers", byId(state.providers, item.provider_id));
  if (catalogKey === "provider-credentials") {
    const endpoint = byId(state["provider-endpoints"], item.provider_endpoint_id);
    push("catalog.meta.endpoint", "provider-endpoints", endpoint);
    push("catalog.meta.provider", "providers", byId(state.providers, endpoint?.provider_id));
  }
  if (catalogKey === "public-models") push("catalog.meta.brand", "brands", byId(state.brands, item.brand_id));
  if (catalogKey === "upstream-models") push("catalog.meta.provider", "providers", byId(state.providers, item.provider_id));
  if (catalogKey === "model-routes") {
    push("catalog.meta.publicModel", "public-models", byId(state["public-models"], item.public_model_id));
    const upstream = byId(state["upstream-models"], item.upstream_model_id);
    push("catalog.meta.upstream", "upstream-models", upstream);
    push("catalog.meta.provider", "providers", byId(state.providers, upstream?.provider_id));
    push("catalog.meta.credential", "provider-credentials", byId(state["provider-credentials"], item.provider_credential_id));
  }

  if (!links.length) return null;
  return (
    <Card className="p-6">
      <Typography variant="h6">{t("catalog.related")}</Typography>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        {links.map((link) => (
          <Link key={`${link.label}-${link.path}`} to={link.path} className="border border-slate-200 bg-white px-4 py-3 hover:bg-slate-50">
            <div className="text-xs text-slate-400">{link.label}</div>
            <div className="mt-1 text-sm font-semibold text-slate-900">{link.name}</div>
          </Link>
        ))}
      </div>
    </Card>
  );
};

const DetailBody = ({ config, item, state }: { config: CatalogConfig; item: CatalogItem; state: CatalogState }) => {
  const { t } = useI18n();
  const pricing =
    config.key === "public-models"
      ? formatPricingSummary(item.pricing, t)
      : config.key === "upstream-models"
        ? formatPricingSummary(item.default_pricing, t)
        : [];
  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <Typography variant="h5" className="break-words">{config.primary(item, state)}</Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1 break-words">
              {config.secondary(item, state, t)}
            </Typography>
          </div>
          <EnabledBadge enabled={item.enabled} />
        </div>
        <div className="mt-6">
          <MetaGrid rows={config.meta(item, state, t)} />
        </div>
      </Card>

      {pricing.length > 0 && (
        <Card className="p-6">
          <Typography variant="h6">{t("catalog.pricingInfo")}</Typography>
          <div className="mt-4 space-y-2 text-sm text-slate-700">
            {pricing.map((line) => <div key={line}>{line}</div>)}
          </div>
        </Card>
      )}

      <RelatedLinks item={item} state={state} catalogKey={config.key} />

      <Card className="p-6">
        <Typography variant="h6">{t("catalog.rawData")}</Typography>
        <pre className="mt-4 max-h-[460px] overflow-auto border border-slate-200 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {JSON.stringify(item, null, 2)}
        </pre>
      </Card>
    </div>
  );
};

export const CatalogListPage = ({ catalogKey }: { catalogKey: CatalogKey }) => {
  const config = configs[catalogKey];
  const navigate = useNavigate();
  const { t } = useI18n();
  const [state, setState] = useState<CatalogState>(emptyState);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  const refresh = async () => {
    const next = await loadCatalogState();
    setState(next);
    return next;
  };

  useEffect(() => {
    let active = true;
    refresh()
      .then((next) => {
        if (active) setState(next);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const items = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return state[catalogKey];
    return state[catalogKey].filter((item) => JSON.stringify(item).toLowerCase().includes(normalized));
  }, [catalogKey, query, state]);

  return (
    <div className="space-y-6">
      <AdminPageIntro title={t(config.titleKey)} description={t(config.descriptionKey)} />
      <Card className="p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <Typography variant="h6">{t("catalog.listTitle", { singular: t(config.singularKey) })}</Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              {loading ? t("catalog.loading") : t("catalog.listCount", { loaded: items.length, total: state[catalogKey].length })}
            </Typography>
          </div>
          <div className="flex flex-col gap-2 md:flex-row md:items-center">
            <input
              className="w-full border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-300 md:w-80"
              placeholder={t("catalog.search", { singular: t(config.singularKey) })}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <Button buttonStyle="filled" variant="primary" onClick={() => navigate(`${config.path}/new`)}>
              {t("catalog.new", { singular: t(config.singularKey) })}
            </Button>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-1 gap-3 xl:grid-cols-2">
          {items.map((item) => <CatalogCard key={item.id} config={config} item={item} state={state} />)}
          {!loading && items.length === 0 && (
            <div className="border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">{t("catalog.noData")}</div>
          )}
        </div>
      </Card>
    </div>
  );
};

const initialFormValues = (catalogKey: CatalogKey): Record<string, unknown> => {
  const values: Record<string, unknown> = {};
  for (const field of createFields[catalogKey]) {
    if (field.type === "boolean") {
      values[field.name] = field.defaultValue ?? false;
    } else if (field.type === "json") {
      values[field.name] = JSON.stringify(field.defaultValue ?? {}, null, 2);
    } else if (field.defaultValue !== undefined) {
      values[field.name] = field.defaultValue;
    } else {
      values[field.name] = "";
    }
  }
  return values;
};

const fieldClass =
  "w-full border border-slate-300 bg-white px-3 py-3 text-sm text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-300";

const FieldLabel = ({ field }: { field: CreateField }) => {
  const { t } = useI18n();
  return (
    <span className="mb-2 block text-sm font-medium text-slate-700">
      {t(field.labelKey)}
      {field.required ? <span className="text-slate-500"> *</span> : null}
    </span>
  );
};

const FormField = ({
  field,
  value,
  state,
  onChange,
}: {
  field: CreateField;
  value: unknown;
  state: CatalogState;
  onChange: (value: unknown) => void;
}) => {
  const { t } = useI18n();
  const common = (
    <>
      <FieldLabel field={field} />
      {field.helper ? <div className="mb-2 text-xs text-slate-500">{field.helper}</div> : null}
    </>
  );

  if (field.type === "boolean") {
    return (
      <label className="flex min-h-[46px] items-center gap-3 border border-slate-200 bg-slate-50 px-3 py-2">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(event.target.checked)}
          className="h-4 w-4 accent-slate-800"
        />
        <span className="text-sm font-medium text-slate-700">{t(field.labelKey)}</span>
      </label>
    );
  }

  if (field.type === "select") {
    const relatedOptions =
      field.optionsFrom?.length
        ? state[field.optionsFrom].map((item) => ({
            value: item.id,
            label: field.optionLabel ? field.optionLabel(item, state) : String(item.name || item.slug || item.id),
          }))
        : [];
    const options = field.options ?? relatedOptions;
    return (
      <label className="block">
        {common}
        <select className={fieldClass} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)}>
          <option value="">{t("catalog.field.unselected")}</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {t(option.label)}
            </option>
          ))}
        </select>
      </label>
    );
  }

  if (field.type === "textarea" || field.type === "json") {
    return (
      <label className="block">
        {common}
        <textarea
          className={`${fieldClass} min-h-28 ${field.type === "json" ? "font-mono text-xs leading-5" : ""}`}
          value={String(value ?? "")}
          onChange={(event) => onChange(event.target.value)}
          placeholder={field.placeholder}
          spellCheck={field.type !== "json"}
        />
      </label>
    );
  }

  return (
    <label className="block">
      {common}
      <input
        className={fieldClass}
        type={field.type === "number" ? "number" : field.type === "secret" ? "password" : "text"}
        value={String(value ?? "")}
        onChange={(event) => onChange(event.target.value)}
        placeholder={field.placeholder}
      />
    </label>
  );
};

const buildPayload = (catalogKey: CatalogKey, values: Record<string, unknown>, t: TranslateFn): Record<string, unknown> => {
  const payload: Record<string, unknown> = {};
  for (const field of createFields[catalogKey]) {
    const value = values[field.name];
    if (field.type === "boolean") {
      payload[field.name] = Boolean(value);
      continue;
    }
    if (field.type === "number") {
      const raw = String(value ?? "").trim();
      if (!raw) {
        if (field.required) payload[field.name] = 0;
        continue;
      }
      const parsed = Number(raw);
      if (!Number.isFinite(parsed)) {
        throw new Error(t("catalog.errNumber", { label: t(field.labelKey) }));
      }
      payload[field.name] = parsed;
      continue;
    }
    if (field.type === "json") {
      const raw = String(value ?? "").trim();
      if (!raw) {
        if (field.required) throw new Error(t("catalog.errEmpty", { label: t(field.labelKey) }));
        continue;
      }
      try {
        payload[field.name] = JSON.parse(raw);
      } catch {
        throw new Error(t("catalog.errJson", { label: t(field.labelKey) }));
      }
      continue;
    }
    const text = String(value ?? "").trim();
    if (text) {
      payload[field.name] = text;
    } else if (field.required) {
      throw new Error(t("catalog.errEmpty", { label: t(field.labelKey) }));
    }
  }
  return payload;
};

export const CatalogCreatePage = ({ catalogKey }: { catalogKey: CatalogKey }) => {
  const config = configs[catalogKey];
  const navigate = useNavigate();
  const { t } = useI18n();
  const [state, setState] = useState<CatalogState>(emptyState);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [values, setValues] = useState<Record<string, unknown>>(() => initialFormValues(catalogKey));

  useEffect(() => {
    let active = true;
    loadCatalogState()
      .then((next) => {
        if (active) setState(next);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const payload = buildPayload(catalogKey, values, t);
      const response = await adminApi.post(`/admin/${catalogKey}`, payload);
      const id = response.data?.id;
      navigate(id ? `${config.path}/${id}` : config.path);
    } catch (error: any) {
      setError(error?.response?.data?.error?.message || error?.response?.data?.message || error?.message || t("catalog.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <Button buttonStyle="text" variant="secondary" onClick={() => navigate(config.path)}>
            {t("catalog.backToList")}
          </Button>
          <Typography variant="h5" className="mt-3">{t("catalog.newTitle", { singular: t(config.singularKey) })}</Typography>
          <Typography variant="body2" color="textSecondary" className="mt-1">{t(config.descriptionKey)}</Typography>
        </div>
        <Badge variant="secondary">{loading ? t("catalog.loadingDeps") : t(config.singularKey)}</Badge>
      </div>

      <Card className="p-6">
        {error ? <div className="mb-5 border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">{error}</div> : null}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {createFields[catalogKey].map((field) => (
            <div key={field.name} className={field.type === "json" || field.type === "textarea" ? "lg:col-span-2" : ""}>
              <FormField
                field={field}
                value={values[field.name]}
                state={state}
                onChange={(next) => setValues((current) => ({ ...current, [field.name]: next }))}
              />
            </div>
          ))}
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <Button buttonStyle="text" variant="secondary" onClick={() => setValues(initialFormValues(catalogKey))} disabled={saving}>
            {t("catalog.reset")}
          </Button>
          <Button buttonStyle="filled" variant="primary" onClick={save} disabled={saving || loading}>
            {saving ? t("catalog.creating") : t("catalog.create", { singular: t(config.singularKey) })}
          </Button>
        </div>
      </Card>
    </div>
  );
};

export const CatalogDetailPage = ({ catalogKey }: { catalogKey: CatalogKey }) => {
  const config = configs[catalogKey];
  const navigate = useNavigate();
  const params = useParams();
  const { t } = useI18n();
  const [state, setState] = useState<CatalogState>(emptyState);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    loadCatalogState()
      .then((next) => {
        if (active) setState(next);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const item = state[catalogKey].find((entry) => entry.id === params.id);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <Button buttonStyle="text" variant="secondary" onClick={() => navigate(config.path)}>
          {t("catalog.backToList")}
        </Button>
        <Badge variant="secondary">{t(config.singularKey)}</Badge>
      </div>
      {loading && (
        <Card className="p-6">
          <Typography variant="body2" color="textSecondary">{t("catalog.loadingDetail")}</Typography>
        </Card>
      )}
      {!loading && !item && (
        <Card className="p-6">
          <Typography variant="h6">{t("catalog.notFound")}</Typography>
          <Typography variant="body2" color="textSecondary" className="mt-1">{t("catalog.notFoundDesc")}</Typography>
        </Card>
      )}
      {!loading && item && <DetailBody config={config} item={item} state={state} />}
    </div>
  );
};

export const AdminBrandsPage = () => <CatalogListPage catalogKey="brands" />;
export const AdminBrandCreatePage = () => <CatalogCreatePage catalogKey="brands" />;
export const AdminBrandDetailPage = () => <CatalogDetailPage catalogKey="brands" />;
export const AdminProvidersPage = () => <CatalogListPage catalogKey="providers" />;
export const AdminProviderCreatePage = () => <CatalogCreatePage catalogKey="providers" />;
export const AdminProviderDetailPage = () => <CatalogDetailPage catalogKey="providers" />;
export const AdminProviderEndpointsPage = () => <CatalogListPage catalogKey="provider-endpoints" />;
export const AdminProviderEndpointCreatePage = () => <CatalogCreatePage catalogKey="provider-endpoints" />;
export const AdminProviderEndpointDetailPage = () => <CatalogDetailPage catalogKey="provider-endpoints" />;
export const AdminProviderCredentialsPage = () => <CatalogListPage catalogKey="provider-credentials" />;
export const AdminProviderCredentialCreatePage = () => <CatalogCreatePage catalogKey="provider-credentials" />;
export const AdminProviderCredentialDetailPage = () => <CatalogDetailPage catalogKey="provider-credentials" />;
export const AdminPublicModelsPage = () => <CatalogListPage catalogKey="public-models" />;
export const AdminPublicModelCreatePage = () => <CatalogCreatePage catalogKey="public-models" />;
export const AdminPublicModelDetailPage = () => <CatalogDetailPage catalogKey="public-models" />;
export const AdminUpstreamModelsPage = () => <CatalogListPage catalogKey="upstream-models" />;
export const AdminUpstreamModelCreatePage = () => <CatalogCreatePage catalogKey="upstream-models" />;
export const AdminUpstreamModelDetailPage = () => <CatalogDetailPage catalogKey="upstream-models" />;
export const AdminModelRoutesPage = () => <CatalogListPage catalogKey="model-routes" />;
export const AdminModelRouteCreatePage = () => <CatalogCreatePage catalogKey="model-routes" />;
export const AdminModelRouteDetailPage = () => <CatalogDetailPage catalogKey="model-routes" />;
