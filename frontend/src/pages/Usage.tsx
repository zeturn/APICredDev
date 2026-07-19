import { Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import api from "../api/client";
import Skeleton from "../ui/Skeleton";
import { useI18n } from "../i18n";

const formatPoints = (value: unknown) => Number(value || 0).toLocaleString();
const formatNumber = (value: unknown) => Number(value || 0).toLocaleString();

const UsagePage = () => {
  const { t } = useI18n();
  const [usage, setUsage] = useState<{ recent_sessions: any[]; by_model: any[] }>({
    recent_sessions: [],
    by_model: [],
  });
  const [conversations, setConversations] = useState<any[]>([]);
  const [conversationPage, setConversationPage] = useState(1);
  const [conversationTotal, setConversationTotal] = useState(0);
  const conversationPageSize = 10;
  const [loading, setLoading] = useState(true);
  const [conversationLoading, setConversationLoading] = useState(true);

  const loadConversations = async (page: number) => {
    setConversationLoading(true);
    try {
      const resp = await api.get("/audit/conversations", { params: { page, page_size: conversationPageSize } });
      setConversations(resp.data.items ?? []);
      setConversationPage(resp.data.page ?? page);
      setConversationTotal(resp.data.total ?? 0);
    } finally {
      setConversationLoading(false);
    }
  };

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await api.get("/billing/usage");
        setUsage(resp.data);
      } finally {
        setLoading(false);
      }
    };
    load();
    loadConversations(1);
  }, []);

  const deleteConversation = async (usageSessionId: string) => {
    await api.delete(`/audit/conversations/${usageSessionId}`);
    await loadConversations(conversationPage);
  };

  const totalPages = Math.max(Math.ceil(conversationTotal / conversationPageSize), 1);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          {t("over.usage")}
        </Typography>
        <Typography variant="h5">{t("usage.title")}</Typography>
        <Typography variant="body2" color="textSecondary">
          {t("usage.desc")}
        </Typography>
      </div>
      <div className="h-[8px] w-full shrink-0 bg-[#103222] dark:bg-[#F0F4F8] mt-[7px] mb-[28px]" />

      <Grid container spacing={2}>
        <Grid item xs={12} md={5}>
          <Card className="p-6">
            <div className="flex items-center justify-between gap-3">
              <Typography variant="h6">{t("usage.byModel")}</Typography>
              <Badge variant="primary">{loading ? "..." : usage.by_model.length}</Badge>
            </div>
            <Table className="mt-4">
              <TableHead>
                <TableRow>
                  <TableCell>{t("common.model")}</TableCell>
                  <TableCell align="right">{t("usage.requests")}</TableCell>
                  <TableCell align="right">{t("usage.usedCredits")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading && Array.from({ length: 4 }).map((_, idx) => (
                  <TableRow key={`by-sk-${idx}`}>
                    <TableCell><Skeleton className="h-3 w-28" /></TableCell>
                    <TableCell align="right"><Skeleton className="ml-auto h-3 w-10" /></TableCell>
                    <TableCell align="right"><Skeleton className="ml-auto h-3 w-14" /></TableCell>
                  </TableRow>
                ))}
                {!loading && usage.by_model.map((item) => (
                  <TableRow key={item.model_id}>
                    <TableCell>{item.model_name}</TableCell>
                    <TableCell align="right">{formatNumber(item.requests)}</TableCell>
                    <TableCell align="right">{formatPoints(item.used_credits)}</TableCell>
                  </TableRow>
                ))}
                {!loading && usage.by_model.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3}>{t("usage.noSettled")}</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </Grid>
        <Grid item xs={12} md={7}>
          <Card className="p-6">
            <div className="flex items-center justify-between gap-3">
              <Typography variant="h6">{t("usage.recentCalls")}</Typography>
              <Badge variant="secondary">{loading ? "..." : usage.recent_sessions.length}</Badge>
            </div>
            <Table className="mt-4">
              <TableHead>
                <TableRow>
                  <TableCell>{t("common.model")}</TableCell>
                  <TableCell>{t("usage.provider")}</TableCell>
                  <TableCell align="right">{t("usage.tokens")}</TableCell>
                  <TableCell align="right">{t("usage.cost")}</TableCell>
                  <TableCell align="right">{t("usage.status")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading && Array.from({ length: 5 }).map((_, idx) => (
                  <TableRow key={`recent-sk-${idx}`}>
                    <TableCell><Skeleton className="h-3 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-3 w-20" /></TableCell>
                    <TableCell align="right"><Skeleton className="ml-auto h-3 w-12" /></TableCell>
                    <TableCell align="right"><Skeleton className="ml-auto h-3 w-12" /></TableCell>
                    <TableCell align="right"><Skeleton className="ml-auto h-3 w-14" /></TableCell>
                  </TableRow>
                ))}
                {!loading && usage.recent_sessions.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.model_name}</TableCell>
                    <TableCell>{item.provider ?? "-"}</TableCell>
                    <TableCell align="right">{formatNumber(item.total_tokens)}</TableCell>
                    <TableCell align="right">{formatPoints(item.final_cost_credits)}</TableCell>
                    <TableCell align="right">{item.status}</TableCell>
                  </TableRow>
                ))}
                {!loading && usage.recent_sessions.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5}>{t("usage.noRecent")}</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </Grid>
      </Grid>

      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Typography variant="h6">{t("usage.myConversations")}</Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              {t("usage.conversationsDesc")}
            </Typography>
          </div>
          <Badge variant="secondary">{conversationLoading ? "..." : conversationTotal}</Badge>
        </div>

        <div className="mt-4 space-y-3">
          {conversationLoading && <div className="text-sm text-slate-500">{t("common.loading")}</div>}
          {!conversationLoading && conversations.map((item) => (
            <div key={item.usage_session_id} className="border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-slate-900">{item.model_name || t("usage.unknownModel")}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    {item.created_at ? item.created_at.replace("T", " ").slice(0, 19) : "-"} · {t("usage.tokens")} {formatNumber(item.total_tokens)} · {t("usage.cost")} {formatPoints(item.final_cost_credits)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={item.status === "completed" ? "primary" : "warning"}>{item.status || "-"}</Badge>
                  <Button buttonStyle="text" variant="error" onClick={() => deleteConversation(item.usage_session_id)}>
                    {t("usage.delete")}
                  </Button>
                </div>
              </div>
              <div className="mt-4 space-y-2">
                {(item.messages ?? []).map((message: any) => (
                  <div key={message.id} className="border border-slate-100 bg-slate-50 px-3 py-2">
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="font-semibold uppercase tracking-[0.16em] text-slate-500">{message.role}</span>
                      <span className="text-slate-400">
                        {message.source || "-"}{message.user_deleted_at ? ` · ${t("usage.userDeleted")}` : ""}
                      </span>
                    </div>
                    <div className="mt-2 whitespace-pre-wrap break-words text-sm text-slate-800">{message.content || "-"}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {!conversationLoading && conversations.length === 0 && <div className="text-sm text-slate-500">{t("usage.noConversations")}</div>}
        </div>

        <div className="mt-4 flex items-center justify-between gap-3">
          <Button
            buttonStyle="text"
            variant="secondary"
            disabled={conversationPage <= 1 || conversationLoading}
            onClick={() => loadConversations(conversationPage - 1)}
          >
            {t("usage.prev")}
          </Button>
          <div className="text-sm text-slate-500">
            {conversationPage} / {totalPages}
          </div>
          <Button
            buttonStyle="text"
            variant="secondary"
            disabled={conversationPage >= totalPages || conversationLoading}
            onClick={() => loadConversations(conversationPage + 1)}
          >
            {t("usage.next")}
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default UsagePage;
