import { useI18n, type Locale } from "./index";

export default function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();
  return (
    <select
      value={locale}
      onChange={(e) => setLocale(e.target.value as Locale)}
      className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-700 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-300"
      aria-label="Language"
    >
      <option value="zh">中文</option>
      <option value="en">English</option>
    </select>
  );
}
