import { useEffect, useState } from "react";
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
      <Panel title={contest.title}>
        <div className="list-card__header">
          <div className="muted">
            {contest.slug} · phase: {contest.phase}
          </div>
          <StatusPill value={contest.status} />
        </div>

        {contest.description ? <p>{contest.description}</p> : null}

        <div className="meta-grid">
          <span>Starts: {contest.starts_at ? new Date(contest.starts_at).toLocaleString() : "—"}</span>
          <span>Ends: {contest.ends_at ? new Date(contest.ends_at).toLocaleString() : "—"}</span>
          <span>Created by: {contest.created_by.username}</span>
        </div>
      </Panel>

      <Panel title="Problems">
        {problems.length === 0 ? (
          <p className="muted">No published problems in this contest yet.</p>
        ) : (
          <div className="list-stack">
            {problems.map((problem) => (
              <article key={problem.id} className="list-card">
                <div className="list-card__header">
                  <div>
                    <strong>
                      <Link
                        className="inline-link"
                        to={`/contests/${contest.slug}/problems/${problem.code}`}
                      >
                        {problem.code} — {problem.title}
                      </Link>
                    </strong>
                    <div className="muted small-text">Position: {problem.position}</div>
                  </div>
                  <StatusPill value={problem.status} />
                </div>

                <div className="meta-grid">
                  <span>Time limit: {problem.time_limit_ms} ms</span>
                  <span>Memory limit: {problem.memory_limit_mb} MB</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}