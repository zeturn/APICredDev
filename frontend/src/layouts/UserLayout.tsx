import { Button, List, ListItem, Typography } from "../lib/watercolor";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { userConsoleRoutes } from "../navigation/consoleRoutes";
import { AdminIcon } from "../pages/admin/adminCommon";
import { useI18n } from "../i18n";
import LanguageSwitcher from "../i18n/LanguageSwitcher";
import ThemeToggle from "../ThemeToggle";
import api from "../api/client";

const UserLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useI18n();
  const navItems = userConsoleRoutes.map((item) => ({ to: item.path, label: item.i18nKey ? t(item.i18nKey) : item.label }));
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
        <aside className="sticky top-4 h-[calc(100vh-2rem)] w-64 shrink-0 self-start">
          <div className="flex h-full flex-col px-2 py-4">
            <div className="flex items-center justify-between gap-2">
              <Typography variant="subtitle2" color="textSecondary" className="uppercase tracking-[0.3em]">
                {t("over.apicred")}
              </Typography>
              <div className="flex items-center gap-2">
                <LanguageSwitcher />
                <ThemeToggle />
              </div>
            </div>
            <Typography variant="h6" className="mt-2 px-3">
              {t("layout.userTitle")}
            </Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              {t("layout.userDesc")}
            </Typography>

            <List className="mt-4 flex-1 space-y-1 overflow-y-auto">
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
                  {t("layout.enterAdmin")}
                </span>
              </Button>
              <Button buttonStyle="text" variant="error" fullWidth onClick={logout}>
                <span className="inline-flex items-center gap-2">
                  <AdminIcon icon="provider" className="h-4 w-4" />
                  {t("layout.logout")}
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
