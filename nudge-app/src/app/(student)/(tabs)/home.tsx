import { router } from "expo-router";
import { Button, Skeleton, Spinner } from "heroui-native";
import { RefreshControl, Text, View } from "react-native";
import Animated from "react-native-reanimated";

import { NudgeMark } from "@/components/brand/nudge-avatar";
import { Icon } from "@/components/ui/icon";
import { Badge, EmptyState, Row } from "@/components/ui/list";
import { LargeTitle, Screen, SectionLabel } from "@/components/ui/screen";
import { Tappable } from "@/components/ui/tappable";
import { useAuth } from "@/lib/auth";
import { dueLabel, greetingDate, initials } from "@/lib/format";
import { enterRow } from "@/lib/motion";
import { useStudentCourses } from "@/lib/queries";
import { useStartChat } from "@/lib/start-chat";

export default function Home() {
  const { user } = useAuth();
  const { data, isLoading, refetch, isRefetching } = useStudentCourses();
  const startChat = useStartChat();
  const upNext = data?.upNext;

  return (
    <Screen
      tabBar
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={() => void refetch()} />}
    >
      <View className="mb-4 flex-row items-center justify-between">
        <NudgeMark size={40} />
        <Tappable
          onPress={() => router.navigate("/profile")}
          className="h-9 w-9 items-center justify-center rounded-full bg-surface-secondary"
          accessibilityLabel="Profile"
        >
          <Text className="text-[14px] font-semibold text-foreground">{initials(user?.name ?? "")}</Text>
        </Tappable>
      </View>

      <LargeTitle caption={greetingDate()} title="Ready to work?" />

      {isLoading ? (
        <Skeleton className="h-[132px] rounded-3xl" />
      ) : upNext ? (
        <Animated.View entering={enterRow(0)} className="rounded-3xl bg-surface-secondary p-5" style={{ borderCurve: "continuous" }}>
          <Text className="text-[13px] font-medium text-muted">Up next</Text>
          <Text className="mt-1 text-[22px] font-bold tracking-tight text-foreground">{upNext.title}</Text>
          <View className="mt-4 flex-row items-center justify-between">
            <Text className="text-[14px] text-muted">
              {upNext.courseCode} · {dueLabel(upNext.dueAt)}
            </Text>
            <Button
              size="sm"
              className="rounded-full px-5"
              isDisabled={startChat.isPending}
              onPress={() =>
                startChat.mutate({ courseId: upNext.courseId, assignmentId: upNext.id, title: upNext.shortTitle })
              }
            >
              {startChat.isPending ? <Spinner size="sm" color="accent-foreground" /> : <Button.Label>Start</Button.Label>}
            </Button>
          </View>
        </Animated.View>
      ) : null}

      <SectionLabel>Courses</SectionLabel>
      {isLoading ? (
        <View className="gap-3">
          <Skeleton className="h-12 rounded-xl" />
          <Skeleton className="h-12 rounded-xl" />
        </View>
      ) : data && data.courses.length > 0 ? (
        <View>
          {data.courses.map((course, index) => (
            <Row
              key={course.id}
              index={index + 1}
              title={course.code}
              subtitle={`${course.section} · ${course.teacherName}`}
              trailing={course.nextDue ? <Badge>{course.nextDue}</Badge> : undefined}
              onPress={() => startChat.mutate({ courseId: course.id, title: "New chat" })}
            />
          ))}
          <Tappable onPress={() => router.push("/join")} className="flex-row items-center gap-2 py-4" accessibilityRole="button">
            <Icon name="plus" size={14} color="muted" />
            <Text className="text-[15px] font-medium text-muted">Add course</Text>
          </Tappable>
        </View>
      ) : (
        <EmptyState
          art={<NudgeMark size={72} />}
          title="No courses yet"
          body="Ask your teacher for the 6-character code, then join to start asking Nudge."
          action={
            <Button size="lg" className="rounded-full" onPress={() => router.push("/join")}>
              <Button.Label>Join a course</Button.Label>
            </Button>
          }
        />
      )}
    </Screen>
  );
}
