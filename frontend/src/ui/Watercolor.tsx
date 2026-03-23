import React from "react";

type BaseProps = React.PropsWithChildren<{ style?: React.CSSProperties; className?: string }>;

export const Card = ({ children, style, className }: BaseProps) => (
  <div className={`wc-card p-6 ${className ?? ""}`} style={style}>
    {children}
  </div>
);

export const Button = ({ children, className, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
  <button
    className={`inline-flex items-center justify-center rounded-xl border border-ink-100 bg-white/80 px-4 py-2 text-sm font-medium text-ink-700 shadow-sm transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink-300 disabled:opacity-60 ${className ?? ""}`}
    {...rest}
  >
    {children}
  </button>
);

export const Input = ({ className, ...rest }: React.InputHTMLAttributes<HTMLInputElement>) => (
  <input
    className={`w-full rounded-xl border border-ink-100 bg-white/70 px-3 py-2 text-sm text-ink-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-ink-200 ${className ?? ""}`}
    {...rest}
  />
);

