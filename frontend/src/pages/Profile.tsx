import { Card, Grid, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import api from "../api/client";

type Me = {
  id: string;
  email: string;
  status: string;
};

const ProfilePage = () => {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const resp = await api.get("/auth/me");
        if (active) {
          setMe(resp.data);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
          profile
        </Typography>
        <Typography variant="h5">个人信息</Typography>
        <Typography variant="body2" color="textSecondary">
          查看当前登录账号的基础资料。
        </Typography>
      </div>

      <Card className="p-6">
        {loading && <Typography variant="body2" color="textSecondary">加载中...</Typography>}

        {!loading && me && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Typography variant="caption" color="textSecondary">用户 ID</Typography>
              <Typography variant="body2" className="mt-1 break-all">{me.id}</Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="caption" color="textSecondary">邮箱</Typography>
              <Typography variant="body2" className="mt-1 break-all">{me.email}</Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="caption" color="textSecondary">状态</Typography>
              <Typography variant="body2" className="mt-1">{me.status}</Typography>
            </Grid>
          </Grid>
        )}
      </Card>
    </div>
  );
};

export default ProfilePage;
