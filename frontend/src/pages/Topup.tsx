import { useEffect, useMemo, useState } from "react";
import { Button, Card, Typography } from "../lib/watercolor";
import api from "../api/client";
import { useI18n } from "../i18n";

const TopupPage = () => {
  const { t } = useI18n();
  const basaltPassBaseUrl = (import.meta as any).env?.VITE_BASALTPASS_BASE_URL ?? "https://auth.beancs.hollowdata.com";
  const fallbackClientId = (import.meta as any).env?.VITE_BASALTPASS_APP_CLIENT_ID ?? "";
  const appRechargePath = "/apps/recharge";
  const giftCardPath = "/wallet/gift-cards/redeem";
  const baseAppRechargeUrl = `${basaltPassBaseUrl.replace(/\/$/, "")}${appRechargePath}`;
  const baseGiftCardUrl = `${basaltPassBaseUrl.replace(/\/$/, "")}${giftCardPath}`;
  const [rechargeUrl, setRechargeUrl] = useState(baseAppRechargeUrl);
  const [giftCardUrl, setGiftCardUrl] = useState(baseGiftCardUrl);

  const fallbackRechargeUrl = useMemo(() => baseAppRechargeUrl, [baseAppRechargeUrl]);
  const fallbackGiftCardUrl = useMemo(() => baseGiftCardUrl, [baseGiftCardUrl]);

  useEffect(() => {
    const buildLinks = async () => {
      let finalUrl = fallbackRechargeUrl;
      let finalGiftUrl = fallbackGiftCardUrl;
      let clientId = fallbackClientId;
      let tenantCode: string | undefined;

      try {
        const response = await api.get("/basalt/tenant-hint");
        const data = response?.data?.data;
        clientId = data?.app_client_id || fallbackClientId;
        tenantCode = data?.tenant_code || undefined;
      } catch {
        // tenant-hint failed; use fallback values
      }

      const query = new URLSearchParams();
      if (clientId) {
        query.set("client_id", String(clientId));
      }
      if (tenantCode) {
        query.set("tenant", String(tenantCode));
      }
      query.set("return_url", `${window.location.origin}/workspace/topup`);
      finalUrl = `${fallbackRechargeUrl}?${query.toString()}`;

      if (tenantCode) {
        finalGiftUrl = `${fallbackGiftCardUrl}?tenant=${encodeURIComponent(String(tenantCode))}`;
      }

      setRechargeUrl(finalUrl);
      setGiftCardUrl(finalGiftUrl);
    };

    void buildLinks();
  }, [fallbackClientId, fallbackGiftCardUrl, fallbackRechargeUrl]);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          {t("over.topup")}
        </Typography>
        <Typography variant="h5" className="text-[#103222] dark:text-[#F0F4F8]">{t("topup.title")}</Typography>
        <Typography variant="body2" color="textSecondary">{t("topup.desc")}</Typography>
      </div>
      <div className="w-full shrink-0 border-t-[3px] border-dashed border-[#103222] dark:border-[#F0F4F8] mt-[7px] mb-[28px]" />

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="p-6">
          <Typography variant="subtitle1">{t("topup.cashTitle")}</Typography>
          <Typography variant="body2" color="textSecondary" className="mt-2">{t("topup.cashDesc")}</Typography>
          <div className="mt-4">
            <Button variant="primary" buttonStyle="filled" onClick={() => { window.location.href = rechargeUrl; }}>
              {t("topup.cashGo")}
            </Button>
          </div>
        </Card>

        <Card className="p-6">
          <Typography variant="subtitle1">{t("topup.giftTitle")}</Typography>
          <Typography variant="body2" color="textSecondary" className="mt-2">{t("topup.giftDesc")}</Typography>
          <div className="mt-4">
            <Button variant="secondary" buttonStyle="outlined" onClick={() => { window.location.href = giftCardUrl; }}>
              {t("topup.giftGo")}
            </Button>
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <Typography variant="subtitle1">{t("topup.noteTitle")}</Typography>
        <Typography variant="body2" color="textSecondary" className="mt-2">{t("topup.note")}</Typography>
      </Card>
    </div>
  );
};

export default TopupPage;
