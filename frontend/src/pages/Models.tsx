import { Badge, Card, Grid, Typography } from "../lib/watercolor";
import { useEffect, useMemo, useState } from "react";
import api from "../api/client";
import { formatPricingSummary } from "../shared/pricing";

const ModelsPage = () => {
  const [models, setModels] = useState<any[]>([]);
  const [keyword, setKeyword] = useState("");

  useEffect(() => {
    const load = async () => {
      const resp = await api.get("/models");
      setModels(resp.data);
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
          models
        </Typography>
        <Typography variant="h5">可用模型目录</Typography>
        <Typography variant="body2" color="textSecondary">
          独立展示模型图标、倍率与价格明细，便于快速选型。
        </Typography>
      </div>

      <Card className="p-6">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="md:col-span-2">
            <label className="mb-2 block text-sm font-medium text-slate-600">搜索模型</label>
            <input
              className="w-full rounded-xl border border-ink-100 bg-white/70 px-3 py-3 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200"
              placeholder="输入模型名、品牌或分类"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <Typography variant="body2" color="textSecondary">当前可见模型</Typography>
            <Typography variant="h3" className="mt-1">{filteredModels.length}</Typography>
          </div>
        </div>
      </Card>

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
                      {m.brand_name || "未标注品牌"} · {m.category || "llm"}
                    </Typography>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={m.enabled ? "primary" : "warning"}>{m.enabled ? "enabled" : "disabled"}</Badge>
                  <Badge variant="secondary">x{m.multiplier}</Badge>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50 p-4">
                <Typography variant="subtitle2" className="text-slate-900">价格</Typography>
                <div className="mt-2 space-y-1">
                  {formatPricingSummary(m.pricing).map((line) => (
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
              <Typography variant="body2" color="textSecondary">
                暂无匹配模型
              </Typography>
            </Card>
          </Grid>
        )}
      </Grid>
    </div>
  );
};

export default ModelsPage;

