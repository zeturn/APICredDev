import { Badge, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminPageIntro } from "./adminCommon";
import { useI18n } from "../../i18n";

const formatPoints = (value: unknown) => Number(value || 0).toLocaleString();
const formatNumber = (value: unknown) => Number(value || 0).toLocaleString();

const AdminUsageDashboardPage = () => {
  const { t } = useI18n();
  const [summary, setSummary] = useState<any>({});
  const [byProvider, setByProvider] = useState<any[]>([]);
  const [byModel, setByModel] = useState<any[]>([]);
  const [topUsers, setTopUsers] = useState<any[]>([]);
  const [errors, setErrors] = useState<any[]>([]);
  const [quota, setQuota] = useState<any>({});

  useEffect(() => {
    const load = async () => {
      const graphqlUrl = "/graphql";
      const query = `
        query {
          adminDashboardData {
            summary { requestCount successCount errorRate finalCostCredits }
            byProvider { provider label requestCount errorRate finalCostCredits }
            byModel { model label requestCount totalTokens finalCostCredits }
            topUsers { user label requestCount finalCostCredits }
            errors { error label errorCount errorRate }
            quota { entryCount reservedCount settledCount rejectedCount failedCount }
          }
        }
      `;
      const resp = await adminApi.post(graphqlUrl, { query });
      const data = resp.data?.data?.adminDashboardData || {};
      
      setSummary(data.summary || {});
      setByProvider(data.byProvider || []);
      setByModel(data.byModel || []);
      setTopUsers(data.topUsers || []);
      setErrors(data.errors || []);
      setQuota(data.quota || {});
    };
    load().catch(() => {
      setSummary({});
      setByProvider([]);
      setByModel([]);
      setTopUsers([]);
      setErrors([]);
      setQuota({});
    });
  }, []);

  return (
    <div className="space-y-6">
      <AdminPageIntro title={t("udash.title")} description={t("udash.desc")} />

      <Grid container spacing={2}>
        <Grid item xs={12} md={3}><Card className="p-4"><Typography variant="body2">{t("udash.requests")}</Typography><Typography variant="h6">{formatNumber(summary.requestCount)}</Typography></Card></Grid>
        <Grid item xs={12} md={3}><Card className="p-4"><Typography variant="body2">{t("udash.success")}</Typography><Typography variant="h6">{formatNumber(summary.successCount)}</Typography></Card></Grid>
        <Grid item xs={12} md={3}><Card className="p-4"><Typography variant="body2">{t("udash.errorRate")}</Typography><Typography variant="h6">{((summary.errorRate || 0) * 100).toFixed(2)}%</Typography></Card></Grid>
        <Grid item xs={12} md={3}><Card className="p-4"><Typography variant="body2">{t("udash.finalCost")}</Typography><Typography variant="h6">{formatPoints(summary.finalCostCredits)}</Typography></Card></Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between"><Typography variant="h6">{t("udash.byProvider")}</Typography><Badge variant="primary">{byProvider.length}</Badge></div>
            <Table className="mt-4"><TableHead><TableRow><TableCell>{t("udash.colProvider")}</TableCell><TableCell align="right">{t("udash.colRequests")}</TableCell><TableCell align="right">{t("udash.errorRate")}</TableCell><TableCell align="right">{t("udash.colCost")}</TableCell></TableRow></TableHead><TableBody>
              {byProvider.map((item) => <TableRow key={item.provider}><TableCell>{item.provider}</TableCell><TableCell align="right">{formatNumber(item.requestCount)}</TableCell><TableCell align="right">{((item.errorRate || 0) * 100).toFixed(2)}%</TableCell><TableCell align="right">{formatPoints(item.finalCostCredits)}</TableCell></TableRow>)}
            </TableBody></Table>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between"><Typography variant="h6">{t("udash.byModel")}</Typography><Badge variant="secondary">{byModel.length}</Badge></div>
            <Table className="mt-4"><TableHead><TableRow><TableCell>{t("udash.colModel")}</TableCell><TableCell align="right">{t("udash.colRequests")}</TableCell><TableCell align="right">{t("udash.colTokens")}</TableCell><TableCell align="right">{t("udash.colCost")}</TableCell></TableRow></TableHead><TableBody>
              {byModel.map((item) => <TableRow key={item.model}><TableCell>{item.model}</TableCell><TableCell align="right">{formatNumber(item.requestCount)}</TableCell><TableCell align="right">{formatNumber(item.totalTokens)}</TableCell><TableCell align="right">{formatPoints(item.finalCostCredits)}</TableCell></TableRow>)}
            </TableBody></Table>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between"><Typography variant="h6">{t("udash.topUsers")}</Typography><Badge variant="warning">{topUsers.length}</Badge></div>
            <Table className="mt-4"><TableHead><TableRow><TableCell>{t("udash.colUser")}</TableCell><TableCell align="right">{t("udash.colRequests")}</TableCell><TableCell align="right">{t("udash.colCost")}</TableCell></TableRow></TableHead><TableBody>
              {topUsers.map((item) => <TableRow key={item.user}><TableCell>{item.label || item.user}</TableCell><TableCell align="right">{formatNumber(item.requestCount)}</TableCell><TableCell align="right">{formatPoints(item.finalCostCredits)}</TableCell></TableRow>)}
            </TableBody></Table>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between"><Typography variant="h6">{t("udash.errors")}</Typography><Badge variant="warning">{errors.length}</Badge></div>
            <Table className="mt-4"><TableHead><TableRow><TableCell>{t("udash.colError")}</TableCell><TableCell align="right">{t("udash.colCount")}</TableCell><TableCell align="right">{t("udash.colRate")}</TableCell></TableRow></TableHead><TableBody>
              {errors.map((item) => <TableRow key={item.error}><TableCell>{item.error}</TableCell><TableCell align="right">{formatNumber(item.errorCount)}</TableCell><TableCell align="right">{((item.errorRate || 0) * 100).toFixed(2)}%</TableCell></TableRow>)}
            </TableBody></Table>
          </Card>
        </Grid>
      </Grid>

      <Card className="p-6">
        <Typography variant="h6">{t("udash.quotaSummary")}</Typography>
        <div className="mt-3 text-sm text-slate-700">
          {t("udash.quotaLine", { entries: quota.entryCount || 0, reserved: quota.reservedCount || 0, settled: quota.settledCount || 0, rejected: quota.rejectedCount || 0, failed: quota.failedCount || 0 })}
        </div>
      </Card>
    </div>
  );
};

export default AdminUsageDashboardPage;
