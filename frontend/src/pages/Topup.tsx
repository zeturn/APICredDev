import { useEffect, useMemo, useState } from "react";
import { Button, Card, Typography } from "../lib/watercolor";
import api from "../api/client";
import { useI18n } from "../i18n";
import { AdminIcon } from "./admin/adminCommon";

const TopupPage = () => {
  const { t } = useI18n();
  const basaltPassBaseUrl = (import.meta as any).env?.VITE_BASALTPASS_BASE_URL ?? "https://auth.beancs.hollowdata.com";
  const rechargePath = "/wallet/recharge";
  const redeemPath = "/wallet/gift-cards/redeem";
  const baseRechargeUrl = `${basaltPassBaseUrl.replace(/\/$/, "")}${rechargePath}`;
  const baseRedeemUrl = `${basaltPassBaseUrl.replace(/\/$/, "")}${redeemPath}`;
  const [rechargeUrl, setRechargeUrl] = useState(baseRechargeUrl);
  const [redeemUrl, setRedeemUrl] = useState(baseRedeemUrl);

  const fallbackRechargeUrl = useMemo(() => baseRechargeUrl, [baseRechargeUrl]);
  const fallbackRedeemUrl = useMemo(() => baseRedeemUrl, [baseRedeemUrl]);

  useEffect(() => {
    const buildUrls = async () => {
      let finalRechargeUrl = fallbackRechargeUrl;
      let finalRedeemUrl = fallbackRedeemUrl;
      try {
        const response = await api.get("/basalt/tenant-hint");
        const tenantCode = response?.data?.data?.tenant_code;
        if (tenantCode) {
          const query = `tenant=${encodeURIComponent(String(tenantCode))}`;
          finalRechargeUrl = `${fallbackRechargeUrl}?${query}`;
          finalRedeemUrl = `${fallbackRedeemUrl}?${query}`;
        }
      } catch {
      }

      setRechargeUrl(finalRechargeUrl);
      setRedeemUrl(finalRedeemUrl);
    };

    void buildUrls();
  }, [fallbackRechargeUrl, fallbackRedeemUrl]);

  const openExternal = (url: string) => {
    window.location.href = url;
  };

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

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="p-6">
          <div className="flex h-full flex-col">
            <div className="flex items-start gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white">
                <AdminIcon icon="wallet" className="h-5 w-5 text-slate-700" />
              </div>
              <div>
                <Typography variant="subtitle1">{t("topup.cashTitle")}</Typography>
                <Typography variant="body2" color="textSecondary" className="mt-2">
                  {t("topup.cashDesc")}
                </Typography>
              </div>
            </div>
            <div className="mt-6">
              <Button variant="primary" buttonStyle="filled" onClick={() => openExternal(rechargeUrl)}>
                {t("topup.cashGo")}
              </Button>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex h-full flex-col">
            <div className="flex items-start gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white">
                <AdminIcon icon="key" className="h-5 w-5 text-slate-700" />
              </div>
              <div>
                <Typography variant="subtitle1">{t("topup.giftTitle")}</Typography>
                <Typography variant="body2" color="textSecondary" className="mt-2">
                  {t("topup.giftDesc")}
                </Typography>
              </div>
            </div>
            <div className="mt-6">
              <Button variant="secondary" buttonStyle="filled" onClick={() => openExternal(redeemUrl)}>
                {t("topup.giftGo")}
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-5">
        <div className="flex items-start gap-3">
          <AdminIcon icon="shield" className="mt-0.5 h-5 w-5 text-slate-500" />
          <div>
            <Typography variant="subtitle2">{t("topup.noteTitle")}</Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              {t("topup.note")}
            </Typography>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default TopupPage;

