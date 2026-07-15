import { Typography } from "../../lib/watercolor";
import { ReactNode } from "react";
import { useI18n } from "../../i18n";

export const AdminPageIntro = ({ title, description }: { title: string; description: string }) => {
  const { t } = useI18n();
  return (
    <div className="space-y-1">
      <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
        {t("admin.overline")}
      </Typography>
      <Typography variant="h5">{title}</Typography>
      <Typography variant="body2" color="textSecondary">
        {description}
      </Typography>
    </div>
  );
};

export const AdminIcon = ({ icon, className }: { icon: "users" | "models" | "provider" | "usage" | "chat" | "api" | "shield" | "home" | "wallet" | "key"; className?: string }) => {
  const base = `h-5 w-5 ${className ?? ""}`;
  const paths: Record<string, ReactNode> = {
    users: (
      <>
        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="8.5" cy="7" r="4" />
        <path d="M20 8v6" />
        <path d="M23 11h-6" />
      </>
    ),
    models: (
      <>
        <path d="M12 2 3 7l9 5 9-5-9-5Z" />
        <path d="m3 17 9 5 9-5" />
        <path d="m3 12 9 5 9-5" />
      </>
    ),
    provider: (
      <>
        <path d="M4 7h16" />
        <path d="M4 12h16" />
        <path d="M4 17h10" />
      </>
    ),
    usage: (
      <>
        <path d="M3 3v18h18" />
        <path d="m7 14 4-4 3 3 5-6" />
      </>
    ),
    chat: (
      <>
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        <path d="M8 9h8" />
        <path d="M8 13h5" />
      </>
    ),
    api: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M7 8h10" />
        <path d="M7 12h6" />
        <path d="M7 16h4" />
      </>
    ),
    shield: (
      <>
        <path d="M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3Z" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
    home: (
      <>
        <path d="M3 10.5 12 3l9 7.5" />
        <path d="M5 9.5V21h14V9.5" />
      </>
    ),
    wallet: (
      <>
        <rect x="2" y="6" width="20" height="12" rx="2" />
        <path d="M16 12h4" />
        <path d="M18 10v4" />
      </>
    ),
    key: (
      <>
        <circle cx="7.5" cy="12" r="3.5" />
        <path d="M11 12h10" />
        <path d="M18 12v3" />
        <path d="M15 12v2" />
      </>
    ),
  };

  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={base}>
      {paths[icon]}
    </svg>
  );
};
