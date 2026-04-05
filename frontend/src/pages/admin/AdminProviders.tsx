import { Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminPageIntro, AdminTokenWarning } from "./adminCommon";

type ProviderPreset = {
  provider: string;
  label: string;
  base_url: string;
  protocol: string;
  notes: string;
};

const AdminProvidersPage = () => {
  const [providerKeys, setProviderKeys] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [modelProviderKeys, setModelProviderKeys] = useState<any[]>([]);
  const [providerPresets, setProviderPresets] = useState<ProviderPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState("");
  const [selectedModelId, setSelectedModelId] = useState("");
  const [selectedProviderKeyId, setSelectedProviderKeyId] = useState("");
  const [mappingBaseUrl, setMappingBaseUrl] = useState("");
  const [mappingPriority, setMappingPriority] = useState("1");
  const [mappingWeight, setMappingWeight] = useState("1");
  const [mappingEnabled, setMappingEnabled] = useState(true);
  const [provider, setProvider] = useState("");
  const [keyName, setKeyName] = useState("");
  const [secretRef, setSecretRef] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [healthState, setHealthState] = useState("healthy");
  const [cooldownUntil, setCooldownUntil] = useState("");
  const adminToken = localStorage.getItem("admin_token") ?? "";

  const activePreset = providerPresets.find((item) => item.provider === selectedPreset) ?? null;

  const load = async () => {
    if (!adminToken) {
      setProviderKeys([]);
      setModels([]);
      setModelProviderKeys([]);
      setProviderPresets([]);
      return;
    }
    const [keysResp, modelsResp, linksResp, presetsResp] = await Promise.all([
      adminApi.get("/admin/provider-keys"),
      adminApi.get("/admin/models"),
      adminApi.get("/admin/model-provider-keys"),
      adminApi.get("/admin/provider-presets"),
    ]);
    setProviderKeys(keysResp.data);
    setModels(modelsResp.data);
    setModelProviderKeys(linksResp.data);
    setProviderPresets(presetsResp.data);
  };

  useEffect(() => {
    load();
  }, [adminToken]);

  const applyPreset = (presetProvider: string) => {
    setSelectedPreset(presetProvider);
    const preset = providerPresets.find((item) => item.provider === presetProvider);
    if (!preset) return;
    setProvider(preset.provider);
    setKeyName(preset.base_url);
  };

  const createProviderKey = async () => {
    await adminApi.post("/admin/provider-keys", {
      provider,
      key_name: keyName,
      secret_ref: secretRef,
      enabled,
      health_state: healthState || "healthy",
      cooldown_until: cooldownUntil || null,
    });
    setSelectedPreset("");
    setProvider("");
    setKeyName("");
    setSecretRef("");
    setEnabled(true);
    setHealthState("healthy");
    setCooldownUntil("");
    await load();
  };

  const createModelProviderKey = async () => {
    const selectedProviderKey = providerKeys.find((item) => item.id === selectedProviderKeyId);
    await adminApi.post("/admin/model-provider-keys", {
      model_id: selectedModelId,
      provider_key_id: selectedProviderKeyId,
      base_url: mappingBaseUrl || selectedProviderKey?.key_name || "",
      enabled: mappingEnabled,
      priority: Number(mappingPriority || 1),
      weight: Number(mappingWeight || 1),
      quota_unit: "requests",
      quota_rules: { minute: 1000 },
    });
    setSelectedModelId("");
    setSelectedProviderKeyId("");
    setMappingBaseUrl("");
    setMappingPriority("1");
    setMappingWeight("1");
    setMappingEnabled(true);
    await load();
  };

  return (
    <div className="space-y-6">
      <AdminPageIntro title="服务商管理" description="维护服务商 API Key，以及模型与服务商的路由绑定关系。" />
      {!adminToken && <AdminTokenWarning />}

      <Card className="p-6">
        <Typography variant="h6">新增服务商 Key</Typography>
        <Typography variant="body2" color="textSecondary" className="mt-1">
          继续保留 `watercolor` 风格，同时支持常见服务商预设自动填充。
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
                未选择预设时，可手动填自定义兼容服务商。
              </div>
            )}
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="Provider" placeholder="openai" value={provider} onChange={(e: any) => setProvider(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="Base URL" placeholder="https://api.openai.com" value={keyName} onChange={(e: any) => setKeyName(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="Secret Ref" placeholder="OPENAI_KEY" value={secretRef} onChange={(e: any) => setSecretRef(e.target.value)} fullWidth />
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
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={createProviderKey} disabled={!provider || !keyName || !secretRef}>
              新增
            </Button>
          </Grid>
        </Grid>
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between gap-3">
          <Typography variant="h6">服务商 Keys</Typography>
          <Badge variant="primary">{providerKeys.length}</Badge>
        </div>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>Provider</TableCell>
              <TableCell>名称</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>健康</TableCell>
              <TableCell align="right">创建时间</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {providerKeys.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.provider}</TableCell>
                <TableCell>{item.key_name}</TableCell>
                <TableCell>{item.enabled ? "enabled" : "disabled"}</TableCell>
                <TableCell>{item.health_state}</TableCell>
                <TableCell align="right">{item.created_at}</TableCell>
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

      <Card className="p-6">
        <Typography variant="h6">模型与服务商绑定</Typography>
        <Grid container spacing={2} className="mt-4" alignItems="flex-end">
          <Grid item xs={12} md={4}>
            <label className="mb-2 block text-sm font-medium text-slate-600">模型</label>
            <select
              className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-3 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200"
              value={selectedModelId}
              onChange={(e) => setSelectedModelId(e.target.value)}
            >
              <option value="">选择模型</option>
              {models.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </Grid>
          <Grid item xs={12} md={4}>
            <label className="mb-2 block text-sm font-medium text-slate-600">服务商 Key</label>
            <select
              className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-3 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200"
              value={selectedProviderKeyId}
              onChange={(e) => {
                const nextId = e.target.value;
                setSelectedProviderKeyId(nextId);
                const selectedProviderKey = providerKeys.find((item) => item.id === nextId);
                setMappingBaseUrl(selectedProviderKey?.key_name ?? "");
              }}
            >
              <option value="">选择服务商 Key</option>
              {providerKeys.map((item) => (
                <option key={item.id} value={item.id}>{item.provider} / {item.key_name}</option>
              ))}
            </select>
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField label="Base URL" value={mappingBaseUrl} onChange={(e: any) => setMappingBaseUrl(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={1}>
            <TextField label="优先级" value={mappingPriority} onChange={(e: any) => setMappingPriority(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={1}>
            <TextField label="权重" value={mappingWeight} onChange={(e: any) => setMappingWeight(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={1}>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={mappingEnabled} onChange={(e) => setMappingEnabled(e.target.checked)} />
              启用
            </label>
          </Grid>
          <Grid item xs={12} md={1}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={createModelProviderKey} disabled={!selectedModelId || !selectedProviderKeyId}>
              新增
            </Button>
          </Grid>
        </Grid>

        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>模型 ID</TableCell>
              <TableCell>服务商 Key ID</TableCell>
              <TableCell>Base URL</TableCell>
              <TableCell>状态</TableCell>
              <TableCell align="right">优先级</TableCell>
              <TableCell align="right">权重</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {modelProviderKeys.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.model_id}</TableCell>
                <TableCell>{item.provider_key_id}</TableCell>
                <TableCell>{item.base_url || "-"}</TableCell>
                <TableCell>{item.enabled ? "enabled" : "disabled"}</TableCell>
                <TableCell align="right">{item.priority}</TableCell>
                <TableCell align="right">{item.weight ?? 1}</TableCell>
              </TableRow>
            ))}
            {modelProviderKeys.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>暂无模型绑定</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default AdminProvidersPage;
