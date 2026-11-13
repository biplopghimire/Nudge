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
