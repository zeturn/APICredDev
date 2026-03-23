import { Alert, Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@zeturn/watercolor-react";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import api from "../api/client";
import adminApi from "../api/adminClient";
import { adminConsoleRoutes, allConsoleRoutes, findConsoleRoute, userConsoleRoutes } from "../navigation/consoleRoutes";

const ConsolePage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const current = useMemo(() => findConsoleRoute(location.pathname), [location.pathname]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [payload, setPayload] = useState<any>(null);

  const routeList = current?.mode === "admin" ? adminConsoleRoutes : userConsoleRoutes;
  const routeIndex = current ? routeList.findIndex((item) => item.path === current.path) : -1;
  const prevRoute = routeIndex > 0 ? routeList[routeIndex - 1] : undefined;
  const nextRoute = routeIndex >= 0 && routeIndex < routeList.length - 1 ? routeList[routeIndex + 1] : undefined;

  useEffect(() => {
    const load = async () => {
      if (!current) return;
      setLoading(true);
      setError("");
      setPayload(null);
      try {
        const client = current.mode === "admin" ? adminApi : api;
        const method = current.method ?? "GET";
        const resp =
          method === "POST"
            ? await client.post(current.apiPath, {})
            : method === "PUT"
            ? await client.put(current.apiPath, {})
            : await client.get(current.apiPath);
        setPayload(resp.data);
      } catch (err: any) {
        const message = err?.response?.data?.error?.message ?? "请求失败，请检查后端服务或权限。";
        setError(message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [current]);

  if (!current) {
    return (
      <Card className="p-6">
        <Typography variant="h6">页面不存在</Typography>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.28em]">
              {current.mode}
            </Typography>
            <Typography variant="h5" className="mt-2">
              {current.label}
            </Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              {current.description}
            </Typography>
          </div>
          <Badge variant={current.mode === "admin" ? "warning" : "primary"}>{current.apiPath}</Badge>
        </div>
      </Card>

      <Grid container spacing={2}>
        <Grid item xs={12} md={8}>
          <Card className="p-6">
            <Typography variant="h6">接口返回</Typography>
            <Typography variant="caption" color="textSecondary">
              {loading ? "加载中..." : "接口调用完成"}
            </Typography>
            {error && (
              <Alert type="error" variant="filled" showIcon className="mt-4">
                {error}
              </Alert>
            )}
            {!error && !loading && (
              <pre className="mt-4 overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-100">
                {JSON.stringify(payload, null, 2)}
              </pre>
            )}
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card className="p-6">
            <Typography variant="h6">快速跳转</Typography>
            <div className="mt-3 grid gap-2">
              {prevRoute && (
                <Button variant="secondary" buttonStyle="text" fullWidth onClick={() => navigate(prevRoute.path)}>
                  上一页：{prevRoute.label}
                </Button>
              )}
              {nextRoute && (
                <Button variant="secondary" buttonStyle="text" fullWidth onClick={() => navigate(nextRoute.path)}>
                  下一页：{nextRoute.label}
                </Button>
              )}
              <Button
                variant="primary"
                buttonStyle="text"
                fullWidth
                onClick={() => navigate(current.mode === "admin" ? "/workspace/dashboard" : "/admin")}
              >
                {current.mode === "admin" ? "跳转用户工作台" : "跳转管理后台"}
              </Button>
            </div>
          </Card>
        </Grid>
      </Grid>

      <Card className="p-6">
        <Typography variant="h6">全部页面导航（{allConsoleRoutes.length}）</Typography>
        <Table striped hover className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>页面</TableCell>
              <TableCell>模式</TableCell>
              <TableCell>API</TableCell>
              <TableCell align="right">跳转</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {allConsoleRoutes.map((item) => (
              <TableRow key={item.path} hover>
                <TableCell>{item.label}</TableCell>
                <TableCell>{item.mode}</TableCell>
                <TableCell>{item.apiPath}</TableCell>
                <TableCell align="right">
                  <Button variant="secondary" buttonStyle="text" onClick={() => navigate(item.path)}>
                    打开
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default ConsolePage;

