import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getContests, isApiError } from "../api/client";
import type { Contest, User } from "../api/types";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { AdminTools } from "../features/admin/AdminTools";
import { AuthPanel } from "../features/auth/AuthPanel";
import { SubmissionsPanel } from "../features/submissions/SubmissionsPanel";

interface HomePageProps {
  user: User | null;
  sessionLoading: boolean;
  onAuthenticated: () => Promise<void>;
}

export function HomePage({ user, sessionLoading, onAuthenticated }: HomePageProps) {
  const [contests, setContests] = useState<Contest[]>([]);
  const [loadingContests, setLoadingContests] = useState(false);
  const [contestError, setContestError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      setContests([]);
      return;
    }

    void (async () => {
      setLoadingContests(true);
      setContestError(null);

      try {
        const data = await getContests();
        setContests(data);
      } catch (error) {
        setContestError(isApiError(error) ? error.message : "Failed to load contests.");
      } finally {
        setLoadingContests(false);
      }
    })();
  }, [user]);

  if (sessionLoading) {
    return <p className="muted">Checking session...</p>;
  }

  if (!user) {
    return (
      <div className="stack">
        <Panel title="Welcome">
          <p className="muted">
            Log in with an existing account or register as a participant.
          </p>
        </Panel>
        <AuthPanel onAuthenticated={onAuthenticated} />
      </div>
    );
  }

  return (
    <div className="stack">
      <Panel title="Published contests">
        {loadingContests ? <p className="muted">Loading contests...</p> : null}
        {contestError ? <p className="feedback feedback--error">{contestError}</p> : null}

        {!loadingContests && !contestError && contests.length === 0 ? (
          <p className="muted">No published contests are available right now.</p>
        ) : null}

        {contests.length > 0 ? (
          <div className="list-stack">
            {contests.map((contest) => (
              <article key={contest.id} className="list-card">
                <div className="list-card__header">
                  <div>
                    <strong>
                      <Link className="inline-link" to={`/contests/${contest.slug}`}>
                        {contest.title}
                      </Link>
                    </strong>
                    <div className="muted small-text">
                      {contest.slug} · phase: {contest.phase}
                    </div>
                  </div>
                  <StatusPill value={contest.status} />
                </div>

                {contest.description ? <p>{contest.description}</p> : null}

                <div className="meta-grid">
                  <span>Starts: {contest.starts_at ? new Date(contest.starts_at).toLocaleString() : "—"}</span>
                  <span>Ends: {contest.ends_at ? new Date(contest.ends_at).toLocaleString() : "—"}</span>
                  <span>Author: {contest.created_by.username}</span>
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </Panel>

      <SubmissionsPanel />

      {user.role === "admin" ? <AdminTools /> : null}
    </div>
  );
}