import { Badge, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import api from "../api/client";

const DashboardPage = () => {
  const [summary, setSummary] = useState({
    balance_credits: 0,
    used_credits: 0,
    usage_sessions: 0,
    available_models: 0,
  });
  const [balance, setBalance] = useState(0);
  const [ledger, setLedger] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      const summaryResp = await api.get("/billing/summary");
      setSummary(summaryResp.data);
      const walletResp = await api.get("/billing/wallet");
      setBalance(walletResp.data.balance_credits);
      const ledgerResp = await api.get("/billing/ledger");
      setLedger(ledgerResp.data.slice(0, 10));
      const modelsResp = await api.get("/models");
      setModels(modelsResp.data);
    };
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          overview
        </Typography>
        <Typography variant="h5">总览</Typography>
      </div>

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Card className="p-6">
            <Typography variant="body2" color="textSecondary">
              剩余额度
            </Typography>
            <Typography variant="h3" className="mt-2">
              {balance}
            </Typography>
            <Typography variant="caption" color="textSecondary">
              credits
            </Typography>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card className="p-6">
            <Typography variant="body2" color="textSecondary">
              已使用额度
            </Typography>
            <Typography variant="h3" className="mt-2">
              {summary.used_credits}
            </Typography>
            <Typography variant="caption" color="textSecondary" className="mt-3 block">
              共 {summary.usage_sessions} 次调用已完成结算。
            </Typography>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card className="p-6">
            <Typography variant="body2" color="textSecondary">
              可用模型
            </Typography>
            <Typography variant="h3" className="mt-2">
              {summary.available_models}
            </Typography>
            <Typography variant="caption" color="textSecondary" className="mt-3 block">
              当前已启用并可调用的模型数量。
            </Typography>
          </Card>
        </Grid>
      </Grid>

      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.28em]">
              models
            </Typography>
            <Typography variant="h6" className="mt-2">
              可用模型列表
            </Typography>
          </div>
          <Badge variant="primary">{models.length}</Badge>
        </div>
        <div className="mt-4">
          <Table striped hover>
            <TableHead>
              <TableRow>
                <TableCell>模型</TableCell>
                <TableCell>定价</TableCell>
                <TableCell align="right">倍率</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {models.map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell>{item.name}</TableCell>
                  <TableCell>{JSON.stringify(item.pricing)}</TableCell>
                  <TableCell align="right">x{item.multiplier}</TableCell>
                </TableRow>
              ))}
              {models.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3}>暂无可用模型</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>

      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.28em]">
              ledger
            </Typography>
            <Typography variant="h6" className="mt-2">
              最近 10 笔
            </Typography>
          </div>
          <Badge variant="secondary">append-only</Badge>
        </div>
        <div className="mt-4">
          <Table striped hover>
            <TableHead>
              <TableRow>
                <TableCell>类型</TableCell>
                <TableCell align="right">额度</TableCell>
                <TableCell align="right">时间</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {ledger.map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell>{item.entry_type}</TableCell>
                  <TableCell align="right">{item.amount_credits}</TableCell>
                  <TableCell align="right">{item.created_at}</TableCell>
                </TableRow>
              ))}
              {ledger.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3}>暂无账本记录</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  );
};

export default DashboardPage;

