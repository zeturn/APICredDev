import { Button, List, ListItem, Typography } from "../lib/watercolor";
import { Suspense, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import LoadingScreen from "../pages/LoadingScreen";
import { userConsoleRoutes, preloadRouteModule } from "../navigation/consoleRoutes";
import { AdminIcon } from "../pages/admin/adminCommon";
import { useI18n } from "../i18n";
import LanguageSwitcher from "../i18n/LanguageSwitcher";
import ThemeToggle from "../ThemeToggle";
import api from "../api/client";

const UserLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useI18n();
  const [mobileOpen, setMobileOpen] = useState(false);

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

  const sidebarContent = (
    <div className="flex h-full flex-col px-2 py-4">
      <div className="shrink-0">
        <div className="flex items-center justify-between">
          <Typography variant="subtitle2" color="textSecondary" className="uppercase tracking-[0.3em]">
            {t("over.apicred")}
          </Typography>
        </div>
        <Typography variant="h6" className="mt-2 px-3 text-[#103222] dark:text-[#F0F4F8]">
          {t("layout.userTitle")}
        </Typography>
        <Typography variant="body2" color="textSecondary" className="mt-1">
          {t("layout.userDesc")}
        </Typography>

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
              {...({ to: item.to } as any)}
              selected={location.pathname === item.to}
              onClick={() => setMobileOpen(false)}
              onMouseEnter={() => preloadRouteModule(item.to)}
            >
              <span className="inline-flex items-center gap-3">
                <AdminIcon icon={iconByPath[item.to] ?? "home"} className={`h-5 w-5 transition-colors ${location.pathname === item.to ? "text-[#09090b]" : ""}`} />
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
        <Button
          buttonStyle="text"
          variant="secondary"
          fullWidth
          onClick={() => {
            setMobileOpen(false);
            navigate("/admin/overview");
          }}
          className="!justify-start !text-[#103222] dark:!text-[#F0F4F8] hover:!bg-[#e9e9ebb5] hover:!text-[#350180] !px-3 !rounded-xl"
        >
          <span className="inline-flex items-center gap-3">
            <AdminIcon icon="shield" className="h-5 w-5" />
            {t("layout.enterAdmin")}
          </span>
        </Button>
        <Button
          buttonStyle="text"
          variant="error"
          fullWidth
          onClick={() => {
            setMobileOpen(false);
            logout();
          }}
          className="!justify-start dark:!text-[rgb(231,27,27)] !px-3 !rounded-xl"
        >
          <span className="inline-flex items-center gap-3">
            <AdminIcon icon="provider" className="h-5 w-5" />
            {t("layout.logout")}
          </span>
        </Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-white dark:bg-[#082D4F] relative">
      <div className="hidden md:block absolute top-0 bottom-0 left-0 w-[calc(16rem+1.5rem)] bg-[#f4f4f5] dark:bg-[#225288] z-0" />

      {/* Mobile Top Header (< md) */}
      <div className="flex md:hidden items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-[#f4f4f5]/90 dark:bg-[#225288]/90 backdrop-blur-md sticky top-0 z-30">
        <Typography variant="h6" className="text-[#103222] dark:text-[#F0F4F8]">
          {t("layout.userTitle")}
        </Typography>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-700/50 focus:outline-none"
          aria-label="Toggle navigation"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {mobileOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile Backdrop & Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden flex">
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity" onClick={() => setMobileOpen(false)} />
          <div className="relative flex-1 w-full max-w-xs bg-[#f4f4f5] dark:bg-[#1e3a5f] p-4 shadow-xl z-50 flex flex-col h-full">
            {sidebarContent}
          </div>
        </div>
      )}

      <div className="flex flex-col md:flex-row min-h-screen w-full gap-6 px-4 py-4 md:px-6 md:py-6 relative z-10">
        {/* Desktop Sidebar (md+) */}
        <aside className="hidden md:flex sticky top-4 h-[calc(100vh-2rem)] w-64 shrink-0 self-start flex-col justify-between">
          {sidebarContent}
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
