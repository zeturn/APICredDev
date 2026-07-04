import { Badge, Button, Card, Typography } from "../../lib/watercolor";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import adminApi from "../../api/adminClient";
import { AdminPageIntro } from "./adminCommon";
import { formatPricingSummary } from "../../shared/pricing";

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

type CatalogConfig = {
  key: CatalogKey;
  path: string;
  title: string;
  description: string;
  singular: string;
  primary: (item: CatalogItem, state: CatalogState) => string;
  secondary: (item: CatalogItem, state: CatalogState) => string;
  meta: (item: CatalogItem, state: CatalogState) => Array<[string, string]>;
};

type CreateField = {
  name: string;
  label: string;
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

const enabledBadge = (item: CatalogItem) => {
  if (typeof item.enabled !== "boolean") return null;
  return <Badge variant={item.enabled ? "primary" : "warning"}>{item.enabled ? "enabled" : "disabled"}</Badge>;
};

const configs: Record<CatalogKey, CatalogConfig> = {
  brands: {
    key: "brands",
    path: "/admin/brands",
    title: "品牌管理",
    description: "管理展示给用户的模型品牌，包括名称、slug、图标和启用状态。",
    singular: "品牌",
    primary: (item) => item.name || item.slug,
    secondary: (item) => item.slug,
    meta: (item) => [
      ["ID", item.id],
      ["Icon", item.icon_url || item.icon_slug || "-"],
      ["Created", item.created_at || "-"],
    ],
  },
  providers: {
    key: "providers",
    path: "/admin/providers",
    title: "Provider 管理",
    description: "管理上游供应商主体，例如 OpenAI、OpenRouter、Azure OpenAI。",
    singular: "Provider",
    primary: (item) => item.name || item.slug,
    secondary: (item) => item.slug,
    meta: (item, state) => [
      ["ID", item.id],
      ["Endpoints", String(state["provider-endpoints"].filter((endpoint) => endpoint.provider_id === item.id).length)],
      ["Upstream Models", String(state["upstream-models"].filter((model) => model.provider_id === item.id).length)],
    ],
  },
  "provider-endpoints": {
    key: "provider-endpoints",
    path: "/admin/provider-endpoints",
    title: "Endpoint 管理",
    description: "管理 Provider 的可用上游入口，包括 base URL、健康状态和冷却时间。",
    singular: "Endpoint",
    primary: (item) => item.display_name || item.slug,
    secondary: (item, state) => `${byId(state.providers, item.provider_id)?.name || item.provider_id} / ${item.slug}`,
    meta: (item, state) => [
      ["Provider", byId(state.providers, item.provider_id)?.name || item.provider_id],
      ["Base URL", item.base_url || "-"],
      ["Health", item.health_state || "-"],
      ["Credentials", String(state["provider-credentials"].filter((credential) => credential.provider_endpoint_id === item.id).length)],
    ],
  },
  "provider-credentials": {
    key: "provider-credentials",
    path: "/admin/provider-credentials",
    title: "Credential 管理",
    description: "管理上游调用凭据。密钥只显示保存状态和 last4，不在前端回显明文。",
    singular: "Credential",
    primary: (item) => item.display_name || item.id,
    secondary: (item, state) => {
      const endpoint = byId(state["provider-endpoints"], item.provider_endpoint_id);
      const provider = byId(state.providers, endpoint?.provider_id);
      return `${provider?.name || "provider"} / ${endpoint?.display_name || item.provider_endpoint_id}`;
    },
    meta: (item, state) => {
      const endpoint = byId(state["provider-endpoints"], item.provider_endpoint_id);
      return [
        ["Endpoint", endpoint?.display_name || item.provider_endpoint_id],
        ["Secret", item.has_secret ? `saved${item.secret_last4 ? ` / ****${item.secret_last4}` : ""}` : "missing"],
        ["Health", item.health_state || "-"],
        ["Cooldown", item.cooldown_until || "-"],
      ];
    },
  },
  "public-models": {
    key: "public-models",
    path: "/admin/public-models",
    title: "Public Model 管理",
    description: "管理用户看到、购买和调用的模型产品目录。",
    singular: "Public Model",
    primary: (item) => item.display_name || item.slug,
    secondary: (item, state) => `${item.slug} / ${byId(state.brands, item.brand_id)?.name || "no brand"}`,
    meta: (item, state) => [
      ["Brand", byId(state.brands, item.brand_id)?.name || item.brand_id || "-"],
      ["Category", item.category || "-"],
      ["Multiplier", `x${item.multiplier ?? 1}`],
      ["Routes", String(state["model-routes"].filter((route) => route.public_model_id === item.id).length)],
    ],
  },
  "upstream-models": {
    key: "upstream-models",
    path: "/admin/upstream-models",
    title: "Upstream Model 管理",
    description: "管理真实传给上游的模型名和能力信息。",
    singular: "Upstream Model",
    primary: (item) => item.display_name || item.upstream_name,
    secondary: (item, state) => `${byId(state.providers, item.provider_id)?.name || item.provider_id} / ${item.upstream_name}`,
    meta: (item, state) => [
      ["Provider", byId(state.providers, item.provider_id)?.name || item.provider_id],
      ["Context", item.context_window ? String(item.context_window) : "-"],
      ["Capabilities", jsonSummary(item.capabilities)],
      ["Routes", String(state["model-routes"].filter((route) => route.upstream_model_id === item.id).length)],
    ],
  },
  "model-routes": {
    key: "model-routes",
    path: "/admin/model-routes",
    title: "Model Route 管理",
    description: "管理 Public Model 到真实上游模型和 credential 的路由关系。",
    singular: "Model Route",
    primary: (item, state) => byId(state["public-models"], item.public_model_id)?.slug || item.public_model_id,
    secondary: (item, state) => {
      const upstream = byId(state["upstream-models"], item.upstream_model_id);
      const provider = byId(state.providers, upstream?.provider_id);
      return `${provider?.slug || "provider"} / ${upstream?.upstream_name || item.upstream_model_id}`;
    },
    meta: (item, state) => [
      ["Public Model", byId(state["public-models"], item.public_model_id)?.slug || item.public_model_id],
      ["Upstream", byId(state["upstream-models"], item.upstream_model_id)?.upstream_name || item.upstream_model_id],
      ["Credential", byId(state["provider-credentials"], item.provider_credential_id)?.display_name || item.provider_credential_id || "-"],
      ["Priority / Weight", `${item.priority ?? "-"} / ${item.weight ?? "-"}`],
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
    { name: "name", label: "名称", type: "text", required: true, placeholder: "OpenAI" },
    { name: "slug", label: "Slug", type: "text", required: true, placeholder: "openai" },
    { name: "icon_slug", label: "图标 Slug", type: "text", placeholder: "openai" },
    { name: "icon_url", label: "图标 URL", type: "text", placeholder: "https://..." },
    { name: "enabled", label: "启用", type: "boolean", defaultValue: true },
  ],
  providers: [
    { name: "name", label: "名称", type: "text", required: true, placeholder: "OpenAI" },
    { name: "slug", label: "Slug", type: "text", required: true, placeholder: "openai" },
    { name: "icon_slug", label: "图标 Slug", type: "text", placeholder: "openai" },
    { name: "icon_url", label: "图标 URL", type: "text", placeholder: "https://..." },
    { name: "enabled", label: "启用", type: "boolean", defaultValue: true },
  ],
  "provider-endpoints": [
    {
      name: "provider_id",
      label: "Provider",
      type: "select",
      required: true,
      optionsFrom: "providers",
      optionLabel: (item) => `${item.name || item.slug} (${item.slug})`,
    },
    { name: "slug", label: "Slug", type: "text", required: true, placeholder: "default" },
    { name: "display_name", label: "显示名称", type: "text", required: true, placeholder: "OpenAI Default" },
    { name: "base_url", label: "Base URL", type: "text", required: true, placeholder: "https://api.openai.com/v1" },
    {
      name: "health_state",
      label: "健康状态",
      type: "select",
      defaultValue: "healthy",
      options: [
        { value: "healthy", label: "healthy" },
        { value: "disabled", label: "disabled" },
        { value: "cooldown", label: "cooldown" },
      ],
    },
    { name: "cooldown_until", label: "冷却截止", type: "text", placeholder: "2026-07-04T12:00:00Z" },
    { name: "enabled", label: "启用", type: "boolean", defaultValue: true },
  ],
  "provider-credentials": [
    {
      name: "provider_endpoint_id",
      label: "Endpoint",
      type: "select",
      required: true,
      optionsFrom: "provider-endpoints",
      optionLabel: (item, state) => {
        const provider = byId(state.providers, item.provider_id);
        return `${provider?.slug || item.provider_id} / ${item.display_name || item.slug}`;
      },
    },
    { name: "display_name", label: "显示名称", type: "text", required: true, placeholder: "OpenAI production key" },
    { name: "api_key", label: "API Key", type: "secret", required: true, placeholder: "sk-..." },
    {
      name: "health_state",
      label: "健康状态",
      type: "select",
      defaultValue: "healthy",
      options: [
        { value: "healthy", label: "healthy" },
        { value: "disabled", label: "disabled" },
        { value: "cooldown", label: "cooldown" },
      ],
    },
    { name: "cooldown_until", label: "冷却截止", type: "text", placeholder: "2026-07-04T12:00:00Z" },
    { name: "enabled", label: "启用", type: "boolean", defaultValue: true },
  ],
  "public-models": [
    { name: "slug", label: "Slug", type: "text", required: true, placeholder: "gpt-4o-mini" },
    { name: "display_name", label: "显示名称", type: "text", required: true, placeholder: "GPT-4o mini" },
    { name: "description", label: "描述", type: "textarea", placeholder: "面向用户展示的模型说明" },
    {
      name: "brand_id",
      label: "品牌",
      type: "select",
      optionsFrom: "brands",
      optionLabel: (item) => `${item.name || item.slug} (${item.slug})`,
    },
    {
      name: "category",
      label: "类别",
      type: "select",
      defaultValue: "llm",
      options: ["llm", "image", "embedding", "audio", "moderation", "realtime", "search", "agent", "robotics"].map((value) => ({ value, label: value })),
    },
    { name: "pricing", label: "计价 JSON", type: "json", required: true, defaultValue: { mode: "request", unit: "request", price: 0 } },
    { name: "multiplier", label: "倍率", type: "number", defaultValue: 1 },
    { name: "enabled", label: "启用", type: "boolean", defaultValue: true },
  ],
  "upstream-models": [
    {
      name: "provider_id",
      label: "Provider",
      type: "select",
      required: true,
      optionsFrom: "providers",
      optionLabel: (item) => `${item.name || item.slug} (${item.slug})`,
    },
    { name: "upstream_name", label: "上游模型名", type: "text", required: true, placeholder: "gpt-4o-mini" },
    { name: "display_name", label: "显示名称", type: "text", required: true, placeholder: "GPT-4o mini" },
    { name: "context_window", label: "上下文窗口", type: "number", placeholder: "128000" },
    { name: "capabilities", label: "能力 JSON", type: "json", required: true, defaultValue: { chat: true } },
    { name: "default_pricing", label: "默认计价 JSON", type: "json", required: true, defaultValue: { mode: "token", unit: "1M tokens" } },
    { name: "enabled", label: "启用", type: "boolean", defaultValue: true },
  ],
  "model-routes": [
    {
      name: "public_model_id",
      label: "Public Model",
      type: "select",
      required: true,
      optionsFrom: "public-models",
      optionLabel: (item) => `${item.display_name || item.slug} (${item.slug})`,
    },
    {
      name: "upstream_model_id",
      label: "Upstream Model",
      type: "select",
      required: true,
      optionsFrom: "upstream-models",
      optionLabel: (item, state) => `${byId(state.providers, item.provider_id)?.slug || item.provider_id} / ${item.upstream_name}`,
    },
    {
      name: "provider_credential_id",
      label: "Credential",
      type: "select",
      optionsFrom: "provider-credentials",
      optionLabel: (item, state) => {
        const endpoint = byId(state["provider-endpoints"], item.provider_endpoint_id);
        const provider = byId(state.providers, endpoint?.provider_id);
        return `${provider?.slug || "provider"} / ${item.display_name || item.id}`;
      },
    },
    { name: "base_url_override", label: "Base URL Override", type: "text", placeholder: "可选" },
    { name: "priority", label: "优先级", type: "number", defaultValue: 1 },
    { name: "weight", label: "权重", type: "number", defaultValue: 1 },
    {
      name: "quota_unit",
      label: "配额单位",
      type: "select",
      defaultValue: "tokens",
      options: [
        { value: "tokens", label: "tokens" },
        { value: "requests", label: "requests" },
      ],
    },
    { name: "quota_rules", label: "配额规则 JSON", type: "json", required: true, defaultValue: { day: 2000 } },
    { name: "enabled", label: "启用", type: "boolean", defaultValue: true },
  ],
};

async function loadCatalogState(): Promise<CatalogState> {
  const responses = await Promise.all(catalogKeys.map((key) => adminApi.get(`/admin/${key}`)));
  return catalogKeys.reduce((next, key, index) => {
    next[key] = Array.isArray(responses[index].data) ? responses[index].data : [];
    return next;
  }, { ...emptyState });
}

const MetaGrid = ({ rows }: { rows: Array<[string, string]> }) => (
  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
    {rows.map(([label, value]) => (
      <div key={label} className="min-w-0 border border-slate-200 bg-slate-50 px-3 py-2">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{label}</div>
        <div className="mt-1 break-words text-sm text-slate-800">{value || "-"}</div>
      </div>
    ))}
  </div>
);

const CatalogCard = ({ config, item, state }: { config: CatalogConfig; item: CatalogItem; state: CatalogState }) => {
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() => navigate(`${config.path}/${item.id}`)}
      className="block w-full border border-slate-200 bg-white p-4 text-left transition hover:border-slate-400 hover:bg-slate-50"
    >
      <div className="flex min-h-10 items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-900">{config.primary(item, state)}</div>
          <div className="mt-1 truncate text-xs text-slate-500">{config.secondary(item, state)}</div>
        </div>
        {enabledBadge(item)}
      </div>
      <div className="mt-4 space-y-2">
        {config.meta(item, state).slice(0, 3).map(([label, value]) => (
          <div key={label} className="flex gap-3 text-xs">
            <span className="w-24 shrink-0 text-slate-400">{label}</span>
            <span className="min-w-0 truncate text-slate-700">{value || "-"}</span>
          </div>
        ))}
      </div>
    </button>
  );
};

