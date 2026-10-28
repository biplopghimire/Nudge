import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useToast } from "heroui-native";

import { api, ApiError } from "./api";
import { haptics } from "./haptics";
import { keys } from "./queries";

/** Start a chat in a course (optionally about an assignment) and open it. */
export function useStartChat() {
  const client = useQueryClient();
  const { toast } = useToast();
  return useMutation({
    mutationFn: (input: { courseId: string; assignmentId?: string; title: string }) => api.createThread(input),
    onSuccess: ({ thread }) => {
      client.setQueryData(keys.thread(thread.id), { thread, messages: [] });
      client.invalidateQueries({ queryKey: keys.threads });
      router.push({ pathname: "/chat/[id]", params: { id: thread.id } });
    },
    onError: (error) => {
      haptics.error();
      toast.show({ variant: "danger", label: "Couldn't start a chat", description: error instanceof ApiError ? error.message : undefined });
    },
  });
}
