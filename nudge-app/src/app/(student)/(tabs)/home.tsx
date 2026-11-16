import { router } from "expo-router";
import { Button, Skeleton } from "heroui-native";
import { RefreshControl, Text, View } from "react-native";

import { NudgeMark } from "@/components/brand/nudge-avatar";
import { UpNextCard } from "@/components/home/up-next-card";
import { Icon } from "@/components/ui/icon";
import { Badge, EmptyState, Row } from "@/components/ui/list";
import { LargeTitle, Screen, SectionLabel } from "@/components/ui/screen";
import { Tappable } from "@/components/ui/tappable";
import { useAuth } from "@/lib/auth";
import { greetingDate, initials } from "@/lib/format";
import { useStudentCourses } from "@/lib/queries";
import { usePullToRefresh } from "@/lib/pull-to-refresh";
import { startChat } from "@/lib/start-chat";

export default function Home() {
  const { user } = useAuth();
  const { data, isLoading, refetch } = useStudentCourses();
  const pullToRefresh = usePullToRefresh(refetch);
  const upNext = data?.upNext;

  return (
    <Screen
      tabBar
      refreshControl={<RefreshControl {...pullToRefresh} />}
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
      ) : data && data.courses.length > 0 ? (
        // With no courses yet, the "No courses yet" state below says what to do instead.
        <UpNextCard
          assignment={upNext ?? null}
          onStart={(assignment) =>
            startChat({
              courseId: assignment.courseId,
              courseCode: assignment.courseCode,
              assignmentId: assignment.id,
              title: assignment.shortTitle,
            })
          }
        />
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
              // Blush marks the course whose assignment is in the Up next card; the rest are mint.
              trailing={
                course.nextDue ? (
                  <Badge tone={course.id === upNext?.courseId ? "blush" : "mint"}>{course.nextDue}</Badge>
                ) : undefined
              }
              onPress={() => startChat({ courseId: course.id, courseCode: course.code, title: "New chat" })}
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
