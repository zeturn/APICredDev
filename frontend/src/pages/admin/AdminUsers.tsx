import { Badge, Button, Card, Grid, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminIcon, AdminPageIntro } from "./adminCommon";
import { useI18n } from "../../i18n";

type ChatSession = {
  usage_session_id: string;
  model_name: string | null;
  upstream_provider: string | null;
  status: string;
  messages: Array<{ id: string; role?: string; source?: string; content?: string; user_deleted_at?: string | null }>;
  total_tokens: number;
  final_cost_credits: number;
  deleted_for_user?: boolean;
  created_at: string | null;
};

const AdminUsersPage = () => {
  const { t } = useI18n();
  const [users, setUsers] = useState<any[]>([]);
  const [activeUserId, setActiveUserId] = useState<string>("");
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatPage, setChatPage] = useState(1);
  const [chatTotal, setChatTotal] = useState(0);
  const chatPageSize = 5;

  const load = async () => {
    try {
      const resp = await adminApi.get("/admin/users");
      setUsers(resp.data);
    } catch {
      setUsers([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const updateStatus = async (userId: string, status: string) => {
    await adminApi.post(`/admin/users/${userId}/status`, { status });
    await load();
  };

  const loadUserChats = async (userId: string, page = 1) => {
    if (activeUserId === userId && page === chatPage) {
      setActiveUserId("");
      setChatSessions([]);
      setChatTotal(0);
      return;
    }
    setChatLoading(true);
    setActiveUserId(userId);
    try {
      const resp = await adminApi.get(`/admin/users/${userId}/audit-conversations`, { params: { page, page_size: chatPageSize } });
      setChatSessions(resp.data.items ?? []);
      setChatPage(resp.data.page ?? page);
      setChatTotal(resp.data.total ?? 0);
    } catch {
      setChatSessions([]);
      setChatTotal(0);
    }
    setChatLoading(false);
  };

  const getPromptPreview = (item: ChatSession) => {
    const first = item.messages?.find((msg) => msg.role === "user") ?? item.messages?.[0];
    return String(first?.content ?? "-").slice(0, 160);
  };
  const chatTotalPages = Math.max(Math.ceil(chatTotal / chatPageSize), 1);

  return (
    <div className="space-y-6">
      <AdminPageIntro title={t("users.title")} description={t("users.desc")} />
      <Card className="p-6">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-lg font-semibold text-slate-900">
            <AdminIcon icon="users" className="h-5 w-5" />
            {t("users.list")}
          </div>
          <Badge variant="warning">{users.length}</Badge>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
          {users.map((item) => (
            <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <Typography variant="subtitle1" className="truncate">{item.email}</Typography>
                  <Typography variant="caption" color="textSecondary">{item.created_at ? String(item.created_at).slice(0, 19).replace("T", " ") : "-"}</Typography>
                </div>
                <Badge variant={item.status === "active" ? "primary" : "warning"}>{item.status}</Badge>
              </div>

              <Grid container spacing={2} className="mt-3">
                <Grid item xs={4}>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-2 text-center">
                    <div className="text-xs text-slate-500">{t("users.balance")}</div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">{item.balance_credits}</div>
                  </div>
                </Grid>
                <Grid item xs={4}>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-2 text-center">
                    <div className="text-xs text-slate-500">{t("users.used")}</div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">{item.used_credits}</div>
                  </div>
                </Grid>
                <Grid item xs={4}>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-2 text-center">
                    <div className="text-xs text-slate-500">{t("users.sessions")}</div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">{item.usage_sessions}</div>
                  </div>
                </Grid>
              </Grid>

              <div className="mt-3 flex flex-wrap gap-2">
                <Button buttonStyle="text" variant="secondary" onClick={() => updateStatus(item.id, "active")}>{t("users.enable")}</Button>
                <Button buttonStyle="text" variant="error" onClick={() => updateStatus(item.id, "disabled")}>{t("users.disable")}</Button>
                <Button buttonStyle="text" variant="warning" onClick={() => loadUserChats(item.id, 1)}>
                  <span className="inline-flex items-center gap-2">
                    <AdminIcon icon="chat" className="h-4 w-4" />
                    {activeUserId === item.id ? t("users.collapseChat") : t("users.viewChat")}
                  </span>
                </Button>
              </div>
            </div>
          ))}

          {users.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-3 text-sm text-slate-500">{t("users.noUsers")}</div>
          )}
        </div>
      </Card>

      {activeUserId && (
        <Card className="p-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <AdminIcon icon="chat" className="h-5 w-5" />
              {t("users.auditChat")}
            </div>
            <Badge variant="secondary">{chatTotal}</Badge>
          </div>

          {chatLoading ? (
            <div className="mt-4 text-sm text-slate-500">{t("common.loading")}</div>
          ) : (
            <div className="mt-4 space-y-3">
              {chatSessions.map((item) => (
                <div key={item.usage_session_id} className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm font-semibold text-slate-900">{item.model_name || t("users.unknownModel")}</div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">{item.upstream_provider || "-"}</Badge>
                      <Badge variant={item.status === "completed" ? "primary" : "warning"}>{item.status}</Badge>
                      {item.deleted_for_user ? <Badge variant="warning">{t("users.userDeleted")}</Badge> : null}
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-slate-500">{item.created_at ? item.created_at.replace("T", " ").slice(0, 19) : "-"}</div>
                  <div className="mt-2 rounded-xl border border-slate-100 bg-slate-50 p-3 text-sm text-slate-700">
                    <div className="font-medium text-slate-900">{t("users.firstContent")}</div>
                    <div className="mt-1 break-words">{getPromptPreview(item)}</div>
                  </div>
                  <div className="mt-3 space-y-2">
                    {(item.messages ?? []).map((message) => (
                      <div key={message.id} className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-sm text-slate-700">
                        <div className="flex items-center justify-between gap-2 text-xs">
                          <span className="font-semibold uppercase tracking-[0.16em] text-slate-500">{message.role || "-"}</span>
                          <span className="text-slate-400">
                            {message.source || "-"}{message.user_deleted_at ? " · user deleted" : ""}
                          </span>
                        </div>
                        <div className="mt-2 whitespace-pre-wrap break-words">{message.content || "-"}</div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 text-xs text-slate-500">tokens: {item.total_tokens} · cost: {item.final_cost_credits}</div>
                </div>
              ))}
              {chatSessions.length === 0 && <div className="text-sm text-slate-500">{t("users.noChat")}</div>}
              {chatSessions.length > 0 && (
                <div className="flex items-center justify-between gap-3">
                  <Button
                    buttonStyle="text"
                    variant="secondary"
                    disabled={chatPage <= 1 || chatLoading}
                    onClick={() => loadUserChats(activeUserId, chatPage - 1)}
                  >
                    {t("users.prev")}
                  </Button>
                  <div className="text-sm text-slate-500">{chatPage} / {chatTotalPages}</div>
                  <Button
                    buttonStyle="text"
                    variant="secondary"
                    disabled={chatPage >= chatTotalPages || chatLoading}
                    onClick={() => loadUserChats(activeUserId, chatPage + 1)}
                  >
                    {t("users.next")}
                  </Button>
                </div>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default AdminUsersPage;
