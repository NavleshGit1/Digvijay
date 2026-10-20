import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "muted" | "bordered";
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = "default",
  className = "",
  ...props
}) => {
  const variantStyles = {
    default: "bg-white border-slate-200 shadow-sm",
    muted: "bg-slate-50 border-slate-200",
    bordered: "bg-white border-slate-300 shadow-sm",
  };

  return (
    <div
      className={`rounded-xl border ${variantStyles[variant]} p-5 transition-shadow ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = "",
  ...props
}) => (
  <div className={`flex items-center justify-between pb-3 border-b border-slate-100 ${className}`} {...props}>
    {children}
  </div>
);

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  children,
  className = "",
  ...props
}) => (
  <h3 className={`text-sm font-semibold text-slate-900 ${className}`} {...props}>
    {children}
  </h3>
);

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = "",
  ...props
}) => (
  <div className={`pt-3 ${className}`} {...props}>
    {children}
  </div>
);
