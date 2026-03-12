import { Link } from "react-router-dom";
import type { User } from "../api/types";

interface PageShellProps {
  user: User | null;
  onLogout: () => Promise<void>;
  children: React.ReactNode;
}

export function PageShell({ user, onLogout, children }: PageShellProps) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <Link to="/" className="app-logo">
            Contester
          </Link>
          <p className="app-subtitle">Local contest management MVP</p>
        </div>

        <div className="app-header__session">
          {user ? (
            <>
              <div className="session-summary">
                <strong>{user.full_name || user.username}</strong>
                <span>
                  @{user.username} · {user.role}
                </span>
              </div>
              <button type="button" className="button button--secondary" onClick={onLogout}>
                Log out
              </button>
            </>
          ) : (
            <span className="muted">Not authenticated</span>
          )}
        </div>
      </header>

      <main className="app-main">{children}</main>
    </div>
  );
}