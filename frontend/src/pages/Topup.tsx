import { useEffect, useMemo, useState } from "react";
import { Button, Card, Typography } from "../lib/watercolor";
import api from "../api/client";
import { useI18n } from "../i18n";

const TopupPage = () => {
  const { t } = useI18n();
  const basaltPassBaseUrl = (import.meta as any).env?.VITE_BASALTPASS_BASE_URL ?? "https://auth.beancs.hollowdata.com";
  const fallbackClientId = (import.meta as any).env?.VITE_BASALTPASS_APP_CLIENT_ID ?? "";
  const appRechargePath = "/apps/recharge";
  const baseAppRechargeUrl = `${basaltPassBaseUrl.replace(/\/$/, "")}${appRechargePath}`;
  const [rechargeUrl, setRechargeUrl] = useState(baseAppRechargeUrl);

  const fallbackRechargeUrl = useMemo(() => baseAppRechargeUrl, [baseAppRechargeUrl]);

  useEffect(() => {
    const buildAndRedirect = async () => {
      let finalUrl = fallbackRechargeUrl;
      try {
        const response = await api.get("/basalt/tenant-hint");
        const tenantCode = response?.data?.data?.tenant_code;
        const appClientId = response?.data?.data?.app_client_id || fallbackClientId;
        const query = new URLSearchParams();
        if (appClientId) {
          query.set("client_id", String(appClientId));
        }
        if (tenantCode) {
          query.set("tenant", String(tenantCode));
        }
        const queryString = query.toString();
        if (queryString) {
          finalUrl = `${fallbackRechargeUrl}?${queryString}`;
        }
      } catch {
        if (fallbackClientId) {
          finalUrl = `${fallbackRechargeUrl}?client_id=${encodeURIComponent(String(fallbackClientId))}`;
        }
      }

      setRechargeUrl(finalUrl);
      window.location.replace(finalUrl);
    };

    void buildAndRedirect();
  }, [fallbackClientId, fallbackRechargeUrl]);

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
        <Typography variant="subtitle1">{t("topup.redirectTitle")}</Typography>
        <Typography variant="body2" color="textSecondary" className="mt-2">
          {t("topup.note")}
        </Typography>
        <div className="mt-4">
          <Button variant="primary" buttonStyle="filled" onClick={() => { window.location.href = rechargeUrl; }}>
            {t("topup.go")}
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default TopupPage;
