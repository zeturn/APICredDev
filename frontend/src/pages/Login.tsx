import { Button, Card, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as any)?.from?.pathname || "/workspace/dashboard";
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8103/v1";

  useEffect(() => {
    const query = new URLSearchParams(location.search);
    const nextPath = query.get("next") || "/workspace/dashboard";
    const source = query.get("source");
    if (source === "basaltpass") {
      navigate(nextPath, { replace: true });
    }
  }, [location.search, navigate]);

  return (
    <Card className="p-6">
      <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.35em]">
        apicred access
      </Typography>
      <Typography variant="h5" className="mt-2">
        BasaltPass SSO 登录
      </Typography>
      <Typography variant="body2" color="textSecondary" className="mt-1">
        APICred 已禁用本地账号注册和密码登录，请使用 BasaltPass 单点登录。
      </Typography>

      <div className="mt-6 grid gap-4">
        <Button
          variant="secondary"
          buttonStyle="outlined"
          fullWidth
          onClick={() => {
            const nextPath = encodeURIComponent(from);
            window.location.href = `${apiBaseUrl}/auth/basalt/login?next=${nextPath}`;
          }}
        >
          使用 BasaltPass 登录
        </Button>
      </div>
    </Card>
  );
};

export default LoginPage;

