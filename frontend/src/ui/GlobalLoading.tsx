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
      <div className="absolute right-6 top-4 flex items-center gap-2.5 border border-[#103222]/20 dark:border-[#F0F4F8]/25 bg-white/85 dark:bg-[#225288]/85 backdrop-blur-md px-3.5 py-1.5 text-xs font-medium text-[#103222] dark:text-[#F0F4F8] !rounded-full shadow-md transition-all duration-200">
        <span className="ui-loading-spinner text-[#103222] dark:text-[#F0F4F8]" aria-hidden="true" />
        <span className="tracking-wide">{t("loading.global")}</span>
      </div>
    </div>
  );
};

export default GlobalLoading;
