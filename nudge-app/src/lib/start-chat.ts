import type { StudentCourseSummary, ThreadSummary } from "@api";
import { router } from "expo-router";

/** The `id` of a chat that isn't saved yet. It is created when its first message is sent. */
export const NEW_CHAT_ID = "new";

export type ChatDraft = { courseId: string; courseCode: string; assignmentId?: string; title: string };

/** Open a new chat in a course (optionally about an assignment). Nothing is saved until the first message. */
export function startChat(draft: ChatDraft) {
  router.push({ pathname: "/chat/[id]", params: { id: NEW_CHAT_ID, ...draft } });
}

/**
 * The course a new chat should open in when the student hasn't picked one (the
 * compose button on Chats): the course of their most recent chat, else their
 * first course. Null when they have no courses.
 */
export function newChatCourse(courses: StudentCourseSummary[], threads: ThreadSummary[]): StudentCourseSummary | null {
  const recent = [...threads].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  for (const thread of recent) {
    const course = courses.find((c) => c.id === thread.courseId);
    if (course) return course;
  }
  return courses[0] ?? null;
}
