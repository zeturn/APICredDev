import axios from "axios";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8103/v1";

const adminApi = axios.create({
  baseURL: apiBaseUrl,
});

let pendingAdminToken: Promise<string | null> | null = null;

export const ensureAdminToken = async (): Promise<string | null> => {
  const existing = localStorage.getItem("admin_token");
  if (existing) {
    return existing;
  }

  const accessToken = localStorage.getItem("access_token");
  if (!accessToken) {
    return null;
  }

  if (!pendingAdminToken) {
    pendingAdminToken = axios
      .get(`${apiBaseUrl}/auth/admin-token`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })
      .then((resp) => {
        const token = resp.data?.admin_token;
        if (typeof token === "string" && token) {
          localStorage.setItem("admin_token", token);
          return token;
        }
        return null;
      })
      .catch(() => {
        localStorage.removeItem("admin_token");
        return null;
      })
      .finally(() => {
        pendingAdminToken = null;
      });
  }

  return pendingAdminToken;
};

adminApi.interceptors.request.use(async (config) => {
  const adminToken = await ensureAdminToken();
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
