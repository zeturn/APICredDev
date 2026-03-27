import { Alert, Button, Card, Grid, TextField, Typography } from "../lib/watercolor";
import { useState } from "react";
import api from "../api/client";

const TopupPage = () => {
  const [code, setCode] = useState("");
  const [balance, setBalance] = useState<number | null>(null);

  const redeem = async () => {
    const resp = await api.post("/billing/redeem", { code });
    setBalance(resp.data.balance_credits);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          topup
        </Typography>
        <Typography variant="h5">充值</Typography>
        <Typography variant="body2" color="textSecondary">
          支持卡密兑换与后续 Stripe 充值。
        </Typography>
      </div>

      <Card className="p-6">
        <Grid container spacing={2} alignItems="flex-end">
          <Grid item xs={12} md={9}>
            <TextField label="卡密" placeholder="卡密" value={code} onChange={(e: any) => setCode(e.target.value)} fullWidth />
          </Grid>
          <Grid item xs={12} md={3}>
            <Button variant="primary" buttonStyle="filled" fullWidth onClick={redeem}>
              兑换
            </Button>
          </Grid>
        </Grid>
      </Card>

      {balance !== null && (
        <Alert type="success" variant="filled" title="兑换成功" showIcon>
          当前余额：{balance}
        </Alert>
      )}

      <Card className="p-6">
        <Typography variant="subtitle1">Stripe 支付入口</Typography>
        <Typography variant="body2" color="textSecondary" className="mt-2">
          后续在此接入支付流程与 webhook 状态。
        </Typography>
      </Card>
    </div>
  );
};

export default TopupPage;

