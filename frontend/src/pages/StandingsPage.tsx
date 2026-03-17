import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getContest, getContestProblems, isApiError } from "../api/client";
import type { Contest, ProblemSummary, User } from "../api/types";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";

interface ContestPageProps {
  user: User | null;
}

export function ContestPage({ user }: ContestPageProps) {
  const { contestSlug } = useParams<{ contestSlug: string }>();
  const [contest, setContest] = useState<Contest | null>(null);
  const [problems, setProblems] = useState<ProblemSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!user || !contestSlug) {
      return;
    }

    void (async () => {
      setLoading(true);
      setErrorMessage(null);

      try {
        const [contestData, problemData] = await Promise.all([
          getContest(contestSlug),
          getContestProblems(contestSlug),
        ]);
        setContest(contestData);
        setProblems(problemData);
      } catch (error) {
        setErrorMessage(isApiError(error) ? error.message : "Failed to load contest.");
      } finally {
        setLoading(false);
      }
    })();
  }, [contestSlug, user]);

  const firstProblem = useMemo(() => problems[0] ?? null, [problems]);

  if (!user) {
    return (
      <Panel title="Authentication required">
        <p className="muted">Please log in first.</p>
      </Panel>
    );
  }

  if (loading) {
    return (
      <Panel title="Contest">
        <p className="muted">Loading contest...</p>
      </Panel>
    );
  }

  if (errorMessage) {
    return (
      <Panel title="Contest">
        <p className="feedback feedback--error">{errorMessage}</p>
      </Panel>
    );
  }

  if (!contest) {
    return (
      <Panel title="Contest">
        <p className="muted">Contest not found.</p>
      </Panel>
    );
  }

  return (
    <div className="stack">
      <section className="page-head">
        <div>
          <span className="page-head__eyebrow">Contest</span>
          <h1 className="page-head__title">{contest.title}</h1>
          <p className="page-head__subtitle">
            Browse problems, move into solving mode, and follow the live scoreboard.
          </p>
        </div>

        <div className="page-actions">
          <Link
            to={`/contests/${contest.slug}/standings`}
            className="button button--secondary"
          >
            View standings
          </Link>

          {firstProblem ? (
            <Link
              to={`/contests/${contest.slug}/problems/${firstProblem.code}`}
              className="button"
            >
              Start solving
            </Link>
          ) : null}
        </div>
      </section>

      <Panel title="Contest overview" subtitle={`Slug: ${contest.slug}`}>
        <div className="list-card__header">
          <div className="muted">
            Phase: {contest.phase}
          </div>
          <StatusPill value={contest.status} />
        </div>

        {contest.description ? <p>{contest.description}</p> : null}

        <div className="stats-grid stats-grid--compact">
          <div className="stat-card">
            <span className="stat-card__label">Starts</span>
            <strong className="stat-card__value stat-card__value--small">
              {contest.starts_at ? new Date(contest.starts_at).toLocaleString() : "—"}
            </strong>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Ends</span>
            <strong className="stat-card__value stat-card__value--small">
              {contest.ends_at ? new Date(contest.ends_at).toLocaleString() : "—"}
            </strong>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Problems</span>
            <strong className="stat-card__value">{problems.length}</strong>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Created by</span>
            <strong className="stat-card__value stat-card__value--small">
              {contest.created_by.username}
            </strong>
          </div>
        </div>
      </Panel>

      <Panel title="Problems" subtitle="Open a task to read the statement and submit a solution.">
        {problems.length === 0 ? (
          <p className="muted">No published problems in this contest yet.</p>
        ) : (
          <div className="contest-grid">
            {problems.map((problem) => (
              <article key={problem.id} className="contest-card">
                <div className="contest-card__header">
                  <div>
                    <h3 className="contest-card__title">
                      {problem.code} — {problem.title}
                    </h3>
                    <p className="contest-card__meta">Position: {problem.position}</p>
                  </div>
                  <StatusPill value={problem.status} />
                </div>

                <div className="meta-grid">
                  <span>Time limit: {problem.time_limit_ms} ms</span>
                  <span>Memory limit: {problem.memory_limit_mb} MB</span>
                </div>

                <div className="contest-card__footer">
                  <Link
                    className="button button--secondary"
                    to={`/contests/${contest.slug}/problems/${problem.code}`}
                  >
                    Open problem
                  </Link>

                  <Link
                    className="inline-link"
                    to={`/contests/${contest.slug}/problems/${problem.code}`}
                  >
                    Solve now
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}