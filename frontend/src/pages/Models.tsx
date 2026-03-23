import { Badge, Card, Grid, Typography } from "@zeturn/watercolor-react";
import { useEffect, useState } from "react";
import api from "../api/client";

const ModelsPage = () => {
  const [models, setModels] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      const resp = await api.get("/models");
      setModels(resp.data);
    };
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          models
        </Typography>
        <Typography variant="h5">模型</Typography>
        <Typography variant="body2" color="textSecondary">
          查看各模型倍率与定价信息。
        </Typography>
      </div>

      <Grid container spacing={2}>
        {models.map((m) => (
          <Grid item xs={12} md={6} key={m.id}>
            <Card className="p-6">
              <div className="flex items-center justify-between">
                <Typography variant="h6">{m.name}</Typography>
                <Badge variant="primary">x{m.multiplier}</Badge>
              </div>
              <pre className="mt-4 whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                {JSON.stringify(m.pricing, null, 2)}
              </pre>
            </Card>
          </Grid>
        ))}
        {models.length === 0 && (
          <Grid item xs={12}>
            <Card className="p-6">
              <Typography variant="body2" color="textSecondary">
                暂无模型配置
              </Typography>
            </Card>
          </Grid>
        )}
      </Grid>
    </div>
  );
};

export default ModelsPage;

