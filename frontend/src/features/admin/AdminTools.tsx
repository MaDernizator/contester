import { useEffect, useMemo, useState } from "react";
import {
  createAdminContest,
  createAdminProblem,
  createAdminTestCase,
  getAdminContests,
  getAdminProblems,
  getAdminQueueStatus,
  getAdminTestCases,
  isApiError,
} from "../../api/client";
import type { Contest, ProblemSummary, QueueStatus, TestCaseSummary } from "../../api/types";
import { Panel } from "../../components/Panel";
import { StatusPill } from "../../components/StatusPill";

interface ContestFormState {
  title: string;
  slug: string;
  description: string;
  status: "draft" | "published" | "archived";
  starts_at: string;
  ends_at: string;
}

interface ProblemFormState {
  code: string;
  title: string;
  statement: string;
  input_specification: string;
  output_specification: string;
  notes: string;
  sample_input: string;
  sample_output: string;
  time_limit_ms: string;
  memory_limit_mb: string;
  position: string;
  status: "draft" | "published" | "archived";
}

interface TestCaseFormState {
  input_data: string;
  expected_output: string;
  position: string;
  is_sample: boolean;
  is_active: boolean;
}

const initialContestForm: ContestFormState = {
  title: "",
  slug: "",
  description: "",
  status: "published",
  starts_at: "",
  ends_at: "",
};

const initialProblemForm: ProblemFormState = {
  code: "",
  title: "",
  statement: "",
  input_specification: "",
  output_specification: "",
  notes: "",
  sample_input: "",
  sample_output: "",
  time_limit_ms: "1000",
  memory_limit_mb: "128",
  position: "",
  status: "published",
};

const initialTestCaseForm: TestCaseFormState = {
  input_data: "",
  expected_output: "",
  position: "",
  is_sample: true,
  is_active: true,
};

const initialQueueStatus: QueueStatus = {
  pending_count: 0,
  running_count: 0,
  finished_count: 0,
  oldest_pending_submission_id: null,
  oldest_pending_created_at: null,
};

