import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createSubmission, getProblem, isApiError } from "../api/client";
import type { Problem, Submission, SubmissionLanguage, User } from "../api/types";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import {
  getLanguageLabel,
  getSolutionTemplate,
} from "../features/solving/codeTemplates";

interface ProblemPageProps {
  user: User | null;
}

const LANGUAGE_OPTIONS: SubmissionLanguage[] = ["python", "cpp"];

function getDraftStorageKey(
  contestSlug: string,
  problemCode: string,
  language: SubmissionLanguage,
): string {
  return `contester:draft:${contestSlug}:${problemCode}:${language}`;
}

export function ProblemPage({ user }: ProblemPageProps) {
  const { contestSlug, problemCode } = useParams<{
    contestSlug: string;
    problemCode: string;
  }>();

  const [problem, setProblem] = useState<Problem | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingError, setLoadingError] = useState<string | null>(null);

  const [language, setLanguage] = useState<SubmissionLanguage>("python");
  const [sourceCode, setSourceCode] = useState(getSolutionTemplate("python"));

  const [submitting, setSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [latestSubmission, setLatestSubmission] = useState<Submission | null>(null);

  const draftStorageKey = useMemo(() => {
    if (!contestSlug || !problemCode) {
      return null;
    }

    return getDraftStorageKey(contestSlug, problemCode, language);
  }, [contestSlug, problemCode, language]);

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

  useEffect(() => {
    if (!draftStorageKey) {
      return;
    }

    const savedDraft = window.localStorage.getItem(draftStorageKey);
    setSourceCode(savedDraft ?? getSolutionTemplate(language));
  }, [draftStorageKey, language]);

  useEffect(() => {
    if (!draftStorageKey) {
      return;
    }

    window.localStorage.setItem(draftStorageKey, sourceCode);
  }, [draftStorageKey, sourceCode]);

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
        language,
        source_code: sourceCode,
      });
      setLatestSubmission(submission);
    } catch (error) {
      setSubmissionError(isApiError(error) ? error.message : "Failed to submit solution.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleApplyTemplate() {
    setSourceCode(getSolutionTemplate(language));
  }

  function handleClearDraft() {
    if (draftStorageKey) {
      window.localStorage.removeItem(draftStorageKey);
    }
    setSourceCode(getSolutionTemplate(language));
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
      <section className="page-head">
        <div>
          <span className="page-head__eyebrow">Problem solving</span>
          <h1 className="page-head__title">
            {problem.code} — {problem.title}
          </h1>
          <p className="page-head__subtitle">
            Solve the task, keep a local draft in the browser, and submit to the
            asynchronous judge.
          </p>
        </div>

        <div className="page-actions">
          <Link
            to={`/contests/${problem.contest.slug}`}
            className="button button--secondary"
          >
            Back to contest
          </Link>
          <Link
            to={`/contests/${problem.contest.slug}/standings`}
            className="button button--secondary"
          >
            Standings
          </Link>
        </div>
      </section>

      <div className="problem-layout">
        <div className="problem-layout__main">
          <Panel title="Statement" subtitle={`Contest: ${problem.contest.title}`}>
            <div className="meta-grid">
              <span>Time limit: {problem.time_limit_ms} ms</span>
              <span>Memory limit: {problem.memory_limit_mb} MB</span>
              <span>Status: {problem.status}</span>
              <span>Language support: Python / C++</span>
            </div>

            <div className="problem-block">
              <h3>Task</h3>
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

            {problem.notes ? (
              <div className="problem-block">
                <h3>Notes</h3>
                <pre>{problem.notes}</pre>
              </div>
            ) : null}

            {(problem.sample_input || problem.sample_output) ? (
              <div className="sample-grid">
                {problem.sample_input ? (
                  <div className="sample-block">
                    <h3>Sample input</h3>
                    <pre className="plain-code-block">{problem.sample_input}</pre>
                  </div>
                ) : null}

                {problem.sample_output ? (
                  <div className="sample-block">
                    <h3>Sample output</h3>
                    <pre className="plain-code-block">{problem.sample_output}</pre>
                  </div>
                ) : null}
              </div>
            ) : null}
          </Panel>

          <Panel
            title="Submit solution"
            subtitle="Drafts are stored locally in your browser for each language."
          >
            <form className="form-stack" onSubmit={handleSubmit}>
              <div className="editor-toolbar">
                <label className="field">
                  <span>Language</span>
                  <select
                    value={language}
                    onChange={(event) =>
                      setLanguage(event.target.value as SubmissionLanguage)
                    }
                  >
                    {LANGUAGE_OPTIONS.map((item) => (
                      <option key={item} value={item}>
                        {getLanguageLabel(item)}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="editor-toolbar__actions">
                  <button
                    type="button"
                    className="button button--secondary"
                    onClick={handleApplyTemplate}
                  >
                    Apply template
                  </button>
                  <button
                    type="button"
                    className="button button--secondary"
                    onClick={handleClearDraft}
                  >
                    Reset draft
                  </button>
                </div>
              </div>

              <label className="field">
                <span>Source code</span>
                <textarea
                  rows={20}
                  value={sourceCode}
                  onChange={(event) => setSourceCode(event.target.value)}
                  spellCheck={false}
                  className="code-area"
                />
              </label>

              <div className="submission-callout">
                Submissions are processed asynchronously. After sending code, open
                the detailed submission page to watch verdict updates live.
              </div>

              <button type="submit" className="button" disabled={submitting}>
                {submitting ? "Submitting..." : `Submit ${getLanguageLabel(language)} solution`}
              </button>
            </form>

            {submissionError ? (
              <p className="feedback feedback--error">{submissionError}</p>
            ) : null}
          </Panel>

          {latestSubmission ? (
            <Panel title="Latest submission" subtitle="Most recent attempt from this page.">
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
                <span>Language: {latestSubmission.language}</span>
                <span>
                  Passed: {latestSubmission.passed_test_count}/
                  {latestSubmission.total_test_count}
                </span>
                <span>Failed test: {latestSubmission.failed_test_position ?? "—"}</span>
              </div>

              <div className="inline-links-row">
                <Link
                  to={`/submissions/${latestSubmission.id}`}
                  className="inline-link"
                >
                  Open detailed submission page
                </Link>
              </div>
            </Panel>
          ) : null}
        </div>

        <aside className="problem-layout__side">
          <Panel title="Quick guide" subtitle="Useful reminders while solving.">
            <div className="hint-list">
              <div className="hint-card">
                <strong>Drafts are local</strong>
                <span>
                  Each problem and language combination has its own browser draft.
                </span>
              </div>

              <div className="hint-card">
                <strong>Judge is asynchronous</strong>
                <span>
                  Verdicts may appear a moment later while workers process the queue.
                </span>
              </div>

              <div className="hint-card">
                <strong>Language templates</strong>
                <span>
                  Use the template button to reset the editor to a clean starter file.
                </span>
              </div>
            </div>
          </Panel>

          <Panel title="Navigation" subtitle="Move quickly around the contest.">
            <div className="hint-list">
              <Link
                to={`/contests/${problem.contest.slug}`}
                className="action-card"
              >
                <strong>Contest overview</strong>
                <span>Return to the full problem list and contest information.</span>
              </Link>

              <Link
                to={`/contests/${problem.contest.slug}/standings`}
                className="action-card"
              >
                <strong>Standings</strong>
                <span>Check current scoreboard and your relative position.</span>
              </Link>
            </div>
          </Panel>
        </aside>
      </div>
    </div>
  );
}