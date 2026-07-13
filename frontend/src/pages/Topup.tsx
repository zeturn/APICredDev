import { useEffect, useMemo, useState } from "react";
import { Button, Card, Typography } from "../lib/watercolor";
import api from "../api/client";
import { useI18n } from "../i18n";

const TopupPage = () => {
  const { t } = useI18n();
  const basaltPassBaseUrl = (import.meta as any).env?.VITE_BASALTPASS_BASE_URL ?? "https://auth.beancs.hollowdata.com";
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
          {t("over.topup")}
        </Typography>
        <Typography variant="h5">{t("topup.title")}</Typography>
        <Typography variant="body2" color="textSecondary">
          {t("topup.desc")}
        </Typography>
      </div>

      <Card className="p-6">
        <Typography variant="subtitle1">{t("topup.ifNot")}</Typography>
        <Typography variant="body2" color="textSecondary" className="mt-2">
          {t("topup.note")}
        </Typography>
        <div className="mt-4">
          <Button
            variant="primary"
            buttonStyle="filled"
            onClick={() => {
              window.location.href = redeemUrl;
            }}
          >
            {t("topup.go")}
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default TopupPage;

