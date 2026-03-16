import type { PropsWithChildren, ReactNode } from "react";

interface PanelProps extends PropsWithChildren {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  className?: string;
}

export function Panel({
  title,
  subtitle,
  actions,
  className,
  children,
}: PanelProps) {
  return (
    <section className={`panel ${className ?? ""}`.trim()}>
      <header className="panel__header">
        <div className="panel__title-group">
          <h2 className="panel__title">{title}</h2>
          {subtitle ? <p className="panel__subtitle">{subtitle}</p> : null}
        </div>

        {actions ? <div className="panel__actions">{actions}</div> : null}
      </header>

      <div className="panel__body">{children}</div>
    </section>
  );
}