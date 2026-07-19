import axios from "axios";
import { emitErrorToast } from "../ui/toastBus.ts";
import { translate } from "../i18n/translate.ts";
import { beginLoading, endLoading, resetLoading } from "../ui/loadingBus.ts";

const viteEnv = (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {};
export const apiBaseUrl = viteEnv.VITE_API_BASE_URL ?? "/v1";
const api = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
});

api.interceptors.request.use(
  (config) => {
    beginLoading();
    return config;
  },
  (error) => {
    endLoading();
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (resp) => {
    endLoading();
    return resp;
  },
  async (error) => {
    const config = error?.config;
    const status = Number(error?.response?.status ?? 0);

    if (config && !config._isRetry && [502, 503, 504].includes(status)) {
      config._isRetry = true;
      await new Promise((res) => setTimeout(res, 500));
      return api(config);
    }

    endLoading();
    const reqUrl = String(config?.url ?? "");
    if (status === 401 && reqUrl.includes("/auth/me")) {
      return Promise.reject(error);
    }
    if (status === 0) {
      resetLoading();
    }
    const msg = error?.response?.data?.error?.message ?? translate("api.requestFailed");
    emitErrorToast(msg);
    return Promise.reject(error);
  }
);

export default api;

