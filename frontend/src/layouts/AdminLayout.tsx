import { Alert, Button, Card, List, ListItem, Typography } from "../lib/watercolor";
import { Suspense, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import LoadingScreen from "../pages/LoadingScreen";
import { adminConsoleRoutes, preloadRouteModule } from "../navigation/consoleRoutes";
import { clearAdminAccessToken, ensureAdminToken } from "../api/adminClient";
import { AdminIcon } from "../pages/admin/adminCommon";
import { useI18n } from "../i18n";
import ThemeToggle from "../ThemeToggle";
import LanguageSwitcher from "../i18n/LanguageSwitcher";
import api from "../api/client";

const AdminLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useI18n();
  const [adminReady, setAdminReady] = useState(false);
  const [adminAllowed, setAdminAllowed] = useState(false);
  const navItems = adminConsoleRoutes.map((item) => ({ to: item.path, label: item.i18nKey ? t(item.i18nKey) : item.label }));
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

  const activeIndex = navItems.findIndex((item) => isSelected(item.to));

  return (
    <div className="min-h-screen bg-white dark:bg-[#082D4F] relative">
      <div className="hidden md:block absolute top-0 bottom-0 left-0 w-[calc(16rem+1.5rem)] bg-[#f4f4f5] dark:bg-[#225288] z-0" />
      <div className="flex flex-col md:flex-row min-h-screen w-full gap-6 px-4 py-6 md:px-6 relative z-10">
        <aside className="sticky top-4 h-[calc(100vh-2rem)] w-full md:w-64 shrink-0 self-start flex flex-col justify-between">
          <div className="flex h-full flex-col px-2 py-4">
            <div className="shrink-0">
              <div className="flex items-center justify-between">
                <Typography variant="subtitle2" color="textSecondary" className="uppercase tracking-[0.3em]">
                  {t("over.apicred")}
                </Typography>
                <div className="flex items-center gap-2">
                </div>
              </div>
              <Typography variant="h6" className="mt-2 px-3 text-[#103222] dark:text-[#F0F4F8]">
                Admin Terminal
              </Typography>
              <Typography variant="body2" color="textSecondary" className="mt-1">
                {t("layout.adminDesc")}
              </Typography>

              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 dark:bg-slate-800 p-3">
                <Typography variant="caption" color="textSecondary">
                  {adminReady ? (adminAllowed ? t("layout.adminTokenOk") : t("layout.adminNoPerm")) : t("layout.adminChecking")}
                </Typography>
              </div>

              <div className="h-[3px] w-full shrink-0 bg-[#103222] dark:bg-[#F0F4F8] mt-[7px] mb-[14px]" />
            </div>

            <div className="-ml-6 md:-ml-8 pl-6 md:pl-8 pr-2 flex-1 overflow-y-auto custom-scrollbar my-1">
              <List className="space-y-1 relative">
                <div
                  className={`absolute left-[-24px] md:left-[-32px] w-1.5 h-6 bg-[#103222] dark:bg-[#F0F4F8] rounded-r-md transition-all duration-300 ease-in-out ${
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
                    selected={isSelected(item.to)}
                    onMouseEnter={() => preloadRouteModule(item.to)}
                  >
                    <span className="inline-flex items-center gap-3">
                      <AdminIcon icon={iconByPath[item.to] ?? "shield"} className={`h-5 w-5 transition-colors ${isSelected(item.to) ? "text-[#09090b]" : ""}`} />
                      {item.label}
                    </span>
                  </ListItem>
                ))}
              </List>

              <div className="mt-3 space-y-1">
                <ThemeToggle />
                <LanguageSwitcher />
              </div>
            </div>

            <div className="mt-auto shrink-0 pt-2 space-y-2">
              <Button buttonStyle="text" variant="secondary" fullWidth onClick={() => navigate("/workspace/dashboard")} className="!justify-start !text-[#103222] dark:!text-[#F0F4F8] hover:!bg-[#e9e9ebb5] hover:!text-[#350180] !px-3 !rounded-xl">
                <span className="inline-flex items-center gap-3">
                  <AdminIcon icon="home" className="h-5 w-5" />
                  {t("layout.backToUser")}
                </span>
              </Button>
              <Button buttonStyle="text" variant="error" fullWidth onClick={logout} className="!justify-start dark:!text-[rgb(231,27,27)] !px-3 !rounded-xl">
                <span className="inline-flex items-center gap-3">
                  <AdminIcon icon="provider" className="h-5 w-5" />
                  {t("layout.logout")}
                </span>
              </Button>
            </div>
          </div>
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
          {adminReady && adminAllowed && (
            <Suspense fallback={<LoadingScreen />}>
              <Outlet />
            </Suspense>
          )}
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
