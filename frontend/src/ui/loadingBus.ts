const LOADING_EVENT = "apicred:loading";

type LoadingDetail = {
  pending: number;
};

let pendingCount = 0;

const dispatch = () => {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent<LoadingDetail>(LOADING_EVENT, { detail: { pending: pendingCount } }));
};

export const beginLoading = (): void => {
  pendingCount += 1;
  dispatch();
};

export const endLoading = (): void => {
  pendingCount = Math.max(0, pendingCount - 1);
  dispatch();
};

export const resetLoading = (): void => {
  pendingCount = 0;
  dispatch();
};

export const loadingEventName = LOADING_EVENT;
