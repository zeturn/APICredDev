import { useState, useRef, useEffect } from "react";
import { useI18n, type Locale } from "./index";
import { Button } from "../lib/watercolor";

export default function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (lang: Locale) => {
    setLocale(lang);
    setIsOpen(false);
  };

  const label = locale === "zh" ? "简体中文" : "English";

  return (
    <div className="relative w-full" ref={containerRef}>
      <Button
        buttonStyle="text"
        variant="secondary"
        fullWidth
        onClick={() => setIsOpen(!isOpen)}
        className="!justify-between !text-[#103222] hover:!bg-[#e9e9ebb5] hover:!text-[#350180] !px-3 !rounded-xl"
      >
        <span className="inline-flex items-center gap-3">
          <svg className="h-[20px] w-[20px] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m5 8 6 6" />
            <path d="m4 14 6-6 2-3" />
            <path d="M2 5h12" />
            <path d="M7 2h1" />
            <path d="m22 22-5-10-5 10" />
            <path d="M14 18h6" />
          </svg>
          {label}
        </span>
        <svg className={`h-4 w-4 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </Button>

      {isOpen && (
        <div className="absolute left-0 right-0 top-full mt-1 rounded-xl border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-800 dark:bg-[#09090b] z-50">
          <button
            onClick={() => handleSelect("zh")}
            className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm font-medium text-[#103222] hover:bg-[#e9e9ebb5] hover:text-[#350180] dark:text-slate-200"
          >
            <span className="inline-flex items-center gap-2">
              <svg className={`h-4 w-4 ${locale === "zh" ? "opacity-100" : "opacity-0"}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
              简体中文
            </span>
          </button>
          <button
            onClick={() => handleSelect("en")}
            className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm font-medium text-[#103222] hover:bg-[#e9e9ebb5] hover:text-[#350180] dark:text-slate-200"
          >
            <span className="inline-flex items-center gap-2">
              <svg className={`h-4 w-4 ${locale === "en" ? "opacity-100" : "opacity-0"}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
              English
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
