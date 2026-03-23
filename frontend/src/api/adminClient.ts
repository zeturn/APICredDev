import axios from "axios";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8103/v1";

const adminApi = axios.create({
  baseURL: apiBaseUrl,
});

adminApi.interceptors.request.use((config) => {
  const adminToken = localStorage.getItem("admin_token");
  if (adminToken) {
    config.headers = config.headers ?? {};
    config.headers["X-Admin-Token"] = adminToken;
  }
  return config;
});

adminApi.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const msg = error?.response?.data?.error?.message ?? "请求失败";
    alert(msg);
    return Promise.reject(error);
  }
);

export default adminApi;
