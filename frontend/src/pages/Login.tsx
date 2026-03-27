import { Alert, Button, Card, TextField, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import api from "../api/client";

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as any)?.from?.pathname || "/workspace/dashboard";
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8103/v1";
  const basaltOAuthProvider = import.meta.env.VITE_BASALT_OAUTH_PROVIDER ?? "google";

  useEffect(() => {
    const query = new URLSearchParams(location.search);
    const callbackToken = query.get("token");
    const nextPath = query.get("next") || "/workspace/dashboard";
    if (callbackToken) {
      localStorage.setItem("access_token", callbackToken);
      navigate(nextPath, { replace: true });
    }
  }, [location.search, navigate]);

  const handleLogin = async () => {
    const resp = await api.post("/auth/login", { email, password });
    localStorage.setItem("access_token", resp.data.access_token);
    navigate(from, { replace: true });
  };

  return (
    <Card className="p-6">
      <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.35em]">
        apicred access
      </Typography>
      <Typography variant="h5" className="mt-2">
        {mode === "login" ? "登录" : "注册"}
      </Typography>
      <Typography variant="body2" color="textSecondary" className="mt-1">
        {mode === "login" ? "使用已有账号登录系统。" : "创建新账号后再登录系统。"}
      </Typography>

      {successMessage && (
        <Alert type="success" variant="filled" showIcon className="mt-4">
          {successMessage}
        </Alert>
      )}
      {errorMessage && (
        <Alert type="error" variant="filled" showIcon className="mt-4">
          {errorMessage}
        </Alert>
      )}

      <div className="mt-6 grid gap-4">
        <TextField label="邮箱" placeholder="email" value={email} onChange={(e: any) => setEmail(e.target.value)} fullWidth />
        <TextField
          label="密码"
          placeholder="password"
          type="password"
          value={password}
          onChange={(e: any) => setPassword(e.target.value)}
          fullWidth
        />
        <Button
          variant="primary"
          buttonStyle="filled"
          fullWidth
          onClick={async () => {
            setErrorMessage("");
            setSuccessMessage("");
            try {
              if (mode === "login") {
                await handleLogin();
              } else {
                await api.post("/auth/register", { email, password });
                setSuccessMessage("注册成功，请使用账号登录。");
                setMode("login");
              }
            } catch (err: any) {
              const message = err?.response?.data?.error?.message || "操作失败，请检查输入。";
              setErrorMessage(message);
            }
          }}
        >
          {mode === "login" ? "登录" : "注册"}
        </Button>
        <Button
          variant="secondary"
          buttonStyle="text"
          fullWidth
          onClick={() => {
            setSuccessMessage("");
            setErrorMessage("");
            setMode(mode === "login" ? "register" : "login");
          }}
        >
          {mode === "login" ? "没有账号？去注册" : "已有账号？去登录"}
        </Button>
        {mode === "login" && (
          <Button
            variant="secondary"
            buttonStyle="outlined"
            fullWidth
            onClick={() => {
              const nextPath = encodeURIComponent(from);
              window.location.href = `${apiBaseUrl}/auth/basalt/oauth/${basaltOAuthProvider}/login?next=${nextPath}`;
            }}
          >
            使用 BasaltPass 登录
          </Button>
        )}
      </div>
    </Card>
  );
};

export default LoginPage;

