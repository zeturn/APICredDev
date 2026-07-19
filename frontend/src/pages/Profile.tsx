import { Card, Grid, Typography } from "../lib/watercolor";
import { useEffect, useState } from "react";
import api from "../api/client";
import { useI18n } from "../i18n";
import Skeleton from "../ui/Skeleton";

type Me = {
  id: string;
  email: string;
  status: string;
};

const ProfilePage = () => {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const { t } = useI18n();

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
          {t("over.profile")}
        </Typography>
        <Typography variant="h5" className="text-[#103222] dark:text-[#F0F4F8]">{t("profile.title")}</Typography>
        <Typography variant="body2" color="textSecondary">
          {t("profile.desc")}
        </Typography>
      </div>
      <div className="w-full shrink-0 border-t-[3px] border-dashed border-[#103222] dark:border-[#F0F4F8] mt-[7px] mb-[28px]" />

      <Card className="p-6">
        {loading && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Skeleton className="h-3 w-16" />
              <Skeleton className="mt-2 h-4 w-full" />
            </Grid>
            <Grid item xs={12} md={4}>
              <Skeleton className="h-3 w-12" />
              <Skeleton className="mt-2 h-4 w-full" />
            </Grid>
            <Grid item xs={12} md={4}>
              <Skeleton className="h-3 w-12" />
              <Skeleton className="mt-2 h-4 w-20" />
            </Grid>
          </Grid>
        )}

        {!loading && me && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Typography variant="caption" color="textSecondary">{t("profile.userId")}</Typography>
              <Typography variant="body2" className="mt-1 break-all">{me.id}</Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="caption" color="textSecondary">{t("profile.email")}</Typography>
              <Typography variant="body2" className="mt-1 break-all">{me.email}</Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="caption" color="textSecondary">{t("profile.status")}</Typography>
              <Typography variant="body2" className="mt-1">{me.status}</Typography>
            </Grid>
          </Grid>
        )}
      </Card>
    </div>
  );
};

export default ProfilePage;
