import { Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import adminApi from "../../api/adminClient";
import { AdminPageIntro, AdminTokenWarning } from "./adminCommon";

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
  const adminToken = localStorage.getItem("admin_token") ?? "";
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
    if (!adminToken) {
      setProviders([]);
      setProviderKeys([]);
      setProviderPresets([]);
      return;
    }
    const [providersResp, keysResp, presetsResp] = await Promise.all([
      adminApi.get("/admin/providers"),
      adminApi.get("/admin/provider-keys"),
      adminApi.get("/admin/provider-presets"),
    ]);
    setProviders(providersResp.data);
    setProviderKeys(keysResp.data);
    setProviderPresets(presetsResp.data);
  };

  useEffect(() => {
    load();
  }, [adminToken]);

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
      <AdminPageIntro title="服务商 Key 管理" description="先创建 Key，再进入详情页配置这把 Key 可服务的模型和特殊 URL。" />
      {!adminToken && <AdminTokenWarning />}

      <Card className="p-6">
        <Typography variant="h6">新增服务商 Key</Typography>
        <Typography variant="body2" color="textSecondary" className="mt-1">
          第一步只创建 Key。保存后会进入详情页，继续配置适用模型、权重和特殊路由。
        </Typography>
        <Grid container spacing={2} className="mt-4" alignItems="flex-end">
          <Grid item xs={12} md={6}>
            <label className="mb-2 block text-sm font-medium text-slate-600">服务商预设</label>
            <select
              className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-3 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200"
              value={selectedPreset}
              onChange={(e) => applyPreset(e.target.value)}
            >
              <option value="">手动填写</option>
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
              <div className="mt-1">协议：{activePreset.protocol}</div>
              <div className="mt-1 break-all">推荐地址：{activePreset.base_url}</div>
              <div className="mt-1">{activePreset.notes}</div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-3 text-sm text-slate-500">
                未选择预设时，可以自行选择服务商；默认 URL 留空时会回退到服务商默认地址。
              </div>
            )}
          </Grid>
          <Grid item xs={12} md={4}>
            <label className="mb-2 block text-sm font-medium text-slate-600">服务商</label>
            <select
              className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-3 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200"
              value={selectedProviderId}
              onChange={(e) => setSelectedProviderId(e.target.value)}
            >
              <option value="">选择服务商</option>
              {providers.filter((item) => item.enabled).map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="默认 Base URL" placeholder="留空则使用服务商默认地址" value={keyName} onChange={(e: any) => setKeyName(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="API Key" placeholder="sk-..." value={apiKey} onChange={(e: any) => setApiKey(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="健康状态" value={healthState} onChange={(e: any) => setHealthState(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="Cooldown Until (ISO)" placeholder="2026-01-01T00:00:00Z" value={cooldownUntil} onChange={(e: any) => setCooldownUntil(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={2}>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              启用
            </label>
          </Grid>
          <Grid item xs={12} md={2}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={createProviderKey} disabled={!selectedProviderId || !apiKey}>
              创建并配置
            </Button>
          </Grid>
        </Grid>
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between gap-3">
          <Typography variant="h6">现有 Keys</Typography>
          <Badge variant="primary">{providerKeys.length}</Badge>
        </div>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>服务商</TableCell>
              <TableCell>默认 URL</TableCell>
              <TableCell>密钥</TableCell>
              <TableCell>状态</TableCell>
              <TableCell align="right">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {providerKeys.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{providers.find((provider) => provider.slug === item.provider)?.name || item.provider}</TableCell>
                <TableCell>{item.key_name}</TableCell>
                <TableCell>{item.has_secret ? (item.secret_last4 ? `已加密保存 · ****${item.secret_last4}` : "已加密保存") : "未设置"}</TableCell>
                <TableCell>{item.enabled ? "enabled" : "disabled"}</TableCell>
                <TableCell align="right">
                  <Button buttonStyle="text" variant="secondary" onClick={() => navigate(`/admin/providers/${item.id}`)}>
                    详情
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {providerKeys.length === 0 && (
              <TableRow>
                <TableCell colSpan={5}>暂无服务商 Key</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default AdminProvidersPage;
