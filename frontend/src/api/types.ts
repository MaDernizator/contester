export type UserRole = "admin" | "participant";

export interface UserSummary {
  id: string;
  username: string;
  full_name: string | null;
  role: UserRole;
}

export interface User extends UserSummary {
  email: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ContestStatus = "draft" | "published" | "archived";
export type ContestPhase = "upcoming" | "running" | "finished" | "unscheduled";

export interface ContestSummary {
  id: string;
  title: string;
  slug: string;
  status: ContestStatus;
}

export interface Contest extends ContestSummary {
  description: string | null;
  starts_at: string | null;
  ends_at: string | null;
  phase: ContestPhase;
  created_at: string;
  updated_at: string;
  created_by: UserSummary;
}

export type ProblemStatus = "draft" | "published" | "archived";

export interface ProblemSummary {
  id: string;
  contest_id: string;
  code: string;
  title: string;
  position: number;
  status: ProblemStatus;
  time_limit_ms: number;
  memory_limit_mb: number;
  created_at: string;
  updated_at: string;
}

export interface Problem extends ProblemSummary {
  statement: string;
  input_specification: string | null;
  output_specification: string | null;
  notes: string | null;
  sample_input: string | null;
  sample_output: string | null;
  contest: ContestSummary;
}

export interface TestCaseSummary {
  id: string;
  problem_id: string;
  position: number;
  is_sample: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TestCase extends TestCaseSummary {
  input_data: string;
  expected_output: string;
}

export type SubmissionLanguage = "python" | "cpp";

export type SubmissionStatus = "pending" | "running" | "finished";

export type SubmissionVerdict =
  | "pending"
  | "accepted"
  | "wrong_answer"
  | "runtime_error"
  | "time_limit_exceeded"
  | "compilation_error"
  | "internal_error"
  | "no_tests";

export interface SubmissionSummary {
  id: string;
  language: SubmissionLanguage;
  status: SubmissionStatus;
  verdict: SubmissionVerdict;
  passed_test_count: number;
  total_test_count: number;
  failed_test_position: number | null;
  execution_time_ms: number | null;
  created_at: string;
  updated_at: string;
  judged_at: string | null;
  problem: ProblemSummary;
  contest: ContestSummary;
  user: UserSummary;
}

export interface Submission extends SubmissionSummary {
  source_code: string;
  judge_log: string | null;
}

export interface QueueStatus {
  pending_count: number;
  running_count: number;
  finished_count: number;
  oldest_pending_submission_id: string | null;
  oldest_pending_created_at: string | null;
}

export interface StandingProblemResult {
  problem: ProblemSummary;
  attempt_count: number;
  accepted: boolean;
  wrong_attempts_before_accept: number;
  last_verdict: SubmissionVerdict | null;
  accepted_at: string | null;
  penalty_minutes: number | null;
}

export interface StandingRow {
  rank: number;
  user: UserSummary;
  solved_count: number;
  penalty_minutes: number;
  total_attempt_count: number;
  last_activity_at: string | null;
  problem_results: StandingProblemResult[];
}

export interface ContestStandings {
  contest: ContestSummary;
  generated_at: string;
  problems: ProblemSummary[];
  rows: StandingRow[];
}