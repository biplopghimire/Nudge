/**
 * Typed client for the Nudge API. Request and response types come from
 * nudge-api/nudge-types.ts, the same file the backend's examples are checked
 * against.
 */
import type {
  AttachmentSource,
  CourseSettings,
  CreateCourseRequest,
  CreateCourseResponse,
  CreateThreadRequest,
  CreateThreadResponse,
  GetMaterialLinkResponse,
  GetStudentCourseResponse,
  GetStudentCoursesResponse,
  GetStudentMeResponse,
  GetTeacherCourseResponse,
  GetTeacherCoursesResponse,
  GetTeacherMeResponse,
  GetThreadResponse,
  GetThreadsResponse,
  JoinCourseResponse,
  LoginResponse,
  MaterialKind,
  Role,
  SendMessageResponse,
  StudentNotifications,
  TeacherNotifications,
  UpdateCourseSettingsResponse,
  UpdateStudentMeResponse,
  UpdateTeacherMeResponse,
  UploadFile,
  UploadMaterialResponse,
} from "@api";

import { File as FsFile } from "expo-file-system";

import { API_URL } from "./config";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

let token: string | null = null;
let onUnauthorized: (() => void) | null = null;

/** Called by the auth provider when the user signs in or out. */
export function setSession(nextToken: string | null, handleUnauthorized?: () => void) {
  token = nextToken;
  onUnauthorized = handleUnauthorized ?? null;
}

type Body = { json?: unknown; form?: FormData };

async function request<T>(method: string, path: string, body: Body = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body.json !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body.form ?? (body.json !== undefined ? JSON.stringify(body.json) : undefined),
    });
  } catch (error) {
    if (__DEV__) console.warn(`[api] ${method} ${path} failed before reaching the server:`, error);
    throw new ApiError(0, "offline", "Can't reach Nudge. Check your connection and try again.");
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && token) onUnauthorized?.();
    throw new ApiError(
      response.status,
      data?.error ?? "error",
      data?.message ?? "Something went wrong. Try again.",
    );
  }
  return data as T;
}

/**
 * A file part for multipart uploads. Expo's fetch (the global fetch since SDK 55)
 * doesn't accept React Native's `{ uri, name, type }` parts: it needs something
 * that can give it bytes. Keep the original name and type, read the bytes from disk.
 */
const file = (f: UploadFile) => {
  const onDisk = new FsFile(f.uri);
  return {
    name: f.name,
    type: f.type,
    bytes: async () => new Uint8Array(await onDisk.arrayBuffer()),
  } as unknown as Blob;
};

export const api = {
  // ---- auth ----
  login: (email: string, password: string) =>
    request<LoginResponse>("POST", "/auth/login", { json: { email, password } }),
  signup: (name: string, email: string, password: string, role: Role) =>
    request<LoginResponse>("POST", "/auth/signup", { json: { name, email, password, role } }),

  // ---- chats (both roles) ----
  threads: (q?: string) =>
    request<GetThreadsResponse>("GET", `/threads${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  createThread: (body: CreateThreadRequest) =>
    request<CreateThreadResponse>("POST", "/threads", { json: body }),
  thread: (id: string) => request<GetThreadResponse>("GET", `/threads/${id}`),
  sendMessage: (
    threadId: string,
    content: string,
    attachment?: { file: UploadFile; source: AttachmentSource },
  ) => {
    const form = new FormData();
    form.append("content", content);
    if (attachment) {
      form.append("attachment", file(attachment.file));
      form.append("attachmentSource", attachment.source);
    }
    return request<SendMessageResponse>("POST", `/threads/${threadId}/messages`, { form });
  },

  // ---- students ----
  studentMe: () => request<GetStudentMeResponse>("GET", "/student/me"),
  updateStudentNotifications: (notifications: Partial<StudentNotifications>) =>
    request<UpdateStudentMeResponse>("PATCH", "/student/me", { json: { notifications } }),
  studentCourses: () => request<GetStudentCoursesResponse>("GET", "/student/courses"),
  studentCourse: (id: string) => request<GetStudentCourseResponse>("GET", `/student/courses/${id}`),
  joinCourse: (joinCode: string) =>
    request<JoinCourseResponse>("POST", "/student/courses/join", { json: { joinCode } }),
  materialLink: (materialId: string, page?: number | null) =>
    request<GetMaterialLinkResponse>(
      "GET",
      `/student/materials/${materialId}/link${page ? `?page=${page}` : ""}`,
    ),

  // ---- teachers ----
  teacherMe: () => request<GetTeacherMeResponse>("GET", "/teacher/me"),
  updateTeacherNotifications: (notifications: Partial<TeacherNotifications>) =>
    request<UpdateTeacherMeResponse>("PATCH", "/teacher/me", { json: { notifications } }),
  teacherCourses: () => request<GetTeacherCoursesResponse>("GET", "/teacher/courses"),
  teacherCourse: (id: string) => request<GetTeacherCourseResponse>("GET", `/teacher/courses/${id}`),
  createCourse: (body: CreateCourseRequest) =>
    request<CreateCourseResponse>("POST", "/teacher/courses", { json: body }),
  updateSettings: (courseId: string, changes: Partial<CourseSettings>) =>
    request<UpdateCourseSettingsResponse>("PATCH", `/teacher/courses/${courseId}/settings`, {
      json: changes,
    }),
  uploadMaterial: (courseId: string, upload: UploadFile, kind: MaterialKind, restricted = false) => {
    const form = new FormData();
    form.append("file", file(upload));
    form.append("kind", kind);
    form.append("restricted", String(restricted));
    return request<UploadMaterialResponse>("POST", `/teacher/courses/${courseId}/materials`, { form });
  },
};
