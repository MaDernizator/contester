import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getSubmission, isApiError } from "../api/client";
import type { Submission, User } from "../api/types";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useAutoRefresh } from "../hooks/useAutoRefresh";

interface SubmissionPageProps {
  user: User | null;
}

const REFRESH_INTERVAL_MS = 2000;

function shouldAutoRefresh(submission: Submission | null): boolean {
  if (submission === null) {
    return false;
  }

  return submission.status === "pending" || submission.status === "running";
}

export function SubmissionPage({ user }: SubmissionPageProps) {
  const { submissionId } = useParams<{ submissionId: string }>();
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const autoRefreshEnabled = useMemo(
    () => shouldAutoRefresh(submission),
    [submission],
  );

  const loadSubmission = useCallback(async (showLoader: boolean = true) => {
    if (!submissionId) {
      return;
    }

    if (showLoader) {
      setLoading(true);
    }

    try {
      const data = await getSubmission(submissionId);
      setSubmission(data);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(isApiError(error) ? error.message : "Failed to load submission.");
    } finally {
      if (showLoader) {
        setLoading(false);
      }
    }
  }, [submissionId]);

  useEffect(() => {
    if (!user || !submissionId) {
      return;
    }

    void loadSubmission(true);
  }, [submissionId, user, loadSubmission]);

  useAutoRefresh({
    enabled: autoRefreshEnabled,
    intervalMs: REFRESH_INTERVAL_MS,
    onRefresh: () => loadSubmission(false),
  });

  if (!user) {
    return (
      <Panel title="Authentication required">
        <p className="muted">Please log in first.</p>
      </Panel>
    );
  }

  if (loading) {
    return (
      <Panel title="Submission">
        <p className="muted">Loading submission...</p>
      </Panel>
    );
  }

  if (errorMessage) {
    return (
      <Panel title="Submission">
        <p className="feedback feedback--error">{errorMessage}</p>
      </Panel>
    );
  }

  if (!submission) {
    return (
      <Panel title="Submission">
        <p className="muted">Submission not found.</p>
      </Panel>
    );
  }

  return (
    <div className="stack">
      <Panel
        title={`Submission ${submission.id}`}
        actions={
          <button
            type="button"
            className="button button--secondary"
            onClick={() => void loadSubmission(true)}
          >
            Refresh
          </button>
        }
      >
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
              Created: {new Date(submission.created_at).toLocaleString()}
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
          <span>Failed test: {submission.failed_test_position ?? "—"}</span>
          <span>Execution time: {submission.execution_time_ms ?? "—"} ms</span>
          <span>
            Judged at:{" "}
            {submission.judged_at
              ? new Date(submission.judged_at).toLocaleString()
              : "—"}
          </span>
        </div>

        <div className="inline-links-row">
          <Link
            to={`/contests/${submission.contest.slug}`}
            className="inline-link"
          >
            Open contest
          </Link>
          <Link
            to={`/contests/${submission.contest.slug}/problems/${submission.problem.code}`}
            className="inline-link"
          >
            Open problem
          </Link>
        </div>

        {autoRefreshEnabled ? (
          <p className="muted small-text">
            Live updates are enabled while the submission is pending or running.
          </p>
        ) : null}
      </Panel>

      {submission.judge_log ? (
        <Panel title="Judge log">
          <pre className="plain-code-block">{submission.judge_log}</pre>
        </Panel>
      ) : null}

      <Panel title="Source code">
        <pre className="plain-code-block">{submission.source_code}</pre>
      </Panel>
    </div>
  );
}
