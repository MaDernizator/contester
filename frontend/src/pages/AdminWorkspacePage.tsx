import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  createAdminContest,
  createAdminProblem,
  createAdminTestCase,
  getAdminContests,
  getAdminProblem,
  getAdminProblems,
  getAdminQueueStatus,
  getAdminSubmissions,
  getAdminTestCase,
  getAdminTestCases,
  isApiError,
  rejudgeAdminSubmission,
  updateAdminContest,
  updateAdminProblem,
  updateAdminTestCase,
} from "../api/client";
import type {
  Contest,
  Problem,
  ProblemSummary,
  QueueStatus,
  SubmissionSummary,
  TestCase,
  TestCaseSummary,
  User,
} from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { FormErrorList } from "../components/FormErrorList";
import { LoadingState } from "../components/LoadingState";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import {
  validateContestForm,
  validateProblemForm,
  validateTestCaseForm,
} from "../features/validation/forms";

interface AdminWorkspacePageProps {
  user: User | null;
}

type AdminTab =
  | "overview"
  | "contests"
  | "problems"
  | "test-cases"
  | "submissions";

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

interface SubmissionFilterState {
  contest_slug: string;
  problem_code: string;
  username: string;
  language: string;
  status: string;
  verdict: string;
}

const STORAGE_KEYS = {
  tab: "contester:admin:tab",
  contestId: "contester:admin:selectedContestId",
  problemId: "contester:admin:selectedProblemId",
  testCaseId: "contester:admin:selectedTestCaseId",
  submissionFilters: "contester:admin:submissionFilters",
};

const initialQueueStatus: QueueStatus = {
  pending_count: 0,
  running_count: 0,
  finished_count: 0,
  oldest_pending_submission_id: null,
  oldest_pending_created_at: null,
};

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
  position: "1",
  status: "published",
};

const initialTestCaseForm: TestCaseFormState = {
  input_data: "",
  expected_output: "",
  position: "1",
  is_sample: true,
  is_active: true,
};

const initialSubmissionFilters: SubmissionFilterState = {
  contest_slug: "",
  problem_code: "",
  username: "",
  language: "",
  status: "",
  verdict: "",
};

function contestToForm(contest: Contest): ContestFormState {
  return {
    title: contest.title,
    slug: contest.slug,
    description: contest.description ?? "",
    status: contest.status,
    starts_at: contest.starts_at ?? "",
    ends_at: contest.ends_at ?? "",
  };
}

function problemToForm(problem: Problem): ProblemFormState {
  return {
    code: problem.code,
    title: problem.title,
    statement: problem.statement,
    input_specification: problem.input_specification ?? "",
    output_specification: problem.output_specification ?? "",
    notes: problem.notes ?? "",
    sample_input: problem.sample_input ?? "",
    sample_output: problem.sample_output ?? "",
    time_limit_ms: String(problem.time_limit_ms),
    memory_limit_mb: String(problem.memory_limit_mb),
    position: String(problem.position),
    status: problem.status,
  };
}

function testCaseToForm(testCase: TestCase): TestCaseFormState {
  return {
    input_data: testCase.input_data,
    expected_output: testCase.expected_output,
    position: String(testCase.position),
    is_sample: testCase.is_sample,
    is_active: testCase.is_active,
  };
}

function readStorageValue(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(key);
}

function writeStorageValue(key: string, value: string) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(key, value);
}

function removeStorageValue(key: string) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(key);
}

function readStoredTab(): AdminTab {
  const value = readStorageValue(STORAGE_KEYS.tab);

  if (
    value === "overview" ||
    value === "contests" ||
    value === "problems" ||
    value === "test-cases" ||
    value === "submissions"
  ) {
    return value;
  }

  return "overview";
}

function readStoredSubmissionFilters(): SubmissionFilterState {
  try {
    const raw = readStorageValue(STORAGE_KEYS.submissionFilters);
    if (!raw) {
      return initialSubmissionFilters;
    }

    const parsed = JSON.parse(raw) as Partial<SubmissionFilterState>;
    return {
      contest_slug: parsed.contest_slug ?? "",
      problem_code: parsed.problem_code ?? "",
      username: parsed.username ?? "",
      language: parsed.language ?? "",
      status: parsed.status ?? "",
      verdict: parsed.verdict ?? "",
    };
  } catch {
    return initialSubmissionFilters;
  }
}

