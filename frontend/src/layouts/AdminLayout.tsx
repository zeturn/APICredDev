import { Button, Card, List, ListItem, TextField, Typography } from "../lib/watercolor";
import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { adminConsoleRoutes } from "../navigation/consoleRoutes";

const AdminLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [adminToken, setAdminToken] = useState(localStorage.getItem("admin_token") ?? "");
  const navItems = adminConsoleRoutes.map((item) => ({ to: item.path, label: item.label }));

  const logout = () => {
    localStorage.removeItem("access_token");
    navigate("/login");
  };

  const saveAdminToken = () => {
    localStorage.setItem("admin_token", adminToken);
    window.location.reload();
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

            <div className="mt-4 space-y-2">
              <TextField
                label="Admin Token"
                placeholder="X-Admin-Token"
                value={adminToken}
                onChange={(e: any) => setAdminToken(e.target.value)}
                fullWidth
              />
              <Button variant="primary" buttonStyle="filled" fullWidth onClick={saveAdminToken}>
                保存管理密钥
              </Button>
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
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
