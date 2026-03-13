import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createSubmission, getProblem, isApiError } from "../api/client";
import type { Problem, Submission, User } from "../api/types";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";

interface ProblemPageProps {
  user: User | null;
}

const defaultPythonTemplate = `a, b = map(int, input().split())
print(a + b)
`;

export function ProblemPage({ user }: ProblemPageProps) {
  const { contestSlug, problemCode } = useParams<{
    contestSlug: string;
    problemCode: string;
  }>();

  const [problem, setProblem] = useState<Problem | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [sourceCode, setSourceCode] = useState(defaultPythonTemplate);
  const [submitting, setSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [latestSubmission, setLatestSubmission] = useState<Submission | null>(null);

  useEffect(() => {
    if (!user || !contestSlug || !problemCode) {
      return;
    }

    void (async () => {
      setLoading(true);
      setLoadingError(null);

      try {
        const data = await getProblem(contestSlug, problemCode);
        setProblem(data);
      } catch (error) {
        setLoadingError(isApiError(error) ? error.message : "Failed to load problem.");
      } finally {
        setLoading(false);
      }
    })();
  }, [contestSlug, problemCode, user]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!contestSlug || !problemCode) {
      return;
    }

    setSubmitting(true);
    setSubmissionError(null);

    try {
      const submission = await createSubmission({
        contestSlug,
        problemCode,
        language: "python",
        source_code: sourceCode,
      });
      setLatestSubmission(submission);
    } catch (error) {
      setSubmissionError(isApiError(error) ? error.message : "Failed to submit solution.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!user) {
    return (
      <Panel title="Authentication required">
        <p className="muted">Please log in first.</p>
      </Panel>
    );
  }

  if (loading) {
    return (
      <Panel title="Problem">
        <p className="muted">Loading problem...</p>
      </Panel>
    );
  }

  if (loadingError) {
    return (
      <Panel title="Problem">
        <p className="feedback feedback--error">{loadingError}</p>
      </Panel>
    );
  }

  if (!problem) {
    return (
      <Panel title="Problem">
        <p className="muted">Problem not found.</p>
      </Panel>
    );
  }

  return (
    <div className="stack">
      <Panel title={`${problem.code} — ${problem.title}`}>
        <div className="list-card__header">
          <div className="muted">Contest: {problem.contest.title}</div>
          <StatusPill value={problem.status} />
        </div>

        <div className="meta-grid">
          <span>Time limit: {problem.time_limit_ms} ms</span>
          <span>Memory limit: {problem.memory_limit_mb} MB</span>
        </div>

        <div className="problem-block">
          <h3>Statement</h3>
          <pre>{problem.statement}</pre>
        </div>

        {problem.input_specification ? (
          <div className="problem-block">
            <h3>Input specification</h3>
            <pre>{problem.input_specification}</pre>
          </div>
        ) : null}

        {problem.output_specification ? (
          <div className="problem-block">
            <h3>Output specification</h3>
            <pre>{problem.output_specification}</pre>
          </div>
        ) : null}

        {problem.sample_input ? (
          <div className="problem-block">
            <h3>Sample input</h3>
            <pre>{problem.sample_input}</pre>
          </div>
        ) : null}

        {problem.sample_output ? (
          <div className="problem-block">
            <h3>Sample output</h3>
            <pre>{problem.sample_output}</pre>
          </div>
        ) : null}

        {problem.notes ? (
          <div className="problem-block">
            <h3>Notes</h3>
            <pre>{problem.notes}</pre>
          </div>
        ) : null}
      </Panel>

      <Panel title="Submit solution">
        <form className="form-stack" onSubmit={handleSubmit}>
          <label className="field">
            <span>Source code</span>
            <textarea
              rows={18}
              value={sourceCode}
              onChange={(event) => setSourceCode(event.target.value)}
              spellCheck={false}
              className="code-area"
            />
          </label>

          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Submitting..." : "Submit solution"}
          </button>
        </form>

        {submissionError ? <p className="feedback feedback--error">{submissionError}</p> : null}
      </Panel>

      {latestSubmission ? (
        <Panel title="Latest submission">
          <div className="list-card__header">
            <div>
              <strong>Submission {latestSubmission.id}</strong>
              <div className="muted small-text">
                {new Date(latestSubmission.created_at).toLocaleString()}
              </div>
            </div>
            <StatusPill value={latestSubmission.verdict} />
          </div>

          <div className="meta-grid">
            <span>Status: {latestSubmission.status}</span>
            <span>
              Passed: {latestSubmission.passed_test_count}/{latestSubmission.total_test_count}
            </span>
            <span>Failed test: {latestSubmission.failed_test_position ?? "—"}</span>
            <span>Time: {latestSubmission.execution_time_ms ?? "—"} ms</span>
          </div>

          <div>
            <Link to={`/submissions/${latestSubmission.id}`} className="inline-link">
              Open detailed submission page
            </Link>
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
