export type ConsoleRoute = {
  path: string;
  label: string;
  mode: "user" | "admin";
  description: string;
  apiPath: string;
  method?: "GET" | "POST" | "PUT";
};

export const userConsoleRoutes: ConsoleRoute[] = [
  { path: "/workspace/dashboard", label: "用户总览", mode: "user", description: "账户与系统运行快照", apiPath: "/billing/wallet" },
  { path: "/workspace/tokens", label: "API Tokens", mode: "user", description: "管理访问令牌与范围", apiPath: "/tokens" },
  { path: "/workspace/models", label: "模型目录", mode: "user", description: "可用模型与定价能力", apiPath: "/models" },
  { path: "/workspace/topup", label: "充值中心", mode: "user", description: "卡密兑换与账本变更", apiPath: "/billing/ledger" },
  { path: "/workspace/wallet", label: "钱包余额", mode: "user", description: "Basalt 钱包实时余额", apiPath: "/basalt/wallet/balance" },
  { path: "/workspace/wallet-history", label: "钱包流水", mode: "user", description: "钱包历史记录", apiPath: "/basalt/wallet/history" },
  { path: "/workspace/usage", label: "调用记录", mode: "user", description: "业务调用与用量汇总", apiPath: "/basalt/usage/records", method: "POST" },
  { path: "/workspace/apps", label: "应用接入", mode: "user", description: "用户可访问应用列表", apiPath: "/basalt/apps" },
  { path: "/workspace/permissions", label: "权限视图", mode: "user", description: "用户权限与授权项", apiPath: "/basalt/permissions" },
  { path: "/workspace/roles", label: "角色视图", mode: "user", description: "用户角色与角色映射", apiPath: "/basalt/roles" },
  { path: "/workspace/subscriptions", label: "订阅管理", mode: "user", description: "套餐与订阅状态", apiPath: "/basalt/subscriptions" },
  { path: "/workspace/orders", label: "订单中心", mode: "user", description: "订单查询与状态跟踪", apiPath: "/basalt/orders" },
  { path: "/workspace/notifications", label: "消息中心", mode: "user", description: "系统消息与待处理事件", apiPath: "/basalt/notifications" },
  { path: "/workspace/security", label: "安全中心", mode: "user", description: "2FA、登录与安全校验", apiPath: "/basalt/security/2fa/setup", method: "POST" },
  { path: "/workspace/profile", label: "账号资料", mode: "user", description: "个人资料与租户信息", apiPath: "/basalt/user/profile" },
  { path: "/workspace/integrations", label: "Basalt 集成", mode: "user", description: "认证/权限/钱包联调入口", apiPath: "/basalt/health" },
];

export const adminConsoleRoutes: ConsoleRoute[] = [
  { path: "/admin", label: "管理总览", mode: "admin", description: "全局运营与关键指标", apiPath: "/admin/basalt/dashboard/stats" },
  { path: "/admin/apps", label: "应用管理", mode: "admin", description: "应用配置与生命周期", apiPath: "/admin/basalt/apps" },
  { path: "/admin/users", label: "用户管理", mode: "admin", description: "用户状态、禁用、详情", apiPath: "/admin/basalt/users" },
  { path: "/admin/roles", label: "角色管理", mode: "admin", description: "角色定义与授权关系", apiPath: "/admin/basalt/roles" },
  { path: "/admin/permissions", label: "权限管理", mode: "admin", description: "权限集合与分类维护", apiPath: "/admin/basalt/permissions" },
  { path: "/admin/wallets", label: "钱包管理", mode: "admin", description: "钱包冻结、解冻与调账", apiPath: "/admin/basalt/wallets" },
  { path: "/admin/wallet-transactions", label: "钱包交易", mode: "admin", description: "钱包交易审计与追踪", apiPath: "/admin/basalt/wallets/stats" },
  { path: "/admin/tenants", label: "租户管理", mode: "admin", description: "多租户配置与管理", apiPath: "/admin/basalt/tenants" },
  { path: "/admin/teams", label: "团队管理", mode: "admin", description: "团队结构与成员管理", apiPath: "/admin/basalt/apps" },
  { path: "/admin/subscriptions", label: "订阅管理", mode: "admin", description: "订阅生命周期与取消", apiPath: "/admin/basalt/subscriptions" },
  { path: "/admin/plans", label: "套餐管理", mode: "admin", description: "套餐和版本控制", apiPath: "/admin/models" },
  { path: "/admin/products", label: "产品管理", mode: "admin", description: "产品配置与上架策略", apiPath: "/admin/provider-keys" },
  { path: "/admin/prices", label: "价格管理", mode: "admin", description: "价格策略与倍率规则", apiPath: "/admin/model-provider-keys" },
  { path: "/admin/notifications", label: "通知管理", mode: "admin", description: "通知发布与回执", apiPath: "/admin/basalt/notifications" },
  { path: "/admin/logs", label: "审计日志", mode: "admin", description: "关键操作日志审计", apiPath: "/admin/basalt/logs" },
  { path: "/admin/settings", label: "系统设置", mode: "admin", description: "基础配置与联动参数", apiPath: "/admin/usage-sessions" },
];

export const allConsoleRoutes: ConsoleRoute[] = [...userConsoleRoutes, ...adminConsoleRoutes];

export const findConsoleRoute = (path: string): ConsoleRoute | undefined =>
  allConsoleRoutes.find((route) => route.path === path);

