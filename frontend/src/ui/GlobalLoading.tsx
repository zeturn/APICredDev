import { useEffect, useState } from "react";
import { loadingEventName } from "./loadingBus";
import { useI18n } from "../i18n";

const MIN_VISIBLE_MS = 350;

const GlobalLoading = () => {
  const [pending, setPending] = useState(0);
  const [visible, setVisible] = useState(false);
  const { t } = useI18n();

  useEffect(() => {
    const onLoading = (evt: Event) => {
      const customEvt = evt as CustomEvent<{ pending: number }>;
      setPending(customEvt.detail?.pending ?? 0);
    };

    window.addEventListener(loadingEventName, onLoading as EventListener);
    return () => {
      window.removeEventListener(loadingEventName, onLoading as EventListener);
    };
  }, []);

  useEffect(() => {
    let hideTimer: number | undefined;

    if (pending > 0) {
      setVisible(true);
      return () => {
        if (hideTimer) {
          window.clearTimeout(hideTimer);
        }
      };
    }

    hideTimer = window.setTimeout(() => {
      setVisible(false);
    }, MIN_VISIBLE_MS);

    return () => {
      if (hideTimer) {
        window.clearTimeout(hideTimer);
      }
    };
  }, [pending]);

  if (!visible) {
    return null;
  }

  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-[1100]">
      <div className="ui-loading-bar" />
      <div className="absolute right-4 top-3 flex items-center gap-2.5 border border-slate-300 dark:border-slate-700 bg-white/95 dark:bg-[#1e293b]/95 px-4 py-1.5 text-xs font-medium text-slate-700 dark:text-[#F0F4F8] !rounded-full shadow-sm">
        <span className="ui-loading-spinner" aria-hidden="true" />
        {t("loading.global")}
      </div>
    </div>
  );
};

export default GlobalLoading;
