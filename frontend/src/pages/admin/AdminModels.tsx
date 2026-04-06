import { Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminPageIntro } from "./adminCommon";
import { formatPricingSummary } from "../../shared/pricing";

type Brand = {
  id: string;
  name: string;
  slug: string;
  enabled: boolean;
  icon_url?: string | null;
};

const AdminModelsPage = () => {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [modelName, setModelName] = useState("");
  const [selectedBrandId, setSelectedBrandId] = useState("");
  const [modelIconUrl, setModelIconUrl] = useState("");
  const [modelCategory, setModelCategory] = useState("llm");
  const [modelMultiplier, setModelMultiplier] = useState("1");
  const [pricingMode, setPricingMode] = useState("token_segments");
  const [modelPrice, setModelPrice] = useState("0");
  const [modelPriceUnit, setModelPriceUnit] = useState("1k_tokens");
  const [inputPrice, setInputPrice] = useState("0");
  const [cachedInputPrice, setCachedInputPrice] = useState("");
  const [outputPrice, setOutputPrice] = useState("0");
  const [modelEnabled, setModelEnabled] = useState(true);
  const adminToken = localStorage.getItem("admin_token") ?? "";

  const load = async () => {
    if (!adminToken) {
      setBrands([]);
      setModels([]);
      return;
    }
    const [brandsResp, modelsResp] = await Promise.all([
      adminApi.get("/admin/brands"),
      adminApi.get("/admin/models"),
    ]);
    setBrands(brandsResp.data);
    setModels(modelsResp.data);
  };

  useEffect(() => {
    load();
  }, [adminToken]);

  const createModel = async () => {
    const pricing =
      pricingMode === "token_segments"
        ? {
            mode: "token_segments",
            input_per_million: Number(inputPrice || 0),
            cached_input_per_million: cachedInputPrice === "" ? undefined : Number(cachedInputPrice),
            output_per_million: Number(outputPrice || 0),
          }
        : { unit: modelPriceUnit, price: Number(modelPrice || 0) };
    await adminApi.post("/admin/models", {
      name: modelName,
      brand_id: selectedBrandId || null,
      icon_url: modelIconUrl || null,
      category: modelCategory,
      enabled: modelEnabled,
      multiplier: Number(modelMultiplier || 1),
      pricing,
    });
    setModelName("");
    setSelectedBrandId("");
    setModelIconUrl("");
    setModelCategory("llm");
    setModelMultiplier("1");
    setPricingMode("token_segments");
    setModelPrice("0");
    setModelPriceUnit("1k_tokens");
    setInputPrice("0");
    setCachedInputPrice("");
    setOutputPrice("0");
    setModelEnabled(true);
    await load();
  };

  return (
    <div className="space-y-6">
      <AdminPageIntro title="模型管理" description="新增和查看对外可售卖的模型，以及对应计价策略。" />
      <Card className="p-6">
        <div className="text-lg font-semibold text-slate-900">新增模型</div>
        <Grid container spacing={2} className="mt-4" alignItems="flex-end">
          <Grid item xs={12} md={3}>
            <label className="mb-2 block text-sm font-medium text-slate-600">品牌</label>
            <select
              className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-3 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200"
              value={selectedBrandId}
              onChange={(e) => setSelectedBrandId(e.target.value)}
            >
              <option value="">选择品牌</option>
              {brands.filter((item) => item.enabled).map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField label="模型名" placeholder="gpt-4o-mini" value={modelName} onChange={(e: any) => setModelName(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField label="模型图标 URL" placeholder="https://..." value={modelIconUrl} onChange={(e: any) => setModelIconUrl(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField label="分类" placeholder="llm / image / embedding" value={modelCategory} onChange={(e: any) => setModelCategory(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField label="倍率" value={modelMultiplier} onChange={(e: any) => setModelMultiplier(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={2}>
            <label className="mb-2 block text-sm font-medium text-slate-600">计费模式</label>
            <select
              className="w-full rounded-xl border border-ink-100 bg-white/80 px-3 py-3 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200"
              value={pricingMode}
              onChange={(e) => setPricingMode(e.target.value)}
            >
              <option value="token_segments">结构化 token</option>
              <option value="simple">简单单价</option>
            </select>
          </Grid>
          {pricingMode === "token_segments" ? (
            <>
              <Grid item xs={12} md={1}>
                <TextField label="输入价/1M" value={inputPrice} onChange={(e: any) => setInputPrice(e.target.value)} fullWidth />
              </Grid>
              <Grid item xs={12} md={1}>
                <TextField label="缓存输入/1M" value={cachedInputPrice} onChange={(e: any) => setCachedInputPrice(e.target.value)} fullWidth />
              </Grid>
              <Grid item xs={12} md={1}>
                <TextField label="输出价/1M" value={outputPrice} onChange={(e: any) => setOutputPrice(e.target.value)} fullWidth />
              </Grid>
            </>
          ) : (
            <>
              <Grid item xs={12} md={1}>
                <TextField label="单价" value={modelPrice} onChange={(e: any) => setModelPrice(e.target.value)} fullWidth />
              </Grid>
              <Grid item xs={12} md={1}>
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
            </>
          )}
          <Grid item xs={12} md={1}>
            <label className="mb-2 block text-sm font-medium text-slate-600">计价单位</label>
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">{pricingMode === "token_segments" ? "按输入/输出" : "简单模式"}</div>
          </Grid>
          <Grid item xs={12} md={1}>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={modelEnabled} onChange={(e) => setModelEnabled(e.target.checked)} />
              启用
            </label>
          </Grid>
          <Grid item xs={12} md={1}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={createModel} disabled={!modelName || !selectedBrandId}>
              新增
            </Button>
          </Grid>
        </Grid>
      </Card>

      <Card className="p-6">
        <div className="text-lg font-semibold text-slate-900">模型列表</div>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>模型</TableCell>
              <TableCell>品牌</TableCell>
              <TableCell>图标</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>定价</TableCell>
              <TableCell align="right">倍率</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {models.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.name}</TableCell>
                <TableCell>{item.brand_name || brands.find((brand) => brand.id === item.brand_id)?.name || "-"}</TableCell>
                <TableCell>
                  {item.effective_icon_url ? (
                    <img src={item.effective_icon_url} alt={item.name} className="h-6 w-6 rounded-md object-contain" />
                  ) : (
                    <div className="flex h-6 w-6 items-center justify-center rounded-md bg-slate-100 text-[10px] font-semibold text-slate-600">
                      {(item.name || "?").slice(0, 2).toUpperCase()}
                    </div>
                  )}
                </TableCell>
                <TableCell>{item.enabled ? "enabled" : "disabled"}</TableCell>
                <TableCell>
                  <div className="space-y-1 text-sm text-slate-700">
                    {formatPricingSummary(item.pricing).map((line) => (
                      <div key={`${item.id}-${line}`}>{line}</div>
                    ))}
                  </div>
                </TableCell>
                <TableCell align="right">x{item.multiplier}</TableCell>
              </TableRow>
            ))}
            {models.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>暂无模型</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default AdminModelsPage;
