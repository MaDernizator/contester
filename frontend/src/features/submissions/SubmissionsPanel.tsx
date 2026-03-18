import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getMySubmissions, isApiError } from "../../api/client";
import type { SubmissionSummary } from "../../api/types";
import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import { Pagination } from "../../components/Pagination";
import { Panel } from "../../components/Panel";
import { StatusPill } from "../../components/StatusPill";

const PAGE_SIZE = 10;

export function SubmissionsPanel() {
  const [submissions, setSubmissions] = useState<SubmissionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    void (async () => {
      setLoading(true);
      setErrorMessage(null);

      try {
        const data = await getMySubmissions();
        const sorted = [...data].sort(
          (left, right) =>
            new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
        );
        setSubmissions(sorted);
        setPage(1);
      } catch (error) {
        setErrorMessage(
          isApiError(error) ? error.message : "Failed to load submissions.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const totalPages = Math.max(1, Math.ceil(submissions.length / PAGE_SIZE));
  const visibleSubmissions = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return submissions.slice(start, start + PAGE_SIZE);
  }, [page, submissions]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  return (
    <Panel title="My submissions">
      {loading ? <LoadingState label="Loading submissions..." /> : null}

      {errorMessage ? <p className="feedback feedback--error">{errorMessage}</p> : null}

      {!loading && !errorMessage && submissions.length === 0 ? (
        <EmptyState
          title="No submissions yet"
          description="Your recent attempts will appear here."
        />
      ) : null}

      {!loading && !errorMessage && visibleSubmissions.length > 0 ? (
        <>
          <div className="list-stack">
            {visibleSubmissions.map((submission) => (
              <article key={submission.id} className="list-card">
                <div className="list-card__header">
                  <div>
                    <strong>
                      {submission.problem.code} — {submission.problem.title}
                    </strong>
                    <div className="muted small-text">
                      {submission.contest.slug} ·{" "}
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

                <div className="inline-links-row">
                  <Link
                    to={`/contests/${submission.contest.slug}/problems/${submission.problem.code}`}
                    className="inline-link"
                  >
                    Open problem
                  </Link>

                  <Link
                    to={`/submissions/${submission.id}`}
                    className="inline-link"
                  >
                    Open submission
                  </Link>
                </div>
              </article>
            ))}
          </div>

          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      ) : null}
    </Panel>
  );
}