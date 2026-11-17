// Mirrors the checks in nudge-api/app/services/auth.py so people see problems before the request is sent.
export const MIN_PASSWORD = 8;
export const MAX_NAME = 100;
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export type AuthMode = "signIn" | "signUp";
export type AuthFields = { name: string; email: string; password: string };
export type AuthErrors = Partial<Record<keyof AuthFields, string>>;

export function validateAuth(mode: AuthMode, { name, email, password }: AuthFields): AuthErrors {
  const errors: AuthErrors = {};

  if (mode === "signUp") {
    const trimmed = name.trim();
    if (!trimmed) errors.name = "Enter your name.";
    else if (trimmed.length > MAX_NAME) errors.name = `Names can be up to ${MAX_NAME} characters.`;
  }

  const trimmedEmail = email.trim();
  if (!trimmedEmail) errors.email = "Enter your email address.";
  else if (!EMAIL.test(trimmedEmail))
    errors.email = "Enter a valid email address, like you@andrew.cmu.edu.";

  if (!password)
    errors.password =
      mode === "signUp"
        ? `Choose a password with at least ${MIN_PASSWORD} characters.`
        : "Enter your password.";
  else if (mode === "signUp" && password.length < MIN_PASSWORD) {
    errors.password = `Passwords need at least ${MIN_PASSWORD} characters (${password.length} so far).`;
  }

  return errors;
}

// Mirrors normalize_course_code in nudge-api/app/services/common.py.
// CMU-style codes only for now ("67-272"). To support other schools later, loosen this to
// uppercase letters/digits with single spaces or dashes (e.g. "CS 101").
const COURSE_CODE = /^\d{2}-\d{3}$/;

/** Formats input as the teacher types: keeps digits only and puts the dash after the first two. */
export function formatCourseCode(input: string): string {
  const digits = input.replace(/\D/g, "").slice(0, 5);
  return digits.length > 2 ? `${digits.slice(0, 2)}-${digits.slice(2)}` : digits;
}

export function isValidCourseCode(code: string): boolean {
  return COURSE_CODE.test(code.trim());
}
