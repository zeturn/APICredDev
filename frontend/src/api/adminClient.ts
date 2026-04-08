import axios from "axios";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8103/v1";

const adminApi = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
});

let pendingAdminToken: Promise<string | null> | null = null;
let adminAccessToken: string | null = null;
let adminAccessTokenExpSeconds = 0;

const decodeJwtExp = (token: string): number => {
  try {
    const payloadPart = token.split(".")[1] ?? "";
    if (!payloadPart) return 0;
    const base64 = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
    const padding = "=".repeat((4 - (base64.length % 4)) % 4);
    const json = atob(base64 + padding);
    const payload = JSON.parse(json);
    const exp = Number(payload?.exp ?? 0);
    return Number.isFinite(exp) ? exp : 0;
  } catch {
    return 0;
  }
};

const hasUsableAdminToken = (): boolean => {
  if (!adminAccessToken) {
    return false;
  }
  if (!adminAccessTokenExpSeconds) {
    return true;
  }
  const now = Math.floor(Date.now() / 1000);
  return now < adminAccessTokenExpSeconds - 30;
};

export const clearAdminAccessToken = (): void => {
  adminAccessToken = null;
  adminAccessTokenExpSeconds = 0;
};

export const ensureAdminToken = async (): Promise<string | null> => {
  if (hasUsableAdminToken()) {
    return adminAccessToken;
  }

  if (!pendingAdminToken) {
    pendingAdminToken = axios
      .get(`${apiBaseUrl}/auth/admin-token`, {
        withCredentials: true,
      })
      .then((resp) => {
        const token = resp.data?.admin_access_token;
        if (typeof token === "string" && token) {
          adminAccessToken = token;
          adminAccessTokenExpSeconds = decodeJwtExp(token);
          return token;
        }
        clearAdminAccessToken();
        return null;
      })
      .catch(() => {
        clearAdminAccessToken();
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
    config.headers["X-Admin-Authorization"] = `Bearer ${adminToken}`;
  }
  return config;
});

adminApi.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = Number(error?.response?.status ?? 0);
    if (status === 401) {
      clearAdminAccessToken();
    }
    const msg = error?.response?.data?.error?.message ?? "请求失败";
    alert(msg);
    return Promise.reject(error);
  }
);

export default adminApi;
