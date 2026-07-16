import React, { createContext, useContext, useEffect, useState } from "react";
import { en, zh, type Dict } from "./translations";
import { detectLocale, persistLocale, setActiveLocale, translate as translateActive } from "./translate";

export type Locale = "zh" | "en";

const dictionaries: Record<Locale, Dict> = { zh, en };

function getStoredLocale(): Locale | null {
  if (typeof window === "undefined") return null;
  try {
    const saved = window.localStorage.getItem("apicred.locale");
    return saved === "en" || saved === "zh" ? saved : null;
  } catch {
    return null;
  }
}

function translateWith(
  key: string,
  locale: Locale,
  params?: Record<string, string | number>,
): string {
  const dict = dictionaries[locale] ?? zh;
  let str = dict[key] ?? zh[key] ?? key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, "g"), String(v));
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
    // Keep the standalone translate() (used in api clients) in sync.
    setActiveLocale(locale);
    persistLocale(locale);
    document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
  }, [locale]);

  const setLocale = (next: Locale) => setLocaleState(next);
  const toggleLocale = () => setLocaleState((l) => (l === "zh" ? "en" : "zh"));
  const t = (key: string, params?: Record<string, string | number>) => translateWith(key, locale, params);

  return (
    <I18nContext.Provider value={{ locale, t, toggleLocale, setLocale }}>{children}</I18nContext.Provider>
  );
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

export { getStoredLocale };
export const translate = translateActive;
