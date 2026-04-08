import { Badge, Button, Card, Grid, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminIcon, AdminPageIntro } from "./adminCommon";

type ChatSession = {
  id: string;
  model_name: string | null;
  upstream_provider: string | null;
  status: string;
  request_messages: Array<{ role?: string; content?: string }>;
  request_text: string | null;
  response_text: string | null;
  total_tokens: number;
  final_cost_credits: number;
  created_at: string | null;
};

const AdminUsersPage = () => {
  const [users, setUsers] = useState<any[]>([]);
  const [activeUserId, setActiveUserId] = useState<string>("");
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

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

  const loadUserChats = async (userId: string) => {
    if (activeUserId === userId) {
      setActiveUserId("");
      setChatSessions([]);
      return;
    }
    setChatLoading(true);
    setActiveUserId(userId);
    try {
      const resp = await adminApi.get(`/admin/users/${userId}/chat-sessions`);
      setChatSessions(resp.data ?? []);
    } catch {
      setChatSessions([]);
    }
    setChatLoading(false);
  };

  const getPromptPreview = (item: ChatSession) => {
    if (item.request_messages?.length) {
      const first = item.request_messages.find((msg) => msg.role === "user") ?? item.request_messages[0];
      const content = first?.content ?? "";
      return String(content).slice(0, 120) || "-";
    }
    return (item.request_text || "-").slice(0, 120);
  };

  return (
    <div className="space-y-6">
      <AdminPageIntro title="用户管理" description="查看用户余额、使用情况，并启用或禁用账号。" />
      <Card className="p-6">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-lg font-semibold text-slate-900">
            <AdminIcon icon="users" className="h-5 w-5" />
            用户列表
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
                    <div className="text-xs text-slate-500">余额</div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">{item.balance_credits}</div>
                  </div>
                </Grid>
                <Grid item xs={4}>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-2 text-center">
                    <div className="text-xs text-slate-500">已用</div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">{item.used_credits}</div>
                  </div>
                </Grid>
                <Grid item xs={4}>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-2 text-center">
                    <div className="text-xs text-slate-500">会话</div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">{item.usage_sessions}</div>
                  </div>
                </Grid>
              </Grid>

              <div className="mt-3 flex flex-wrap gap-2">
                <Button buttonStyle="text" variant="secondary" onClick={() => updateStatus(item.id, "active")}>启用</Button>
                <Button buttonStyle="text" variant="error" onClick={() => updateStatus(item.id, "disabled")}>禁用</Button>
                <Button buttonStyle="text" variant="warning" onClick={() => loadUserChats(item.id)}>
                  <span className="inline-flex items-center gap-2">
                    <AdminIcon icon="chat" className="h-4 w-4" />
                    {activeUserId === item.id ? "收起聊天记录" : "查看聊天记录"}
                  </span>
                </Button>
              </div>
            </div>
          ))}

          {users.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-3 text-sm text-slate-500">暂无用户数据</div>
          )}
        </div>
      </Card>

      {activeUserId && (
        <Card className="p-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <AdminIcon icon="chat" className="h-5 w-5" />
              用户聊天记录
            </div>
            <Badge variant="secondary">{chatSessions.length}</Badge>
          </div>

          {chatLoading ? (
            <div className="mt-4 text-sm text-slate-500">加载中...</div>
          ) : (
            <div className="mt-4 space-y-3">
              {chatSessions.map((item) => (
                <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm font-semibold text-slate-900">{item.model_name || "unknown model"}</div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">{item.upstream_provider || "-"}</Badge>
                      <Badge variant={item.status === "completed" ? "primary" : "warning"}>{item.status}</Badge>
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-slate-500">{item.created_at ? item.created_at.replace("T", " ").slice(0, 19) : "-"}</div>
                  <div className="mt-2 rounded-xl border border-slate-100 bg-slate-50 p-3 text-sm text-slate-700">
                    <div className="font-medium text-slate-900">用户输入</div>
                    <div className="mt-1 break-words">{getPromptPreview(item)}</div>
                  </div>
                  {item.response_text ? (
                    <div className="mt-2 rounded-xl border border-slate-100 bg-slate-50 p-3 text-sm text-slate-700">
                      <div className="font-medium text-slate-900">模型回复（截断）</div>
                      <div className="mt-1 break-words">{item.response_text.slice(0, 200)}</div>
                    </div>
                  ) : null}
                  <div className="mt-2 text-xs text-slate-500">tokens: {item.total_tokens} · cost: {item.final_cost_credits}</div>
                </div>
              ))}
              {chatSessions.length === 0 && <div className="text-sm text-slate-500">暂无聊天记录</div>}
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default AdminUsersPage;
