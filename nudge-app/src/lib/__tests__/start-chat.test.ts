import type { StudentCourseSummary, ThreadSummary } from "@api";

import { newChatCourse } from "../start-chat";

jest.mock("expo-router", () => ({ router: { push: jest.fn() } }));

const course = (id: string): StudentCourseSummary => ({
  id,
  code: id,
  section: "Sec 1",
  teacherName: "Dr. Kim",
  nextDue: null,
  currentAssignmentTitle: null,
});

const thread = (id: string, courseId: string, updatedAt: string): ThreadSummary => ({
  id,
  courseId,
  courseCode: courseId,
  assignmentId: null,
  ownerRole: "student",
  title: "Chat",
  updatedAt,
});

const courses = [course("67-272"), course("15-213")];

describe("newChatCourse", () => {
  it("picks the course of the most recent chat, whatever order the chats come in", () => {
    const threads = [
      thread("a", "67-272", "2025-11-01T10:00:00Z"),
      thread("b", "15-213", "2025-11-04T10:00:00Z"),
      thread("c", "67-272", "2025-11-02T10:00:00Z"),
    ];
    expect(newChatCourse(courses, threads)?.id).toBe("15-213");
  });

  it("falls back to the first course when there are no chats", () => {
    expect(newChatCourse(courses, [])?.id).toBe("67-272");
  });

  it("skips chats from courses the student is no longer in", () => {
    const threads = [
      thread("a", "old-course", "2025-11-04T10:00:00Z"),
      thread("b", "15-213", "2025-11-01T10:00:00Z"),
    ];
    expect(newChatCourse(courses, threads)?.id).toBe("15-213");
  });

  it("returns null when the student has no courses", () => {
    expect(newChatCourse([], [])).toBeNull();
  });
});
