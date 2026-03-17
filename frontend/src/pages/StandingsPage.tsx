import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getContestStandings, isApiError } from "../api/client";
import type {
  ContestStandings,
  StandingProblemResult,
  SubmissionVerdict,
  User,
} from "../api/types";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";

interface StandingsPageProps {
  user: User | null;
}

function getProblemCellText(result: StandingProblemResult): string {
  if (!result.accepted && result.attempt_count === 0) {
    return "—";
  }

  if (result.accepted) {
    return result.wrong_attempts_before_accept > 0
      ? `+${result.wrong_attempts_before_accept}`
      : "+";
  }

  return `-${result.attempt_count}`;
}

function getProblemCellStatus(
  result: StandingProblemResult,
): SubmissionVerdict | "accepted" | "pending" {
  if (result.accepted) {
    return "accepted";
  }

  return result.last_verdict ?? "pending";
}

export function StandingsPage({ user }: StandingsPageProps) {
  const { contestSlug } = useParams<{ contestSlug: string }>();
  const [standings, setStandings] = useState<ContestStandings | null>(null);
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
        const data = await getContestStandings(contestSlug);
        setStandings(data);
      } catch (error) {
        setErrorMessage(isApiError(error) ? error.message : "Failed to load standings.");
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
      <Panel title="Standings">
        <p className="muted">Loading standings...</p>
      </Panel>
    );
  }

  if (errorMessage) {
    return (
      <Panel title="Standings">
        <p className="feedback feedback--error">{errorMessage}</p>
      </Panel>
    );
  }

  if (!standings) {
    return (
      <Panel title="Standings">
        <p className="muted">Standings are unavailable.</p>
      </Panel>
    );
  }

  return (
    <div className="stack">
      <section className="page-head">
        <div>
          <span className="page-head__eyebrow">Scoreboard</span>
          <h1 className="page-head__title">{standings.contest.title}</h1>
          <p className="page-head__subtitle">
            Follow ranking, solved problems, and per-problem progress.
          </p>
        </div>

        <div className="page-actions">
          <Link
            to={`/contests/${standings.contest.slug}`}
            className="button button--secondary"
          >
            Back to contest
          </Link>
        </div>
      </section>

      <Panel title="Standings overview" subtitle={`Contest: ${standings.contest.slug}`}>
        <div className="stats-grid stats-grid--compact">
          <div className="stat-card">
            <span className="stat-card__label">Problems</span>
            <strong className="stat-card__value">{standings.problems.length}</strong>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Participants</span>
            <strong className="stat-card__value">{standings.rows.length}</strong>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Generated</span>
            <strong className="stat-card__value stat-card__value--small">
              {new Date(standings.generated_at).toLocaleString()}
            </strong>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Your role</span>
            <strong className="stat-card__value stat-card__value--small">
              {user.role}
            </strong>
          </div>
        </div>
      </Panel>

      <Panel title="Scoreboard table" subtitle="Current ranking in ICPC-style format.">
        {standings.rows.length === 0 ? (
          <p className="muted">No participants in standings yet.</p>
        ) : (
          <div className="table-scroll">
            <table className="scoreboard-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>User</th>
                  <th>Solved</th>
                  <th>Penalty</th>
                  {standings.problems.map((problem) => (
                    <th key={problem.id}>{problem.code}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {standings.rows.map((row) => {
                  const isCurrentUser = row.user.id === user.id;

                  return (
                    <tr
                      key={row.user.id}
                      className={isCurrentUser ? "scoreboard-row--current" : ""}
                    >
                      <td>{row.rank}</td>
                      <td>
                        <div className="scoreboard-user">
                          <strong>{row.user.full_name || row.user.username}</strong>
                          <span className="muted small-text">@{row.user.username}</span>
                        </div>
                      </td>
                      <td>{row.solved_count}</td>
                      <td>{row.penalty_minutes}</td>

                      {row.problem_results.map((result) => (
                        <td key={result.problem.id}>
                          <div className="scoreboard-cell">
                            <StatusPill value={getProblemCellStatus(result)} />
                            <strong>{getProblemCellText(result)}</strong>
                            <span className="scoreboard-cell__meta">
                              {result.accepted
                                ? `Attempts: ${result.attempt_count}`
                                : result.attempt_count > 0
                                  ? `Tried: ${result.attempt_count}`
                                  : "No attempts"}
                            </span>
                          </div>
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}