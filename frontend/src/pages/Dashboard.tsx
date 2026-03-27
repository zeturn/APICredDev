import { Badge, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import api from "../api/client";

const DashboardPage = () => {
  const [balance, setBalance] = useState(0);
  const [ledger, setLedger] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      const walletResp = await api.get("/billing/wallet");
      setBalance(walletResp.data.balance_credits);
      const ledgerResp = await api.get("/billing/ledger");
      setLedger(ledgerResp.data.slice(0, 10));
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
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <Typography variant="body2" color="textSecondary">
              当前余额
            </Typography>
            <Typography variant="h3" className="mt-2">
              {balance}
            </Typography>
            <Typography variant="caption" color="textSecondary">
              credits
            </Typography>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card className="p-6">
            <Typography variant="body2" color="textSecondary">
              今日窗口
            </Typography>
            <Typography variant="h6" className="mt-2">
              账单日状态
            </Typography>
            <Typography variant="caption" color="textSecondary" className="mt-3 block">
              余额与账本保持一致，可追溯审计。
            </Typography>
          </Card>
        </Grid>
      </Grid>

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
          <Badge variant="primary">append-only</Badge>
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

