import { Button, List, ListItem, Typography } from "../lib/watercolor";
import { Suspense } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import LoadingScreen from "../pages/LoadingScreen";
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

  const activeIndex = navItems.findIndex((item) => location.pathname === item.to);

  return (
    <div className="min-h-screen bg-white dark:bg-[#09090b] relative">
      <div className="absolute top-0 bottom-0 left-0 w-[calc(16rem+1rem)] md:w-[calc(16rem+1.5rem)] bg-[#f4f4f5] dark:bg-[#f4f4f5] z-0" />
      <div className="flex min-h-screen w-full gap-6 px-4 py-6 md:px-6 relative z-10">
        <aside className="sticky top-4 h-[calc(100vh-2rem)] w-64 shrink-0 self-start">
          <div className="flex h-full flex-col px-2 py-4">
            <div className="flex items-center justify-between gap-2">
              <Typography variant="subtitle2" color="textSecondary" className="uppercase tracking-[0.3em]">
                {t("over.apicred")}
              </Typography>
              <div className="flex items-center gap-2">
              </div>
            </div>
            <Typography variant="h6" className="mt-2 px-3">
              {t("layout.userTitle")}
            </Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              {t("layout.userDesc")}
            </Typography>

            <div className="h-[3px] w-full shrink-0 bg-[#103222] mt-[7px] mb-[28px]" />

            <List className="mt-4 space-y-1 relative">
              <div
                className={`absolute left-[-24px] md:left-[-32px] w-1.5 h-6 bg-[#103222] rounded-r-md transition-all duration-300 ease-in-out ${
                  activeIndex === -1 ? "opacity-0" : "opacity-100"
                }`}
                style={{ top: `${Math.max(0, activeIndex) * 40 + 6}px` }}
              />
              {navItems.map((item) => (
                <ListItem
                  key={item.to}
                  button
                  component={NavLink}
                  to={item.to}
                  selected={location.pathname === item.to}
                >
                  <span className="inline-flex items-center gap-3">
                    <AdminIcon icon={iconByPath[item.to] ?? "home"} className={`h-5 w-5 transition-colors ${location.pathname === item.to ? "text-[#09090b]" : ""}`} />
                    {item.label}
                  </span>
                </ListItem>
              ))}
            </List>

            <div className="mt-1 space-y-1">
              <ThemeToggle />
              <LanguageSwitcher />
            </div>

            <div className="flex-1" />

            <div className="mt-6 space-y-2">
              <Button buttonStyle="text" variant="secondary" fullWidth onClick={() => navigate("/admin/overview")} className="!justify-start !text-[#103222] hover:!bg-[#e9e9ebb5] hover:!text-[#350180] !px-3 !rounded-xl">
                <span className="inline-flex items-center gap-3">
                  <AdminIcon icon="shield" className="h-5 w-5" />
                  {t("layout.enterAdmin")}
                </span>
              </Button>
              <Button buttonStyle="text" variant="error" fullWidth onClick={logout} className="!justify-start !px-3 !rounded-xl">
                <span className="inline-flex items-center gap-3">
                  <AdminIcon icon="provider" className="h-5 w-5" />
                  {t("layout.logout")}
                </span>
              </Button>
            </div>
            </div>
        </aside>
        <main className="min-w-0 flex-1">
          <Suspense fallback={<LoadingScreen />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
};

export default UserLayout;
