import { en, zh, type Dict } from "./translations.ts";

export type Locale = "zh" | "en";
export type Params = Record<string, string | number>;

const dictionaries: Record<Locale, Dict> = { zh, en };
const STORAGE_KEY = "apicred.locale";

export function detectLocale(): Locale {
  try {
    const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
    if (stored === "zh" || stored === "en") return stored;
    if (typeof navigator !== "undefined" && navigator.language?.toLowerCase().startsWith("zh")) return "zh";
  } catch {
    // ignore (SSR / no storage)
  }
  return "zh";
}

let activeLocale: Locale = detectLocale();

export function getActiveLocale(): Locale {
  return activeLocale;
}

export function setActiveLocale(next: Locale): void {
  activeLocale = next;
}

export function persistLocale(next: Locale): void {
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // ignore
  }
}

export function translate(key: string, params?: Params): string {
  const dict = dictionaries[activeLocale] ?? zh;
  let text = dict[key] ?? zh[key] ?? key;
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      text = text.replace(new RegExp(`\\{\\{${name}\\}\\}`, "g"), String(value));
    }
  }
  return text;
}
