interface StatusPillProps {
  value: string;
}

function getStatusClass(value: string): string {
  const normalized = value.toLowerCase();

  if (normalized === "accepted" || normalized === "published" || normalized === "running") {
    return "status-pill status-pill--success";
  }

  if (normalized === "wrong_answer" || normalized === "runtime_error") {
    return "status-pill status-pill--danger";
  }

  if (normalized === "time_limit_exceeded" || normalized === "archived") {
    return "status-pill status-pill--warning";
  }

  return "status-pill status-pill--neutral";
}

export function StatusPill({ value }: StatusPillProps) {
  return <span className={getStatusClass(value)}>{value}</span>;
}