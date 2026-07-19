import { Badge, Button, Card, Grid, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { AdminIcon } from "./admin/adminCommon";
import { useI18n } from "../i18n";
import Skeleton from "../ui/Skeleton";
import { LedgerItem, normalizeLedger } from "./dashboardData";

const formatPoints = (value: unknown) => Number(value || 0).toLocaleString();

const DashboardPage = () => {
  const navigate = useNavigate();
  const { t } = useI18n();
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
          {t("over.overview")}
        </Typography>
        <Typography variant="h5">{t("dash.title")}</Typography>
      </div>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card className="p-6 !bg-transparent !shadow-none !border-none">
                <div className="mb-2 flex items-center justify-between">
                  <Typography variant="body2" color="textSecondary">
                    {t("dash.balanceRemaining")}
                  </Typography>
                  <AdminIcon icon="wallet" className="h-4 w-4 text-slate-500" />
                </div>
                <Typography variant="h3" className="mt-2">
                  {loading ? <Skeleton className="h-10 w-24" /> : formatPoints(balance)}
                </Typography>
                  <Typography variant="caption" color="textSecondary">
                    {t("over.credits")}
                  </Typography>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card className="p-6 !bg-transparent !shadow-none !border-none">
                <div className="mb-2 flex items-center justify-between">
                  <Typography variant="body2" color="textSecondary">
                    {t("dash.usedCredits")}
                  </Typography>
                  <AdminIcon icon="usage" className="h-4 w-4 text-slate-500" />
                </div>
                <Typography variant="h3" className="mt-2">
                  {loading ? <Skeleton className="h-10 w-24" /> : formatPoints(summary.used_credits)}
                </Typography>
                <Typography variant="caption" color="textSecondary" className="mt-3 block">
                  {loading ? <Skeleton className="h-3 w-40" /> : t("dash.usedCalls", { count: summary.usage_sessions })}
                </Typography>
              </Card>
            </Grid>
          </Grid>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card className="h-full p-6 !bg-transparent !shadow-none !border-none">
                <div className="mb-2 flex items-center justify-between">
                  <Typography variant="body2" color="textSecondary">
                    {t("dash.availableModels")}
                  </Typography>
                  <AdminIcon icon="models" className="h-4 w-4 text-slate-500" />
                </div>
            <Typography variant="h3" className="mt-2">
              {loading ? <Skeleton className="h-10 w-20" /> : summary.available_models}
            </Typography>
            <Typography variant="caption" color="textSecondary" className="mt-3 block">
              {t("dash.availableModelsDesc")}
            </Typography>
            <div className="mt-4">
              <Button variant="secondary" buttonStyle="text" onClick={() => navigate("/workspace/models")}>
                <span className="inline-flex items-center gap-2">
                  <AdminIcon icon="api" className="h-4 w-4" />
                  {t("dash.viewPricing")}
                </span>
              </Button>
            </div>
          </Card>
        </Grid>
      </Grid>

      <Card className="p-6 !bg-transparent !shadow-none !border-none">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.28em]">
              {t("over.ledger")}
            </Typography>
            <div className="mt-2 flex items-center gap-2">
              <AdminIcon icon="wallet" className="h-4 w-4 text-slate-500" />
              <Typography variant="h6">{t("dash.recent10")}</Typography>
            </div>
          </div>
          <Badge variant="secondary">append-only</Badge>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 font-medium">
                <th className="pb-3 pr-4 font-medium">Order number</th>
                <th className="pb-3 px-4 font-medium">Purchase date</th>
                <th className="pb-3 px-4 font-medium">Customer</th>
                <th className="pb-3 px-4 font-medium">Event</th>
                <th className="pb-3 pl-4 text-right font-medium">Amount</th>
              </tr>
            </thead>
            <tbody>
              {loading && Array.from({ length: 5 }).map((_, idx) => (
                <tr key={`sk-${idx}`} className="border-b border-slate-100 dark:border-slate-800/50 last:border-none">
                  <td className="py-4 pr-4"><Skeleton className="h-4 w-24" /></td>
                  <td className="py-4 px-4"><Skeleton className="h-4 w-32" /></td>
                  <td className="py-4 px-4"><Skeleton className="h-4 w-24" /></td>
                  <td className="py-4 px-4"><Skeleton className="h-4 w-32" /></td>
                  <td className="py-4 pl-4"><Skeleton className="h-4 w-16 ml-auto" /></td>
                </tr>
              ))}
              {!loading && ledger.map((item) => (
                <tr key={item.id} className="border-b border-slate-100 dark:border-slate-800/50 last:border-none hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors">
                  <td className="py-4 pr-4 text-slate-600 dark:text-slate-300 font-medium">{item.id.slice(0, 8)}</td>
                  <td className="py-4 px-4 text-slate-500 dark:text-slate-400">{item.created_at ? String(item.created_at).replace("T", " ").slice(0, 19) : "-"}</td>
                  <td className="py-4 px-4 text-slate-900 dark:text-slate-200 font-medium">{user?.name || user?.email || "-"}</td>
                  <td className="py-4 px-4">
                    <span className="inline-flex items-center gap-2">
                       <div className="w-6 h-6 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center shrink-0">
                         <AdminIcon icon="wallet" className="w-3 h-3 text-slate-500 dark:text-slate-400" />
                       </div>
                       <span className="text-slate-900 dark:text-slate-200 font-medium">{item.entry_type}</span>
                    </span>
                  </td>
                  <td className="py-4 pl-4 text-right text-slate-900 dark:text-slate-200 font-semibold">{formatPoints(item.amount_credits)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && ledger.length === 0 && <div className="text-sm text-slate-500 text-center py-8">{t("dash.noLedger")}</div>}
        </div>
      </Card>
    </div>
  );
};

export default DashboardPage;
