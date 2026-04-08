export type ToastKind = "error" | "success" | "info";

export type ToastPayload = {
  id: string;
  kind: ToastKind;
  message: string;
};

const TOAST_EVENT = "apicred:toast";

export const emitToast = (kind: ToastKind, message: string): void => {
  const detail: ToastPayload = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    kind,
    message,
  };
  window.dispatchEvent(new CustomEvent<ToastPayload>(TOAST_EVENT, { detail }));
};

export const emitErrorToast = (message: string): void => emitToast("error", message);

export const toastEventName = TOAST_EVENT;
