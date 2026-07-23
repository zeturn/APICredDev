import { Typography } from "../lib/watercolor";
import { useI18n } from "../i18n";

const LoadingScreen = () => {
  const { t } = useI18n();
  return (
    <div className="flex min-h-screen items-center justify-center bg-white dark:bg-[#0f172a] px-4 transition-colors">
      <div className="w-full max-w-sm text-center">
        <Typography variant="h5" className="text-[#103222] dark:text-[#F0F4F8]">
          {t("loading.appName")}
        </Typography>

        <div className="ui-triple-ring-loader">
          <div className="ring ring-outer" />
          <div className="ring ring-middle" />
          <div className="ring ring-inner" />
        </div>

        <Typography variant="caption" color="textSecondary" className="mt-1 block dark:text-slate-400">
          {t("loading.screen")}
        </Typography>
      </div>
    </div>
  );
};

export default LoadingScreen;
