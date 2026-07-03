import { Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminPageIntro } from "./adminCommon";

type HealthItem = {
  provider: string;
  endpoint: string;
  credential_id: string;
  credential_name: string;
  enabled: boolean;
  health_state: string;
  cooldown_until?: string | null;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  last_error_code?: string | null;
  consecutive_failures: number;
  routes_count: number;
  quota_status?: Record<string, string>;
};

const AdminProviderHealthPage = () => {
  const [items, setItems] = useState<HealthItem[]>([]);
  const [benchmarks, setBenchmarks] = useState<any[]>([]);
  const [rotateCredentialId, setRotateCredentialId] = useState("");
  const [rotateSecret, setRotateSecret] = useState("");

  const load = async () => {
    try {
      const resp = await adminApi.get("/admin/provider-health");
      setItems((resp.data?.items || []) as HealthItem[]);
      const benchmarkResp = await adminApi.get("/admin/provider-benchmarks");
      setBenchmarks(benchmarkResp.data || []);
    } catch {
      setItems([]);
      setBenchmarks([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const action = async (url: string, body?: any) => {
    await adminApi.post(url, body || {});
    await load();
  };

  const rotate = async () => {
    if (!rotateCredentialId || !rotateSecret) return;
    await action(`/admin/provider-credentials/${rotateCredentialId}/rotate-secret`, { secret: rotateSecret });
    setRotateSecret("");
    setRotateCredentialId("");
  };

  return (
    <div className="space-y-6">
      <AdminPageIntro title="Provider Health Console" description="查看 provider/credential 健康状态、路由覆盖、并执行启停/健康检查/密钥轮换。" />

      <Card className="p-6">
        <Typography variant="h6">Secret Rotation</Typography>
        <Grid container spacing={2} className="mt-4" alignItems="flex-end">
          <Grid item xs={12} md={4}>
            <TextField label="Credential ID" value={rotateCredentialId} onChange={(e: any) => setRotateCredentialId(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField label="New Secret" type="password" value={rotateSecret} onChange={(e: any) => setRotateSecret(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={2}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={rotate} disabled={!rotateCredentialId || !rotateSecret}>
              Rotate
            </Button>
          </Grid>
        </Grid>
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between">
          <Typography variant="h6">Provider Health</Typography>
          <Badge variant="primary">{items.length}</Badge>
        </div>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>Provider</TableCell>
              <TableCell>Endpoint</TableCell>
              <TableCell>Credential</TableCell>
              <TableCell>Health</TableCell>
              <TableCell>Enabled</TableCell>
              <TableCell>Cooldown</TableCell>
              <TableCell>Last Success</TableCell>
              <TableCell>Last Failure</TableCell>
              <TableCell>Error</TableCell>
              <TableCell align="right">Failures</TableCell>
              <TableCell align="right">Routes</TableCell>
              <TableCell>Quota</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.credential_id}>
                <TableCell>{item.provider}</TableCell>
                <TableCell>{item.endpoint}</TableCell>
                <TableCell>{item.credential_name}</TableCell>
                <TableCell>{item.health_state}</TableCell>
                <TableCell>{item.enabled ? "yes" : "no"}</TableCell>
                <TableCell>{item.cooldown_until || "-"}</TableCell>
                <TableCell>{item.last_success_at || "-"}</TableCell>
                <TableCell>{item.last_failure_at || "-"}</TableCell>
                <TableCell>{item.last_error_code || "-"}</TableCell>
                <TableCell align="right">{item.consecutive_failures}</TableCell>
                <TableCell align="right">{item.routes_count}</TableCell>
                <TableCell>
                  m:{item.quota_status?.minute || "-"} h:{item.quota_status?.hour || "-"} d:{item.quota_status?.day || "-"}
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button buttonStyle="text" variant="primary" onClick={() => action(`/admin/provider-credentials/${item.credential_id}/health-check`)}>
                      Check
                    </Button>
                    <Button buttonStyle="text" variant="secondary" onClick={() => action(`/admin/provider-credentials/${item.credential_id}/${item.enabled ? "disable" : "enable"}`)}>
                      {item.enabled ? "Disable" : "Enable"}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {items.length === 0 && (
              <TableRow>
                <TableCell colSpan={13}>No provider health data.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between">
          <Typography variant="h6">Recent Benchmarks</Typography>
          <Badge variant="secondary">{benchmarks.length}</Badge>
        </div>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>Run</TableCell>
              <TableCell>Provider</TableCell>
              <TableCell>Model</TableCell>
              <TableCell align="right">Runs</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Summary</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {benchmarks.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.id}</TableCell>
                <TableCell>{item.provider || "-"}</TableCell>
                <TableCell>{item.public_model || "-"}</TableCell>
                <TableCell align="right">{item.runs}</TableCell>
                <TableCell>{item.status}</TableCell>
                <TableCell>{JSON.stringify(item.summary_json || {})}</TableCell>
              </TableRow>
            ))}
            {benchmarks.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>No benchmark runs.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default AdminProviderHealthPage;
