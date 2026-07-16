import { Button, Card, Typography } from "../lib/watercolor";
import { useLocation } from "react-router-dom";
import { useI18n } from "../i18n";
import LanguageSwitcher from "../i18n/LanguageSwitcher";
import ThemeToggle from "../ThemeToggle";
import { apiBaseUrl } from "../api/client";

const LoginPage = () => {
  const location = useLocation();
  const { t } = useI18n();
  const from = (location.state as any)?.from?.pathname || "/workspace/dashboard";

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between gap-2">
        <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.35em]">
          apicred access
        </Typography>
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </div>
      <Typography variant="h5" className="mt-2">
        {t("login.title")}
      </Typography>
      <Typography variant="body2" color="textSecondary" className="mt-1">
        {t("login.desc")}
      </Typography>

      <div className="mt-6 grid gap-4">
        <Button
          variant="secondary"
          buttonStyle="outlined"
          fullWidth
          onClick={() => {
            const nextPath = encodeURIComponent(from);
            window.location.href = `${apiBaseUrl}/auth/basalt/login?next=${nextPath}`;
          }}
        >
          {t("login.button")}
        </Button>
      </div>
    </Card>
  );
};

export default LoginPage;

