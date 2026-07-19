import { Alert, Badge, Button, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import api from "../api/client";
import { useI18n } from "../i18n";

const TokensPage = () => {
  const { t } = useI18n();
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
          {t("over.tokens")}
        </Typography>
        <Typography variant="h5">{t("tokens.title")}</Typography>
        <Typography variant="body2" color="textSecondary">
          {t("tokens.desc")}
        </Typography>
      </div>
      <div className="h-[8px] w-full shrink-0 bg-[#103222] dark:bg-[#F0F4F8] mt-[7px] mb-[28px]" />

      <Card className="p-6">
        <Grid container spacing={2} alignItems="flex-end">
          <Grid item xs={12} md={4}>
            <TextField label={t("tokens.name")} placeholder={t("tokens.namePlaceholder")} value={name} onChange={(e: any) => setName(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              label={t("tokens.scopes")}
              placeholder={t("tokens.scopesPlaceholder")}
              value={scopes}
              onChange={(e: any) => setScopes(e.target.value)}
              fullWidth
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={createToken}>
              {t("tokens.create")}
            </Button>
          </Grid>
        </Grid>
      </Card>

      {newToken && (
        <Alert type="success" variant="filled" title={t("tokens.new")} showIcon>
          {t("tokens.newAlert")}<code>{newToken}</code>
        </Alert>
      )}

      <Card className="p-6">
        <Table striped hover>
          <TableHead>
            <TableRow>
              <TableCell>{t("tokens.nameCol")}</TableCell>
              <TableCell>{t("tokens.scopesCol")}</TableCell>
              <TableCell>{t("tokens.statusCol")}</TableCell>
              <TableCell align="right">{t("tokens.actionCol")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tokens.map((token) => (
              <TableRow key={token.id} hover>
                <TableCell>{token.name}</TableCell>
                <TableCell>{token.scopes.join(", ")}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{token.status}</Badge>
                </TableCell>
                <TableCell align="right">
                  <Button buttonStyle="text" variant="error" onClick={() => revoke(token.id)}>
                    {t("tokens.revoke")}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {tokens.length === 0 && (
              <TableRow>
                <TableCell colSpan={4}>{t("tokens.noTokens")}</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default TokensPage;

