import { Alert, Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@zeturn/watercolor-react";
import { useEffect, useState } from "react";
import adminApi from "../api/adminClient";

const AdminPage = () => {
  const [adminToken, setAdminToken] = useState(localStorage.getItem("admin_token") ?? "");
  const [providerKeys, setProviderKeys] = useState<any[]>([]);
  const [provider, setProvider] = useState("");
  const [keyName, setKeyName] = useState("");
  const [secretRef, setSecretRef] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [healthState, setHealthState] = useState("healthy");
  const [cooldownUntil, setCooldownUntil] = useState("");

  const loadProviderKeys = async () => {
    if (!adminToken) {
      setProviderKeys([]);
      return;
    }
    const resp = await adminApi.get("/admin/provider-keys");
    setProviderKeys(resp.data);
  };

  useEffect(() => {
    loadProviderKeys();
  }, []);

  const saveAdminToken = async () => {
    localStorage.setItem("admin_token", adminToken);
    await loadProviderKeys();
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
    await loadProviderKeys();
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
        <Grid container spacing={2} className="mt-2" alignItems="flex-end">
          <Grid item xs={12} md={4}>
            <TextField label="Provider" placeholder="openai" value={provider} onChange={(e: any) => setProvider(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="Key 名称" placeholder="default" value={keyName} onChange={(e: any) => setKeyName(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField label="Secret Ref" placeholder="env:OPENAI_KEY" value={secretRef} onChange={(e: any) => setSecretRef(e.target.value)} fullWidth />
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
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={createProviderKey}>
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
