import React from "react";

type CommonProps = {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
};

const cx = (...parts: Array<string | false | null | undefined>) => parts.filter(Boolean).join(" ");

const COLOR_CLASS: Record<string, string> = {
  textSecondary: "text-slate-500",
  primary: "text-slate-800",
  secondary: "text-slate-700",
  warning: "text-slate-700",
  error: "text-slate-700",
};

const TYPOGRAPHY_CLASS: Record<string, string> = {
  overline: "text-[11px] font-semibold uppercase tracking-[0.22em]",
  h3: "text-[30px] font-semibold",
  h5: "text-[26px] font-semibold",
  h6: "text-[18px] font-semibold",
  subtitle1: "text-base font-semibold",
  subtitle2: "text-sm font-semibold",
  body2: "text-sm leading-[1.6]",
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
        ? "border-slate-700 bg-slate-800 text-white hover:bg-slate-900"
        : "border-slate-300 text-slate-700 hover:bg-slate-100"
      : variant === "error"
        ? buttonStyle === "filled"
          ? "border-red-600 bg-red-600 text-white hover:bg-red-700"
          : "border-red-300 text-red-700 hover:bg-red-50"
        : variant === "warning"
          ? buttonStyle === "filled"
            ? "border-amber-500 bg-amber-500 text-white hover:bg-amber-600"
            : "border-amber-300 text-amber-700 hover:bg-amber-50"
          : buttonStyle === "filled"
            ? "border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
            : "border-slate-300 text-slate-700 hover:bg-slate-100";
  const surface = buttonStyle === "text" ? "border-transparent bg-transparent" : "";
  return (
    <button
      className={cx(
        "inline-flex items-center justify-center border px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-300 disabled:cursor-not-allowed disabled:opacity-60",
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
      ? "border-slate-300 bg-white text-slate-800"
      : type === "warning"
        ? "border-slate-300 bg-white text-slate-800"
        : type === "error"
          ? "border-slate-300 bg-white text-slate-800"
          : "border-slate-300 bg-white text-slate-800";
  const icon = type === "success" ? "✓" : type === "warning" ? "!" : type === "error" ? "×" : "i";
  return (
    <div className={cx("border px-4 py-3 text-sm", tone, className)}>
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
      ? "border-slate-300 bg-white text-slate-700"
      : variant === "secondary"
        ? "border-slate-300 bg-white text-slate-700"
        : "border-slate-300 bg-white text-slate-700";
  return <span className={cx("inline-flex items-center border px-2.5 py-1 text-xs font-semibold", tone, className)}>{children}</span>;
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
        "w-full border border-slate-300 bg-white px-3 py-3 text-sm text-ink-800 focus:outline-none focus:ring-1 focus:ring-slate-300",
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
  const XS_SPAN_CLASS: Record<number, string> = {
    1: "col-span-1",
    2: "col-span-2",
    3: "col-span-3",
    4: "col-span-4",
    5: "col-span-5",
    6: "col-span-6",
    7: "col-span-7",
    8: "col-span-8",
    9: "col-span-9",
    10: "col-span-10",
    11: "col-span-11",
    12: "col-span-12",
  };
  const MD_SPAN_CLASS: Record<number, string> = {
    1: "md:col-span-1",
    2: "md:col-span-2",
    3: "md:col-span-3",
    4: "md:col-span-4",
    5: "md:col-span-5",
    6: "md:col-span-6",
    7: "md:col-span-7",
    8: "md:col-span-8",
    9: "md:col-span-9",
    10: "md:col-span-10",
    11: "md:col-span-11",
    12: "md:col-span-12",
  };

  const spanClass = (value?: number | boolean, prefix = "") => {
    if (value === undefined || value === false) return "";
    if (value === true) return prefix ? "md:col-span-12" : "col-span-12";
    const numberValue = typeof value === "number" ? value : 12;
    if (prefix === "md:") {
      return MD_SPAN_CLASS[numberValue] ?? "md:col-span-12";
    }
    return XS_SPAN_CLASS[numberValue] ?? "col-span-12";
  };

  const gapClass =
    spacing <= 0
      ? ""
      : spacing === 1
        ? "gap-1"
        : spacing === 2
          ? "gap-2"
          : spacing === 3
            ? "gap-3"
            : spacing === 4
              ? "gap-4"
              : "gap-4";

  if (container) {
    return (
      <div
        className={cx("grid grid-cols-12", gapClass, alignItems === "flex-end" && "items-end", className)}
        style={style}
      >
        {children}
      </div>
    );
  }

  if (item) {
    return (
      <div className={cx("col-span-12", spanClass(xs), spanClass(md, "md:"), className)} style={style}>
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
        "relative flex h-9 items-center px-3 !rounded-xl text-sm font-medium text-slate-700 transition-colors",
        button && "cursor-pointer hover:!bg-slate-200/60",
        selected && "!bg-slate-200 font-semibold !text-slate-900",
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  );
};
