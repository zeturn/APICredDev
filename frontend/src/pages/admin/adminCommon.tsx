import { Typography } from "../../lib/watercolor";

export const AdminPageIntro = ({ title, description }: { title: string; description: string }) => (
  <div className="space-y-1">
    <Typography variant="overline" color="textSecondary" className="uppercase tracking-[0.3em]">
      admin
    </Typography>
    <Typography variant="h5">{title}</Typography>
    <Typography variant="body2" color="textSecondary">
      {description}
    </Typography>
  </div>
);
