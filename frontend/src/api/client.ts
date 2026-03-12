import type {
  Contest,
  Problem,
  ProblemSummary,
  Submission,
  SubmissionSummary,
  TestCase,
  TestCaseSummary,
  User,
} from "./types";

export class ApiError extends Error {
  public readonly status: number;
  public readonly payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (
    payload &&
    typeof payload === "object" &&
    "error" in payload &&
    payload.error &&
    typeof payload.error === "object" &&
    "message" in payload.error &&
    typeof payload.error.message === "string"
  ) {
    return payload.error.message;
  }

  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Accept", "application/json");

  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers,
  });

  const contentType = response.headers.get("Content-Type") ?? "";
  const isJson = contentType.includes("application/json");

  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    throw new ApiError(
      extractErrorMessage(payload, `Request failed with status ${response.status}.`),
      response.status,
      payload,
    );
  }

  return payload as T;
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export async function getCurrentUser(): Promise<User> {
  const payload = await request<{ user: User }>("/api/v1/auth/me");
  return payload.user;
}

export async function login(username: string, password: string): Promise<User> {
  const payload = await request<{ user: User }>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  return payload.user;
}

export async function registerParticipant(input: {
  username: string;
  password: string;
  email?: string;
  full_name?: string;
}): Promise<User> {
  const payload = await request<{ user: User }>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
  return payload.user;
}

export async function logout(): Promise<void> {
  await request("/api/v1/auth/logout", { method: "POST" });
}

export async function getContests(): Promise<Contest[]> {
  const payload = await request<{ contests: Contest[] }>("/api/v1/contests");
  return payload.contests;
}

export async function getContest(slug: string): Promise<Contest> {
  const payload = await request<{ contest: Contest }>(`/api/v1/contests/${slug}`);
  return payload.contest;
}

export async function getContestProblems(slug: string): Promise<ProblemSummary[]> {
  const payload = await request<{ problems: ProblemSummary[] }>(
    `/api/v1/contests/${slug}/problems`,
  );
  return payload.problems;
}

export async function getProblem(
  contestSlug: string,
  problemCode: string,
): Promise<Problem> {
  const payload = await request<{ problem: Problem }>(
    `/api/v1/contests/${contestSlug}/problems/${problemCode}`,
  );
  return payload.problem;
}

export async function createSubmission(input: {
  contestSlug: string;
  problemCode: string;
  language: "python";
  source_code: string;
}): Promise<Submission> {
  const payload = await request<{ submission: Submission }>(
    `/api/v1/contests/${input.contestSlug}/problems/${input.problemCode}/submissions`,
    {
      method: "POST",
      body: JSON.stringify({
        language: input.language,
        source_code: input.source_code,
      }),
    },
  );
  return payload.submission;
}

export async function getMySubmissions(): Promise<SubmissionSummary[]> {
  const payload = await request<{ submissions: SubmissionSummary[] }>("/api/v1/submissions");
  return payload.submissions;
}

export async function getSubmission(submissionId: string): Promise<Submission> {
  const payload = await request<{ submission: Submission }>(
    `/api/v1/submissions/${submissionId}`,
  );
  return payload.submission;
}

export async function getAdminContests(): Promise<Contest[]> {
  const payload = await request<{ contests: Contest[] }>("/api/v1/admin/contests");
  return payload.contests;
}

export async function createAdminContest(input: {
  title: string;
  slug: string;
  description?: string;
  starts_at?: string;
  ends_at?: string;
  status: "draft" | "published" | "archived";
}): Promise<Contest> {
  const payload = await request<{ contest: Contest }>("/api/v1/admin/contests", {
    method: "POST",
    body: JSON.stringify(input),
  });
  return payload.contest;
}

export async function getAdminProblems(contestId: string): Promise<ProblemSummary[]> {
  const payload = await request<{ problems: ProblemSummary[] }>(
    `/api/v1/admin/contests/${contestId}/problems`,
  );
  return payload.problems;
}

export async function createAdminProblem(input: {
  contestId: string;
  code: string;
  title: string;
  statement: string;
  input_specification?: string;
  output_specification?: string;
  notes?: string;
  sample_input?: string;
  sample_output?: string;
  time_limit_ms: number;
  memory_limit_mb: number;
  position?: number;
  status: "draft" | "published" | "archived";
}): Promise<Problem> {
  const payload = await request<{ problem: Problem }>(
    `/api/v1/admin/contests/${input.contestId}/problems`,
    {
      method: "POST",
      body: JSON.stringify({
        code: input.code,
        title: input.title,
        statement: input.statement,
        input_specification: input.input_specification,
        output_specification: input.output_specification,
        notes: input.notes,
        sample_input: input.sample_input,
        sample_output: input.sample_output,
        time_limit_ms: input.time_limit_ms,
        memory_limit_mb: input.memory_limit_mb,
        position: input.position,
        status: input.status,
      }),
    },
  );
  return payload.problem;
}

export async function getAdminTestCases(problemId: string): Promise<TestCaseSummary[]> {
  const payload = await request<{ test_cases: TestCaseSummary[] }>(
    `/api/v1/admin/problems/${problemId}/test-cases`,
  );
  return payload.test_cases;
}

export async function createAdminTestCase(input: {
  problemId: string;
  input_data: string;
  expected_output: string;
  position?: number;
  is_sample: boolean;
  is_active: boolean;
}): Promise<TestCase> {
  const payload = await request<{ test_case: TestCase }>(
    `/api/v1/admin/problems/${input.problemId}/test-cases`,
    {
      method: "POST",
      body: JSON.stringify({
        input_data: input.input_data,
        expected_output: input.expected_output,
        position: input.position,
        is_sample: input.is_sample,
        is_active: input.is_active,
      }),
    },
  );
  return payload.test_case;
}