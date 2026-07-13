import { Badge, Button, Card, Grid, TextField, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import adminApi from "../../api/adminClient";
import { AdminPageIntro } from "./adminCommon";
import { useI18n } from "../../i18n";

type ProviderPreset = {
  provider: string;
  label: string;
  base_url: string;
  protocol: string;
  notes: string;
};

type Provider = {
  id: string;
  name: string;
  slug: string;
  icon_url?: string | null;
  enabled: boolean;
};

const AdminProvidersPage = () => {
  const navigate = useNavigate();
  const { t } = useI18n();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [providerKeys, setProviderKeys] = useState<any[]>([]);
  const [providerPresets, setProviderPresets] = useState<ProviderPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState("");
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [keyName, setKeyName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [healthState, setHealthState] = useState("healthy");
  const [cooldownUntil, setCooldownUntil] = useState("");

  const activePreset = providerPresets.find((item) => item.provider === selectedPreset) ?? null;

  const load = async () => {
    try {
      const [providersResp, keysResp, presetsResp] = await Promise.all([
        adminApi.get("/admin/providers"),
        adminApi.get("/admin/provider-keys"),
        adminApi.get("/admin/provider-presets"),
      ]);
      setProviders(providersResp.data);
      setProviderKeys(keysResp.data);
      setProviderPresets(presetsResp.data);
    } catch {
      setProviders([]);
      setProviderKeys([]);
      setProviderPresets([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const applyPreset = (presetProvider: string) => {
    setSelectedPreset(presetProvider);
    const preset = providerPresets.find((item) => item.provider === presetProvider);
    if (!preset) return;
    const provider = providers.find((item) => item.slug === preset.provider);
    setSelectedProviderId(provider?.id ?? "");
    setKeyName(preset.base_url);
  };

  const createProviderKey = async () => {
    const provider = providers.find((item) => item.id === selectedProviderId);
    const resp = await adminApi.post("/admin/provider-keys", {
      provider_id: selectedProviderId || null,
      provider: provider?.slug || "",
      key_name: keyName.trim(),
      api_key: apiKey,
      enabled,
      health_state: healthState || "healthy",
      cooldown_until: cooldownUntil || null,
    });
    navigate(`/admin/providers/${resp.data.id}`);
  };

  return (
    <div className="space-y-6">
      <AdminPageIntro title={t("providers.title")} description={t("providers.desc")} />

      <Card className="p-6">
        <Typography variant="h6">{t("providers.add")}</Typography>
        <Typography variant="body2" color="textSecondary" className="mt-1">
          {t("providers.addDesc")}
        </Typography>
        <Grid container spacing={2} className="mt-4" alignItems="flex-end">
          <Grid item xs={12} md={6}>
            <label className="mb-2 block text-sm font-medium text-slate-600">{t("providers.preset")}</label>
            <select
              className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-3 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200"
              value={selectedPreset}
              onChange={(e) => applyPreset(e.target.value)}
            >
              <option value="">{t("providers.manual")}</option>
              {providerPresets.map((item) => (
                <option key={item.provider} value={item.provider}>
                  {item.label} ({item.provider})
                </option>
              ))}
            </select>
          </Grid>
          <Grid item xs={12} md={6}>
            {activePreset ? (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <div className="font-medium text-slate-900">{activePreset.label}</div>
              <div className="mt-1">{t("providers.protocol", { p: activePreset.protocol })}</div>
              <div className="mt-1 break-all">{t("providers.recommendedUrl", { u: activePreset.base_url })}</div>
              <div className="mt-1">{activePreset.notes}</div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-3 text-sm text-slate-500">
                {t("providers.presetHint")}
              </div>
            )}
          </Grid>
          <Grid item xs={12} md={4}>
            <label className="mb-2 block text-sm font-medium text-slate-600">{t("providers.provider")}</label>
            <select
              className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-3 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200"
              value={selectedProviderId}
              onChange={(e) => setSelectedProviderId(e.target.value)}
            >
              <option value="">{t("providers.selectProvider")}</option>
              {providers.filter((item) => item.enabled).map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label={t("providers.defaultBaseUrl")} placeholder={t("providers.defaultBaseUrlPlaceholder")} value={keyName} onChange={(e: any) => setKeyName(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label={t("providers.apiKey")} placeholder="sk-..." value={apiKey} onChange={(e: any) => setApiKey(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label={t("providers.healthState")} value={healthState} onChange={(e: any) => setHealthState(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label={t("providers.cooldownUntil")} placeholder="2026-01-01T00:00:00Z" value={cooldownUntil} onChange={(e: any) => setCooldownUntil(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={2}>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              {t("providers.enable")}
            </label>
          </Grid>
          <Grid item xs={12} md={2}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={createProviderKey} disabled={!selectedProviderId || !apiKey}>
              {t("providers.createConfig")}
            </Button>
          </Grid>
        </Grid>
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between gap-3">
          <Typography variant="h6">{t("providers.existing")}</Typography>
          <Badge variant="primary">{providerKeys.length}</Badge>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
          {providerKeys.map((item) => (
            <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-slate-900">{providers.find((provider) => provider.slug === item.provider)?.name || item.provider}</div>
                  <div className="mt-1 break-all text-xs text-slate-500">{item.key_name || "-"}</div>
                </div>
                <Badge variant={item.enabled ? "primary" : "warning"}>{item.enabled ? t("common.enabled") : t("common.disabled")}</Badge>
              </div>
              <div className="mt-3 text-sm text-slate-600">{item.has_secret ? (item.secret_last4 ? t("key.encryptedLast4", { last4: item.secret_last4 }) : t("key.encrypted")) : t("key.notSet")}</div>
              <div className="mt-3">
                <Button buttonStyle="text" variant="secondary" onClick={() => navigate(`/admin/providers/${item.id}`)}>
                  {t("providers.detail")}
                </Button>
              </div>
            </div>
          ))}

          {providerKeys.length === 0 && <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-3 text-sm text-slate-500">{t("providers.noKeys")}</div>}
        </div>
      </Card>
    </div>
  );
};

export default AdminProvidersPage;