export function AdminTools() {
  const [contests, setContests] = useState<Contest[]>([]);
  const [selectedContestId, setSelectedContestId] = useState("");
  const [problems, setProblems] = useState<ProblemSummary[]>([]);
  const [selectedProblemId, setSelectedProblemId] = useState("");
  const [testCases, setTestCases] = useState<TestCaseSummary[]>([]);
  const [queueStatus, setQueueStatus] = useState<QueueStatus>(initialQueueStatus);
  const [contestForm, setContestForm] = useState(initialContestForm);
  const [problemForm, setProblemForm] = useState(initialProblemForm);
  const [testCaseForm, setTestCaseForm] = useState(initialTestCaseForm);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const selectedContest = useMemo(
    () => contests.find((contest) => contest.id === selectedContestId) ?? null,
    [contests, selectedContestId],
  );

  const selectedProblem = useMemo(
    () => problems.find((problem) => problem.id === selectedProblemId) ?? null,
    [problems, selectedProblemId],
  );

  async function loadQueueStatus() {
    const queue = await getAdminQueueStatus();
    setQueueStatus(queue);
  }

  async function loadContests() {
    const contestItems = await getAdminContests();
    setContests(contestItems);

    if (contestItems.length > 0) {
      setSelectedContestId((current) =>
        contestItems.some((contest) => contest.id === current) ? current : contestItems[0].id,
      );
    } else {
      setSelectedContestId("");
      setProblems([]);
      setSelectedProblemId("");
      setTestCases([]);
    }
  }

  async function loadProblems(contestId: string) {
    if (!contestId) {
      setProblems([]);
      setSelectedProblemId("");
      setTestCases([]);
      return;
    }

    const problemItems = await getAdminProblems(contestId);
    setProblems(problemItems);

    if (problemItems.length > 0) {
      setSelectedProblemId((current) =>
        problemItems.some((problem) => problem.id === current) ? current : problemItems[0].id,
      );
    } else {
      setSelectedProblemId("");
      setTestCases([]);
    }
  }

  async function loadTestCases(problemId: string) {
    if (!problemId) {
      setTestCases([]);
      return;
    }

    const testCaseItems = await getAdminTestCases(problemId);
    setTestCases(testCaseItems);
  }

  async function bootstrap() {
    setLoading(true);
    setErrorMessage(null);

    try {
      await Promise.all([loadContests(), loadQueueStatus()]);
    } catch (error) {
      setErrorMessage(isApiError(error) ? error.message : "Failed to load admin data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void bootstrap();
  }, []);

  useEffect(() => {
    if (!selectedContestId) {
      return;
    }

    void (async () => {
      try {
        await loadProblems(selectedContestId);
      } catch (error) {
        setErrorMessage(isApiError(error) ? error.message : "Failed to load problems.");
      }
    })();
  }, [selectedContestId]);

  useEffect(() => {
    if (!selectedProblemId) {
      return;
    }

    void (async () => {
      try {
        await loadTestCases(selectedProblemId);
      } catch (error) {
        setErrorMessage(isApiError(error) ? error.message : "Failed to load test cases.");
      }
    })();
  }, [selectedProblemId]);

  async function handleCreateContest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyAction("contest");
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const created = await createAdminContest({
        title: contestForm.title,
        slug: contestForm.slug,
        description: contestForm.description || undefined,
        starts_at: contestForm.starts_at || undefined,
        ends_at: contestForm.ends_at || undefined,
        status: contestForm.status,
      });

      await loadContests();
      setSelectedContestId(created.id);
      setContestForm(initialContestForm);
      setSuccessMessage(`Contest "${created.title}" created.`);
    } catch (error) {
      setErrorMessage(isApiError(error) ? error.message : "Failed to create contest.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCreateProblem(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedContestId) {
      setErrorMessage("Select a contest before creating a problem.");
      return;
    }

    setBusyAction("problem");
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const created = await createAdminProblem({
        contestId: selectedContestId,
        code: problemForm.code,
        title: problemForm.title,
        statement: problemForm.statement,
        input_specification: problemForm.input_specification || undefined,
        output_specification: problemForm.output_specification || undefined,
        notes: problemForm.notes || undefined,
        sample_input: problemForm.sample_input || undefined,
        sample_output: problemForm.sample_output || undefined,
        time_limit_ms: Number(problemForm.time_limit_ms),
        memory_limit_mb: Number(problemForm.memory_limit_mb),
        position: problemForm.position ? Number(problemForm.position) : undefined,
        status: problemForm.status,
      });

      await loadProblems(selectedContestId);
      setSelectedProblemId(created.id);
      setProblemForm(initialProblemForm);
      setSuccessMessage(`Problem "${created.code}" created.`);
    } catch (error) {
      setErrorMessage(isApiError(error) ? error.message : "Failed to create problem.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCreateTestCase(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedProblemId) {
      setErrorMessage("Select a problem before creating a test case.");
      return;
    }

    setBusyAction("test-case");
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const created = await createAdminTestCase({
        problemId: selectedProblemId,
        input_data: testCaseForm.input_data,
        expected_output: testCaseForm.expected_output,
        position: testCaseForm.position ? Number(testCaseForm.position) : undefined,
        is_sample: testCaseForm.is_sample,
        is_active: testCaseForm.is_active,
      });

      await loadTestCases(selectedProblemId);
      setTestCaseForm(initialTestCaseForm);
      setSuccessMessage(`Test case #${created.position} created.`);
    } catch (error) {
      setErrorMessage(isApiError(error) ? error.message : "Failed to create test case.");
    } finally {
      setBusyAction(null);
    }
  }

  if (loading) {
    return (
      <Panel title="Admin tools">
        <p className="muted">Loading admin data...</p>
      </Panel>
    );
  }

  return (
    <div className="stack">
      <Panel
        title="Queue monitor"
        actions={
          <button
            type="button"
            className="button button--secondary"
            onClick={() => void loadQueueStatus()}
          >
            Refresh queue
          </button>
        }
      >
        <div className="meta-grid">
          <span>Pending: {queueStatus.pending_count}</span>
          <span>Running: {queueStatus.running_count}</span>
          <span>Finished: {queueStatus.finished_count}</span>
          <span>
            Oldest pending:{" "}
            {queueStatus.oldest_pending_created_at
              ? new Date(queueStatus.oldest_pending_created_at).toLocaleString()
              : "—"}
          </span>
        </div>

        {queueStatus.oldest_pending_submission_id ? (
          <p className="muted small-text">
            Oldest pending submission ID: {queueStatus.oldest_pending_submission_id}
          </p>
        ) : (
          <p className="muted small-text">Queue is empty right now.</p>
        )}
      </Panel>

      <Panel title="Admin tools">
        <p className="muted">
          This section is intentionally simple. It exists to speed up local manual testing.
        </p>
        {errorMessage ? <p className="feedback feedback--error">{errorMessage}</p> : null}
        {successMessage ? <p className="feedback feedback--success">{successMessage}</p> : null}
      </Panel>

      <div className="two-column-grid">
        <Panel title="Create contest">
          <form className="form-stack" onSubmit={handleCreateContest}>
            <label className="field">
              <span>Title</span>
              <input
                value={contestForm.title}
                onChange={(event) =>
                  setContestForm((current) => ({ ...current, title: event.target.value }))
                }
              />
            </label>

            <label className="field">
              <span>Slug</span>
              <input
                value={contestForm.slug}
                onChange={(event) =>
                  setContestForm((current) => ({ ...current, slug: event.target.value }))
                }
                placeholder="spring-camp-2026"
              />
            </label>

            <label className="field">
              <span>Description</span>
              <textarea
                rows={3}
                value={contestForm.description}
                onChange={(event) =>
                  setContestForm((current) => ({ ...current, description: event.target.value }))
                }
              />
            </label>

            <label className="field">
              <span>Status</span>
              <select
                value={contestForm.status}
                onChange={(event) =>
                  setContestForm((current) => ({
                    ...current,
                    status: event.target.value as ContestFormState["status"],
                  }))
                }
              >
                <option value="draft">draft</option>
                <option value="published">published</option>
                <option value="archived">archived</option>
              </select>
            </label>

            <label className="field">
              <span>Starts at (ISO 8601, optional)</span>
              <input
                value={contestForm.starts_at}
                onChange={(event) =>
                  setContestForm((current) => ({ ...current, starts_at: event.target.value }))
                }
                placeholder="2026-03-20T10:00:00Z"
              />
            </label>

            <label className="field">
              <span>Ends at (ISO 8601, optional)</span>
              <input
                value={contestForm.ends_at}
                onChange={(event) =>
                  setContestForm((current) => ({ ...current, ends_at: event.target.value }))
                }
                placeholder="2026-03-20T15:00:00Z"
              />
            </label>

            <button type="submit" className="button" disabled={busyAction !== null}>
              {busyAction === "contest" ? "Creating..." : "Create contest"}
            </button>
          </form>
        </Panel>

        <Panel title="Admin contests">
          {contests.length === 0 ? (
            <p className="muted">No contests yet.</p>
          ) : (
            <div className="list-stack">
              {contests.map((contest) => (
                <button
                  key={contest.id}
                  type="button"
                  className={`selectable-card ${contest.id === selectedContestId ? "selectable-card--active" : ""}`}
                  onClick={() => setSelectedContestId(contest.id)}
                >
                  <div className="list-card__header">
                    <div>
                      <strong>{contest.title}</strong>
                      <div className="muted small-text">{contest.slug}</div>
                    </div>
                    <StatusPill value={contest.status} />
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="two-column-grid">
        <Panel title="Create problem">
          <form className="form-stack" onSubmit={handleCreateProblem}>
            <label className="field">
              <span>Contest</span>
              <select
                value={selectedContestId}
                onChange={(event) => setSelectedContestId(event.target.value)}
              >
                <option value="">Select contest</option>
                {contests.map((contest) => (
                  <option key={contest.id} value={contest.id}>
                    {contest.title}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Code</span>
              <input
                value={problemForm.code}
                onChange={(event) =>
                  setProblemForm((current) => ({ ...current, code: event.target.value }))
                }
                placeholder="A"
              />
            </label>

            <label className="field">
              <span>Title</span>
              <input
                value={problemForm.title}
                onChange={(event) =>
                  setProblemForm((current) => ({ ...current, title: event.target.value }))
                }
              />
            </label>

            <label className="field">
              <span>Statement</span>
              <textarea
                rows={6}
                value={problemForm.statement}
                onChange={(event) =>
                  setProblemForm((current) => ({ ...current, statement: event.target.value }))
                }
              />
            </label>

            <label className="field">
              <span>Input specification</span>
              <textarea
                rows={3}
                value={problemForm.input_specification}
                onChange={(event) =>
                  setProblemForm((current) => ({
                    ...current,
                    input_specification: event.target.value,
                  }))
                }
              />
            </label>

            <label className="field">
              <span>Output specification</span>
              <textarea
                rows={3}
                value={problemForm.output_specification}
                onChange={(event) =>
                  setProblemForm((current) => ({
                    ...current,
                    output_specification: event.target.value,
                  }))
                }
              />
            </label>

            <label className="field">
              <span>Sample input</span>
              <textarea
                rows={3}
                value={problemForm.sample_input}
                onChange={(event) =>
                  setProblemForm((current) => ({ ...current, sample_input: event.target.value }))
                }
              />
            </label>

            <label className="field">
              <span>Sample output</span>
              <textarea
                rows={3}
                value={problemForm.sample_output}
                onChange={(event) =>
                  setProblemForm((current) => ({ ...current, sample_output: event.target.value }))
                }
              />
            </label>

            <div className="two-column-grid">
              <label className="field">
                <span>Time limit (ms)</span>
                <input
                  type="number"
                  min={100}
                  value={problemForm.time_limit_ms}
                  onChange={(event) =>
                    setProblemForm((current) => ({
                      ...current,
                      time_limit_ms: event.target.value,
                    }))
                  }
                />
              </label>

              <label className="field">
                <span>Memory limit (MB)</span>
                <input
                  type="number"
                  min={16}
                  value={problemForm.memory_limit_mb}
                  onChange={(event) =>
                    setProblemForm((current) => ({
                      ...current,
                      memory_limit_mb: event.target.value,
                    }))
                  }
                />
              </label>
            </div>

            <div className="two-column-grid">
              <label className="field">
                <span>Position (optional)</span>
                <input
                  type="number"
                  min={1}
                  value={problemForm.position}
                  onChange={(event) =>
                    setProblemForm((current) => ({ ...current, position: event.target.value }))
                  }
                />
              </label>

              <label className="field">
                <span>Status</span>
                <select
                  value={problemForm.status}
                  onChange={(event) =>
                    setProblemForm((current) => ({
                      ...current,
                      status: event.target.value as ProblemFormState["status"],
                    }))
                  }
                >
                  <option value="draft">draft</option>
                  <option value="published">published</option>
                  <option value="archived">archived</option>
                </select>
              </label>
            </div>

            <button type="submit" className="button" disabled={busyAction !== null}>
              {busyAction === "problem" ? "Creating..." : "Create problem"}
            </button>
          </form>
        </Panel>

        <Panel title={`Problems${selectedContest ? ` in "${selectedContest.title}"` : ""}`}>
          {!selectedContest ? (
            <p className="muted">Select a contest first.</p>
          ) : problems.length === 0 ? (
            <p className="muted">No problems in this contest yet.</p>
          ) : (
            <div className="list-stack">
              {problems.map((problem) => (
                <button
                  key={problem.id}
                  type="button"
                  className={`selectable-card ${problem.id === selectedProblemId ? "selectable-card--active" : ""}`}
                  onClick={() => setSelectedProblemId(problem.id)}
                >
                  <div className="list-card__header">
                    <div>
                      <strong>
                        {problem.code} — {problem.title}
                      </strong>
                      <div className="muted small-text">Position: {problem.position}</div>
                    </div>
                    <StatusPill value={problem.status} />
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="two-column-grid">
        <Panel title="Create test case">
          <form className="form-stack" onSubmit={handleCreateTestCase}>
            <label className="field">
              <span>Problem</span>
              <select
                value={selectedProblemId}
                onChange={(event) => setSelectedProblemId(event.target.value)}
              >
                <option value="">Select problem</option>
                {problems.map((problem) => (
                  <option key={problem.id} value={problem.id}>
                    {problem.code} — {problem.title}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Input data</span>
              <textarea
                rows={4}
                value={testCaseForm.input_data}
                onChange={(event) =>
                  setTestCaseForm((current) => ({ ...current, input_data: event.target.value }))
                }
              />
            </label>

            <label className="field">
              <span>Expected output</span>
              <textarea
                rows={4}
                value={testCaseForm.expected_output}
                onChange={(event) =>
                  setTestCaseForm((current) => ({
                    ...current,
                    expected_output: event.target.value,
                  }))
                }
              />
            </label>

            <label className="field">
              <span>Position (optional)</span>
              <input
                type="number"
                min={1}
                value={testCaseForm.position}
                onChange={(event) =>
                  setTestCaseForm((current) => ({ ...current, position: event.target.value }))
                }
              />
            </label>

            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={testCaseForm.is_sample}
                onChange={(event) =>
                  setTestCaseForm((current) => ({ ...current, is_sample: event.target.checked }))
                }
              />
              <span>Sample test</span>
            </label>

            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={testCaseForm.is_active}
                onChange={(event) =>
                  setTestCaseForm((current) => ({ ...current, is_active: event.target.checked }))
                }
              />
              <span>Active</span>
            </label>

            <button type="submit" className="button" disabled={busyAction !== null}>
              {busyAction === "test-case" ? "Creating..." : "Create test case"}
            </button>
          </form>
        </Panel>

        <Panel title={`Test cases${selectedProblem ? ` for ${selectedProblem.code}` : ""}`}>
          {!selectedProblem ? (
            <p className="muted">Select a problem first.</p>
          ) : testCases.length === 0 ? (
            <p className="muted">No test cases yet.</p>
          ) : (
            <div className="list-stack">
              {testCases.map((testCase) => (
                <article key={testCase.id} className="list-card">
                  <div className="list-card__header">
                    <div>
                      <strong>Test #{testCase.position}</strong>
                      <div className="muted small-text">
                        {testCase.is_sample ? "sample" : "hidden"} ·{" "}
                        {testCase.is_active ? "active" : "inactive"}
                      </div>
                    </div>
                    <StatusPill value={testCase.is_active ? "active" : "inactive"} />
                  </div>
                </article>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
