import React from "react";

type CommonProps = {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
};

const cx = (...parts: Array<string | false | null | undefined>) => parts.filter(Boolean).join(" ");

const COLOR_CLASS: Record<string, string> = {
  textSecondary: "text-slate-500",
  primary: "text-sky-700",
  secondary: "text-slate-700",
  warning: "text-amber-700",
  error: "text-rose-700",
};

const TYPOGRAPHY_CLASS: Record<string, string> = {
  overline: "text-[11px] font-semibold uppercase tracking-[0.28em]",
  h3: "text-3xl font-semibold tracking-tight",
  h5: "text-2xl font-semibold tracking-tight",
  h6: "text-lg font-semibold tracking-tight",
  subtitle1: "text-base font-semibold",
  subtitle2: "text-sm font-semibold",
  body2: "text-sm leading-6",
  caption: "text-xs leading-5",
};

export const ThemeProvider = ({ children }: CommonProps) => <>{children}</>;

export const Typography = ({
  variant = "body2",
  color,
  className,
  children,
}: CommonProps & { variant?: string; color?: string }) => {
  const Tag =
    variant === "h3" ? "h3" : variant === "h5" ? "h2" : variant === "h6" ? "h3" : variant === "subtitle1" ? "h4" : "p";
  return <Tag className={cx(TYPOGRAPHY_CLASS[variant] ?? TYPOGRAPHY_CLASS.body2, color ? COLOR_CLASS[color] : "", className)}>{children}</Tag>;
};

export const Card = ({ children, className, style }: CommonProps) => (
  <div className={cx("wc-card", className)} style={style}>
    {children}
  </div>
);

export const Button = ({
  variant = "secondary",
  buttonStyle = "filled",
  fullWidth,
  className,
  children,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string; buttonStyle?: string; fullWidth?: boolean }) => {
  const palette =
    variant === "primary"
      ? buttonStyle === "filled"
        ? "border-sky-600 bg-sky-600 text-white hover:bg-sky-700"
        : "border-sky-200 text-sky-700 hover:bg-sky-50"
      : variant === "error"
        ? "border-rose-200 text-rose-700 hover:bg-rose-50"
        : variant === "warning"
          ? "border-amber-200 text-amber-700 hover:bg-amber-50"
          : "border-slate-200 text-slate-700 hover:bg-slate-50";
  const surface = buttonStyle === "text" ? "border-transparent bg-transparent shadow-none" : "bg-white/80 shadow-sm";
  return (
    <button
      className={cx(
        "inline-flex items-center justify-center rounded-xl border px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-200 disabled:cursor-not-allowed disabled:opacity-60",
        surface,
        palette,
        fullWidth && "w-full",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
};

export const Alert = ({
  type = "info",
  title,
  showIcon,
  className,
  children,
}: CommonProps & { type?: string; variant?: string; title?: string; showIcon?: boolean }) => {
  const tone =
    type === "success"
      ? "border-emerald-200 bg-emerald-50 text-emerald-900"
      : type === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-900"
        : type === "error"
          ? "border-rose-200 bg-rose-50 text-rose-900"
          : "border-sky-200 bg-sky-50 text-sky-900";
  const icon = type === "success" ? "✓" : type === "warning" ? "!" : type === "error" ? "×" : "i";
  return (
    <div className={cx("rounded-2xl border px-4 py-3 text-sm", tone, className)}>
      <div className="flex gap-3">
        {showIcon && <div className="pt-0.5 text-sm font-semibold">{icon}</div>}
        <div className="min-w-0">
          {title && <div className="font-semibold">{title}</div>}
          <div>{children}</div>
        </div>
      </div>
    </div>
  );
};

export const Badge = ({ variant = "primary", className, children }: CommonProps & { variant?: string }) => {
  const tone =
    variant === "warning"
      ? "bg-amber-100 text-amber-800"
      : variant === "secondary"
        ? "bg-slate-100 text-slate-700"
        : "bg-sky-100 text-sky-800";
  return <span className={cx("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold", tone, className)}>{children}</span>;
};

export const TextField = ({
  label,
  fullWidth,
  className,
  ...rest
}: React.InputHTMLAttributes<HTMLInputElement> & { label?: string; fullWidth?: boolean }) => (
  <label className={cx("block", fullWidth && "w-full")}>
    {label && <span className="mb-2 block text-sm font-medium text-slate-600">{label}</span>}
    <input
      className={cx(
        "w-full rounded-xl border border-ink-100 bg-white/70 px-3 py-3 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200",
        className,
      )}
      {...rest}
    />
  </label>
);

export const Grid = ({
  container,
  item,
  spacing = 0,
  xs,
  md,
  alignItems,
  className,
  style,
  children,
}: CommonProps & { container?: boolean; item?: boolean; spacing?: number; xs?: number | boolean; md?: number | boolean; alignItems?: string }) => {
  const widthClass = (value?: number | boolean, prefix = "") => {
    if (value === undefined || value === false) return "";
    if (value === true || value === 12) return `${prefix}w-full`;
    if (value === 9) return `${prefix}w-3/4`;
    if (value === 8) return `${prefix}w-2/3`;
    if (value === 6) return `${prefix}w-1/2`;
    if (value === 4) return `${prefix}w-1/3`;
    if (value === 3) return `${prefix}w-1/4`;
    if (value === 2) return `${prefix}w-1/6`;
    return `${prefix}w-full`;
  };

  if (container) {
    return (
      <div
        className={cx("flex flex-wrap", spacing ? "gap-4" : "", alignItems === "flex-end" && "items-end", className)}
        style={style}
      >
        {children}
      </div>
    );
  }

  if (item) {
    return (
      <div className={cx("w-full", widthClass(xs), widthClass(md, "md:"), className)} style={style}>
        {children}
      </div>
    );
  }

  return (
    <div className={className} style={style}>
      {children}
    </div>
  );
};

export const Table = ({ className, children }: CommonProps & { striped?: boolean; hover?: boolean }) => (
  <div className="overflow-x-auto">
    <table className={cx("min-w-full border-separate border-spacing-0", className)}>{children}</table>
  </div>
);

export const TableHead = ({ children }: CommonProps) => <thead className="bg-slate-50/80">{children}</thead>;
export const TableBody = ({ children }: CommonProps) => <tbody>{children}</tbody>;
export const TableRow = ({ className, children }: CommonProps & { hover?: boolean }) => (
  <tr className={cx("border-b border-slate-100 last:border-b-0", className)}>{children}</tr>
);
export const TableCell = ({
  align,
  className,
  children,
  ...rest
}: React.TdHTMLAttributes<HTMLTableCellElement> & { align?: string }) => (
  <td
    className={cx("border-b border-slate-100 px-4 py-3 text-sm text-slate-700", align === "right" && "text-right", className)}
    {...rest}
  >
    {children}
  </td>
);

export const List = ({ className, children }: CommonProps) => <div className={className}>{children}</div>;

export const ListItem = ({
  component: Component,
  button,
  selected,
  className,
  children,
  ...rest
}: CommonProps & { component?: React.ElementType; button?: boolean; selected?: boolean }) => {
  const Tag = Component ?? "div";
  return (
    <Tag
      className={cx(
        "block rounded-xl px-3 py-2 text-sm text-slate-700 transition",
        button && "cursor-pointer hover:bg-slate-50",
        selected && "bg-sky-50 text-sky-700",
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  );
};
