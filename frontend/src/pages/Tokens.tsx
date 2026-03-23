import { Alert, Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@zeturn/watercolor-react";
import { useEffect, useState } from "react";
import api from "../api/client";

const TokensPage = () => {
  const [tokens, setTokens] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState("llm");
  const [newToken, setNewToken] = useState<string | null>(null);

  const load = async () => {
    const resp = await api.get("/tokens");
    setTokens(resp.data);
  };

  useEffect(() => {
    load();
  }, []);

  const createToken = async () => {
    const resp = await api.post("/tokens", { name, scopes: scopes.split(",").map((s) => s.trim()) });
    setNewToken(resp.data.token);
    setName("");
    await load();
  };

  const revoke = async (id: string) => {
    await api.delete(`/tokens/${id}`);
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          tokens
        </Typography>
        <Typography variant="h5">API Tokens</Typography>
        <Typography variant="body2" color="textSecondary">
          Token 仅明文展示一次，请及时保存。
        </Typography>
      </div>

      <Card className="p-6">
        <Grid container spacing={2} alignItems="flex-end">
          <Grid item xs={12} md={4}>
            <TextField label="名称" placeholder="name" value={name} onChange={(e: any) => setName(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              label="Scopes"
              placeholder="scopes (comma)"
              value={scopes}
              onChange={(e: any) => setScopes(e.target.value)}
              fullWidth
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={createToken}>
              创建
            </Button>
          </Grid>
        </Grid>
      </Card>

      {newToken && (
        <Alert type="success" variant="filled" title="新 Token" showIcon>
          新 token（仅显示一次）：<code>{newToken}</code>
        </Alert>
      )}

      <Card className="p-6">
        <Table striped hover>
          <TableHead>
            <TableRow>
              <TableCell>名称</TableCell>
              <TableCell>Scopes</TableCell>
              <TableCell>状态</TableCell>
              <TableCell align="right">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tokens.map((t) => (
              <TableRow key={t.id} hover>
                <TableCell>{t.name}</TableCell>
                <TableCell>{t.scopes.join(", ")}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{t.status}</Badge>
                </TableCell>
                <TableCell align="right">
                  <Button buttonStyle="text" variant="error" onClick={() => revoke(t.id)}>
                    撤销
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {tokens.length === 0 && (
              <TableRow>
                <TableCell colSpan={4}>暂无 Token</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default TokensPage;

