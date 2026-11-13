import { MAX_NAME, validateAuth } from "../validation";

const valid = { name: "Sam Lee", email: "sam@andrew.cmu.edu", password: "longenough" };

describe("validateAuth", () => {
  it("accepts a complete sign-up", () => {
    expect(validateAuth("signUp", valid)).toEqual({});
  });

  it("flags badly formatted emails", () => {
    for (const email of ["sam", "sam@", "sam@cmu", "@cmu.edu", "sam lee@cmu.edu"]) {
      expect(validateAuth("signUp", { ...valid, email }).email).toMatch(/valid email/);
    }
  });

  it("asks for an email when it is blank", () => {
    expect(validateAuth("signUp", { ...valid, email: "  " }).email).toBe(
      "Enter your email address."
    );
  });

  it("flags passwords shorter than 8 characters on sign-up", () => {
    expect(validateAuth("signUp", { ...valid, password: "short" }).password).toBe(
      "Passwords need at least 8 characters (5 so far)."
    );
    expect(validateAuth("signUp", { ...valid, password: "" }).password).toMatch(/at least 8/);
  });

  it("requires a name on sign-up, up to the API's limit", () => {
    expect(validateAuth("signUp", { ...valid, name: "   " }).name).toBe("Enter your name.");
    expect(validateAuth("signUp", { ...valid, name: "x".repeat(MAX_NAME + 1) }).name).toMatch(
      /up to 100/
    );
  });

  it("only checks the email format and a non-empty password on sign-in", () => {
    expect(
      validateAuth("signIn", { name: "", email: "sam@andrew.cmu.edu", password: "x" })
    ).toEqual({});
    expect(validateAuth("signIn", { name: "", email: "sam@andrew.cmu.edu", password: "" })).toEqual(
      {
        password: "Enter your password.",
      }
    );
  });
});
