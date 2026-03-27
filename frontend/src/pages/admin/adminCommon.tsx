import { Alert, Typography } from "../../lib/watercolor";

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

export const AdminTokenWarning = () => (
  <Alert type="warning" variant="filled" showIcon>
    需要先在左侧保存 `Admin Token`，当前页面的数据请求才会通过。
  </Alert>
);
