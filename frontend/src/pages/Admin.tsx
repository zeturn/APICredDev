import { Alert, Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../api/adminClient";

type ProviderPreset = {
  provider: string;
  label: string;
  base_url: string;
  protocol: string;
  notes: string;
};

const AdminPage = () => {
  const [adminToken, setAdminToken] = useState(localStorage.getItem("admin_token") ?? "");
  const [dashboard, setDashboard] = useState<any | null>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [providerKeys, setProviderKeys] = useState<any[]>([]);
  const [modelProviderKeys, setModelProviderKeys] = useState<any[]>([]);
  const [providerPresets, setProviderPresets] = useState<ProviderPreset[]>([]);
  const [modelName, setModelName] = useState("");
  const [modelMultiplier, setModelMultiplier] = useState("1");
  const [modelPrice, setModelPrice] = useState("0");
  const [modelPriceUnit, setModelPriceUnit] = useState("1k_tokens");
  const [modelEnabled, setModelEnabled] = useState(true);
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

  const activePreset = providerPresets.find((item) => item.provider === selectedPreset) ?? null;

  const loadAdminData = async () => {
    if (!adminToken) {
      setDashboard(null);
      setUsers([]);
      setModels([]);
      setProviderKeys([]);
      setModelProviderKeys([]);
      setProviderPresets([]);
      return;
    }
    const [dashboardResp, usersResp, modelsResp, keysResp, modelKeysResp, presetsResp] = await Promise.all([
      adminApi.get("/admin/dashboard"),
      adminApi.get("/admin/users"),
      adminApi.get("/admin/models"),
      adminApi.get("/admin/provider-keys"),
      adminApi.get("/admin/model-provider-keys"),
      adminApi.get("/admin/provider-presets"),
    ]);
    setDashboard(dashboardResp.data);
    setUsers(usersResp.data);
    setModels(modelsResp.data);
    setProviderKeys(keysResp.data);
    setModelProviderKeys(modelKeysResp.data);
    setProviderPresets(presetsResp.data);
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const saveAdminToken = async () => {
    localStorage.setItem("admin_token", adminToken);
    await loadAdminData();
  };

  const applyPreset = (presetProvider: string) => {
    setSelectedPreset(presetProvider);
    const preset = providerPresets.find((item) => item.provider === presetProvider);
    if (!preset) {
      return;
    }
    setProvider(preset.provider);
    setKeyName(preset.base_url);
    if (!healthState) {
      setHealthState("healthy");
    }
  };

  const createProviderKey = async () => {
    const payload = {
      provider,
      key_name: keyName,
      secret_ref: secretRef,
      enabled,
      health_state: healthState || "healthy",
      cooldown_until: cooldownUntil || null,
    };
    await adminApi.post("/admin/provider-keys", payload);
    setProvider("");
    setKeyName("");
    setSecretRef("");
    setEnabled(true);
    setHealthState("healthy");
    setCooldownUntil("");
    setSelectedPreset("");
    await loadAdminData();
  };

  const createModel = async () => {
    await adminApi.post("/admin/models", {
      name: modelName,
      category: "llm",
      enabled: modelEnabled,
      multiplier: Number(modelMultiplier || 1),
      pricing: {
        unit: modelPriceUnit,
        price: Number(modelPrice || 0),
      },
    });
    setModelName("");
    setModelMultiplier("1");
    setModelPrice("0");
    setModelPriceUnit("1k_tokens");
    setModelEnabled(true);
    await loadAdminData();
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
    await loadAdminData();
  };

  const updateUserStatus = async (userId: string, status: string) => {
    await adminApi.post(`/admin/users/${userId}/status`, { status });
    await loadAdminData();
  };

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          admin
        </Typography>
        <Typography variant="h5">Admin 控制面板</Typography>
        <Typography variant="body2" color="textSecondary">
          用户、模型、服务商与全站额度运营控制台。
        </Typography>
      </div>

      <Card className="p-6">
        <Grid container spacing={2} alignItems="flex-end">
          <Grid item xs={12} md={9}>
            <TextField
              label="Admin Token"
              placeholder="X-Admin-Token"
              value={adminToken}
              onChange={(e: any) => setAdminToken(e.target.value)}
              fullWidth
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={saveAdminToken}>
              保存
            </Button>
          </Grid>
        </Grid>
        {!adminToken && (
          <Alert type="warning" variant="filled" showIcon className="mt-4">
            请先填写并保存 Admin Token 才能访问管理接口。
          </Alert>
        )}
      </Card>

      {dashboard && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <Typography variant="body2" color="textSecondary">用户总数</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.total_users}</Typography>
              <Typography variant="caption" color="textSecondary">活跃 {dashboard.active_users}</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <Typography variant="body2" color="textSecondary">模型总数</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.total_models}</Typography>
              <Typography variant="caption" color="textSecondary">启用 {dashboard.enabled_models}</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <Typography variant="body2" color="textSecondary">服务商 Key</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.provider_keys}</Typography>
              <Typography variant="caption" color="textSecondary">启用 {dashboard.enabled_provider_keys}</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <Typography variant="body2" color="textSecondary">全站已使用额度</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.total_usage_credits}</Typography>
              <Typography variant="caption" color="textSecondary">剩余 {dashboard.total_remaining_credits}</Typography>
            </Card>
          </Grid>
        </Grid>
      )}

      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Typography variant="h6">用户管理</Typography>
          <Badge variant="warning">{users.length}</Badge>
        </div>
        <div className="mt-4">
          <Table striped hover>
            <TableHead>
              <TableRow>
                <TableCell>邮箱</TableCell>
                <TableCell>状态</TableCell>
                <TableCell align="right">余额</TableCell>
                <TableCell align="right">已使用</TableCell>
                <TableCell align="right">调用次数</TableCell>
                <TableCell align="right">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell>{item.email}</TableCell>
                  <TableCell>{item.status}</TableCell>
                  <TableCell align="right">{item.balance_credits}</TableCell>
                  <TableCell align="right">{item.used_credits}</TableCell>
                  <TableCell align="right">{item.usage_sessions}</TableCell>
                  <TableCell align="right">
                    <div className="flex justify-end gap-2">
                      <Button buttonStyle="text" variant="secondary" onClick={() => updateUserStatus(item.id, "active")}>启用</Button>
                      <Button buttonStyle="text" variant="error" onClick={() => updateUserStatus(item.id, "disabled")}>禁用</Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      <Card className="p-6">
        <Typography variant="h6">模型与服务商管理</Typography>
        <Grid container spacing={2} className="mt-2" alignItems="flex-end">
          <Grid item xs={12} md={4}>
            <TextField label="模型名" placeholder="gpt-4o-mini" value={modelName} onChange={(e: any) => setModelName(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField label="倍率" value={modelMultiplier} onChange={(e: any) => setModelMultiplier(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField label="单价" value={modelPrice} onChange={(e: any) => setModelPrice(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={2}>
            <label className="mb-2 block text-sm font-medium text-slate-600">计价单位</label>
            <select
              className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-3 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200"
              value={modelPriceUnit}
              onChange={(e) => setModelPriceUnit(e.target.value)}
            >
              <option value="1k_tokens">1k_tokens</option>
              <option value="request">request</option>
            </select>
          </Grid>
          <Grid item xs={12} md={1}>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={modelEnabled} onChange={(e) => setModelEnabled(e.target.checked)} />
              启用
            </label>
          </Grid>
          <Grid item xs={12} md={1}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={createModel} disabled={!modelName}>
              新增
            </Button>
          </Grid>
        </Grid>
        <div className="mt-4">
          <Table striped hover>
            <TableHead>
              <TableRow>
                <TableCell>模型</TableCell>
                <TableCell>状态</TableCell>
                <TableCell>定价</TableCell>
                <TableCell align="right">倍率</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {models.map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell>{item.name}</TableCell>
                  <TableCell>{item.enabled ? "enabled" : "disabled"}</TableCell>
                  <TableCell>{JSON.stringify(item.pricing)}</TableCell>
                  <TableCell align="right">x{item.multiplier}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      <Card className="p-6">
        <Typography variant="h6">新增模型提供商 Key</Typography>
        <Typography variant="body2" color="textSecondary" className="mt-1">
          可先从预设中选择常见服务商，自动填入 `provider` 与推荐 `base_url`。
        </Typography>
        <Grid container spacing={2} className="mt-2" alignItems="flex-end">
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
                未选择预设时，可继续手动填写自定义服务商。
              </div>
            )}
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="Provider" placeholder="openai" value={provider} onChange={(e: any) => setProvider(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              label="Base URL"
              placeholder="https://api.openai.com"
              value={keyName}
              onChange={(e: any) => setKeyName(e.target.value)}
              fullWidth
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="Secret Ref" placeholder="OPENAI_KEY" value={secretRef} onChange={(e: any) => setSecretRef(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="健康状态" placeholder="healthy" value={healthState} onChange={(e: any) => setHealthState(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              label="Cooldown Until (ISO)"
              placeholder="2026-01-01T00:00:00Z"
              value={cooldownUntil}
              onChange={(e: any) => setCooldownUntil(e.target.value)}
              fullWidth
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              启用
            </label>
          </Grid>
          <Grid item xs={12} md={2}>
            <Button
              variant="primary"
              buttonStyle="filled"
              fullWidth
              onClick={createProviderKey}
              disabled={!provider || !keyName || !secretRef}
            >
              新增
            </Button>
          </Grid>
        </Grid>
      </Card>

      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Typography variant="h6">提供商 Keys</Typography>
          <Badge variant="primary">{providerKeys.length}</Badge>
        </div>
        <div className="mt-4">
          <Table striped hover>
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
                <TableRow key={item.id} hover>
                  <TableCell>{item.provider}</TableCell>
                  <TableCell>{item.key_name}</TableCell>
                  <TableCell>{item.enabled ? "enabled" : "disabled"}</TableCell>
                  <TableCell>{item.health_state}</TableCell>
                  <TableCell align="right">{item.created_at}</TableCell>
                </TableRow>
              ))}
              {providerKeys.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5}>暂无提供商 Key</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>

      <Card className="p-6">
        <Typography variant="h6">模型与服务商绑定</Typography>
        <Grid container spacing={2} className="mt-2" alignItems="flex-end">
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
            <Button
              variant="primary"
              buttonStyle="filled"
              fullWidth
              onClick={createModelProviderKey}
              disabled={!selectedModelId || !selectedProviderKeyId}
            >
              新增
            </Button>
          </Grid>
        </Grid>
        <div className="mt-4">
          <Table striped hover>
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
                <TableRow key={item.id} hover>
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
                  <TableCell colSpan={6}>暂无模型与服务商绑定</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  );
};

export default AdminPage;
