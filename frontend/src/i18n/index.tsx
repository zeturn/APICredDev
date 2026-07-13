import React, { createContext, useContext, useEffect, useState } from "react";

type Locale = "zh" | "en";

const STORAGE_KEY = "apicred.locale";

const zh: Record<string, string> = {
  "nav.overview": "总览",
  "nav.users": "用户管理",
  "nav.brands": "品牌",
  "nav.publicModels": "对外模型",
  "nav.upstreamModels": "上游模型",
  "nav.providers": "供应商",
  "nav.endpoints": "端点",
  "nav.credentials": "凭据",
  "nav.routes": "路由",
  "nav.apiModels": "API 模型支持",
  "nav.usage": "使用统计",
  "nav.providerHealth": "供应商健康",
  "nav.usageDashboard": "用量看板",
  "common.backToUser": "返回用户端",
  "common.logout": "退出登录",
  "common.language": "语言",
};

const en: Record<string, string> = {
  "nav.overview": "Overview",
  "nav.users": "Users",
  "nav.brands": "Brands",
  "nav.publicModels": "Public Models",
  "nav.upstreamModels": "Upstream Models",
  "nav.providers": "Providers",
  "nav.endpoints": "Endpoints",
  "nav.credentials": "Credentials",
  "nav.routes": "Routes",
  "nav.apiModels": "API Models",
  "nav.usage": "Usage",
  "nav.providerHealth": "Provider Health",
  "nav.usageDashboard": "Usage Dashboard",
  "common.backToUser": "Back to User Console",
  "common.logout": "Log out",
  "common.language": "Language",
};

const dictionaries: Record<Locale, Record<string, string>> = { zh, en };

function getStoredLocale(): Locale | null {
  if (typeof window === "undefined") return null;
  const saved = window.localStorage.getItem(STORAGE_KEY);
  return saved === "en" || saved === "zh" ? saved : null;
}

function detectLocale(): Locale {
  const saved = getStoredLocale();
  if (saved) return saved;
  if (typeof navigator !== "undefined" && navigator.language?.toLowerCase().startsWith("zh")) return "zh";
  return "en";
}

function translate(key: string, params?: Record<string, string | number>, locale: Locale = detectLocale()): string {
  let str = dictionaries[locale]?.[key] ?? dictionaries.zh[key] ?? key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      str = str.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
    }
  }
  return str;
}

interface I18nValue {
  locale: Locale;
  t: (key: string, params?: Record<string, string | number>) => string;
  toggleLocale: () => void;
  setLocale: (locale: Locale) => void;
}

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(detectLocale());

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
  }, [locale]);

  const toggleLocale = () => setLocaleState((l) => (l === "zh" ? "en" : "zh"));
  const setLocale = (next: Locale) => setLocaleState(next);
  const t = (key: string, params?: Record<string, string | number>) => translate(key, params, locale);

  return (
    <I18nContext.Provider value={{ locale, t, toggleLocale, setLocale }}>{children}</I18nContext.Provider>
  );
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

export { getStoredLocale, translate };
