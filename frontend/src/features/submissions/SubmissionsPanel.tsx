import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getMySubmissions, isApiError } from "../../api/client";
import type { SubmissionSummary } from "../../api/types";
import { Panel } from "../../components/Panel";
import { StatusPill } from "../../components/StatusPill";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

const SUBMISSIONS_REFRESH_INTERVAL_MS = 3000;

export function SubmissionsPanel() {
  const [submissions, setSubmissions] = useState<SubmissionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const hasActiveSubmissions = submissions.some(
    (submission) =>
      submission.status === "pending" || submission.status === "running",
  );

  const loadSubmissions = useCallback(async (showLoader: boolean = true) => {
    if (showLoader) {
      setLoading(true);
    }

    try {
      const data = await getMySubmissions();
      setSubmissions(data);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(
        isApiError(error) ? error.message : "Failed to load submissions.",
      );
    } finally {
      if (showLoader) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadSubmissions(true);
  }, [loadSubmissions]);

  useAutoRefresh({
    enabled: hasActiveSubmissions,
    intervalMs: SUBMISSIONS_REFRESH_INTERVAL_MS,
    onRefresh: () => loadSubmissions(false),
  });

  return (
    <Panel
      title="My submissions"
      actions={
        <button
          type="button"
          className="button button--secondary"
          onClick={() => void loadSubmissions(true)}
        >
          Refresh
        </button>
      }
    >
      {loading ? <p className="muted">Loading submissions...</p> : null}
      {errorMessage ? <p className="feedback feedback--error">{errorMessage}</p> : null}

      {hasActiveSubmissions ? (
        <p className="muted small-text">
          Live updates are enabled while you have pending or running submissions.
        </p>
      ) : null}

      {!loading && !errorMessage && submissions.length === 0 ? (
        <p className="muted">No submissions yet.</p>
      ) : null}

      {submissions.length > 0 ? (
        <div className="list-stack">
          {submissions.map((submission) => (
            <article key={submission.id} className="list-card">
              <div className="list-card__header">
                <div>
                  <strong>
                    <Link
                      to={`/contests/${submission.contest.slug}/problems/${submission.problem.code}`}
                      className="inline-link"
                    >
                      {submission.problem.code} — {submission.problem.title}
                    </Link>
                  </strong>
                  <div className="muted small-text">
                    {new Date(submission.created_at).toLocaleString()}
                  </div>
                </div>
                <StatusPill value={submission.verdict} />
              </div>

              <div className="meta-grid">
                <span>Status: {submission.status}</span>
                <span>Language: {submission.language}</span>
                <span>
                  Passed: {submission.passed_test_count}/{submission.total_test_count}
                </span>
                <span>Time: {submission.execution_time_ms ?? "—"} ms</span>
              </div>

              <div>
                <Link to={`/submissions/${submission.id}`} className="inline-link">
                  Open submission details
                </Link>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </Panel>
  );
}
