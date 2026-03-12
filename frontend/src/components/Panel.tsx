import type { PropsWithChildren, ReactNode } from "react";

interface PanelProps extends PropsWithChildren {
  title: string;
  actions?: ReactNode;
}

export function Panel({ title, actions, children }: PanelProps) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h2>{title}</h2>
        {actions ? <div className="panel__actions">{actions}</div> : null}
      </div>
      <div className="panel__body">{children}</div>
    </section>
  );
}