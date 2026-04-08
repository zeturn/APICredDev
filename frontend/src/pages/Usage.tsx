import { Badge, Card, Grid, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import api from "../api/client";
import Skeleton from "../ui/Skeleton";

const UsagePage = () => {
  const [usage, setUsage] = useState<{ recent_sessions: any[]; by_model: any[] }>({
    recent_sessions: [],
    by_model: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await api.get("/billing/usage");
        setUsage(resp.data);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          usage
        </Typography>
        <Typography variant="h5">用量分析</Typography>
        <Typography variant="body2" color="textSecondary">
          查看最近调用记录，以及不同模型累计消耗了多少额度。
        </Typography>
      </div>

      <Grid container spacing={2}>
        <Grid item xs={12} md={5}>
          <Card className="p-6">
            <div className="flex items-center justify-between gap-3">
              <Typography variant="h6">按模型消费</Typography>
              <Badge variant="primary">{loading ? "..." : usage.by_model.length}</Badge>
            </div>
            <Table className="mt-4">
              <TableHead>
                <TableRow>
                  <TableCell>模型</TableCell>
                  <TableCell align="right">请求数</TableCell>
                  <TableCell align="right">已用额度</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading && Array.from({ length: 4 }).map((_, idx) => (
                  <TableRow key={`by-sk-${idx}`}>
                    <TableCell><Skeleton className="h-3 w-28" /></TableCell>
                    <TableCell align="right"><Skeleton className="ml-auto h-3 w-10" /></TableCell>
                    <TableCell align="right"><Skeleton className="ml-auto h-3 w-14" /></TableCell>
                  </TableRow>
                ))}
                {!loading && usage.by_model.map((item) => (
                  <TableRow key={item.model_id}>
                    <TableCell>{item.model_name}</TableCell>
                    <TableCell align="right">{item.requests}</TableCell>
                    <TableCell align="right">{item.used_credits}</TableCell>
                  </TableRow>
                ))}
                {!loading && usage.by_model.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3}>暂无已结算调用记录</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </Grid>
        <Grid item xs={12} md={7}>
          <Card className="p-6">
            <div className="flex items-center justify-between gap-3">
              <Typography variant="h6">最近调用</Typography>
              <Badge variant="secondary">{loading ? "..." : usage.recent_sessions.length}</Badge>
            </div>
            <Table className="mt-4">
              <TableHead>
                <TableRow>
                  <TableCell>模型</TableCell>
                  <TableCell>服务商</TableCell>
                  <TableCell align="right">Tokens</TableCell>
                  <TableCell align="right">费用</TableCell>
                  <TableCell align="right">状态</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading && Array.from({ length: 5 }).map((_, idx) => (
                  <TableRow key={`recent-sk-${idx}`}>
                    <TableCell><Skeleton className="h-3 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-3 w-20" /></TableCell>
                    <TableCell align="right"><Skeleton className="ml-auto h-3 w-12" /></TableCell>
                    <TableCell align="right"><Skeleton className="ml-auto h-3 w-12" /></TableCell>
                    <TableCell align="right"><Skeleton className="ml-auto h-3 w-14" /></TableCell>
                  </TableRow>
                ))}
                {!loading && usage.recent_sessions.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.model_name}</TableCell>
                    <TableCell>{item.provider ?? "-"}</TableCell>
                    <TableCell align="right">{item.total_tokens}</TableCell>
                    <TableCell align="right">{item.final_cost_credits}</TableCell>
                    <TableCell align="right">{item.status}</TableCell>
                  </TableRow>
                ))}
                {!loading && usage.recent_sessions.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5}>暂无调用记录</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </Grid>
      </Grid>
    </div>
  );
};

export default UsagePage;
