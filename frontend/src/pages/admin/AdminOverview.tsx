import { Badge, Card, Grid, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminIcon, AdminPageIntro } from "./adminCommon";
import { useI18n } from "../../i18n";

const AdminOverviewPage = () => {
  const { t } = useI18n();
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
      <AdminPageIntro title={t("overview.title")} description={t("overview.desc")} />
      {dashboard && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <div className="mb-2 inline-flex rounded-lg bg-sky-50 p-2 text-sky-700"><AdminIcon icon="users" /></div>
              <Typography variant="body2" color="textSecondary">{t("overview.users")}</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.total_users}</Typography>
              <Typography variant="caption" color="textSecondary">{t("overview.active", { n: dashboard.active_users })}</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <div className="mb-2 inline-flex rounded-lg bg-sky-50 p-2 text-sky-700"><AdminIcon icon="models" /></div>
              <Typography variant="body2" color="textSecondary">{t("overview.publicModels")}</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.public_models}</Typography>
              <Typography variant="caption" color="textSecondary">{t("overview.upstream", { n: dashboard.upstream_models })}</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <div className="mb-2 inline-flex rounded-lg bg-sky-50 p-2 text-sky-700"><AdminIcon icon="provider" /></div>
              <Typography variant="body2" color="textSecondary">{t("overview.credentials")}</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.provider_credentials}</Typography>
              <Typography variant="caption" color="textSecondary">{t("overview.endpoints", { n: dashboard.provider_endpoints })}</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card className="p-6">
              <div className="mb-2 inline-flex rounded-lg bg-sky-50 p-2 text-sky-700"><AdminIcon icon="usage" /></div>
              <Typography variant="body2" color="textSecondary">{t("overview.sessions")}</Typography>
              <Typography variant="h3" className="mt-2">{dashboard.usage_sessions}</Typography>
              <Typography variant="caption" color="textSecondary">{t("overview.completed", { n: dashboard.completed_usage_sessions })}</Typography>
            </Card>
          </Grid>
        </Grid>
      )}
      {dashboard && (
        <Card className="p-6">
          <div className="flex items-center justify-between gap-3">
            <Typography variant="h6">{t("overview.routingQuota")}</Typography>
            <Badge variant="warning">{t("overview.sitewide")}</Badge>
          </div>
          <Grid container spacing={2} className="mt-4">
            <Grid item xs={12} md={4}>
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                <Typography variant="body2" color="textSecondary">{t("overview.modelRoutes")}</Typography>
                <Typography variant="h3" className="mt-2">{dashboard.model_routes}</Typography>
              </div>
            </Grid>
            <Grid item xs={12} md={4}>
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                <Typography variant="body2" color="textSecondary">{t("overview.totalUsed")}</Typography>
                <Typography variant="h3" className="mt-2">{dashboard.total_usage_credits}</Typography>
              </div>
            </Grid>
            <Grid item xs={12} md={4}>
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                <Typography variant="body2" color="textSecondary">{t("overview.totalRemaining")}</Typography>
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
