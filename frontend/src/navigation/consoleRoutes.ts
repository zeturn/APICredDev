export type ConsoleRoute = {
  path: string;
  label: string;
  mode: "user" | "admin";
  description: string;
  apiPath: string;
  method?: "GET" | "POST" | "PUT";
};

export const userConsoleRoutes: ConsoleRoute[] = [
  { path: "/workspace/dashboard", label: "用户总览", mode: "user", description: "余额、模型与使用额度概览", apiPath: "/billing/summary" },
  { path: "/workspace/usage", label: "用量分析", mode: "user", description: "最近调用记录与按模型消费", apiPath: "/billing/usage" },
  { path: "/workspace/tokens", label: "API Tokens", mode: "user", description: "管理访问令牌与范围", apiPath: "/tokens" },
  { path: "/workspace/models", label: "模型目录", mode: "user", description: "可用模型与定价能力", apiPath: "/models" },
  { path: "/workspace/topup", label: "充值中心", mode: "user", description: "卡密兑换与账本变更", apiPath: "/billing/ledger" },
  { path: "/workspace/profile", label: "个人信息", mode: "user", description: "查看当前登录账号信息", apiPath: "/auth/me" },
];

export const adminConsoleRoutes: ConsoleRoute[] = [
  { path: "/admin/overview", label: "总览", mode: "admin", description: "全站用户、模型、额度总览", apiPath: "/admin/dashboard" },
  { path: "/admin/users", label: "用户管理", mode: "admin", description: "查看用户与启停账号", apiPath: "/admin/users" },
  { path: "/admin/brands", label: "品牌", mode: "admin", description: "模型品牌目录", apiPath: "/admin/brands" },
  { path: "/admin/public-models", label: "Public Models", mode: "admin", description: "用户可见模型产品目录", apiPath: "/admin/public-models" },
  { path: "/admin/upstream-models", label: "Upstream Models", mode: "admin", description: "真实上游模型目录", apiPath: "/admin/upstream-models" },
  { path: "/admin/providers", label: "Providers", mode: "admin", description: "上游供应商目录", apiPath: "/admin/providers" },
  { path: "/admin/provider-endpoints", label: "Endpoints", mode: "admin", description: "供应商上游入口", apiPath: "/admin/provider-endpoints" },
  { path: "/admin/provider-credentials", label: "Credentials", mode: "admin", description: "上游密钥与健康状态", apiPath: "/admin/provider-credentials" },
  { path: "/admin/model-routes", label: "Routes", mode: "admin", description: "模型路由策略", apiPath: "/admin/model-routes" },
  { path: "/admin/api-models", label: "API 模型支持", mode: "admin", description: "查看任意 API 支持模型", apiPath: "/admin/api-supported-models" },
  { path: "/admin/usage", label: "使用统计", mode: "admin", description: "全站调用记录与消费汇总", apiPath: "/admin/usage-summary" },
];

export const allConsoleRoutes: ConsoleRoute[] = [...userConsoleRoutes, ...adminConsoleRoutes];

export const findConsoleRoute = (path: string): ConsoleRoute | undefined =>
  allConsoleRoutes.find((route) => route.path === path);

