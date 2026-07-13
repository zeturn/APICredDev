import { Typography } from "../lib/watercolor";
import { useI18n } from "../i18n";

const LoadingScreen = () => {
  const { t } = useI18n();
  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-4">
      <div className="w-full max-w-sm text-center">
        <Typography variant="h5">{t("loading.appName")}</Typography>
        <div className="ui-center-loading-track mt-5 w-full border border-slate-200 bg-slate-100" />
        <Typography variant="caption" color="textSecondary" className="mt-3 block">
          {t("loading.screen")}
        </Typography>
      </div>
    </div>
  );
};

export default LoadingScreen;
