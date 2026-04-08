import { useEffect, useState } from "react";
import { loadingEventName } from "./loadingBus";

const MIN_VISIBLE_MS = 350;

const GlobalLoading = () => {
  const [pending, setPending] = useState(0);
  const [visible, setVisible] = useState(false);

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
      <div className="absolute right-4 top-3 flex items-center gap-2 border border-slate-300 bg-white/95 px-3 py-1.5 text-xs text-slate-700">
        <span className="ui-loading-spinner" aria-hidden="true" />
        加载中...
      </div>
    </div>
  );
};

export default GlobalLoading;
