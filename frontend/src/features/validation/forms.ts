import type { SubmissionLanguage } from "../../api/types";

export function validateLoginForm(input: {
  username: string;
  password: string;
}): string[] {
  const errors: string[] = [];

  if (!input.username.trim()) {
    errors.push("Username is required.");
  }

  if (!input.password) {
    errors.push("Password is required.");
  }

  return errors;
}

export function validateRegisterForm(input: {
  username: string;
  password: string;
  email: string;
}): string[] {
  const errors: string[] = [];

  if (!input.username.trim()) {
    errors.push("Username is required.");
  }

  if (input.password.length < 8) {
    errors.push("Password must contain at least 8 characters.");
  }

  if (input.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.email.trim())) {
    errors.push("Email format is invalid.");
  }

  return errors;
}

export function validateSubmissionForm(input: {
  language: SubmissionLanguage;
  sourceCode: string;
}): string[] {
  const errors: string[] = [];

  if (!input.language) {
    errors.push("Language is required.");
  }

  if (!input.sourceCode.trim()) {
    errors.push("Source code must not be empty.");
  }

  if (input.sourceCode.length > 100000) {
    errors.push("Source code is too large.");
  }

  return errors;
}

export function validateContestForm(input: {
  title: string;
  slug: string;
  starts_at: string;
  ends_at: string;
}): string[] {
  const errors: string[] = [];

  if (!input.title.trim()) {
    errors.push("Contest title is required.");
  }

  if (!input.slug.trim()) {
    errors.push("Contest slug is required.");
  }

  if (input.starts_at.trim() && Number.isNaN(Date.parse(input.starts_at.trim()))) {
    errors.push("Contest start time must be a valid ISO datetime.");
  }

  if (input.ends_at.trim() && Number.isNaN(Date.parse(input.ends_at.trim()))) {
    errors.push("Contest end time must be a valid ISO datetime.");
  }

  if (
    input.starts_at.trim() &&
    input.ends_at.trim() &&
    !Number.isNaN(Date.parse(input.starts_at.trim())) &&
    !Number.isNaN(Date.parse(input.ends_at.trim())) &&
    Date.parse(input.ends_at.trim()) <= Date.parse(input.starts_at.trim())
  ) {
    errors.push("Contest end time must be later than start time.");
  }

  return errors;
}

export function validateProblemForm(input: {
  code: string;
  title: string;
  statement: string;
  time_limit_ms: string;
  memory_limit_mb: string;
  position: string;
}): string[] {
  const errors: string[] = [];

  if (!input.code.trim()) {
    errors.push("Problem code is required.");
  }

  if (!input.title.trim()) {
    errors.push("Problem title is required.");
  }

  if (!input.statement.trim()) {
    errors.push("Problem statement is required.");
  }

  const timeLimit = Number(input.time_limit_ms);
  if (!Number.isInteger(timeLimit) || timeLimit < 100) {
    errors.push("Time limit must be an integer greater than or equal to 100 ms.");
  }

  const memoryLimit = Number(input.memory_limit_mb);
  if (!Number.isInteger(memoryLimit) || memoryLimit < 16) {
    errors.push("Memory limit must be an integer greater than or equal to 16 MB.");
  }

  const position = Number(input.position);
  if (!Number.isInteger(position) || position < 1) {
    errors.push("Problem position must be a positive integer.");
  }

  return errors;
}

export function validateTestCaseForm(input: {
  input_data: string;
  expected_output: string;
  position: string;
}): string[] {
  const errors: string[] = [];

  if (!input.input_data.trim()) {
    errors.push("Test case input must not be empty.");
  }

  if (!input.expected_output.trim()) {
    errors.push("Expected output must not be empty.");
  }

  const position = Number(input.position);
  if (!Number.isInteger(position) || position < 1) {
    errors.push("Test case position must be a positive integer.");
  }

  return errors;
}