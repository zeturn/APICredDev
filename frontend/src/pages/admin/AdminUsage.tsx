import { Badge, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminPageIntro } from "./adminCommon";

const AdminUsagePage = () => {
  const [usage, setUsage] = useState<{ recent_sessions: any[]; by_model: any[]; by_provider: any[] }>({
    recent_sessions: [],
    by_model: [],
    by_provider: [],
  });
  const adminToken = localStorage.getItem("admin_token") ?? "";

  useEffect(() => {
    const load = async () => {
      if (!adminToken) {
        setUsage({ recent_sessions: [], by_model: [], by_provider: [] });
        return;
      }
      const resp = await adminApi.get("/admin/usage-summary");
      setUsage(resp.data);
    };
    load();
  }, [adminToken]);

  return (
    <div className="space-y-6">
      <AdminPageIntro title="使用统计" description="查看全站最近调用记录，并按模型与服务商聚合额度消耗。" />

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between gap-3">
              <Typography variant="h6">按模型汇总</Typography>
              <Badge variant="primary">{usage.by_model.length}</Badge>
            </div>
            <Table className="mt-4">
              <TableHead>
                <TableRow>
                  <TableCell>模型</TableCell>
                  <TableCell align="right">请求数</TableCell>
                  <TableCell align="right">已用额度</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {usage.by_model.map((item) => (
                  <TableRow key={item.model_id}>
                    <TableCell>{item.model_name}</TableCell>
                    <TableCell align="right">{item.requests}</TableCell>
                    <TableCell align="right">{item.used_credits}</TableCell>
                  </TableRow>
                ))}
                {usage.by_model.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3}>暂无统计数据</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <div className="flex items-center justify-between gap-3">
              <Typography variant="h6">按服务商汇总</Typography>
              <Badge variant="warning">{usage.by_provider.length}</Badge>
            </div>
            <Table className="mt-4">
              <TableHead>
                <TableRow>
                  <TableCell>服务商</TableCell>
                  <TableCell align="right">请求数</TableCell>
                  <TableCell align="right">已用额度</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {usage.by_provider.map((item) => (
                  <TableRow key={item.provider}>
                    <TableCell>{item.provider}</TableCell>
                    <TableCell align="right">{item.requests}</TableCell>
                    <TableCell align="right">{item.used_credits}</TableCell>
                  </TableRow>
                ))}
                {usage.by_provider.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3}>暂无统计数据</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </Grid>
      </Grid>

      <Card className="p-6">
        <div className="flex items-center justify-between gap-3">
          <Typography variant="h6">最近调用记录</Typography>
          <Badge variant="secondary">{usage.recent_sessions.length}</Badge>
        </div>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>用户</TableCell>
              <TableCell>模型</TableCell>
              <TableCell>服务商</TableCell>
              <TableCell align="right">Tokens</TableCell>
              <TableCell align="right">费用</TableCell>
              <TableCell align="right">状态</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {usage.recent_sessions.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.user_email}</TableCell>
                <TableCell>{item.model_name}</TableCell>
                <TableCell>{item.provider ?? "-"}</TableCell>
                <TableCell align="right">{item.total_tokens}</TableCell>
                <TableCell align="right">{item.final_cost_credits}</TableCell>
                <TableCell align="right">{item.status}</TableCell>
              </TableRow>
            ))}
            {usage.recent_sessions.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>暂无调用记录</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default AdminUsagePage;
