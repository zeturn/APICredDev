import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getActiveLocale, persistLocale, setActiveLocale, translate, type Locale, type Params } from "./translate";

export { translate, type Locale };

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Params) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(getActiveLocale());

  const setLocale = (next: Locale) => {
    setActiveLocale(next);
    setLocaleState(next);
    persistLocale(next);
    if (typeof document !== "undefined") {
      document.documentElement.lang = next === "zh" ? "zh-CN" : "en";
    }
  };

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
    }
  }, [locale]);

  const t = (key: string, params?: Params) => translate(key, params);

  return <I18nContext.Provider value={{ locale, setLocale, t }}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    return { locale: getActiveLocale(), setLocale: () => {}, t: translate };
  }
  return ctx;
}
