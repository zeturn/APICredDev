import { Alert, Button, Card, List, ListItem, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { adminConsoleRoutes } from "../navigation/consoleRoutes";
import { ensureAdminToken } from "../api/adminClient";

const AdminLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [adminReady, setAdminReady] = useState(false);
  const [adminAllowed, setAdminAllowed] = useState(false);
  const navItems = adminConsoleRoutes.map((item) => ({ to: item.path, label: item.label }));

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

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("admin_token");
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="mx-auto flex min-h-screen max-w-6xl gap-6 px-6 py-6">
        <aside className="w-64 shrink-0">
          <Card className="p-5">
            <Typography variant="subtitle2" color="textSecondary" className="uppercase tracking-[0.3em]">
              apicred
            </Typography>
            <Typography variant="h6" className="mt-2">
              管理控制台
            </Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              Key Pool 与模型策略配置。
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
                  selected={location.pathname === item.to}
                >
                  {item.label}
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
        <main className="flex-1">
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
