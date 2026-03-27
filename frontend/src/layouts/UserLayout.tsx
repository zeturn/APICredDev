import { Button, Card, List, ListItem, Typography } from "../lib/watercolor";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { userConsoleRoutes } from "../navigation/consoleRoutes";

const UserLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const navItems = userConsoleRoutes.map((item) => ({ to: item.path, label: item.label }));

  const logout = () => {
    localStorage.removeItem("access_token");
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto flex min-h-screen max-w-6xl gap-6 px-6 py-6">
        <aside className="w-64 shrink-0">
          <Card className="p-5">
            <Typography variant="subtitle2" color="textSecondary" className="uppercase tracking-[0.3em]">
              apicred
            </Typography>
            <Typography variant="h6" className="mt-2">
              用户工作台
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
                  {item.label}
                </ListItem>
              ))}
            </List>

            <div className="mt-6 space-y-2">
              <Button buttonStyle="text" variant="secondary" fullWidth onClick={() => navigate("/admin")}>
                进入管理后台
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

export default UserLayout;
