import { Alert, Button, Card, List, ListItem, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { adminConsoleRoutes } from "../navigation/consoleRoutes";
import { clearAdminAccessToken, ensureAdminToken } from "../api/adminClient";
import { AdminIcon } from "../pages/admin/adminCommon";
import api from "../api/client";

const AdminLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [adminReady, setAdminReady] = useState(false);
  const [adminAllowed, setAdminAllowed] = useState(false);
  const navItems = adminConsoleRoutes.map((item) => ({ to: item.path, label: item.label }));
  const iconByPath: Record<string, "users" | "models" | "provider" | "usage" | "chat" | "api" | "shield"> = {
    "/admin/overview": "shield",
    "/admin/users": "users",
    "/admin/brands": "models",
    "/admin/public-models": "models",
    "/admin/upstream-models": "models",
    "/admin/providers": "provider",
    "/admin/provider-endpoints": "provider",
    "/admin/provider-credentials": "provider",
    "/admin/model-routes": "api",
    "/admin/usage": "usage",
    "/admin/api-models": "api",
  };
  const isSelected = (path: string) => location.pathname === path || location.pathname.startsWith(`${path}/`);

  useEffect(() => {
    let active = true;
    const bootstrap = async () => {
      const token = await ensureAdminToken();
      if (!active) {
        return;
      }
      setAdminAllowed(Boolean(token));
      setAdminReady(true);
    };
    bootstrap();
    return () => {
      active = false;
    };
  }, []);

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
    }
    clearAdminAccessToken();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="flex min-h-screen w-full gap-6 px-4 py-6 md:px-6">
        <aside className="sticky top-4 h-fit w-64 shrink-0 self-start">
          <Card className="p-5">
            <Typography variant="subtitle2" color="textSecondary" className="uppercase tracking-[0.3em]">
              apicred
            </Typography>
            <Typography variant="h6" className="mt-2">
              管理控制台
            </Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              模型目录、上游路由与密钥配置。
            </Typography>

            <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
              <Typography variant="caption" color="textSecondary">
                {adminReady ? (adminAllowed ? "已自动配置 Admin Token" : "当前账号无 Admin 权限") : "正在自动校验 Admin 权限..."}
              </Typography>
            </div>

            <List className="mt-4 space-y-1">
              {navItems.map((item) => (
                <ListItem
                  key={item.to}
                  button
                  component={NavLink}
                  to={item.to}
                  selected={isSelected(item.to)}
                >
                  <span className="inline-flex items-center gap-2">
                    <AdminIcon icon={iconByPath[item.to] ?? "shield"} className="h-4 w-4" />
                    {item.label}
                  </span>
                </ListItem>
              ))}
            </List>

            <div className="mt-6 space-y-2">
              <Button buttonStyle="text" variant="secondary" fullWidth onClick={() => navigate("/workspace/dashboard")}>
                返回用户端
              </Button>
              <Button buttonStyle="text" variant="error" fullWidth onClick={logout}>
                退出登录
              </Button>
            </div>
          </Card>
        </aside>
        <main className="min-w-0 flex-1">
          {!adminReady && (
            <Card className="p-6">
              <Typography variant="body2" color="textSecondary">正在校验管理员权限...</Typography>
            </Card>
          )}
          {adminReady && !adminAllowed && (
            <Alert type="warning" variant="filled" showIcon>
              当前账号不具备管理员权限，无法访问管理控制台。
            </Alert>
          )}
          {adminReady && adminAllowed && <Outlet />}
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
