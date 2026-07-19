import { Badge, Button, Card, Grid, Typography } from "../lib/watercolor";
import { useEffect, useMemo, useState } from "react";
import api from "../api/client";
import { formatPricingSummary } from "../shared/pricing";
import Skeleton from "../ui/Skeleton";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../i18n";

const ModelsPage = () => {
  const navigate = useNavigate();
  const { t } = useI18n();
  const [models, setModels] = useState<any[]>([]);
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await api.get("/models");
        setModels(resp.data);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filteredModels = useMemo(() => {
    const normalized = keyword.trim().toLowerCase();
    if (!normalized) {
      return models;
    }
    return models.filter((item) => {
      const brand = (item.brand_name || "").toLowerCase();
      const name = (item.name || "").toLowerCase();
      const category = (item.category || "").toLowerCase();
      return brand.includes(normalized) || name.includes(normalized) || category.includes(normalized);
    });
  }, [models, keyword]);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          {t("over.models")}
        </Typography>
        <Typography variant="h5" className="text-[#103222] dark:text-[#F0F4F8]">{t("models.title")}</Typography>
        <Typography variant="body2" color="textSecondary">
          {t("models.desc")}
        </Typography>
      </div>
      <div className="w-full shrink-0 border-t-[3px] border-dashed border-[#103222] dark:border-[#F0F4F8] mt-[7px] mb-[28px]" />

      <Card className="p-6">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="md:col-span-2">
            <label className="mb-2 block text-sm font-medium text-slate-600 dark:text-slate-400">{t("models.search")}</label>
            <input
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/70 px-3 py-3 text-sm text-slate-800 dark:text-slate-100 shadow-inner focus:outline-none focus:ring-2 focus:ring-slate-400"
              placeholder={t("models.searchPlaceholder")}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
          <div className="rounded-2xl border border-slate-200 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-800/40 p-4">
            <Typography variant="body2" color="textSecondary">{t("models.visibleModels")}</Typography>
            <Typography variant="h3" className="mt-1">{filteredModels.length}</Typography>
          </div>
        </div>
      </Card>

      {loading && (
        <Grid container spacing={2}>
          {Array.from({ length: 4 }).map((_, idx) => (
            <Grid item xs={12} md={6} key={`sk-${idx}`}>
              <Card className="p-6">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-14 w-14" rounded="lg" />
                  <div className="min-w-0 flex-1">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="mt-2 h-3 w-28" />
                  </div>
                </div>
                <Skeleton className="mt-4 h-24 w-full" rounded="lg" />
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {!loading && (
      <Grid container spacing={2}>
        {filteredModels.map((m) => (
          <Grid item xs={12} md={6} key={m.id}>
            <Card className="p-6">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  {m.effective_icon_url ? (
                    <div className="rounded-2xl border border-sky-100 bg-gradient-to-br from-sky-50 to-indigo-50 p-2 shadow-sm">
                      <img src={m.effective_icon_url} alt={m.name} className="h-10 w-10 rounded-xl object-contain" />
                    </div>
                  ) : (
                    <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-sky-100 bg-gradient-to-br from-sky-50 to-indigo-50 text-sm font-semibold text-sky-700 shadow-sm">
                      {(m.name || "?").slice(0, 2).toUpperCase()}
                    </div>
                  )}
                  <div>
                    <Typography variant="h6">{m.name}</Typography>
                    <Typography variant="caption" color="textSecondary" className="mt-1 block">
                      {m.brand_name || t("models.noBrand")} · {m.category || "llm"}
                    </Typography>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={m.enabled ? "primary" : "warning"}>{m.enabled ? t("common.enabled") : t("common.disabled")}</Badge>
                  <Badge variant="secondary">x{m.multiplier}</Badge>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50 p-4">
                <Typography variant="subtitle2" className="text-slate-900">{t("models.price")}</Typography>
                <div className="mt-2 space-y-1">
                  {formatPricingSummary(m.pricing, t).map((line) => (
                    <Typography key={`${m.id}-${line}`} variant="body2" color="textSecondary">
                      {line}
                    </Typography>
                  ))}
                </div>
              </div>
            </Card>
          </Grid>
        ))}

        {filteredModels.length === 0 && (
          <Grid item xs={12}>
            <Card className="p-6">
              <Typography variant="h6">{t("models.noModels")}</Typography>
              <Typography variant="body2" color="textSecondary" className="mt-2">
                {t("models.noModelsDesc")}
              </Typography>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button variant="secondary" buttonStyle="outlined" onClick={() => window.location.reload()}>
                  {t("models.reload")}
                </Button>
                <Button variant="secondary" buttonStyle="text" onClick={() => navigate("/admin/public-models")}>
                  {t("models.notifyAdmin")}
                </Button>
              </div>
            </Card>
          </Grid>
        )}
      </Grid>
      )}
    </div>
  );
};

export default ModelsPage;

