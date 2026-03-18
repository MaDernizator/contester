interface LoadingStateProps {
  label?: string;
}

export function LoadingState({
  label = "Loading, please wait...",
}: LoadingStateProps) {
  return (
    <div className="loading-state">
      <div className="loading-state__spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}