import { Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminPageIntro, AdminTokenWarning } from "./adminCommon";

const AdminModelsPage = () => {
  const [models, setModels] = useState<any[]>([]);
  const [modelName, setModelName] = useState("");
  const [modelMultiplier, setModelMultiplier] = useState("1");
  const [modelPrice, setModelPrice] = useState("0");
  const [modelPriceUnit, setModelPriceUnit] = useState("1k_tokens");
  const [modelEnabled, setModelEnabled] = useState(true);
  const adminToken = localStorage.getItem("admin_token") ?? "";

  const load = async () => {
    if (!adminToken) {
      setModels([]);
      return;
    }
    const resp = await adminApi.get("/admin/models");
    setModels(resp.data);
  };

  useEffect(() => {
    load();
  }, [adminToken]);

  const createModel = async () => {
    await adminApi.post("/admin/models", {
      name: modelName,
      category: "llm",
      enabled: modelEnabled,
      multiplier: Number(modelMultiplier || 1),
      pricing: { unit: modelPriceUnit, price: Number(modelPrice || 0) },
    });
    setModelName("");
    setModelMultiplier("1");
    setModelPrice("0");
    setModelPriceUnit("1k_tokens");
    setModelEnabled(true);
    await load();
  };

  return (
    <div className="space-y-6">
      <AdminPageIntro title="模型管理" description="新增和查看对外可售卖的模型，以及对应计价策略。" />
      {!adminToken && <AdminTokenWarning />}
      <Card className="p-6">
        <div className="text-lg font-semibold text-slate-900">新增模型</div>
        <Grid container spacing={2} className="mt-4" alignItems="flex-end">
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
      </Card>

      <Card className="p-6">
        <div className="text-lg font-semibold text-slate-900">模型列表</div>
        <Table className="mt-4">
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
              <TableRow key={item.id}>
                <TableCell>{item.name}</TableCell>
                <TableCell>{item.enabled ? "enabled" : "disabled"}</TableCell>
                <TableCell>{JSON.stringify(item.pricing)}</TableCell>
                <TableCell align="right">x{item.multiplier}</TableCell>
              </TableRow>
            ))}
            {models.length === 0 && (
              <TableRow>
                <TableCell colSpan={4}>暂无模型</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default AdminModelsPage;
