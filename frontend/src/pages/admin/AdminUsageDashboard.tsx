import { Badge, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminPageIntro } from "./adminCommon";

const AdminUsageDashboardPage = () => {
  const [summary, setSummary] = useState<any>({});
  const [byProvider, setByProvider] = useState<any[]>([]);
  const [byModel, setByModel] = useState<any[]>([]);
  const [topUsers, setTopUsers] = useState<any[]>([]);
  const [errors, setErrors] = useState<any[]>([]);
  const [quota, setQuota] = useState<any>({});

  useEffect(() => {
    const load = async () => {
      const [summaryResp, providerResp, modelResp, usersResp, errorsResp, quotaResp] = await Promise.all([
        adminApi.get("/admin/usage/summary"),
        adminApi.get("/admin/usage/by-provider"),
        adminApi.get("/admin/usage/by-model"),
        adminApi.get("/admin/usage/top-users"),
        adminApi.get("/admin/usage/errors"),
        adminApi.get("/admin/quota/summary"),
      ]);
      setSummary(summaryResp.data || {});
      setByProvider(providerResp.data || []);
      setByModel(modelResp.data || []);
      setTopUsers(usersResp.data || []);
      setErrors(errorsResp.data || []);
      setQuota(quotaResp.data || {});
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
      <AdminPageIntro title="Usage / Cost Dashboard" description="按 provider/model/user/错误维度查看请求、token、成本、配额状态。" />

      <Grid container spacing={2}>
        <Grid item xs={12} md={3}><Card className="p-4"><Typography variant="body2">Requests</Typography><Typography variant="h6">{summary.request_count || 0}</Typography></Card></Grid>
        <Grid item xs={12} md={3}><Card className="p-4"><Typography variant="body2">Success</Typography><Typography variant="h6">{summary.success_count || 0}</Typography></Card></Grid>
        <Grid item xs={12} md={3}><Card className="p-4"><Typography variant="body2">Error Rate</Typography><Typography variant="h6">{((summary.error_rate || 0) * 100).toFixed(2)}%</Typography></Card></Grid>
        <Grid item xs={12} md={3}><Card className="p-4"><Typography variant="body2">Final Cost</Typography><Typography variant="h6">{summary.final_cost_credits || 0}</Typography></Card></Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between"><Typography variant="h6">Usage by Provider</Typography><Badge variant="primary">{byProvider.length}</Badge></div>
            <Table className="mt-4"><TableHead><TableRow><TableCell>Provider</TableCell><TableCell align="right">Requests</TableCell><TableCell align="right">Error Rate</TableCell><TableCell align="right">Cost</TableCell></TableRow></TableHead><TableBody>
              {byProvider.map((item) => <TableRow key={item.provider}><TableCell>{item.provider}</TableCell><TableCell align="right">{item.request_count}</TableCell><TableCell align="right">{((item.error_rate || 0) * 100).toFixed(2)}%</TableCell><TableCell align="right">{item.final_cost_credits}</TableCell></TableRow>)}
            </TableBody></Table>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between"><Typography variant="h6">Usage by Model</Typography><Badge variant="secondary">{byModel.length}</Badge></div>
            <Table className="mt-4"><TableHead><TableRow><TableCell>Model</TableCell><TableCell align="right">Requests</TableCell><TableCell align="right">Tokens</TableCell><TableCell align="right">Cost</TableCell></TableRow></TableHead><TableBody>
              {byModel.map((item) => <TableRow key={item.model}><TableCell>{item.model}</TableCell><TableCell align="right">{item.request_count}</TableCell><TableCell align="right">{item.total_tokens}</TableCell><TableCell align="right">{item.final_cost_credits}</TableCell></TableRow>)}
            </TableBody></Table>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between"><Typography variant="h6">Top Users</Typography><Badge variant="warning">{topUsers.length}</Badge></div>
            <Table className="mt-4"><TableHead><TableRow><TableCell>User</TableCell><TableCell align="right">Requests</TableCell><TableCell align="right">Cost</TableCell></TableRow></TableHead><TableBody>
              {topUsers.map((item) => <TableRow key={item.user}><TableCell>{item.label || item.user}</TableCell><TableCell align="right">{item.request_count}</TableCell><TableCell align="right">{item.final_cost_credits}</TableCell></TableRow>)}
            </TableBody></Table>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between"><Typography variant="h6">Errors</Typography><Badge variant="warning">{errors.length}</Badge></div>
            <Table className="mt-4"><TableHead><TableRow><TableCell>Error</TableCell><TableCell align="right">Count</TableCell><TableCell align="right">Rate</TableCell></TableRow></TableHead><TableBody>
              {errors.map((item) => <TableRow key={item.error}><TableCell>{item.error}</TableCell><TableCell align="right">{item.error_count}</TableCell><TableCell align="right">{((item.error_rate || 0) * 100).toFixed(2)}%</TableCell></TableRow>)}
            </TableBody></Table>
          </Card>
        </Grid>
      </Grid>

      <Card className="p-6">
        <Typography variant="h6">Quota Summary</Typography>
        <div className="mt-3 text-sm text-slate-700">
          entries: {quota.entry_count || 0} | reserved: {quota.reserved_count || 0} | settled: {quota.settled_count || 0} | rejected: {quota.rejected_count || 0} | failed: {quota.failed_count || 0}
        </div>
      </Card>
    </div>
  );
};

export default AdminUsageDashboardPage;
