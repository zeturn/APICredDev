import axios from "axios";
import { emitErrorToast } from "../ui/toastBus";
import { beginLoading, endLoading, resetLoading } from "../ui/loadingBus";

const getApiBaseUrl = () => {
  const envUrl = (window as any).__env__?.API_BASE_URL;
  if (envUrl && envUrl !== "%%API_BASE_URL%%") {
    return envUrl;
  }
  return import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8103/v1";
};

const apiBaseUrl = getApiBaseUrl();
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
  (error) => {
    endLoading();
    const status = Number(error?.response?.status ?? 0);
    const reqUrl = String(error?.config?.url ?? "");
    if (status === 401 && reqUrl.includes("/auth/me")) {
      return Promise.reject(error);
    }
    if (status === 0) {
      resetLoading();
    }
    const msg = error?.response?.data?.error?.message ?? "请求失败";
    emitErrorToast(msg);
    return Promise.reject(error);
  }
);

export default api;

