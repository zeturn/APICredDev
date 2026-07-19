export type ConsoleRoute = {
  path: string;
  label: string;
  i18nKey?: string;
  mode: "user" | "admin";
  description: string;
  apiPath: string;
  method?: "GET" | "POST" | "PUT";
};

export const userConsoleRoutes: ConsoleRoute[] = [
  { path: "/workspace/dashboard", label: "用户总览", i18nKey: "nav.userDashboard", mode: "user", description: "余额、模型与使用额度概览", apiPath: "/billing/summary" },
  { path: "/workspace/usage", label: "用量分析", i18nKey: "nav.userUsage", mode: "user", description: "最近调用记录与按模型消费", apiPath: "/billing/usage" },
  { path: "/workspace/tokens", label: "API Tokens", i18nKey: "nav.userTokens", mode: "user", description: "管理访问令牌与范围", apiPath: "/tokens" },
  { path: "/workspace/models", label: "模型目录", i18nKey: "nav.userModels", mode: "user", description: "可用模型与定价能力", apiPath: "/models" },
  { path: "/workspace/topup", label: "充值中心", i18nKey: "nav.userTopup", mode: "user", description: "卡密兑换与账本变更", apiPath: "/billing/ledger" },
  { path: "/workspace/profile", label: "个人信息", i18nKey: "nav.userProfile", mode: "user", description: "查看当前登录账号信息", apiPath: "/auth/me" },
];

export const adminConsoleRoutes: ConsoleRoute[] = [
  { path: "/admin/overview", label: "总览", i18nKey: "nav.adminOverview", mode: "admin", description: "全站用户、模型、额度总览", apiPath: "/admin/dashboard" },
  { path: "/admin/users", label: "用户管理", i18nKey: "nav.adminUsers", mode: "admin", description: "查看用户与启停账号", apiPath: "/admin/users" },
  { path: "/admin/brands", label: "品牌", i18nKey: "nav.adminBrands", mode: "admin", description: "模型品牌目录", apiPath: "/admin/brands" },
  { path: "/admin/public-models", label: "Public Models", i18nKey: "nav.adminPublicModels", mode: "admin", description: "用户可见模型产品目录", apiPath: "/admin/public-models" },
  { path: "/admin/upstream-models", label: "Upstream Models", i18nKey: "nav.adminUpstreamModels", mode: "admin", description: "真实上游模型目录", apiPath: "/admin/upstream-models" },
  { path: "/admin/providers", label: "Providers", i18nKey: "nav.adminProviders", mode: "admin", description: "上游供应商目录", apiPath: "/admin/providers" },
  { path: "/admin/provider-endpoints", label: "Endpoints", i18nKey: "nav.adminEndpoints", mode: "admin", description: "供应商上游入口", apiPath: "/admin/provider-endpoints" },
  { path: "/admin/provider-credentials", label: "Credentials", i18nKey: "nav.adminCredentials", mode: "admin", description: "上游密钥与健康状态", apiPath: "/admin/provider-credentials" },
  { path: "/admin/model-routes", label: "Routes", i18nKey: "nav.adminRoutes", mode: "admin", description: "模型路由策略", apiPath: "/admin/model-routes" },
  { path: "/admin/api-models", label: "API 模型支持", i18nKey: "nav.adminApiModels", mode: "admin", description: "查看任意 API 支持模型", apiPath: "/admin/api-supported-models" },
  { path: "/admin/usage", label: "使用统计", i18nKey: "nav.adminUsage", mode: "admin", description: "全站调用记录与消费汇总", apiPath: "/admin/usage-summary" },
  { path: "/admin/provider-health", label: "Provider Health", i18nKey: "nav.adminProviderHealth", mode: "admin", description: "Provider/credential 健康运营控制台", apiPath: "/admin/provider-health" },
  { path: "/admin/usage-dashboard", label: "Usage Dashboard", i18nKey: "nav.adminUsageDashboard", mode: "admin", description: "多维 usage/cost/quota 分析", apiPath: "/admin/usage/summary" },
];

export const allConsoleRoutes: ConsoleRoute[] = [...userConsoleRoutes, ...adminConsoleRoutes];

export const findConsoleRoute = (path: string): ConsoleRoute | undefined =>
  allConsoleRoutes.find((route) => route.path === path);

export const preloadRouteModule = (path: string) => {
  switch (path) {
    case "/workspace/dashboard": import("../pages/Dashboard"); break;
    case "/workspace/usage": import("../pages/Usage"); break;
    case "/workspace/tokens": import("../pages/Tokens"); break;
    case "/workspace/models": import("../pages/Models"); break;
    case "/workspace/topup": import("../pages/Topup"); break;
    case "/workspace/profile": import("../pages/Profile"); break;

    case "/admin/overview": import("../pages/admin/AdminOverview"); break;
    case "/admin/users": import("../pages/admin/AdminUsers"); break;
    case "/admin/brands":
    case "/admin/public-models":
    case "/admin/upstream-models":
    case "/admin/providers":
    case "/admin/provider-endpoints":
    case "/admin/provider-credentials":
    case "/admin/model-routes":
      import("../pages/admin/AdminCatalogPages"); break;
    case "/admin/api-models": import("../pages/admin/AdminApiModels"); break;
    case "/admin/usage": import("../pages/admin/AdminUsage"); break;
    case "/admin/provider-health": import("../pages/admin/AdminProviderHealth"); break;
    case "/admin/usage-dashboard": import("../pages/admin/AdminUsageDashboard"); break;
  }
};