export function AdminWorkspacePage({ user }: AdminWorkspacePageProps) {
  const [activeTab, setActiveTab] = useState<AdminTab>(() => readStoredTab());

  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const [queueStatus, setQueueStatus] = useState<QueueStatus>(initialQueueStatus);

  const [contests, setContests] = useState<Contest[]>([]);
  const [selectedContestId, setSelectedContestId] = useState(
    () => readStorageValue(STORAGE_KEYS.contestId) ?? "",
  );
  const [createContestForm, setCreateContestForm] = useState(initialContestForm);
  const [editContestForm, setEditContestForm] = useState(initialContestForm);

  const [problems, setProblems] = useState<ProblemSummary[]>([]);
  const [selectedProblemId, setSelectedProblemId] = useState(
    () => readStorageValue(STORAGE_KEYS.problemId) ?? "",
  );
  const [selectedProblem, setSelectedProblem] = useState<Problem | null>(null);
  const [createProblemForm, setCreateProblemForm] = useState(initialProblemForm);
  const [editProblemForm, setEditProblemForm] = useState(initialProblemForm);

  const [testCases, setTestCases] = useState<TestCaseSummary[]>([]);
  const [selectedTestCaseId, setSelectedTestCaseId] = useState(
    () => readStorageValue(STORAGE_KEYS.testCaseId) ?? "",
  );
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null);
  const [createTestCaseForm, setCreateTestCaseForm] = useState(initialTestCaseForm);
  const [editTestCaseForm, setEditTestCaseForm] = useState(initialTestCaseForm);

  const [submissionFilters, setSubmissionFilters] = useState<SubmissionFilterState>(
    () => readStoredSubmissionFilters(),
  );
  const [submissions, setSubmissions] = useState<SubmissionSummary[]>([]);
  const [submissionsLoading, setSubmissionsLoading] = useState(false);

  const [contestFormErrors, setContestFormErrors] = useState<string[]>([]);
  const [contestEditErrors, setContestEditErrors] = useState<string[]>([]);
  const [problemFormErrors, setProblemFormErrors] = useState<string[]>([]);
  const [problemEditErrors, setProblemEditErrors] = useState<string[]>([]);
  const [testCaseFormErrors, setTestCaseFormErrors] = useState<string[]>([]);
  const [testCaseEditErrors, setTestCaseEditErrors] = useState<string[]>([]);

  const selectedContest = useMemo(
    () => contests.find((contest) => contest.id === selectedContestId) ?? null,
    [contests, selectedContestId],
  );

  const selectedProblemSummary = useMemo(
    () => problems.find((problem) => problem.id === selectedProblemId) ?? null,
    [problems, selectedProblemId],
  );

  const selectedTestCaseSummary = useMemo(
    () => testCases.find((testCase) => testCase.id === selectedTestCaseId) ?? null,
    [testCases, selectedTestCaseId],
  );

  const queueHasActiveWork =
    queueStatus.pending_count > 0 || queueStatus.running_count > 0;

  useEffect(() => {
    writeStorageValue(STORAGE_KEYS.tab, activeTab);
  }, [activeTab]);

  useEffect(() => {
    if (selectedContestId) {
      writeStorageValue(STORAGE_KEYS.contestId, selectedContestId);
    } else {
      removeStorageValue(STORAGE_KEYS.contestId);
    }
  }, [selectedContestId]);

  useEffect(() => {
    if (selectedProblemId) {
      writeStorageValue(STORAGE_KEYS.problemId, selectedProblemId);
    } else {
      removeStorageValue(STORAGE_KEYS.problemId);
    }
  }, [selectedProblemId]);

  useEffect(() => {
    if (selectedTestCaseId) {
      writeStorageValue(STORAGE_KEYS.testCaseId, selectedTestCaseId);
    } else {
      removeStorageValue(STORAGE_KEYS.testCaseId);
    }
  }, [selectedTestCaseId]);

  useEffect(() => {
    writeStorageValue(
      STORAGE_KEYS.submissionFilters,
      JSON.stringify(submissionFilters),
    );
  }, [submissionFilters]);

  const loadQueueStatus = useCallback(async () => {
    const data = await getAdminQueueStatus();
    setQueueStatus(data);
  }, []);

  const loadContests = useCallback(async () => {
    const data = await getAdminContests();
    setContests(data);

    setSelectedContestId((current) => {
      if (data.length === 0) {
        return "";
      }
      return data.some((contest) => contest.id === current) ? current : data[0].id;
    });
  }, []);

  const loadProblems = useCallback(async (contestId: string) => {
    if (!contestId) {
      setProblems([]);
      setSelectedProblemId("");
      return;
    }

    const data = await getAdminProblems(contestId);
    setProblems(data);

    setSelectedProblemId((current) => {
      if (data.length === 0) {
        return "";
      }
      return data.some((problem) => problem.id === current) ? current : data[0].id;
    });
  }, []);

  const loadProblemDetail = useCallback(async (problemId: string) => {
    if (!problemId) {
      setSelectedProblem(null);
      setEditProblemForm(initialProblemForm);
      return;
    }

    const data = await getAdminProblem(problemId);
    setSelectedProblem(data);
    setEditProblemForm(problemToForm(data));
  }, []);

  const loadTestCases = useCallback(async (problemId: string) => {
    if (!problemId) {
      setTestCases([]);
      setSelectedTestCaseId("");
      return;
    }

    const data = await getAdminTestCases(problemId);
    setTestCases(data);

    setSelectedTestCaseId((current) => {
      if (data.length === 0) {
        return "";
      }
      return data.some((testCase) => testCase.id === current) ? current : data[0].id;
    });
  }, []);

  const loadTestCaseDetail = useCallback(async (testCaseId: string) => {
    if (!testCaseId) {
      setSelectedTestCase(null);
      setEditTestCaseForm(initialTestCaseForm);
      return;
    }

    const data = await getAdminTestCase(testCaseId);
    setSelectedTestCase(data);
    setEditTestCaseForm(testCaseToForm(data));
  }, []);

  const loadSubmissions = useCallback(async (filters: SubmissionFilterState) => {
    setSubmissionsLoading(true);

    try {
      const data = await getAdminSubmissions(filters);
      setSubmissions(data);
    } finally {
      setSubmissionsLoading(false);
    }
  }, []);

  async function bootstrap() {
    setLoading(true);
    setErrorMessage(null);

    try {
      await Promise.all([
        loadContests(),
        loadQueueStatus(),
        loadSubmissions(submissionFilters),
      ]);
    } catch (error) {
      setErrorMessage(
        isApiError(error) ? error.message : "Failed to load admin workspace.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!user || user.role !== "admin") {
      return;
    }

    void bootstrap();
  }, [user]);

  useEffect(() => {
    if (!selectedContest) {
      setEditContestForm(initialContestForm);
      setProblems([]);
      setSelectedProblemId("");
      return;
    }

    setEditContestForm(contestToForm(selectedContest));

    void (async () => {
      try {
        await loadProblems(selectedContest.id);
      } catch (error) {
        setErrorMessage(
          isApiError(error) ? error.message : "Failed to load problems.",
        );
      }
    })();
  }, [selectedContest, loadProblems]);

  useEffect(() => {
    if (!selectedProblemId) {
      setSelectedProblem(null);
      setEditProblemForm(initialProblemForm);
      setTestCases([]);
      setSelectedTestCaseId("");
      return;
    }

    void (async () => {
      try {
        await Promise.all([
          loadProblemDetail(selectedProblemId),
          loadTestCases(selectedProblemId),
        ]);
      } catch (error) {
        setErrorMessage(
          isApiError(error) ? error.message : "Failed to load problem details.",
        );
      }
    })();
  }, [selectedProblemId, loadProblemDetail, loadTestCases]);

  useEffect(() => {
    if (!selectedTestCaseId) {
      setSelectedTestCase(null);
      setEditTestCaseForm(initialTestCaseForm);
      return;
    }

    void (async () => {
      try {
        await loadTestCaseDetail(selectedTestCaseId);
      } catch (error) {
        setErrorMessage(
          isApiError(error) ? error.message : "Failed to load test case details.",
        );
      }
    })();
  }, [selectedTestCaseId, loadTestCaseDetail]);

  async function handleCreateContest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyAction("create-contest");
    setErrorMessage(null);
    setSuccessMessage(null);

    const errors = validateContestForm(createContestForm);
    setContestFormErrors(errors);

    if (errors.length > 0) {
      setBusyAction(null);
      return;
    }

    try {
      const created = await createAdminContest({
        title: createContestForm.title,
        slug: createContestForm.slug,
        description: createContestForm.description || undefined,
        starts_at: createContestForm.starts_at || undefined,
        ends_at: createContestForm.ends_at || undefined,
        status: createContestForm.status,
      });

      await loadContests();
      setSelectedContestId(created.id);
      setCreateContestForm(initialContestForm);
      setContestFormErrors([]);
      setSuccessMessage(`Contest "${created.title}" created.`);
      setActiveTab("contests");
    } catch (error) {
      setErrorMessage(
        isApiError(error) ? error.message : "Failed to create contest.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleUpdateContest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedContestId) {
      return;
    }

    setBusyAction("update-contest");
    setErrorMessage(null);
    setSuccessMessage(null);

    const errors = validateContestForm(editContestForm);
    setContestEditErrors(errors);

    if (errors.length > 0) {
      setBusyAction(null);
      return;
    }

    try {
      await updateAdminContest(selectedContestId, {
        title: editContestForm.title,
        slug: editContestForm.slug,
        description: editContestForm.description || null,
        starts_at: editContestForm.starts_at || null,
        ends_at: editContestForm.ends_at || null,
        status: editContestForm.status,
      });

      await loadContests();
      setContestEditErrors([]);
      setSuccessMessage(`Contest "${editContestForm.title}" updated.`);
    } catch (error) {
      setErrorMessage(
        isApiError(error) ? error.message : "Failed to update contest.",
      );
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

    setBusyAction("create-problem");
    setErrorMessage(null);
    setSuccessMessage(null);

    const errors = validateProblemForm(createProblemForm);
    setProblemFormErrors(errors);

    if (errors.length > 0) {
      setBusyAction(null);
      return;
    }

    try {
      const created = await createAdminProblem({
        contestId: selectedContestId,
        code: createProblemForm.code,
        title: createProblemForm.title,
        statement: createProblemForm.statement,
        input_specification: createProblemForm.input_specification || undefined,
        output_specification: createProblemForm.output_specification || undefined,
        notes: createProblemForm.notes || undefined,
        sample_input: createProblemForm.sample_input || undefined,
        sample_output: createProblemForm.sample_output || undefined,
        time_limit_ms: Number(createProblemForm.time_limit_ms),
        memory_limit_mb: Number(createProblemForm.memory_limit_mb),
        position: Number(createProblemForm.position),
        status: createProblemForm.status,
      });

      await loadProblems(selectedContestId);
      setSelectedProblemId(created.id);
      setCreateProblemForm(initialProblemForm);
      setProblemFormErrors([]);
      setSuccessMessage(`Problem "${created.code}" created.`);
      setActiveTab("problems");
    } catch (error) {
      setErrorMessage(
        isApiError(error) ? error.message : "Failed to create problem.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleUpdateProblem(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProblemId) {
      return;
    }

    setBusyAction("update-problem");
    setErrorMessage(null);
    setSuccessMessage(null);

    const errors = validateProblemForm(editProblemForm);
    setProblemEditErrors(errors);

    if (errors.length > 0) {
      setBusyAction(null);
      return;
    }

    try {
      await updateAdminProblem(selectedProblemId, {
        code: editProblemForm.code,
        title: editProblemForm.title,
        statement: editProblemForm.statement,
        input_specification: editProblemForm.input_specification || null,
        output_specification: editProblemForm.output_specification || null,
        notes: editProblemForm.notes || null,
        sample_input: editProblemForm.sample_input || null,
        sample_output: editProblemForm.sample_output || null,
        time_limit_ms: Number(editProblemForm.time_limit_ms),
        memory_limit_mb: Number(editProblemForm.memory_limit_mb),
        position: Number(editProblemForm.position),
        status: editProblemForm.status,
      });

      await loadProblems(selectedContestId);
      await loadProblemDetail(selectedProblemId);
      setProblemEditErrors([]);
      setSuccessMessage(`Problem "${editProblemForm.code}" updated.`);
    } catch (error) {
      setErrorMessage(
        isApiError(error) ? error.message : "Failed to update problem.",
      );
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

    setBusyAction("create-test-case");
    setErrorMessage(null);
    setSuccessMessage(null);

    const errors = validateTestCaseForm(createTestCaseForm);
    setTestCaseFormErrors(errors);

    if (errors.length > 0) {
      setBusyAction(null);
      return;
    }

    try {
      const created = await createAdminTestCase({
        problemId: selectedProblemId,
        input_data: createTestCaseForm.input_data,
        expected_output: createTestCaseForm.expected_output,
        position: Number(createTestCaseForm.position),
        is_sample: createTestCaseForm.is_sample,
        is_active: createTestCaseForm.is_active,
      });

      await loadTestCases(selectedProblemId);
      setSelectedTestCaseId(created.id);
      setCreateTestCaseForm(initialTestCaseForm);
      setTestCaseFormErrors([]);
      setSuccessMessage(`Test case #${created.position} created.`);
      setActiveTab("test-cases");
    } catch (error) {
      setErrorMessage(
        isApiError(error) ? error.message : "Failed to create test case.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleUpdateTestCase(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTestCaseId) {
      return;
    }

    setBusyAction("update-test-case");
    setErrorMessage(null);
    setSuccessMessage(null);

    const errors = validateTestCaseForm(editTestCaseForm);
    setTestCaseEditErrors(errors);

    if (errors.length > 0) {
      setBusyAction(null);
      return;
    }

    try {
      await updateAdminTestCase(selectedTestCaseId, {
        input_data: editTestCaseForm.input_data,
        expected_output: editTestCaseForm.expected_output,
        position: Number(editTestCaseForm.position),
        is_sample: editTestCaseForm.is_sample,
        is_active: editTestCaseForm.is_active,
      });

      await loadTestCases(selectedProblemId);
      await loadTestCaseDetail(selectedTestCaseId);
      setTestCaseEditErrors([]);
      setSuccessMessage(`Test case #${editTestCaseForm.position} updated.`);
    } catch (error) {
      setErrorMessage(
        isApiError(error) ? error.message : "Failed to update test case.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleApplySubmissionFilters(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    setErrorMessage(null);

    try {
      await loadSubmissions(submissionFilters);
      setActiveTab("submissions");
    } catch (error) {
      setErrorMessage(
        isApiError(error) ? error.message : "Failed to load submissions.",
      );
    }
  }

  async function handleClearSubmissionFilters() {
    setSubmissionFilters(initialSubmissionFilters);
    setErrorMessage(null);

    try {
      await loadSubmissions(initialSubmissionFilters);
    } catch (error) {
      setErrorMessage(
        isApiError(error) ? error.message : "Failed to load submissions.",
      );
    }
  }

  async function handleRejudge(submissionId: string) {
    setBusyAction(`rejudge-${submissionId}`);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await rejudgeAdminSubmission(submissionId);
      await Promise.all([loadSubmissions(submissionFilters), loadQueueStatus()]);
      setSuccessMessage(`Submission ${submissionId} was queued for rejudge.`);
    } catch (error) {
      setErrorMessage(
        isApiError(error) ? error.message : "Failed to rejudge submission.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  if (!user) {
    return (
      <Panel title="Authentication required">
        <EmptyState
          title="Login required"
          description="Please log in first."
        />
      </Panel>
    );
  }

  if (user.role !== "admin") {
    return (
      <Panel title="Access denied">
        <p className="feedback feedback--error">
          Only admins can access the workspace.
        </p>
      </Panel>
    );
  }

  if (loading) {
    return (
      <Panel title="Admin workspace" subtitle="Loading organizer tools.">
        <LoadingState label="Loading organizer tools..." />
      </Panel>
    );
  }

  return (
    <div className="stack">
      <section className="page-head">
        <div>
          <span className="page-head__eyebrow">Organizer tools</span>
          <h1 className="page-head__title">Admin workspace</h1>
          <p className="page-head__subtitle">
            Manage contest content, inspect judge activity, and operate the
            submission pipeline from one place.
          </p>
        </div>
      </section>

      {errorMessage ? <p className="feedback feedback--error">{errorMessage}</p> : null}
      {successMessage ? (
        <p className="feedback feedback--success">{successMessage}</p>
      ) : null}

      <Panel
        title="Workspace navigation"
        subtitle="Choose an area of responsibility."
      >
        <div className="admin-tabs">
          <button
            type="button"
            className={`admin-tab ${activeTab === "overview" ? "admin-tab--active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            Overview
          </button>
          <button
            type="button"
            className={`admin-tab ${activeTab === "contests" ? "admin-tab--active" : ""}`}
            onClick={() => setActiveTab("contests")}
          >
            Contests
          </button>
          <button
            type="button"
            className={`admin-tab ${activeTab === "problems" ? "admin-tab--active" : ""}`}
            onClick={() => setActiveTab("problems")}
          >
            Problems
          </button>
          <button
            type="button"
            className={`admin-tab ${activeTab === "test-cases" ? "admin-tab--active" : ""}`}
            onClick={() => setActiveTab("test-cases")}
          >
            Test cases
          </button>
          <button
            type="button"
            className={`admin-tab ${activeTab === "submissions" ? "admin-tab--active" : ""}`}
            onClick={() => setActiveTab("submissions")}
          >
            Submissions
          </button>
        </div>
      </Panel>

      {activeTab === "overview" ? (
        <div className="workspace-grid">
          <div className="workspace-grid__main">
            <Panel
              title="Judge queue"
              subtitle="Operational overview of the asynchronous judging pipeline."
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
              <div className="stats-grid stats-grid--compact">
                <div className="stat-card">
                  <span className="stat-card__label">Pending</span>
                  <strong className="stat-card__value">{queueStatus.pending_count}</strong>
                </div>
                <div className="stat-card">
                  <span className="stat-card__label">Running</span>
                  <strong className="stat-card__value">{queueStatus.running_count}</strong>
                </div>
                <div className="stat-card">
                  <span className="stat-card__label">Finished</span>
                  <strong className="stat-card__value">{queueStatus.finished_count}</strong>
                </div>
                <div className="stat-card">
                  <span className="stat-card__label">Oldest pending</span>
                  <strong className="stat-card__value stat-card__value--small">
                    {queueStatus.oldest_pending_created_at
                      ? new Date(queueStatus.oldest_pending_created_at).toLocaleString()
                      : "—"}
                  </strong>
                </div>
              </div>

              {queueHasActiveWork ? (
                <p className="muted small-text">
                  The judge queue currently has active work in progress.
                </p>
              ) : null}
            </Panel>

            <Panel
              title="Current selection"
              subtitle="The workspace remembers these entities between page reloads."
            >
              <div className="hint-list">
                <div className="hint-card">
                  <strong>Contest</strong>
                  <span>
                    {selectedContest
                      ? `${selectedContest.title} (${selectedContest.slug})`
                      : "Not selected"}
                  </span>
                </div>
                <div className="hint-card">
                  <strong>Problem</strong>
                  <span>
                    {selectedProblemSummary
                      ? `${selectedProblemSummary.code} — ${selectedProblemSummary.title}`
                      : "Not selected"}
                  </span>
                </div>
                <div className="hint-card">
                  <strong>Test case</strong>
                  <span>
                    {selectedTestCaseSummary
                      ? `#${selectedTestCaseSummary.position}`
                      : "Not selected"}
                  </span>
                </div>
              </div>
            </Panel>
          </div>

          <div className="workspace-grid__side">
            <Panel
              title="Recommended flow"
              subtitle="Typical organizer workflow inside the system."
            >
              <div className="hint-list">
                <div className="hint-card">
                  <strong>1. Prepare contest</strong>
                  <span>Create or edit a contest and define its publication status.</span>
                </div>
                <div className="hint-card">
                  <strong>2. Add problems</strong>
                  <span>Fill statements, constraints, samples, and metadata.</span>
                </div>
                <div className="hint-card">
                  <strong>3. Configure tests</strong>
                  <span>Build visible and hidden cases for each problem.</span>
                </div>
                <div className="hint-card">
                  <strong>4. Monitor submissions</strong>
                  <span>Inspect verdicts, queue load, and rejudge when needed.</span>
                </div>
              </div>
            </Panel>
          </div>
        </div>
      ) : null}

      {activeTab === "contests" ? (
        <Panel
          title="Contests"
          subtitle="Select an existing contest or create a new one."
          actions={
            <button
              type="button"
              className="button button--secondary"
              onClick={() => void loadContests()}
            >
              Reload contests
            </button>
          }
        >
          <div className="workspace-two-column">
            <div className="list-stack">
              {contests.length === 0 ? (
                <EmptyState
                  title="No contests yet"
                  description="Create the first contest to start building the event."
                />
              ) : (
                contests.map((contest) => (
                  <button
                    key={contest.id}
                    type="button"
                    className={`selectable-card ${
                      contest.id === selectedContestId
                        ? "selectable-card--active"
                        : ""
                    }`}
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
                ))
              )}
            </div>

            <div className="stack">
              <Panel title="Create contest" subtitle="Add a new contest entity.">
                <FormErrorList errors={contestFormErrors} />

                <form className="form-stack" onSubmit={handleCreateContest}>
                  <label className="field">
                    <span>Title</span>
                    <input
                      value={createContestForm.title}
                      onChange={(event) => {
                        setCreateContestForm((current) => ({
                          ...current,
                          title: event.target.value,
                        }));
                        if (contestFormErrors.length > 0) {
                          setContestFormErrors([]);
                        }
                      }}
                    />
                  </label>

                  <label className="field">
                    <span>Slug</span>
                    <input
                      value={createContestForm.slug}
                      onChange={(event) => {
                        setCreateContestForm((current) => ({
                          ...current,
                          slug: event.target.value,
                        }));
                        if (contestFormErrors.length > 0) {
                          setContestFormErrors([]);
                        }
                      }}
                    />
                  </label>

                  <label className="field">
                    <span>Description</span>
                    <textarea
                      rows={3}
                      value={createContestForm.description}
                      onChange={(event) =>
                        setCreateContestForm((current) => ({
                          ...current,
                          description: event.target.value,
                        }))
                      }
                    />
                  </label>

                  <div className="two-column-grid">
                    <label className="field">
                      <span>Status</span>
                      <select
                        value={createContestForm.status}
                        onChange={(event) =>
                          setCreateContestForm((current) => ({
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
                      <span>Starts at</span>
                      <input
                        value={createContestForm.starts_at}
                        onChange={(event) => {
                          setCreateContestForm((current) => ({
                            ...current,
                            starts_at: event.target.value,
                          }));
                          if (contestFormErrors.length > 0) {
                            setContestFormErrors([]);
                          }
                        }}
                        placeholder="2026-03-20T10:00:00Z"
                      />
                    </label>
                  </div>

                  <label className="field">
                    <span>Ends at</span>
                    <input
                      value={createContestForm.ends_at}
                      onChange={(event) => {
                        setCreateContestForm((current) => ({
                          ...current,
                          ends_at: event.target.value,
                        }));
                        if (contestFormErrors.length > 0) {
                          setContestFormErrors([]);
                        }
                      }}
                      placeholder="2026-03-20T15:00:00Z"
                    />
                  </label>

                  <button
                    type="submit"
                    className="button"
                    disabled={busyAction !== null}
                  >
                    {busyAction === "create-contest" ? "Creating..." : "Create contest"}
                  </button>
                </form>
              </Panel>

              {selectedContest ? (
                <Panel
                  title="Edit selected contest"
                  subtitle={`Currently selected: ${selectedContest.title}`}
                >
                  <FormErrorList errors={contestEditErrors} />

                  <form className="form-stack" onSubmit={handleUpdateContest}>
                    <label className="field">
                      <span>Title</span>
                      <input
                        value={editContestForm.title}
                        onChange={(event) => {
                          setEditContestForm((current) => ({
                            ...current,
                            title: event.target.value,
                          }));
                          if (contestEditErrors.length > 0) {
                            setContestEditErrors([]);
                          }
                        }}
                      />
                    </label>

                    <label className="field">
                      <span>Slug</span>
                      <input
                        value={editContestForm.slug}
                        onChange={(event) => {
                          setEditContestForm((current) => ({
                            ...current,
                            slug: event.target.value,
                          }));
                          if (contestEditErrors.length > 0) {
                            setContestEditErrors([]);
                          }
                        }}
                      />
                    </label>

                    <label className="field">
                      <span>Description</span>
                      <textarea
                        rows={3}
                        value={editContestForm.description}
                        onChange={(event) =>
                          setEditContestForm((current) => ({
                            ...current,
                            description: event.target.value,
                          }))
                        }
                      />
                    </label>

                    <div className="two-column-grid">
                      <label className="field">
                        <span>Status</span>
                        <select
                          value={editContestForm.status}
                          onChange={(event) =>
                            setEditContestForm((current) => ({
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
                        <span>Starts at</span>
                        <input
                          value={editContestForm.starts_at}
                          onChange={(event) => {
                            setEditContestForm((current) => ({
                              ...current,
                              starts_at: event.target.value,
                            }));
                            if (contestEditErrors.length > 0) {
                              setContestEditErrors([]);
                            }
                          }}
                        />
                      </label>
                    </div>

                    <label className="field">
                      <span>Ends at</span>
                      <input
                        value={editContestForm.ends_at}
                        onChange={(event) => {
                          setEditContestForm((current) => ({
                            ...current,
                            ends_at: event.target.value,
                          }));
                          if (contestEditErrors.length > 0) {
                            setContestEditErrors([]);
                          }
                        }}
                      />
                    </label>

                    <div className="inline-links-row">
                      <button
                        type="submit"
                        className="button"
                        disabled={busyAction !== null}
                      >
                        {busyAction === "update-contest" ? "Saving..." : "Save changes"}
                      </button>

                      <Link
                        to={`/contests/${selectedContest.slug}`}
                        className="inline-link"
                      >
                        Open public contest page
                      </Link>
                    </div>
                  </form>
                </Panel>
              ) : null}
            </div>
          </div>
        </Panel>
      ) : null}

      {activeTab === "problems" ? (
        <Panel
          title="Problems"
          subtitle="Manage problem statements for the selected contest."
        >
          {!selectedContest ? (
            <EmptyState
              title="No contest selected"
              description="Select a contest first from the Contests tab."
            />
          ) : (
            <div className="workspace-two-column">
              <div className="list-stack">
                {problems.length === 0 ? (
                  <EmptyState
                    title="No problems yet"
                    description="Create the first problem for the selected contest."
                  />
                ) : (
                  problems.map((problem) => (
                    <button
                      key={problem.id}
                      type="button"
                      className={`selectable-card ${
                        problem.id === selectedProblemId
                          ? "selectable-card--active"
                          : ""
                      }`}
                      onClick={() => setSelectedProblemId(problem.id)}
                    >
                      <div className="list-card__header">
                        <div>
                          <strong>
                            {problem.code} — {problem.title}
                          </strong>
                          <div className="muted small-text">
                            Position: {problem.position}
                          </div>
                        </div>
                        <StatusPill value={problem.status} />
                      </div>
                    </button>
                  ))
                )}
              </div>

              <div className="stack">
                <Panel
                  title="Create problem"
                  subtitle={`Contest: ${selectedContest.title}`}
                >
                  <FormErrorList errors={problemFormErrors} />

                  <form className="form-stack" onSubmit={handleCreateProblem}>
                    <div className="two-column-grid">
                      <label className="field">
                        <span>Code</span>
                        <input
                          value={createProblemForm.code}
                          onChange={(event) => {
                            setCreateProblemForm((current) => ({
                              ...current,
                              code: event.target.value,
                            }));
                            if (problemFormErrors.length > 0) {
                              setProblemFormErrors([]);
                            }
                          }}
                        />
                      </label>

                      <label className="field">
                        <span>Title</span>
                        <input
                          value={createProblemForm.title}
                          onChange={(event) => {
                            setCreateProblemForm((current) => ({
                              ...current,
                              title: event.target.value,
                            }));
                            if (problemFormErrors.length > 0) {
                              setProblemFormErrors([]);
                            }
                          }}
                        />
                      </label>
                    </div>

                    <label className="field">
                      <span>Statement</span>
                      <textarea
                        rows={6}
                        value={createProblemForm.statement}
                        onChange={(event) => {
                          setCreateProblemForm((current) => ({
                            ...current,
                            statement: event.target.value,
                          }));
                          if (problemFormErrors.length > 0) {
                            setProblemFormErrors([]);
                          }
                        }}
                      />
                    </label>

                    <label className="field">
                      <span>Input specification</span>
                      <textarea
                        rows={3}
                        value={createProblemForm.input_specification}
                        onChange={(event) =>
                          setCreateProblemForm((current) => ({
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
                        value={createProblemForm.output_specification}
                        onChange={(event) =>
                          setCreateProblemForm((current) => ({
                            ...current,
                            output_specification: event.target.value,
                          }))
                        }
                      />
                    </label>

                    <label className="field">
                      <span>Notes</span>
                      <textarea
                        rows={3}
                        value={createProblemForm.notes}
                        onChange={(event) =>
                          setCreateProblemForm((current) => ({
                            ...current,
                            notes: event.target.value,
                          }))
                        }
                      />
                    </label>

                    <div className="two-column-grid">
                      <label className="field">
                        <span>Sample input</span>
                        <textarea
                          rows={3}
                          value={createProblemForm.sample_input}
                          onChange={(event) =>
                            setCreateProblemForm((current) => ({
                              ...current,
                              sample_input: event.target.value,
                            }))
                          }
                        />
                      </label>

                      <label className="field">
                        <span>Sample output</span>
                        <textarea
                          rows={3}
                          value={createProblemForm.sample_output}
                          onChange={(event) =>
                            setCreateProblemForm((current) => ({
                              ...current,
                              sample_output: event.target.value,
                            }))
                          }
                        />
                      </label>
                    </div>

                    <div className="two-column-grid">
                      <label className="field">
                        <span>Time limit (ms)</span>
                        <input
                          type="number"
                          min={100}
                          value={createProblemForm.time_limit_ms}
                          onChange={(event) => {
                            setCreateProblemForm((current) => ({
                              ...current,
                              time_limit_ms: event.target.value,
                            }));
                            if (problemFormErrors.length > 0) {
                              setProblemFormErrors([]);
                            }
                          }}
                        />
                      </label>

                      <label className="field">
                        <span>Memory limit (MB)</span>
                        <input
                          type="number"
                          min={16}
                          value={createProblemForm.memory_limit_mb}
                          onChange={(event) => {
                            setCreateProblemForm((current) => ({
                              ...current,
                              memory_limit_mb: event.target.value,
                            }));
                            if (problemFormErrors.length > 0) {
                              setProblemFormErrors([]);
                            }
                          }}
                        />
                      </label>
                    </div>

                    <div className="two-column-grid">
                      <label className="field">
                        <span>Position</span>
                        <input
                          type="number"
                          min={1}
                          value={createProblemForm.position}
                          onChange={(event) => {
                            setCreateProblemForm((current) => ({
                              ...current,
                              position: event.target.value,
                            }));
                            if (problemFormErrors.length > 0) {
                              setProblemFormErrors([]);
                            }
                          }}
                        />
                      </label>

                      <label className="field">
                        <span>Status</span>
                        <select
                          value={createProblemForm.status}
                          onChange={(event) =>
                            setCreateProblemForm((current) => ({
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

                    <button
                      type="submit"
                      className="button"
                      disabled={busyAction !== null}
                    >
                      {busyAction === "create-problem" ? "Creating..." : "Create problem"}
                    </button>
                  </form>
                </Panel>

                {selectedProblem ? (
                  <Panel
                    title="Edit selected problem"
                    subtitle={`Selected: ${selectedProblem.code} — ${selectedProblem.title}`}
                  >
                    <FormErrorList errors={problemEditErrors} />

                    <form className="form-stack" onSubmit={handleUpdateProblem}>
                      <div className="two-column-grid">
                        <label className="field">
                          <span>Code</span>
                          <input
                            value={editProblemForm.code}
                            onChange={(event) => {
                              setEditProblemForm((current) => ({
                                ...current,
                                code: event.target.value,
                              }));
                              if (problemEditErrors.length > 0) {
                                setProblemEditErrors([]);
                              }
                            }}
                          />
                        </label>

                        <label className="field">
                          <span>Title</span>
                          <input
                            value={editProblemForm.title}
                            onChange={(event) => {
                              setEditProblemForm((current) => ({
                                ...current,
                                title: event.target.value,
                              }));
                              if (problemEditErrors.length > 0) {
                                setProblemEditErrors([]);
                              }
                            }}
                          />
                        </label>
                      </div>

                      <label className="field">
                        <span>Statement</span>
                        <textarea
                          rows={6}
                          value={editProblemForm.statement}
                          onChange={(event) => {
                            setEditProblemForm((current) => ({
                              ...current,
                              statement: event.target.value,
                            }));
                            if (problemEditErrors.length > 0) {
                              setProblemEditErrors([]);
                            }
                          }}
                        />
                      </label>

                      <label className="field">
                        <span>Input specification</span>
                        <textarea
                          rows={3}
                          value={editProblemForm.input_specification}
                          onChange={(event) =>
                            setEditProblemForm((current) => ({
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
                          value={editProblemForm.output_specification}
                          onChange={(event) =>
                            setEditProblemForm((current) => ({
                              ...current,
                              output_specification: event.target.value,
                            }))
                          }
                        />
                      </label>

                      <label className="field">
                        <span>Notes</span>
                        <textarea
                          rows={3}
                          value={editProblemForm.notes}
                          onChange={(event) =>
                            setEditProblemForm((current) => ({
                              ...current,
                              notes: event.target.value,
                            }))
                          }
                        />
                      </label>

                      <div className="two-column-grid">
                        <label className="field">
                          <span>Sample input</span>
                          <textarea
                            rows={3}
                            value={editProblemForm.sample_input}
                            onChange={(event) =>
                              setEditProblemForm((current) => ({
                                ...current,
                                sample_input: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <label className="field">
                          <span>Sample output</span>
                          <textarea
                            rows={3}
                            value={editProblemForm.sample_output}
                            onChange={(event) =>
                              setEditProblemForm((current) => ({
                                ...current,
                                sample_output: event.target.value,
                              }))
                            }
                          />
                        </label>
                      </div>

                      <div className="two-column-grid">
                        <label className="field">
                          <span>Time limit (ms)</span>
                          <input
                            type="number"
                            min={100}
                            value={editProblemForm.time_limit_ms}
                            onChange={(event) => {
                              setEditProblemForm((current) => ({
                                ...current,
                                time_limit_ms: event.target.value,
                              }));
                              if (problemEditErrors.length > 0) {
                                setProblemEditErrors([]);
                              }
                            }}
                          />
                        </label>

                        <label className="field">
                          <span>Memory limit (MB)</span>
                          <input
                            type="number"
                            min={16}
                            value={editProblemForm.memory_limit_mb}
                            onChange={(event) => {
                              setEditProblemForm((current) => ({
                                ...current,
                                memory_limit_mb: event.target.value,
                              }));
                              if (problemEditErrors.length > 0) {
                                setProblemEditErrors([]);
                              }
                            }}
                          />
                        </label>
                      </div>

                      <div className="two-column-grid">
                        <label className="field">
                          <span>Position</span>
                          <input
                            type="number"
                            min={1}
                            value={editProblemForm.position}
                            onChange={(event) => {
                              setEditProblemForm((current) => ({
                                ...current,
                                position: event.target.value,
                              }));
                              if (problemEditErrors.length > 0) {
                                setProblemEditErrors([]);
                              }
                            }}
                          />
                        </label>

                        <label className="field">
                          <span>Status</span>
                          <select
                            value={editProblemForm.status}
                            onChange={(event) =>
                              setEditProblemForm((current) => ({
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

                      <div className="inline-links-row">
                        <button
                          type="submit"
                          className="button"
                          disabled={busyAction !== null}
                        >
                          {busyAction === "update-problem" ? "Saving..." : "Save changes"}
                        </button>

                        <Link
                          to={`/contests/${selectedContest?.slug}/problems/${selectedProblem.code}`}
                          className="inline-link"
                        >
                          Open public problem page
                        </Link>
                      </div>
                    </form>
                  </Panel>
                ) : null}
              </div>
            </div>
          )}
        </Panel>
      ) : null}

      {activeTab === "test-cases" ? (
        <Panel
          title="Test cases"
          subtitle="Maintain the selected problem test suite."
        >
          {!selectedProblem ? (
            <EmptyState
              title="No problem selected"
              description="Select a problem first from the Problems tab."
            />
          ) : (
            <div className="workspace-two-column">
              <div className="list-stack">
                {testCases.length === 0 ? (
                  <EmptyState
                    title="No test cases yet"
                    description="Create the first test case for the selected problem."
                  />
                ) : (
                  testCases.map((testCase) => (
                    <button
                      key={testCase.id}
                      type="button"
                      className={`selectable-card ${
                        testCase.id === selectedTestCaseId
                          ? "selectable-card--active"
                          : ""
                      }`}
                      onClick={() => setSelectedTestCaseId(testCase.id)}
                    >
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
                    </button>
                  ))
                )}
              </div>

              <div className="stack">
                <Panel
                  title="Create test case"
                  subtitle={`Problem: ${selectedProblem.code} — ${selectedProblem.title}`}
                >
                  <FormErrorList errors={testCaseFormErrors} />

                  <form className="form-stack" onSubmit={handleCreateTestCase}>
                    <label className="field">
                      <span>Input data</span>
                      <textarea
                        rows={5}
                        value={createTestCaseForm.input_data}
                        onChange={(event) => {
                          setCreateTestCaseForm((current) => ({
                            ...current,
                            input_data: event.target.value,
                          }));
                          if (testCaseFormErrors.length > 0) {
                            setTestCaseFormErrors([]);
                          }
                        }}
                      />
                    </label>

                    <label className="field">
                      <span>Expected output</span>
                      <textarea
                        rows={5}
                        value={createTestCaseForm.expected_output}
                        onChange={(event) => {
                          setCreateTestCaseForm((current) => ({
                            ...current,
                            expected_output: event.target.value,
                          }));
                          if (testCaseFormErrors.length > 0) {
                            setTestCaseFormErrors([]);
                          }
                        }}
                      />
                    </label>

                    <label className="field">
                      <span>Position</span>
                      <input
                        type="number"
                        min={1}
                        value={createTestCaseForm.position}
                        onChange={(event) => {
                          setCreateTestCaseForm((current) => ({
                            ...current,
                            position: event.target.value,
                          }));
                          if (testCaseFormErrors.length > 0) {
                            setTestCaseFormErrors([]);
                          }
                        }}
                      />
                    </label>

                    <label className="checkbox-field">
                      <input
                        type="checkbox"
                        checked={createTestCaseForm.is_sample}
                        onChange={(event) =>
                          setCreateTestCaseForm((current) => ({
                            ...current,
                            is_sample: event.target.checked,
                          }))
                        }
                      />
                      <span>Sample test</span>
                    </label>

                    <label className="checkbox-field">
                      <input
                        type="checkbox"
                        checked={createTestCaseForm.is_active}
                        onChange={(event) =>
                          setCreateTestCaseForm((current) => ({
                            ...current,
                            is_active: event.target.checked,
                          }))
                        }
                      />
                      <span>Active</span>
                    </label>

                    <button
                      type="submit"
                      className="button"
                      disabled={busyAction !== null}
                    >
                      {busyAction === "create-test-case" ? "Creating..." : "Create test case"}
                    </button>
                  </form>
                </Panel>

                {selectedTestCase ? (
                  <Panel
                    title="Edit selected test case"
                    subtitle={`Currently selected: #${selectedTestCase.position}`}
                  >
                    <FormErrorList errors={testCaseEditErrors} />

                    <form className="form-stack" onSubmit={handleUpdateTestCase}>
                      <label className="field">
                        <span>Input data</span>
                        <textarea
                          rows={5}
                          value={editTestCaseForm.input_data}
                          onChange={(event) => {
                            setEditTestCaseForm((current) => ({
                              ...current,
                              input_data: event.target.value,
                            }));
                            if (testCaseEditErrors.length > 0) {
                              setTestCaseEditErrors([]);
                            }
                          }}
                        />
                      </label>

                      <label className="field">
                        <span>Expected output</span>
                        <textarea
                          rows={5}
                          value={editTestCaseForm.expected_output}
                          onChange={(event) => {
                            setEditTestCaseForm((current) => ({
                              ...current,
                              expected_output: event.target.value,
                            }));
                            if (testCaseEditErrors.length > 0) {
                              setTestCaseEditErrors([]);
                            }
                          }}
                        />
                      </label>

                      <label className="field">
                        <span>Position</span>
                        <input
                          type="number"
                          min={1}
                          value={editTestCaseForm.position}
                          onChange={(event) => {
                            setEditTestCaseForm((current) => ({
                              ...current,
                              position: event.target.value,
                            }));
                            if (testCaseEditErrors.length > 0) {
                              setTestCaseEditErrors([]);
                            }
                          }}
                        />
                      </label>

                      <label className="checkbox-field">
                        <input
                          type="checkbox"
                          checked={editTestCaseForm.is_sample}
                          onChange={(event) =>
                            setEditTestCaseForm((current) => ({
                              ...current,
                              is_sample: event.target.checked,
                            }))
                          }
                        />
                        <span>Sample test</span>
                      </label>

                      <label className="checkbox-field">
                        <input
                          type="checkbox"
                          checked={editTestCaseForm.is_active}
                          onChange={(event) =>
                            setEditTestCaseForm((current) => ({
                              ...current,
                              is_active: event.target.checked,
                            }))
                          }
                        />
                        <span>Active</span>
                      </label>

                      <button
                        type="submit"
                        className="button"
                        disabled={busyAction !== null}
                      >
                        {busyAction === "update-test-case" ? "Saving..." : "Save changes"}
                      </button>
                    </form>
                  </Panel>
                ) : null}
              </div>
            </div>
          )}
        </Panel>
      ) : null}

      {activeTab === "submissions" ? (
        <div className="workspace-grid">
          <div className="workspace-grid__main">
            <Panel
              title="Submission filters"
              subtitle="Narrow down the submission list by contest, problem, user, or verdict."
            >
              <form className="form-stack" onSubmit={handleApplySubmissionFilters}>
                <div className="two-column-grid">
                  <label className="field">
                    <span>Contest slug</span>
                    <input
                      value={submissionFilters.contest_slug}
                      onChange={(event) =>
                        setSubmissionFilters((current) => ({
                          ...current,
                          contest_slug: event.target.value,
                        }))
                      }
                    />
                  </label>

                  <label className="field">
                    <span>Problem code</span>
                    <input
                      value={submissionFilters.problem_code}
                      onChange={(event) =>
                        setSubmissionFilters((current) => ({
                          ...current,
                          problem_code: event.target.value,
                        }))
                      }
                    />
                  </label>
                </div>

                <div className="two-column-grid">
                  <label className="field">
                    <span>Username</span>
                    <input
                      value={submissionFilters.username}
                      onChange={(event) =>
                        setSubmissionFilters((current) => ({
                          ...current,
                          username: event.target.value,
                        }))
                      }
                    />
                  </label>

                  <label className="field">
                    <span>Language</span>
                    <select
                      value={submissionFilters.language}
                      onChange={(event) =>
                        setSubmissionFilters((current) => ({
                          ...current,
                          language: event.target.value,
                        }))
                      }
                    >
                      <option value="">any</option>
                      <option value="python">python</option>
                      <option value="cpp">cpp</option>
                    </select>
                  </label>
                </div>

                <div className="two-column-grid">
                  <label className="field">
                    <span>Status</span>
                    <select
                      value={submissionFilters.status}
                      onChange={(event) =>
                        setSubmissionFilters((current) => ({
                          ...current,
                          status: event.target.value,
                        }))
                      }
                    >
                      <option value="">any</option>
                      <option value="pending">pending</option>
                      <option value="running">running</option>
                      <option value="finished">finished</option>
                    </select>
                  </label>

                  <label className="field">
                    <span>Verdict</span>
                    <select
                      value={submissionFilters.verdict}
                      onChange={(event) =>
                        setSubmissionFilters((current) => ({
                          ...current,
                          verdict: event.target.value,
                        }))
                      }
                    >
                      <option value="">any</option>
                      <option value="pending">pending</option>
                      <option value="accepted">accepted</option>
                      <option value="wrong_answer">wrong_answer</option>
                      <option value="runtime_error">runtime_error</option>
                      <option value="time_limit_exceeded">time_limit_exceeded</option>
                      <option value="compilation_error">compilation_error</option>
                      <option value="internal_error">internal_error</option>
                      <option value="no_tests">no_tests</option>
                    </select>
                  </label>
                </div>

                <div className="inline-links-row">
                  <button type="submit" className="button" disabled={submissionsLoading}>
                    {submissionsLoading ? "Loading..." : "Apply filters"}
                  </button>

                  <button
                    type="button"
                    className="button button--secondary"
                    onClick={() => void handleClearSubmissionFilters()}
                  >
                    Clear
                  </button>
                </div>
              </form>
            </Panel>
          </div>

          <div className="workspace-grid__side">
            <Panel
              title="Filtered submissions"
              subtitle="Inspect verdicts and trigger rejudge when needed."
            >
              {submissionsLoading ? <LoadingState label="Loading submissions..." /> : null}

              {!submissionsLoading && submissions.length === 0 ? (
                <EmptyState
                  title="No submissions found"
                  description="Try changing filters or clear them to see a broader list."
                />
              ) : null}

              {submissions.length > 0 ? (
                <div className="list-stack">
                  {submissions.map((submission) => (
                    <article key={submission.id} className="list-card">
                      <div className="list-card__header">
                        <div>
                          <strong>
                            {submission.user.username} · {submission.problem.code}
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
                          to={`/submissions/${submission.id}`}
                          className="inline-link"
                        >
                          Open submission
                        </Link>

                        <button
                          type="button"
                          className="button button--secondary"
                          disabled={
                            submission.status === "running" ||
                            busyAction === `rejudge-${submission.id}`
                          }
                          onClick={() => void handleRejudge(submission.id)}
                        >
                          {busyAction === `rejudge-${submission.id}`
                            ? "Queueing..."
                            : "Rejudge"}
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}
            </Panel>
          </div>
        </div>
      ) : null}
    </div>
  );
}