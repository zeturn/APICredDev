import { useEffect, useState } from "react";
import { toastEventName, type ToastPayload } from "./toastBus";

type ToastItem = ToastPayload & { expiresAt: number };

const TTL_MS = 3500;

const ToastViewport = () => {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => {
    const onToast = (evt: Event) => {
      const customEvt = evt as CustomEvent<ToastPayload>;
      const payload = customEvt.detail;
      setItems((prev) => [...prev, { ...payload, expiresAt: Date.now() + TTL_MS }]);
    };

    window.addEventListener(toastEventName, onToast as EventListener);
    const timer = window.setInterval(() => {
      const now = Date.now();
      setItems((prev) => prev.filter((item) => item.expiresAt > now));
    }, 250);

    return () => {
      window.removeEventListener(toastEventName, onToast as EventListener);
      window.clearInterval(timer);
    };
  }, []);

  if (!items.length) {
    return null;
  }

  return (
    <div className="fixed right-4 top-4 z-[1000] flex w-[min(92vw,360px)] flex-col gap-2">
      {items.map((item) => (
        <div
          key={item.id}
          className={`border bg-white px-4 py-3 text-sm text-slate-800 shadow-sm ${
            item.kind === "error" ? "border-rose-300" : item.kind === "success" ? "border-emerald-300" : "border-slate-300"
          }`}
        >
          {item.message}
        </div>
      ))}
    </div>
  );
};

export default ToastViewport;
