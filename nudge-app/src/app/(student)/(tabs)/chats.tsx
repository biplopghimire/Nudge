import type { ThreadSummary } from "@api";
import { router } from "expo-router";
import { SearchField, Skeleton } from "heroui-native";
import { useMemo, useState } from "react";
import { RefreshControl, Text, View } from "react-native";

import { NudgeMark } from "@/components/brand/nudge-avatar";
import { Badge, EmptyState, Row } from "@/components/ui/list";
import { IconButton, LargeTitle, Screen, SectionLabel } from "@/components/ui/screen";
import { dayGroup, relativeTime } from "@/lib/format";
import { useStudentCourses, useThreads } from "@/lib/queries";
import { usePullToRefresh } from "@/lib/pull-to-refresh";
import { newChatCourse, startChat } from "@/lib/start-chat";

export default function Chats() {
  const { data, isLoading, refetch } = useThreads();
  const pullToRefresh = usePullToRefresh(refetch);
  const { data: courseData } = useStudentCourses();
  const [query, setQuery] = useState("");

  function newChat() {
    // Courses are normally cached from Home. If they haven't loaded, Home is where to pick one.
    if (!courseData) return router.navigate("/home");
    const course = newChatCourse(courseData.courses, data?.threads ?? []);
    if (!course) return router.push("/join");
    startChat({ courseId: course.id, courseCode: course.code, title: "New chat" });
  }

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const threads = (data?.threads ?? []).filter(
      (t) => !q || t.title.toLowerCase().includes(q) || t.courseCode.includes(q),
    );
    const byGroup = new Map<string, ThreadSummary[]>();
    for (const thread of threads) {
      const group = dayGroup(thread.updatedAt);
      byGroup.set(group, [...(byGroup.get(group) ?? []), thread]);
    }
    return [...byGroup.entries()];
  }, [data, query]);

  let index = 0;
  return (
    <Screen tabBar refreshControl={<RefreshControl {...pullToRefresh} />}>
      <LargeTitle title="Chats" trailing={<IconButton icon="compose" label="New chat" tone="accent" onPress={newChat} />} />

      <SearchField value={query} onChange={setQuery}>
        <SearchField.Group>
          <SearchField.SearchIcon />
          <SearchField.Input placeholder="Search chats" />
          <SearchField.ClearButton />
        </SearchField.Group>
      </SearchField>

      {isLoading ? (
        <View className="mt-6 gap-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-14 rounded-xl" />
          ))}
        </View>
      ) : groups.length === 0 ? (
        <EmptyState
          art={<NudgeMark size={72} />}
          title={query ? "No chats match" : "No chats yet"}
          body={query ? "Try a different word." : "Tap the pencil above to start your first chat."}
        />
      ) : (
        groups.map(([group, threads]) => (
          <View key={group}>
            <SectionLabel>{group}</SectionLabel>
            {threads.map((thread) => (
              <Row
                key={thread.id}
                index={index++}
                title={thread.title}
                trailing={
                  <View className="items-end gap-1">
                    <Badge tone="mint">{thread.courseCode}</Badge>
                    <Text className="text-[12px] text-muted">{relativeTime(thread.updatedAt)}</Text>
                  </View>
                }
                chevron={false}
                onPress={() => router.push({ pathname: "/chat/[id]", params: { id: thread.id } })}
              />
            ))}
          </View>
        ))
      )}
    </Screen>
  );
}
