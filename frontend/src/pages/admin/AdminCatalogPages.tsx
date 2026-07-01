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
  const [state, setState] = useState<CatalogState>(emptyState);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState(JSON.stringify(upsertTemplates[catalogKey], null, 2));
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

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

  useEffect(() => {
    setDraft(JSON.stringify(upsertTemplates[catalogKey], null, 2));
    setSaveError("");
  }, [catalogKey]);

  const saveDraft = async () => {
    setSaving(true);
    setSaveError("");
    try {
      const payload = JSON.parse(draft);
      await adminApi.post(`/admin/${catalogKey}`, payload);
      await refresh();
    } catch (error: any) {
      setSaveError(error?.response?.data?.message || error?.message || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const items = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return state[catalogKey];
    return state[catalogKey].filter((item) => JSON.stringify(item).toLowerCase().includes(normalized));
  }, [catalogKey, query, state]);

  return (
    <div className="space-y-6">
      <AdminPageIntro title={config.title} description={config.description} />
      <Card className="p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="lg:w-80">
            <Typography variant="h6">新增或更新 {config.singular}</Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              填写 JSON 后保存；带 `id` 时更新对应对象，不带 `id` 时创建新对象。
            </Typography>
            {saveError ? <div className="mt-3 border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">{saveError}</div> : null}
          </div>
          <div className="min-w-0 flex-1">
            <textarea
              className="h-64 w-full border border-slate-300 bg-slate-950 p-4 font-mono text-xs leading-5 text-slate-100 focus:outline-none focus:ring-1 focus:ring-slate-400"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              spellCheck={false}
            />
            <div className="mt-3 flex justify-end">
              <Button buttonStyle="filled" variant="primary" onClick={saveDraft} disabled={saving}>
                {saving ? "保存中..." : "保存"}
              </Button>
            </div>
          </div>
        </div>
      </Card>
      <Card className="p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <Typography variant="h6">{config.singular} 列表</Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              {loading ? "正在加载..." : `${items.length} / ${state[catalogKey].length}`}
            </Typography>
          </div>
          <input
            className="w-full border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-300 md:w-80"
            placeholder={`搜索 ${config.singular}`}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
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
export const AdminBrandDetailPage = () => <CatalogDetailPage catalogKey="brands" />;
export const AdminProvidersPage = () => <CatalogListPage catalogKey="providers" />;
export const AdminProviderDetailPage = () => <CatalogDetailPage catalogKey="providers" />;
export const AdminProviderEndpointsPage = () => <CatalogListPage catalogKey="provider-endpoints" />;
export const AdminProviderEndpointDetailPage = () => <CatalogDetailPage catalogKey="provider-endpoints" />;
export const AdminProviderCredentialsPage = () => <CatalogListPage catalogKey="provider-credentials" />;
export const AdminProviderCredentialDetailPage = () => <CatalogDetailPage catalogKey="provider-credentials" />;
export const AdminPublicModelsPage = () => <CatalogListPage catalogKey="public-models" />;
export const AdminPublicModelDetailPage = () => <CatalogDetailPage catalogKey="public-models" />;
export const AdminUpstreamModelsPage = () => <CatalogListPage catalogKey="upstream-models" />;
export const AdminUpstreamModelDetailPage = () => <CatalogDetailPage catalogKey="upstream-models" />;
export const AdminModelRoutesPage = () => <CatalogListPage catalogKey="model-routes" />;
export const AdminModelRouteDetailPage = () => <CatalogDetailPage catalogKey="model-routes" />;
