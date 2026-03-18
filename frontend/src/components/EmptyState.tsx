import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  actions?: ReactNode;
}

export function EmptyState({ title, description, actions }: EmptyStateProps) {
  return (
    <div className="empty-state-card">
      <div className="empty-state-card__icon">○</div>
      <div className="empty-state-card__content">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {actions ? <div className="empty-state-card__actions">{actions}</div> : null}
    </div>
  );
}