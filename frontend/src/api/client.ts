import axios from "axios";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8103/v1";
const api = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
});

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = Number(error?.response?.status ?? 0);
    const reqUrl = String(error?.config?.url ?? "");
    if (status === 401 && reqUrl.includes("/auth/me")) {
      return Promise.reject(error);
    }
    const msg = error?.response?.data?.error?.message ?? "请求失败";
    alert(msg);
    return Promise.reject(error);
  }
);

export default api;

