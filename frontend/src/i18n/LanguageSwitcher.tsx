import { useI18n, type Locale } from "./index";

export default function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();

  return (
    <div className="group relative w-fit">
      <div className="flex items-center justify-between gap-2 px-2.5 py-1 text-xs font-medium text-[#103222] dark:text-[#F0F4F8] rounded-lg pointer-events-none">
        <span className="inline-flex items-center gap-2 shrink-0">
          <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m5 8 6 6" />
            <path d="m4 14 6-6 2-3" />
            <path d="M2 5h12" />
            <path d="M7 2h1" />
            <path d="m22 22-5-10-5 10" />
            <path d="M14 18h6" />
          </svg>
          <span>{locale === "zh" ? "简体中文" : "English"}</span>
        </span>
        <svg className="h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </div>

      <select
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer appearance-none bg-transparent"
        aria-label="Language"
      >
        <option value="zh" className="text-slate-900 bg-white dark:bg-[#09090b] dark:text-slate-200">简体中文</option>
        <option value="en" className="text-slate-900 bg-white dark:bg-[#09090b] dark:text-slate-200">English</option>
      </select>
    </div>
  );
}
