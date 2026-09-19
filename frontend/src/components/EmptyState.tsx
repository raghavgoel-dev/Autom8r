interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: string;
}

export default function EmptyState({ title, description, icon }: EmptyStateProps) {
  return (
    <div className="empty-state">
      {icon !== undefined ? (
        <div className="empty-state-icon" aria-hidden="true">
          {icon}
        </div>
      ) : null}
      <p className="empty-state-title">{title}</p>
      {description !== undefined ? <p className="empty-state-text">{description}</p> : null}
    </div>
  );
}