const RelatedLinks = ({ item, state, catalogKey }: { item: CatalogItem; state: CatalogState; catalogKey: CatalogKey }) => {
  const links: Array<{ label: string; path: string; name: string }> = [];
  const push = (label: string, configKey: CatalogKey, related: CatalogItem | undefined, name?: string) => {
    if (!related) return;
    links.push({ label, path: `${configs[configKey].path}/${related.id}`, name: name || configs[configKey].primary(related, state) });
  };

  if (catalogKey === "provider-endpoints") push("Provider", "providers", byId(state.providers, item.provider_id));
  if (catalogKey === "provider-credentials") {
    const endpoint = byId(state["provider-endpoints"], item.provider_endpoint_id);
    push("Endpoint", "provider-endpoints", endpoint);
    push("Provider", "providers", byId(state.providers, endpoint?.provider_id));
  }
  if (catalogKey === "public-models") push("Brand", "brands", byId(state.brands, item.brand_id));
  if (catalogKey === "upstream-models") push("Provider", "providers", byId(state.providers, item.provider_id));
  if (catalogKey === "model-routes") {
    push("Public Model", "public-models", byId(state["public-models"], item.public_model_id));
    const upstream = byId(state["upstream-models"], item.upstream_model_id);
    push("Upstream Model", "upstream-models", upstream);
    push("Provider", "providers", byId(state.providers, upstream?.provider_id));
    push("Credential", "provider-credentials", byId(state["provider-credentials"], item.provider_credential_id));
  }

  if (!links.length) return null;
  return (
    <Card className="p-6">
      <Typography variant="h6">关联对象</Typography>
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
  const pricing =
    config.key === "public-models"
      ? formatPricingSummary(item.pricing)
      : config.key === "upstream-models"
        ? formatPricingSummary(item.default_pricing)
        : [];
  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <Typography variant="h5" className="break-words">{config.primary(item, state)}</Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1 break-words">
              {config.secondary(item, state)}
            </Typography>
          </div>
          {enabledBadge(item)}
        </div>
        <div className="mt-6">
          <MetaGrid rows={config.meta(item, state)} />
        </div>
      </Card>

      {pricing.length > 0 && (
        <Card className="p-6">
          <Typography variant="h6">计价信息</Typography>
          <div className="mt-4 space-y-2 text-sm text-slate-700">
            {pricing.map((line) => <div key={line}>{line}</div>)}
          </div>
        </Card>
      )}

      <RelatedLinks item={item} state={state} catalogKey={config.key} />

      <Card className="p-6">
        <Typography variant="h6">原始数据</Typography>
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
      <AdminPageIntro title={config.title} description={config.description} />
      <Card className="p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <Typography variant="h6">{config.singular} 列表</Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              {loading ? "正在加载..." : `${items.length} / ${state[catalogKey].length}`}
            </Typography>
          </div>
          <div className="flex flex-col gap-2 md:flex-row md:items-center">
            <input
              className="w-full border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-300 md:w-80"
              placeholder={`搜索 ${config.singular}`}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <Button buttonStyle="filled" variant="primary" onClick={() => navigate(`${config.path}/new`)}>
              新建 {config.singular}
            </Button>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-1 gap-3 xl:grid-cols-2">
          {items.map((item) => <CatalogCard key={item.id} config={config} item={item} state={state} />)}
          {!loading && items.length === 0 && (
            <div className="border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">暂无数据</div>
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

const fieldLabel = (field: CreateField) => (
  <span className="mb-2 block text-sm font-medium text-slate-700">
    {field.label}
    {field.required ? <span className="text-slate-500"> *</span> : null}
  </span>
);

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
  const common = (
    <>
      {fieldLabel(field)}
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
        <span className="text-sm font-medium text-slate-700">{field.label}</span>
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
          <option value="">未选择</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
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

const buildPayload = (catalogKey: CatalogKey, values: Record<string, unknown>): Record<string, unknown> => {
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
        throw new Error(`${field.label} 必须是数字`);
      }
      payload[field.name] = parsed;
      continue;
    }
    if (field.type === "json") {
      const raw = String(value ?? "").trim();
      if (!raw) {
        if (field.required) throw new Error(`${field.label} 不能为空`);
        continue;
      }
      try {
        payload[field.name] = JSON.parse(raw);
      } catch {
        throw new Error(`${field.label} 不是有效 JSON`);
      }
      continue;
    }
    const text = String(value ?? "").trim();
    if (text) {
      payload[field.name] = text;
    } else if (field.required) {
      throw new Error(`${field.label} 不能为空`);
    }
  }
  return payload;
};

export const CatalogCreatePage = ({ catalogKey }: { catalogKey: CatalogKey }) => {
  const config = configs[catalogKey];
  const navigate = useNavigate();
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
      const payload = buildPayload(catalogKey, values);
      const response = await adminApi.post(`/admin/${catalogKey}`, payload);
      const id = response.data?.id;
      navigate(id ? `${config.path}/${id}` : config.path);
    } catch (error: any) {
      setError(error?.response?.data?.error?.message || error?.response?.data?.message || error?.message || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <Button buttonStyle="text" variant="secondary" onClick={() => navigate(config.path)}>
            返回列表
          </Button>
          <Typography variant="h5" className="mt-3">新建 {config.singular}</Typography>
          <Typography variant="body2" color="textSecondary" className="mt-1">{config.description}</Typography>
        </div>
        <Badge variant="secondary">{loading ? "加载依赖中" : config.singular}</Badge>
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
            重置
          </Button>
          <Button buttonStyle="filled" variant="primary" onClick={save} disabled={saving || loading}>
            {saving ? "创建中..." : `创建 ${config.singular}`}
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
          返回列表
        </Button>
        <Badge variant="secondary">{config.singular}</Badge>
      </div>
      {loading && (
        <Card className="p-6">
          <Typography variant="body2" color="textSecondary">正在加载详情...</Typography>
        </Card>
      )}
      {!loading && !item && (
        <Card className="p-6">
          <Typography variant="h6">未找到对象</Typography>
          <Typography variant="body2" color="textSecondary" className="mt-1">当前对象可能已被删除或 ID 不正确。</Typography>
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
