import { Alert, Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@zeturn/watercolor-react";
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
  const [providerKeys, setProviderKeys] = useState<any[]>([]);
  const [providerPresets, setProviderPresets] = useState<ProviderPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState("");
  const [provider, setProvider] = useState("");
  const [keyName, setKeyName] = useState("");
  const [secretRef, setSecretRef] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [healthState, setHealthState] = useState("healthy");
  const [cooldownUntil, setCooldownUntil] = useState("");

  const activePreset = providerPresets.find((item) => item.provider === selectedPreset) ?? null;

  const loadAdminData = async () => {
    if (!adminToken) {
      setProviderKeys([]);
      setProviderPresets([]);
      return;
    }
    const [keysResp, presetsResp] = await Promise.all([
      adminApi.get("/admin/provider-keys"),
      adminApi.get("/admin/provider-presets"),
    ]);
    setProviderKeys(keysResp.data);
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

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          admin
        </Typography>
        <Typography variant="h5">Admin 控制面板</Typography>
        <Typography variant="body2" color="textSecondary">
          管理模型提供商 Key 与模型配置。
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
    </div>
  );
};

export default AdminPage;
