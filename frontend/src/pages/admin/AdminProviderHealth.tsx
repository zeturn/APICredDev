import { Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import adminApi from "../../api/adminClient";
import { AdminPageIntro } from "./adminCommon";
import { useI18n } from "../../i18n";

type HealthItem = {
  provider: string;
  endpoint: string;
  credential_id: string;
  credential_name: string;
  enabled: boolean;
  health_state: string;
  cooldown_until?: string | null;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  last_error_code?: string | null;
  consecutive_failures: number;
  routes_count: number;
  quota_status?: Record<string, string>;
};

const AdminProviderHealthPage = () => {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [items, setItems] = useState<HealthItem[]>([]);
  const [benchmarks, setBenchmarks] = useState<any[]>([]);
  const [rotateCredentialId, setRotateCredentialId] = useState("");
  const [rotateSecret, setRotateSecret] = useState("");

  const load = async () => {
    try {
      const resp = await adminApi.get("/admin/provider-health");
      setItems((resp.data?.items || []) as HealthItem[]);
      const benchmarkResp = await adminApi.get("/admin/provider-benchmarks");
      setBenchmarks(benchmarkResp.data || []);
    } catch {
      setItems([]);
      setBenchmarks([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const action = async (url: string, body?: any) => {
    await adminApi.post(url, body || {});
    await load();
  };

  const rotate = async () => {
    if (!rotateCredentialId || !rotateSecret) return;
    await action(`/admin/provider-credentials/${rotateCredentialId}/rotate-secret`, { secret: rotateSecret });
    setRotateSecret("");
    setRotateCredentialId("");
  };

  return (
    <div className="space-y-6">
      <AdminPageIntro title={t("health.title")} description={t("health.desc")} />

      <Card className="p-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Typography variant="h6">{t("health.manageObjects")}</Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              {t("health.manageObjectsDesc")}
            </Typography>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button buttonStyle="filled" variant="primary" onClick={() => navigate("/admin/provider-credentials/new")}>
              {t("health.newCredential")}
            </Button>
            <Button buttonStyle="text" variant="secondary" onClick={() => navigate("/admin/provider-endpoints/new")}>
              {t("health.newEndpoint")}
            </Button>
            <Button buttonStyle="text" variant="secondary" onClick={() => navigate("/admin/providers/new")}>
              {t("health.newProvider")}
            </Button>
            <Button buttonStyle="text" variant="secondary" onClick={() => navigate("/admin/model-routes/new")}>
              {t("health.newRoute")}
            </Button>
          </div>
        </div>
      </Card>

      <Card className="p-6">
        <Typography variant="h6">{t("health.secretRotation")}</Typography>
        <Grid container spacing={2} className="mt-4" alignItems="flex-end">
          <Grid item xs={12} md={4}>
            <TextField label={t("health.credentialId")} value={rotateCredentialId} onChange={(e: any) => setRotateCredentialId(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField label={t("health.newSecret")} type="password" value={rotateSecret} onChange={(e: any) => setRotateSecret(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={2}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={rotate} disabled={!rotateCredentialId || !rotateSecret}>
              {t("health.rotate")}
            </Button>
          </Grid>
        </Grid>
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between">
          <Typography variant="h6">{t("health.providerHealth")}</Typography>
          <Badge variant="primary">{items.length}</Badge>
        </div>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>{t("health.colProvider")}</TableCell>
              <TableCell>{t("health.colEndpoint")}</TableCell>
              <TableCell>{t("health.colCredential")}</TableCell>
              <TableCell>{t("health.colHealth")}</TableCell>
              <TableCell>{t("health.colEnabled")}</TableCell>
              <TableCell>{t("health.colCooldown")}</TableCell>
              <TableCell>{t("health.colLastSuccess")}</TableCell>
              <TableCell>{t("health.colLastFailure")}</TableCell>
              <TableCell>{t("health.colError")}</TableCell>
              <TableCell align="right">{t("health.colFailures")}</TableCell>
              <TableCell align="right">{t("health.colRoutes")}</TableCell>
              <TableCell>{t("health.colQuota")}</TableCell>
              <TableCell>{t("health.colActions")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.credential_id}>
                <TableCell>{item.provider}</TableCell>
                <TableCell>{item.endpoint}</TableCell>
                <TableCell>{item.credential_name}</TableCell>
                <TableCell>{item.health_state}</TableCell>
                <TableCell>{item.enabled ? t("common.yes") : t("common.no")}</TableCell>
                <TableCell>{item.cooldown_until || "-"}</TableCell>
                <TableCell>{item.last_success_at || "-"}</TableCell>
                <TableCell>{item.last_failure_at || "-"}</TableCell>
                <TableCell>{item.last_error_code || "-"}</TableCell>
                <TableCell align="right">{item.consecutive_failures}</TableCell>
                <TableCell align="right">{item.routes_count}</TableCell>
                <TableCell>
                  {t("health.quotaLine", { minute: item.quota_status?.minute || "-", hour: item.quota_status?.hour || "-", day: item.quota_status?.day || "-" })}
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button buttonStyle="text" variant="primary" onClick={() => action(`/admin/provider-credentials/${item.credential_id}/health-check`)}>
                      {t("health.check")}
                    </Button>
                    <Button buttonStyle="text" variant="secondary" onClick={() => action(`/admin/provider-credentials/${item.credential_id}/${item.enabled ? "disable" : "enable"}`)}>
                      {item.enabled ? t("health.disable") : t("health.enable")}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {items.length === 0 && (
              <TableRow>
                <TableCell colSpan={13}>{t("health.noData")}</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between">
          <Typography variant="h6">{t("health.recentBenchmarks")}</Typography>
          <Badge variant="secondary">{benchmarks.length}</Badge>
        </div>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>{t("health.colRun")}</TableCell>
              <TableCell>{t("health.colProvider")}</TableCell>
              <TableCell>{t("health.colModel")}</TableCell>
              <TableCell align="right">{t("health.colRuns")}</TableCell>
              <TableCell>{t("health.colStatus")}</TableCell>
              <TableCell>{t("health.colSummary")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {benchmarks.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.id}</TableCell>
                <TableCell>{item.provider || "-"}</TableCell>
                <TableCell>{item.public_model || "-"}</TableCell>
                <TableCell align="right">{item.runs}</TableCell>
                <TableCell>{item.status}</TableCell>
                <TableCell>{JSON.stringify(item.summary_json || {})}</TableCell>
              </TableRow>
            ))}
            {benchmarks.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>{t("health.noBenchmarks")}</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default AdminProviderHealthPage;
