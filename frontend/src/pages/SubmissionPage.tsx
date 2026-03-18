import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getSubmission, isApiError } from "../api/client";
import type { Submission, User } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
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
        <EmptyState
          title="Login required"
          description="Please log in before opening submission details."
        />
      </Panel>
    );
  }

  if (loading) {
    return (
      <Panel title="Submission">
        <LoadingState label="Loading submission..." />
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
        <EmptyState
          title="Submission not found"
          description="The requested submission could not be loaded."
        />
      </Panel>
    );
  }

  return (
    <div className="stack">
      <section className="page-head">
        <div>
          <span className="page-head__eyebrow">Submission details</span>
          <h1 className="page-head__title">Submission {submission.id}</h1>
          <p className="page-head__subtitle">
            Inspect current judging state, logs, source code, and final verdict.
          </p>
        </div>

        <div className="page-actions">
          <button
            type="button"
            className="button button--secondary"
            onClick={() => void loadSubmission(true)}
          >
            Refresh
          </button>
        </div>
      </section>

      <Panel title="Summary" subtitle="Current state of this submission.">
        <div className="submission-summary-grid">
          <div className="submission-summary-card">
            <span className="submission-summary-card__label">Verdict</span>
            <StatusPill value={submission.verdict} />
          </div>

          <div className="submission-summary-card">
            <span className="submission-summary-card__label">Status</span>
            <strong>{submission.status}</strong>
          </div>

          <div className="submission-summary-card">
            <span className="submission-summary-card__label">Language</span>
            <strong>{submission.language}</strong>
          </div>

          <div className="submission-summary-card">
            <span className="submission-summary-card__label">Execution time</span>
            <strong>{submission.execution_time_ms ?? "—"} ms</strong>
          </div>
        </div>

        <div className="meta-grid">
          <span>
            Problem: {submission.problem.code} — {submission.problem.title}
          </span>
          <span>Contest: {submission.contest.slug}</span>
          <span>
            Passed tests: {submission.passed_test_count}/{submission.total_test_count}
          </span>
          <span>Failed test: {submission.failed_test_position ?? "—"}</span>
          <span>Created: {new Date(submission.created_at).toLocaleString()}</span>
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
          <div className="auto-refresh-banner">
            <div className="auto-refresh-banner__dot" aria-hidden="true" />
            <span>
              Live updates are enabled while the submission is pending or running.
            </span>
          </div>
        ) : null}
      </Panel>

      {submission.judge_log ? (
        <Panel title="Judge log" subtitle="Technical output from the judging pipeline.">
          <pre className="plain-code-block">{submission.judge_log}</pre>
        </Panel>
      ) : (
        <Panel title="Judge log" subtitle="Technical output from the judging pipeline.">
          <EmptyState
            title="No judge log yet"
            description="The judge has not produced a log for this submission yet."
          />
        </Panel>
      )}

      <Panel title="Source code" subtitle="Submitted program text.">
        <pre className="plain-code-block">{submission.source_code}</pre>
      </Panel>
    </div>
  );
}