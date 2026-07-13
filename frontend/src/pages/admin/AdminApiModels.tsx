import { Badge, Button, Card, Grid, TextField, Typography } from "../../lib/watercolor";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import adminApi from "../../api/adminClient";
import { AdminIcon, AdminPageIntro } from "./adminCommon";
import { useI18n } from "../../i18n";

type ApiModelLink = {
  model_id: string;
  model_name: string;
  enabled: boolean;
  priority: number;
  weight: number;
  base_url: string | null;
};

type ApiSupportItem = {
  api_id: string;
  provider: string;
  provider_name: string;
  endpoint_id: string | null;
  endpoint_slug: string | null;
  endpoint_name: string | null;
  credential_name: string | null;
  enabled: boolean;
  health_state: string;
  base_url: string | null;
  supported_models: ApiModelLink[];
};

const AdminApiModelsPage = () => {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [items, setItems] = useState<ApiSupportItem[]>([]);
  const [keyword, setKeyword] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await adminApi.get("/admin/api-supported-models");
        setItems(resp.data ?? []);
      } catch {
        setItems([]);
      }
    };
    load();
  }, []);

  const filtered = useMemo(() => {
    const normalized = keyword.trim().toLowerCase();
    if (!normalized) {
      return items;
    }

    return items.filter((item) => {
      const inMeta =
        item.provider.toLowerCase().includes(normalized) ||
        item.provider_name.toLowerCase().includes(normalized) ||
        (item.api_id || "").toLowerCase().includes(normalized) ||
        (item.endpoint_name || "").toLowerCase().includes(normalized) ||
        (item.credential_name || "").toLowerCase().includes(normalized);
      if (inMeta) {
        return true;
      }
      return item.supported_models.some((model) => model.model_name.toLowerCase().includes(normalized));
    });
  }, [items, keyword]);

  return (
    <div className="space-y-6">
      <AdminPageIntro title={t("apimodels.title")} description={t("apimodels.desc")} />

      <Card className="p-6">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Typography variant="h6">{t("apimodels.manageObjects")}</Typography>
            <Typography variant="body2" color="textSecondary" className="mt-1">
              {t("apimodels.manageObjectsDesc")}
            </Typography>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button buttonStyle="filled" variant="primary" onClick={() => navigate("/admin/model-routes/new")}>
              {t("apimodels.newRoute")}
            </Button>
            <Button buttonStyle="text" variant="secondary" onClick={() => navigate("/admin/provider-credentials/new")}>
              {t("apimodels.newCredential")}
            </Button>
            <Button buttonStyle="text" variant="secondary" onClick={() => navigate("/admin/upstream-models/new")}>
              {t("apimodels.newUpstream")}
            </Button>
            <Button buttonStyle="text" variant="secondary" onClick={() => navigate("/admin/public-models/new")}>
              {t("apimodels.newPublic")}
            </Button>
          </div>
        </div>

        <Grid container spacing={2} alignItems="flex-end">
          <Grid item xs={12} md={8}>
            <TextField
              label={t("apimodels.search")}
              placeholder={t("apimodels.searchPlaceholder")}
              value={keyword}
              onChange={(e: any) => setKeyword(e.target.value)}
              fullWidth
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              {t("apimodels.currentCount")}<span className="font-semibold text-slate-900">{filtered.length}</span>
            </div>
          </Grid>
        </Grid>
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {filtered.map((item) => (
          <Card key={item.api_id || `${item.provider}-${item.endpoint_id}`} className="p-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 text-slate-900">
                  <AdminIcon icon="api" className="h-4 w-4" />
                  <Typography variant="subtitle1">{item.credential_name || item.endpoint_name || item.provider_name}</Typography>
                </div>
                <Typography variant="caption" color="textSecondary" className="mt-1 break-all">
                  {t("common.provider")}: {item.provider_name} · {t("health.colEndpoint")}: {item.endpoint_name || "-"}
                </Typography>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={item.enabled ? "primary" : "warning"}>{item.enabled ? "enabled" : "disabled"}</Badge>
                <Badge variant="secondary">{item.health_state}</Badge>
              </div>
            </div>

            <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-3">
              <Typography variant="caption" color="textSecondary" className="block">{t("apimodels.endpointBaseUrl")}</Typography>
              <Typography variant="body2" className="mt-1 break-all">{item.base_url || "-"}</Typography>
            </div>

            <div className="mt-4">
              <div className="mb-2 flex items-center justify-between">
                <Typography variant="subtitle2">{t("apimodels.supportedModels")}</Typography>
                <Badge variant="warning">{item.supported_models.length}</Badge>
              </div>
              {item.supported_models.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-3 text-sm text-slate-500">{t("apimodels.noBound")}</div>
              ) : (
                <div className="space-y-2">
                  {item.supported_models.map((model) => (
                    <div key={`${item.api_id}-${model.model_id}`} className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
                          <AdminIcon icon="models" className="h-4 w-4" />
                          {model.model_name}
                        </div>
                        <Badge variant={model.enabled ? "primary" : "warning"}>{model.enabled ? t("common.enabled") : t("common.disabled")}</Badge>
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {t("apimodels.priorityWeight", { p: model.priority, w: model.weight })}
                      </div>
                      {model.base_url ? <div className="mt-1 break-all text-xs text-slate-500">{t("apimodels.baseUrlLine", { u: model.base_url })}</div> : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Card>
        ))}

        {filtered.length === 0 && (
          <Card className="p-6">
            <Typography variant="body2" color="textSecondary">{t("apimodels.noData")}</Typography>
          </Card>
        )}
      </div>
    </div>
  );
};

export default AdminApiModelsPage;
