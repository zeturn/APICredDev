import { useEffect, useMemo, useState } from "react";
import { Button, Card, Typography } from "../lib/watercolor";
import api from "../api/client";

const TopupPage = () => {
  const basaltPassBaseUrl = (import.meta as any).env?.VITE_BASALTPASS_BASE_URL ?? "http://localhost:5104";
  const redeemPath = "/wallet/gift-cards/redeem";
  const baseRedeemUrl = `${basaltPassBaseUrl.replace(/\/$/, "")}${redeemPath}`;
  const [redeemUrl, setRedeemUrl] = useState(baseRedeemUrl);

  const fallbackRedeemUrl = useMemo(() => baseRedeemUrl, [baseRedeemUrl]);

  useEffect(() => {
    const buildAndRedirect = async () => {
      let finalUrl = fallbackRedeemUrl;
      try {
        const response = await api.get("/basalt/tenant-hint");
        const tenantCode = response?.data?.data?.tenant_code;
        if (tenantCode) {
          finalUrl = `${fallbackRedeemUrl}?tenant=${encodeURIComponent(String(tenantCode))}`;
        }
      } catch {
      }

      setRedeemUrl(finalUrl);
      window.location.replace(finalUrl);
    };

    void buildAndRedirect();
  }, [fallbackRedeemUrl]);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          topup
        </Typography>
        <Typography variant="h5">充值</Typography>
        <Typography variant="body2" color="textSecondary">
          正在跳转到 BasaltPass 钱包 Gift Card 兑换页面。
        </Typography>
      </div>

      <Card className="p-6">
        <Typography variant="subtitle1">若未自动跳转，请点击下方按钮</Typography>
        <Typography variant="body2" color="textSecondary" className="mt-2">
          你将进入 BasaltPass 用户钱包中的 Gift Card 兑换页。
        </Typography>
        <div className="mt-4">
          <Button
            variant="primary"
            buttonStyle="filled"
            onClick={() => {
              window.location.href = redeemUrl;
            }}
          >
            前往 Gift Card 兑换
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default TopupPage;

