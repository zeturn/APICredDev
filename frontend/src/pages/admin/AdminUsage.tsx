import { Badge, Card, Grid, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminIcon, AdminPageIntro } from "./adminCommon";

const AdminUsagePage = () => {
  const [usage, setUsage] = useState<{ recent_sessions: any[]; by_model: any[]; by_provider: any[] }>({
    recent_sessions: [],
    by_model: [],
    by_provider: [],
  });

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await adminApi.get("/admin/usage-summary");
        setUsage(resp.data);
      } catch {
        setUsage({ recent_sessions: [], by_model: [], by_provider: [] });
      }
    };
    load();
  }, []);

  return (
    <div className="space-y-6">
      <AdminPageIntro title="使用统计" description="查看全站最近调用记录，并按模型与服务商聚合额度消耗。" />

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AdminIcon icon="models" className="h-5 w-5" />
                <Typography variant="h6">按模型汇总</Typography>
              </div>
              <Badge variant="primary">{usage.by_model.length}</Badge>
            </div>
            <div className="mt-4 space-y-2">
              {usage.by_model.map((item) => (
                <div key={item.model_id} className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium text-slate-900">{item.model_name}</span>
                    <span className="text-slate-500">请求 {item.requests} · 额度 {item.used_credits}</span>
                  </div>
                </div>
              ))}
              {usage.by_model.length === 0 && <div className="text-sm text-slate-500">暂无统计数据</div>}
            </div>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AdminIcon icon="provider" className="h-5 w-5" />
                <Typography variant="h6">按服务商汇总</Typography>
              </div>
              <Badge variant="warning">{usage.by_provider.length}</Badge>
            </div>
            <div className="mt-4 space-y-2">
              {usage.by_provider.map((item) => (
                <div key={item.provider} className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium text-slate-900">{item.provider}</span>
                    <span className="text-slate-500">请求 {item.requests} · 额度 {item.used_credits}</span>
                  </div>
                </div>
              ))}
              {usage.by_provider.length === 0 && <div className="text-sm text-slate-500">暂无统计数据</div>}
            </div>
          </Card>
        </Grid>
      </Grid>

      <Card className="p-6">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AdminIcon icon="usage" className="h-5 w-5" />
            <Typography variant="h6">最近调用记录</Typography>
          </div>
          <Badge variant="secondary">{usage.recent_sessions.length}</Badge>
        </div>
        <div className="mt-4 space-y-2">
          {usage.recent_sessions.map((item) => (
            <div key={item.id} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-medium text-slate-900">{item.user_email}</div>
                <Badge variant={item.status === "completed" ? "primary" : "warning"}>{item.status}</Badge>
              </div>
              <div className="mt-1 text-sm text-slate-700">{item.model_name} · {item.provider ?? "-"}</div>
              <div className="mt-1 text-xs text-slate-500">tokens: {item.total_tokens} · fee: {item.final_cost_credits}</div>
            </div>
          ))}
          {usage.recent_sessions.length === 0 && <div className="text-sm text-slate-500">暂无调用记录</div>}
        </div>
      </Card>
    </div>
  );
};

export default AdminUsagePage;
