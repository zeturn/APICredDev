import { Button, Card, List, ListItem, Typography } from "../lib/watercolor";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { userConsoleRoutes } from "../navigation/consoleRoutes";
import { AdminIcon } from "../pages/admin/adminCommon";
import api from "../api/client";

const UserLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const navItems = userConsoleRoutes.map((item) => ({ to: item.path, label: item.label }));
  const iconByPath: Record<string, "home" | "usage" | "key" | "models" | "wallet"> = {
    "/workspace/dashboard": "home",
    "/workspace/usage": "usage",
    "/workspace/tokens": "key",
    "/workspace/models": "models",
    "/workspace/topup": "wallet",
    "/workspace/profile": "home",
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
    }
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="flex min-h-screen w-full gap-6 px-4 py-6 md:px-6">
        <aside className="sticky top-4 h-fit w-64 shrink-0 self-start">
          <div className="px-2 py-4">
            <Typography variant="subtitle2" color="textSecondary" className="uppercase tracking-[0.3em]">
              apicred
            </Typography>
            <Typography variant="h6" className="mt-2 px-3">
              用户终端
            </Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              日常调用、Token 与余额管理。
            </Typography>

            <List className="mt-4 space-y-1">
              {navItems.map((item) => (
                <ListItem
                  key={item.to}
                  button
                  component={NavLink}
                  to={item.to}
                  selected={location.pathname === item.to}
                >
                  <span className="inline-flex items-center gap-3">
                    <AdminIcon icon={iconByPath[item.to] ?? "home"} className="h-5 w-5" />
                    {item.label}
                  </span>
                </ListItem>
              ))}
            </List>

            <div className="mt-6 space-y-2">
              <Button buttonStyle="text" variant="secondary" fullWidth onClick={() => navigate("/admin/overview")}>
                <span className="inline-flex items-center gap-2">
                  <AdminIcon icon="shield" className="h-4 w-4" />
                  进入管理后台
                </span>
              </Button>
              <Button buttonStyle="text" variant="error" fullWidth onClick={logout}>
                <span className="inline-flex items-center gap-2">
                  <AdminIcon icon="provider" className="h-4 w-4" />
                  退出登录
                </span>
              </Button>
            </div>
            </div>
        </aside>
        <main className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default UserLayout;
