import { Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import adminApi from "../../api/adminClient";
import { AdminPageIntro } from "./adminCommon";

type Provider = {
  id: string;
  name: string;
  slug: string;
  default_base_url?: string | null;
  icon_url?: string | null;
  enabled: boolean;
};

const AdminProviderKeyDetailPage = () => {
  const { providerKeyId = "" } = useParams();
  const navigate = useNavigate();
  const adminToken = localStorage.getItem("admin_token") ?? "";
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [providerKey, setProviderKey] = useState<any | null>(null);
  const [modelLinks, setModelLinks] = useState<any[]>([]);
  const [keyBaseUrl, setKeyBaseUrl] = useState("");
  const [replacementApiKey, setReplacementApiKey] = useState("");
  const [validateResult, setValidateResult] = useState<any | null>(null);
  const [selectedModelId, setSelectedModelId] = useState("");
  const [mappingBaseUrl, setMappingBaseUrl] = useState("");
  const [mappingPriority, setMappingPriority] = useState("1");
  const [mappingWeight, setMappingWeight] = useState("1");
  const [mappingEnabled, setMappingEnabled] = useState(true);

  const load = async () => {
    if (!adminToken || !providerKeyId) {
      setProviders([]);
      setModels([]);
      setProviderKey(null);
      setModelLinks([]);
      return;
    }
    const [providersResp, modelsResp, detailResp] = await Promise.all([
      adminApi.get("/admin/providers"),
      adminApi.get("/admin/models"),
      adminApi.get(`/admin/provider-keys/${providerKeyId}`),
    ]);
    setProviders(providersResp.data);
    setModels(modelsResp.data);
    setProviderKey(detailResp.data.provider_key);
    setKeyBaseUrl(detailResp.data.provider_key?.key_name || "");
    setModelLinks(detailResp.data.model_links ?? []);
  };

  useEffect(() => {
    load();
  }, [adminToken, providerKeyId]);

  const createModelLink = async () => {
    if (!providerKey) return;
    await adminApi.post("/admin/model-provider-keys", {
      model_id: selectedModelId,
      provider_key_id: providerKey.id,
      base_url: mappingBaseUrl.trim() || null,
      enabled: mappingEnabled,
      priority: Number(mappingPriority || 1),
      weight: Number(mappingWeight || 1),
      quota_unit: "requests",
      quota_rules: { minute: 1000 },
    });
    setSelectedModelId("");
    setMappingBaseUrl("");
    setMappingPriority("1");
    setMappingWeight("1");
    setMappingEnabled(true);
    await load();
  };

  const saveProviderKey = async () => {
    if (!providerKey) return;
    await adminApi.post("/admin/provider-keys", {
      id: providerKey.id,
      provider_id: providerKey.provider_id || null,
      provider: providerKey.provider,
      key_name: keyBaseUrl.trim(),
      api_key: replacementApiKey.trim() || null,
      enabled: providerKey.enabled,
      health_state: providerKey.health_state || "healthy",
      cooldown_until: providerKey.cooldown_until || null,
    });
    setReplacementApiKey("");
    await load();
  };

  const validateProviderKey = async () => {
    if (!providerKey) return;
    const resp = await adminApi.post(`/admin/provider-keys/${providerKey.id}/validate`);
    setValidateResult(resp.data);
    await load();
  };

  const provider = providers.find((item) => item.slug === providerKey?.provider);

  return (
    <div className="space-y-6">
      <AdminPageIntro title="Key 详情" description="先创建 Key，再在详情页为这把 Key 配置可服务模型和特殊路由参数。" />

      <Card className="p-6">
        <div className="flex items-center justify-between gap-3">
          <Typography variant="h6">基础信息</Typography>
          <Button buttonStyle="text" variant="secondary" onClick={() => navigate("/admin/providers")}>
            返回 Key 列表
          </Button>
        </div>
        {providerKey ? (
          <Grid container spacing={2} className="mt-4">
            <Grid item xs={12} md={3}>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-sm text-slate-500">服务商</div>
                <div className="mt-2 flex items-center gap-3">
                  {provider?.icon_url ? (
                    <img src={provider.icon_url} alt={provider.name} className="h-8 w-8 rounded-md object-contain" />
                  ) : (
                    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-100 text-xs font-semibold text-slate-600">
                      {(providerKey.provider || "?").slice(0, 2).toUpperCase()}
                    </div>
                  )}
                  <div className="font-medium text-slate-900">{provider?.name || providerKey.provider}</div>
                </div>
              </div>
            </Grid>
            <Grid item xs={12} md={3}>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-sm text-slate-500">默认 URL</div>
                <div className="mt-2 break-all font-medium text-slate-900">{providerKey.key_name}</div>
              </div>
            </Grid>
            <Grid item xs={12} md={3}>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-sm text-slate-500">密钥状态</div>
                <div className="mt-2 break-all font-medium text-slate-900">{providerKey.has_secret ? (providerKey.secret_last4 ? `已加密保存 · ****${providerKey.secret_last4}` : "已加密保存") : "未设置"}</div>
              </div>
            </Grid>
            <Grid item xs={12} md={3}>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-sm text-slate-500">状态</div>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant={providerKey.enabled ? "primary" : "warning"}>{providerKey.enabled ? "enabled" : "disabled"}</Badge>
                  <Badge variant="secondary">{providerKey.health_state}</Badge>
                </div>
              </div>
            </Grid>
          </Grid>
        ) : (
          <div className="mt-4 text-sm text-slate-500">未找到这把 Key。</div>
        )}
      </Card>

      <Card className="p-6">
        <Typography variant="h6">编辑与测试</Typography>
        <Typography variant="body2" color="textSecondary" className="mt-1">
          可以更新默认 URL、轮换 API key，并直接测试这把 key 是否对服务商生效。
        </Typography>
        <Grid container spacing={2} className="mt-4" alignItems="flex-end">
          <Grid item xs={12} md={5}>
            <TextField label="默认 Base URL" placeholder="留空则使用服务商默认地址" value={keyBaseUrl} onChange={(e: any) => setKeyBaseUrl(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={5}>
            <TextField label="替换 API Key" placeholder="留空则不修改现有密钥" value={replacementApiKey} onChange={(e: any) => setReplacementApiKey(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={1}>
            <Button variant="secondary" buttonStyle="filled" fullWidth onClick={saveProviderKey} disabled={!providerKey}>
              保存
            </Button>
          </Grid>
          <Grid item xs={12} md={1}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={validateProviderKey} disabled={!providerKey}>
              测试
            </Button>
          </Grid>
        </Grid>
        {validateResult && (
          <div className={`mt-4 rounded-2xl border px-4 py-3 text-sm ${validateResult.ok ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-800"}`}>
            <div className="font-medium">{validateResult.ok ? "Key 可用" : "Key 校验失败"}</div>
            <div className="mt-1 break-all">Base URL: {validateResult.base_url || "-"}</div>
            {validateResult.status_code ? <div className="mt-1">HTTP: {validateResult.status_code}</div> : null}
            {validateResult.model_count != null ? <div className="mt-1">可见模型数: {validateResult.model_count}</div> : null}
            {validateResult.message ? <div className="mt-1 break-all">{String(validateResult.message)}</div> : null}
          </div>
        )}
      </Card>

      <Card className="p-6">
        <Typography variant="h6">新增适用模型</Typography>
        <Typography variant="body2" color="textSecondary" className="mt-1">
          如果不填写特殊 URL，系统会依次回退到 Key 默认 URL、服务商默认地址和协议内置地址。
        </Typography>
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
                <option key={item.id} value={item.id}>{item.brand_name ? `${item.brand_name} / ${item.name}` : item.name}</option>
              ))}
            </select>
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              label="特殊 Base URL"
              placeholder={providerKey?.key_name || "留空则使用默认 URL"}
              value={mappingBaseUrl}
              onChange={(e: any) => setMappingBaseUrl(e.target.value)}
              fullWidth
            />
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
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={createModelLink} disabled={!providerKey || !selectedModelId}>
              新增
            </Button>
          </Grid>
        </Grid>
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between gap-3">
          <Typography variant="h6">当前适用模型</Typography>
          <Badge variant="primary">{modelLinks.length}</Badge>
        </div>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>模型</TableCell>
              <TableCell>Base URL</TableCell>
              <TableCell>状态</TableCell>
              <TableCell align="right">优先级</TableCell>
              <TableCell align="right">权重</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {modelLinks.map((item) => {
              const model = models.find((modelItem) => modelItem.id === item.model_id);
              return (
                <TableRow key={item.id}>
                  <TableCell>{model ? (model.brand_name ? `${model.brand_name} / ${model.name}` : model.name) : item.model_id}</TableCell>
                  <TableCell>{item.base_url || providerKey?.key_name || provider?.default_base_url || "-"}</TableCell>
                  <TableCell>{item.enabled ? "enabled" : "disabled"}</TableCell>
                  <TableCell align="right">{item.priority}</TableCell>
                  <TableCell align="right">{item.weight ?? 1}</TableCell>
                </TableRow>
              );
            })}
            {modelLinks.length === 0 && (
              <TableRow>
                <TableCell colSpan={5}>这把 Key 还没有绑定任何模型</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default AdminProviderKeyDetailPage;
