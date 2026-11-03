import { router } from "expo-router";

/** The `id` of a chat that isn't saved yet. It is created when its first message is sent. */
export const NEW_CHAT_ID = "new";

export type ChatDraft = { courseId: string; courseCode: string; assignmentId?: string; title: string };

/** Open a new chat in a course (optionally about an assignment). Nothing is saved until the first message. */
export function startChat(draft: ChatDraft) {
  router.push({ pathname: "/chat/[id]", params: { id: NEW_CHAT_ID, ...draft } });
}
