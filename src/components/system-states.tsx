export function DashboardSkeleton() {
  return (
    <div className="page-shell" aria-label="Loading dashboard">
      <div className="skeleton skeleton-title" />
      <div className="stats-grid">
        {Array.from({ length: 4 }).map((_, index) => (
          <div className="skeleton skeleton-stat" key={index} />
        ))}
      </div>
      <div className="skeleton skeleton-panel" />
    </div>
  );
}

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="error-notice" role="alert">
      <div>
        <strong>Live data interrupted</strong>
        <p>{message}</p>
      </div>
      {onRetry ? <button className="secondary-button" onClick={onRetry}>Retry</button> : null}
    </div>
  );
}
