import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  createSubmission,
  getMySubmissions,
  getProblem,
  isApiError,
} from "../api/client";
import type {
  Problem,
  SubmissionLanguage,
  SubmissionSummary,
  User,
} from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { FormErrorList } from "../components/FormErrorList";
import { LoadingState } from "../components/LoadingState";
import { Pagination } from "../components/Pagination";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import {
  getLanguageLabel,
  getSolutionTemplate,
} from "../features/solving/codeTemplates";
import { validateSubmissionForm } from "../features/validation/forms";

interface ProblemPageProps {
  user: User | null;
}

const LANGUAGE_OPTIONS: SubmissionLanguage[] = ["python", "cpp"];
const SUBMISSIONS_PAGE_SIZE = 8;

function getDraftStorageKey(
  contestSlug: string,
  problemCode: string,
  language: SubmissionLanguage,
): string {
  return `contester:draft:${contestSlug}:${problemCode}:${language}`;
}

function getLanguageStorageKey(contestSlug: string, problemCode: string): string {
  return `contester:language:${contestSlug}:${problemCode}`;
}

function guessLanguageFromFileName(name: string): SubmissionLanguage | null {
  const lower = name.toLowerCase();

  if (lower.endsWith(".py")) {
    return "python";
  }

  if (
    lower.endsWith(".cpp") ||
    lower.endsWith(".cc") ||
    lower.endsWith(".cxx") ||
    lower.endsWith(".c++")
  ) {
    return "cpp";
  }

  return null;
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
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const [submitting, setSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const [problemSubmissions, setProblemSubmissions] = useState<SubmissionSummary[]>([]);
  const [submissionsLoading, setSubmissionsLoading] = useState(false);
  const [submissionsPage, setSubmissionsPage] = useState(1);

  const draftStorageKey = useMemo(() => {
    if (!contestSlug || !problemCode) {
      return null;
    }

    return getDraftStorageKey(contestSlug, problemCode, language);
  }, [contestSlug, problemCode, language]);

  const languageStorageKey = useMemo(() => {
    if (!contestSlug || !problemCode) {
      return null;
    }

    return getLanguageStorageKey(contestSlug, problemCode);
  }, [contestSlug, problemCode]);

  const visibleSubmissions = useMemo(() => {
    const start = (submissionsPage - 1) * SUBMISSIONS_PAGE_SIZE;
    return problemSubmissions.slice(start, start + SUBMISSIONS_PAGE_SIZE);
  }, [problemSubmissions, submissionsPage]);

  const totalSubmissionPages = Math.max(
    1,
    Math.ceil(problemSubmissions.length / SUBMISSIONS_PAGE_SIZE),
  );

  useEffect(() => {
    if (submissionsPage > totalSubmissionPages) {
      setSubmissionsPage(totalSubmissionPages);
    }
  }, [submissionsPage, totalSubmissionPages]);

  useEffect(() => {
    if (!languageStorageKey) {
      return;
    }

    const savedLanguage = window.localStorage.getItem(languageStorageKey);
    if (savedLanguage === "python" || savedLanguage === "cpp") {
      setLanguage(savedLanguage);
    }
  }, [languageStorageKey]);

  useEffect(() => {
    if (!languageStorageKey) {
      return;
    }

    window.localStorage.setItem(languageStorageKey, language);
  }, [language, languageStorageKey]);

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

  async function loadProblemSubmissions() {
    if (!contestSlug || !problemCode) {
      return;
    }

    setSubmissionsLoading(true);

    try {
      const all = await getMySubmissions();
      const filtered = all
        .filter(
          (submission) =>
            submission.contest.slug === contestSlug &&
            submission.problem.code === problemCode,
        )
        .sort(
          (left, right) =>
            new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
        );

      setProblemSubmissions(filtered);
      setSubmissionsPage(1);
    } catch (error) {
      setSubmissionError(
        isApiError(error)
          ? error.message
          : "Failed to load submissions for this problem.",
      );
    } finally {
      setSubmissionsLoading(false);
    }
  }

  useEffect(() => {
    if (!user || !contestSlug || !problemCode) {
      return;
    }

    void loadProblemSubmissions();
  }, [user, contestSlug, problemCode]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!contestSlug || !problemCode) {
      return;
    }

    const errors = validateSubmissionForm({
      language,
      sourceCode,
    });

    setValidationErrors(errors);
    setSubmissionError(null);

    if (errors.length > 0) {
      return;
    }

    setSubmitting(true);

    try {
      await createSubmission({
        contestSlug,
        problemCode,
        language,
        source_code: sourceCode,
      });

      await loadProblemSubmissions();
    } catch (error) {
      setSubmissionError(isApiError(error) ? error.message : "Failed to submit solution.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleApplyTemplate() {
    setSourceCode(getSolutionTemplate(language));
    setValidationErrors([]);
  }

  function handleClearDraft() {
    if (draftStorageKey) {
      window.localStorage.removeItem(draftStorageKey);
    }
    setSourceCode(getSolutionTemplate(language));
    setValidationErrors([]);
  }

  async function handleSourceFileSelected(
    event: React.ChangeEvent<HTMLInputElement>,
  ) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const guessedLanguage = guessLanguageFromFileName(file.name);
    const text = await file.text();

    if (guessedLanguage) {
      setLanguage(guessedLanguage);
    }

    setSourceCode(text);
    setValidationErrors([]);
    setSubmissionError(null);

    event.target.value = "";
  }

  if (!user) {
    return (
      <Panel title="Authentication required">
        <EmptyState
          title="Login required"
          description="Please log in before opening a problem statement."
        />
      </Panel>
    );
  }

  if (loading) {
    return (
      <Panel title="Problem">
        <LoadingState label="Loading problem..." />
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
        <EmptyState
          title="Problem not found"
          description="The requested problem could not be loaded."
        />
      </Panel>
    );
  }

  return (
    <div className="stack">
      <section className="page-head">
        <div>
          <span className="page-head__eyebrow">Problem</span>
          <h1 className="page-head__title">
            {problem.code} — {problem.title}
          </h1>
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
          <Panel title="Statement">
            <div className="meta-grid">
              <span>Time limit: {problem.time_limit_ms} ms</span>
              <span>Memory limit: {problem.memory_limit_mb} MB</span>
              <span>Status: {problem.status}</span>
              <span>Contest: {problem.contest.title}</span>
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

          <Panel title="Submit solution">
            <form className="form-stack" onSubmit={handleSubmit}>
              <div className="editor-toolbar editor-toolbar--row">
                <label className="field">
                  <span>Language</span>
                  <select
                    value={language}
                    onChange={(event) => {
                      setLanguage(event.target.value as SubmissionLanguage);
                      setValidationErrors([]);
                      setSubmissionError(null);
                    }}
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
                    Template
                  </button>

                  <button
                    type="button"
                    className="button button--secondary"
                    onClick={handleClearDraft}
                  >
                    Reset draft
                  </button>

                  <label className="button button--secondary file-picker-button">
                    Load file
                    <input
                      type="file"
                      accept=".py,.cpp,.cc,.cxx,.c++,.txt"
                      onChange={handleSourceFileSelected}
                      hidden
                    />
                  </label>
                </div>
              </div>

              <FormErrorList errors={validationErrors} />

              <label className="field">
                <span>Source code</span>
                <textarea
                  rows={20}
                  value={sourceCode}
                  onChange={(event) => {
                    setSourceCode(event.target.value);
                    if (validationErrors.length > 0) {
                      setValidationErrors([]);
                    }
                  }}
                  spellCheck={false}
                  className="code-area"
                />
              </label>

              <button type="submit" className="button" disabled={submitting}>
                {submitting ? "Submitting..." : `Submit ${getLanguageLabel(language)}`}
              </button>
            </form>

            {submissionError ? (
              <p className="feedback feedback--error">{submissionError}</p>
            ) : null}
          </Panel>

          <Panel
            title="My submissions for this problem"
            actions={
              <button
                type="button"
                className="button button--secondary"
                onClick={() => void loadProblemSubmissions()}
              >
                Refresh
              </button>
            }
          >
            {submissionsLoading ? (
              <LoadingState label="Loading problem submissions..." />
            ) : null}

            {!submissionsLoading && problemSubmissions.length === 0 ? (
              <EmptyState
                title="No submissions yet"
                description="Your submissions for this problem will appear here."
              />
            ) : null}

            {!submissionsLoading && visibleSubmissions.length > 0 ? (
              <>
                <div className="list-stack">
                  {visibleSubmissions.map((submission) => (
                    <article key={submission.id} className="list-card">
                      <div className="list-card__header">
                        <div>
                          <strong>{submission.id}</strong>
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
                          Passed: {submission.passed_test_count}/
                          {submission.total_test_count}
                        </span>
                        <span>Time: {submission.execution_time_ms ?? "—"} ms</span>
                      </div>

                      <div className="inline-links-row">
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

                <Pagination
                  page={submissionsPage}
                  totalPages={totalSubmissionPages}
                  onPageChange={setSubmissionsPage}
                />
              </>
            ) : null}
          </Panel>
        </div>

        <aside className="problem-layout__side">
          <Panel title="Navigation">
            <div className="hint-list">
              <Link
                to={`/contests/${problem.contest.slug}`}
                className="action-card"
              >
                <strong>Contest overview</strong>
                <span>Return to the problem list.</span>
              </Link>

              <Link
                to={`/contests/${problem.contest.slug}/standings`}
                className="action-card"
              >
                <strong>Standings</strong>
                <span>Open the current scoreboard.</span>
              </Link>
            </div>
          </Panel>
        </aside>
      </div>
    </div>
  );
}