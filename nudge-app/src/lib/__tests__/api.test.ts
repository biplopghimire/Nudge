import { api, ApiError, setSession } from "../api";
import { API_URL } from "../config";

jest.mock("expo-file-system", () => ({
  File: jest.fn().mockImplementation(() => ({ arrayBuffer: async () => new ArrayBuffer(3) })),
}));

const fetchMock = jest.fn();
globalThis.fetch = fetchMock;

const respond = (status: number, body: unknown) =>
  fetchMock.mockResolvedValueOnce({ ok: status < 400, status, json: async () => body });

const lastCall = () => {
  const [url, init] = fetchMock.mock.calls.at(-1) as [string, RequestInit];
  return { url, init, headers: init.headers as Record<string, string> };
};

beforeEach(() => {
  fetchMock.mockReset();
  setSession(null);
});

describe("api requests", () => {
  it("sends JSON to the API with no token when signed out", async () => {
    respond(200, { token: "t", user: {} });
    await api.login("a@b.edu", "pw");

    const { url, init, headers } = lastCall();
    expect(url).toBe(`${API_URL}/auth/login`);
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ email: "a@b.edu", password: "pw" }));
    expect(headers["Content-Type"]).toBe("application/json");
    expect(headers.Authorization).toBeUndefined();
  });

  it("adds the token once signed in", async () => {
    setSession("abc");
    respond(200, { courses: [] });
    await api.studentCourses();
    expect(lastCall().headers.Authorization).toBe("Bearer abc");
  });

  it("returns the response body", async () => {
    respond(200, { threads: [{ id: "1" }] });
    await expect(api.threads()).resolves.toEqual({ threads: [{ id: "1" }] });
  });

  it("encodes search text and optional pages in the URL", async () => {
    respond(200, {});
    await api.threads("chain rule & limits");
    expect(lastCall().url).toBe(`${API_URL}/threads?q=chain%20rule%20%26%20limits`);

    respond(200, {});
    await api.materialLink("m1", 4);
    expect(lastCall().url).toBe(`${API_URL}/student/materials/m1/link?page=4`);

    respond(200, {});
    await api.materialLink("m1", null);
    expect(lastCall().url).toBe(`${API_URL}/student/materials/m1/link`);
  });

  it("sends messages as multipart form data without a JSON content type", async () => {
    respond(200, {});
    await api.sendMessage("t1", "hi", {
      file: { uri: "file:///p.jpg", name: "p.jpg", type: "image/jpeg" },
      source: "camera",
    });

    const { url, init, headers } = lastCall();
    expect(url).toBe(`${API_URL}/threads/t1/messages`);
    expect(init.body).toBeInstanceOf(FormData);
    expect(headers["Content-Type"]).toBeUndefined();
  });
});

describe("api errors", () => {
  it("turns error responses into ApiError with the server's code and message", async () => {
    respond(400, { error: "invalid_code", message: "That code doesn't match a course." });
    const error = await api.joinCourse("XXXXXX").catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 400,
      code: "invalid_code",
      message: "That code doesn't match a course.",
    });
  });

  it("falls back to a generic message when the body isn't JSON", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 502,
      json: async () => Promise.reject(new SyntaxError()),
    });
    await expect(api.studentMe()).rejects.toMatchObject({
      status: 502,
      code: "error",
      message: "Something went wrong. Try again.",
    });
  });

  it("reports offline when the request never reaches the server", async () => {
    jest.spyOn(console, "warn").mockImplementation(() => {});
    fetchMock.mockRejectedValueOnce(new TypeError("Network request failed"));
    await expect(api.studentMe()).rejects.toMatchObject({ status: 0, code: "offline" });
  });

  it("signs out on a 401 when there was a session", async () => {
    const onUnauthorized = jest.fn();
    setSession("expired", onUnauthorized);
    respond(401, { error: "unauthorized", message: "Sign in again." });
    await expect(api.teacherMe()).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("doesn't sign out on a 401 from logging in with a wrong password", async () => {
    const onUnauthorized = jest.fn();
    setSession(null, onUnauthorized);
    respond(401, { error: "invalid_credentials", message: "Wrong email or password." });
    await expect(api.login("a@b.edu", "nope")).rejects.toMatchObject({
      code: "invalid_credentials",
    });
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});
