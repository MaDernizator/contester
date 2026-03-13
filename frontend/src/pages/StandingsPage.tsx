import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getContestStandings, isApiError } from "../api/client";
import type { ContestStandings, StandingProblemResult, User } from "../api/types";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";

interface StandingsPageProps {
  user: User | null;
}

function renderProblemCell(result: StandingProblemResult) {
  if (!result.accepted && result.attempt_count === 0) {
    return "—";
  }

  if (result.accepted) {
    return `+${result.wrong_attempts_before_accept > 0 ? result.wrong_attempts_before_accept : ""}`;
  }

  return `-${result.attempt_count}`;
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
      <Panel
        title={`Standings — ${standings.contest.title}`}
        actions={
          <Link to={`/contests/${standings.contest.slug}`} className="button button--secondary">
            Back to contest
          </Link>
        }
      >
        <div className="meta-grid">
          <span>Contest: {standings.contest.slug}</span>
          <span>Problems: {standings.problems.length}</span>
          <span>Generated: {new Date(standings.generated_at).toLocaleString()}</span>
        </div>
      </Panel>

      <Panel title="Scoreboard">
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
                {standings.rows.map((row) => (
                  <tr key={row.user.id}>
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
                          <StatusPill value={result.accepted ? "accepted" : result.last_verdict ?? "pending"} />
                          <span>{renderProblemCell(result)}</span>
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
