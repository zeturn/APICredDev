import { Badge, Button, Card, Grid, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { AdminIcon } from "./admin/adminCommon";
import Skeleton from "../ui/Skeleton";
import { LedgerItem, normalizeLedger } from "./dashboardData";

const DashboardPage = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState({
    balance_credits: 0,
    used_credits: 0,
    usage_sessions: 0,
    available_models: 0,
  });
  const [balance, setBalance] = useState(0);
  const [ledger, setLedger] = useState<LedgerItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [summaryResp, walletResp, ledgerResp] = await Promise.all([
          api.get("/billing/summary"),
          api.get("/billing/wallet"),
          api.get("/billing/ledger"),
        ]);
        setSummary(summaryResp.data);
        setBalance(walletResp.data.balance_credits);
        setLedger(normalizeLedger(ledgerResp.data));
      } finally {
        setLoading(false);
      }
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

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card className="p-6">
                <div className="mb-2 flex items-center justify-between">
                  <Typography variant="body2" color="textSecondary">
                    剩余额度
                  </Typography>
                  <AdminIcon icon="wallet" className="h-4 w-4 text-slate-500" />
                </div>
                <Typography variant="h3" className="mt-2">
                  {loading ? <Skeleton className="h-10 w-24" /> : balance}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  credits
                </Typography>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card className="p-6">
                <div className="mb-2 flex items-center justify-between">
                  <Typography variant="body2" color="textSecondary">
                    已使用额度
                  </Typography>
                  <AdminIcon icon="usage" className="h-4 w-4 text-slate-500" />
                </div>
                <Typography variant="h3" className="mt-2">
                  {loading ? <Skeleton className="h-10 w-24" /> : summary.used_credits}
                </Typography>
                <Typography variant="caption" color="textSecondary" className="mt-3 block">
                  {loading ? <Skeleton className="h-3 w-40" /> : `共 ${summary.usage_sessions} 次调用已完成结算。`}
                </Typography>
              </Card>
            </Grid>
          </Grid>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card className="h-full p-6">
            <div className="mb-2 flex items-center justify-between">
              <Typography variant="body2" color="textSecondary">
                可用模型
              </Typography>
              <AdminIcon icon="models" className="h-4 w-4 text-slate-500" />
            </div>
            <Typography variant="h3" className="mt-2">
              {loading ? <Skeleton className="h-10 w-20" /> : summary.available_models}
            </Typography>
            <Typography variant="caption" color="textSecondary" className="mt-3 block">
              当前已启用并可调用的模型数量。
            </Typography>
            <div className="mt-4">
              <Button variant="secondary" buttonStyle="text" onClick={() => navigate("/workspace/models")}>
                <span className="inline-flex items-center gap-2">
                  <AdminIcon icon="api" className="h-4 w-4" />
                  查看模型价格与图标
                </span>
              </Button>
            </div>
          </Card>
        </Grid>
      </Grid>

      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.28em]">
              ledger
            </Typography>
            <div className="mt-2 flex items-center gap-2">
              <AdminIcon icon="wallet" className="h-4 w-4 text-slate-500" />
              <Typography variant="h6">最近 10 笔</Typography>
            </div>
          </div>
          <Badge variant="secondary">append-only</Badge>
        </div>
        <div className="mt-4 space-y-2">
          {loading && Array.from({ length: 5 }).map((_, idx) => (
            <div key={`sk-${idx}`} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Skeleton className="h-3 w-36" />
                <Skeleton className="h-3 w-20" />
              </div>
              <Skeleton className="mt-2 h-3 w-32" />
            </div>
          ))}

          {!loading && ledger.map((item) => (
            <div key={item.id} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-medium text-slate-900">{item.entry_type}</div>
                <div className="text-sm font-semibold text-slate-900">{item.amount_credits}</div>
              </div>
              <div className="mt-1 text-xs text-slate-500">{item.created_at ? String(item.created_at).replace("T", " ").slice(0, 19) : "-"}</div>
            </div>
          ))}

          {!loading && ledger.length === 0 && <div className="text-sm text-slate-500">暂无账本记录</div>}
        </div>
      </Card>
    </div>
  );
};

export default DashboardPage;
