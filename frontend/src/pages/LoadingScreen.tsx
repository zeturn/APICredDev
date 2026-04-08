import { Typography } from "../lib/watercolor";

const LoadingScreen = () => {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-4">
      <div className="w-full max-w-sm text-center">
        <Typography variant="h5">API Cred</Typography>
        <div className="ui-center-loading-track mt-5 w-full border border-slate-200 bg-slate-100" />
        <Typography variant="caption" color="textSecondary" className="mt-3 block">
          正在加载，请稍候...
        </Typography>
      </div>
    </div>
  );
};

export default LoadingScreen;
