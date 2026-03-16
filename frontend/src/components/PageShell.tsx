import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";
import type { User } from "../api/types";

interface PageShellProps extends PropsWithChildren {
  user: User | null;
  onLogout: () => void | Promise<void>;
}

export function PageShell({ user, onLogout, children }: PageShellProps) {
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <div className="page-container app-shell__header-inner">
          <div className="brand-block">
            <NavLink to="/" className="brand-block__title">
              Contester
            </NavLink>
            <p className="brand-block__subtitle">
              Local contest management system
            </p>
          </div>

          <nav className="top-nav" aria-label="Main navigation">
            <NavLink to="/" className="top-nav__link">
              Home
            </NavLink>

            {user?.role === "admin" ? (
              <NavLink to="/admin" className="top-nav__link">
                Admin workspace
              </NavLink>
            ) : null}
          </nav>

          <div className="user-box">
            {user ? (
              <>
                <div className="user-box__meta">
                  <span className="user-box__name">
                    {user.full_name || user.username}
                  </span>
                  <span className="user-box__secondary">
                    @{user.username} · {user.role}
                  </span>
                </div>

                <button
                  type="button"
                  className="button button--secondary"
                  onClick={() => void onLogout()}
                >
                  Log out
                </button>
              </>
            ) : (
              <span className="user-box__secondary">Guest mode</span>
            )}
          </div>
        </div>
      </header>

      <main className="app-shell__main">
        <div className="page-container">{children}</div>
      </main>
    </div>
  );
}