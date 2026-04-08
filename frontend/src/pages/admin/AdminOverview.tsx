import { Badge, Card, Grid, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminIcon, AdminPageIntro } from "./adminCommon";

const AdminOverviewPage = () => {
  const [dashboard, setDashboard] = useState<any | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await adminApi.get("/admin/dashboard");
        setDashboard(resp.data);
      } catch {
        setDashboard(null);
      }
    };
    load();
  }, []);

  return (
    <div className="space-y-6">
      <AdminPageIntro title="总览" description="查看全站用户、模型、服务商和额度运行状态。" />
      {dashboard && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <div className="mb-2 inline-flex rounded-lg bg-sky-50 p-2 text-sky-700"><AdminIcon icon="users" /></div>
              <Typography variant="body2" color="textSecondary">用户</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.total_users}</Typography>
              <Typography variant="caption" color="textSecondary">活跃 {dashboard.active_users}</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <div className="mb-2 inline-flex rounded-lg bg-sky-50 p-2 text-sky-700"><AdminIcon icon="models" /></div>
              <Typography variant="body2" color="textSecondary">模型</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.total_models}</Typography>
              <Typography variant="caption" color="textSecondary">启用 {dashboard.enabled_models}</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <div className="mb-2 inline-flex rounded-lg bg-sky-50 p-2 text-sky-700"><AdminIcon icon="provider" /></div>
              <Typography variant="body2" color="textSecondary">服务商 Key</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.provider_keys}</Typography>
              <Typography variant="caption" color="textSecondary">启用 {dashboard.enabled_provider_keys}</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <div className="mb-2 inline-flex rounded-lg bg-sky-50 p-2 text-sky-700"><AdminIcon icon="usage" /></div>
              <Typography variant="body2" color="textSecondary">调用会话</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.usage_sessions}</Typography>
              <Typography variant="caption" color="textSecondary">完成 {dashboard.completed_usage_sessions}</Typography>
            </Card>
          </Grid>
        </Grid>
      )}
      {dashboard && (
        <Card className="p-6">
          <div className="flex items-center justify-between gap-3">
            <Typography variant="h6">额度概览</Typography>
            <Badge variant="warning">sitewide</Badge>
          </div>
          <Grid container spacing={2} className="mt-4">
            <Grid item xs={12} md={6}>
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                <Typography variant="body2" color="textSecondary">全站已使用额度</Typography>
                <Typography variant="h3" className="mt-2">{dashboard.total_usage_credits}</Typography>
              </div>
            </Grid>
            <Grid item xs={12} md={6}>
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                <Typography variant="body2" color="textSecondary">全站剩余额度</Typography>
                <Typography variant="h3" className="mt-2">{dashboard.total_remaining_credits}</Typography>
              </div>
            </Grid>
          </Grid>
        </Card>
      )}
    </div>
  );
};

export default AdminOverviewPage;
