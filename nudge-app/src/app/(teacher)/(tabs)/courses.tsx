import { router } from "expo-router";
import { Button, Skeleton } from "heroui-native";
import { RefreshControl, Text, View } from "react-native";
import Animated from "react-native-reanimated";

import { NudgeMark } from "@/components/brand/nudge-avatar";
import { Badge, EmptyState, Row } from "@/components/ui/list";
import { LargeTitle, Screen, SectionLabel } from "@/components/ui/screen";
import { enterRow } from "@/lib/motion";
import { useTeacherCourses } from "@/lib/queries";

export default function Courses() {
  const { data, isLoading, refetch, isRefetching } = useTeacherCourses();
  const current = data?.semesters.find((s) => s.isCurrent);
  const past = data?.semesters.filter((s) => !s.isCurrent) ?? [];

  return (
    <Screen tabBar refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={() => void refetch()} />}>
      <View className="h-6" />
      <LargeTitle title="Courses" />

      {isLoading ? (
        <Skeleton className="h-36 rounded-3xl" />
      ) : !data || data.semesters.length === 0 ? (
        <EmptyState
          art={<NudgeMark size={72} />}
          title="Set up your first course"
          body="Add your slides and notes, then share the join code with your class."
        />
      ) : (
        <>
          {current ? (
            <Animated.View entering={enterRow(0)} className="rounded-3xl bg-surface-secondary px-4 pb-1 pt-4" style={{ borderCurve: "continuous" }}>
              <View className="mb-1 flex-row items-center gap-2">
                <Text className="text-[15px] font-semibold text-foreground">{current.name}</Text>
                <Badge tone="mint">Current</Badge>
              </View>
              {current.courses.map((course, index) => (
                <Row
                  key={course.id}
                  index={index + 1}
                  title={`${course.code} · ${course.section}`}
                  subtitle={`${course.materialCount} materials · ${course.studentCount} students`}
                  divider={index < current.courses.length - 1}
                  onPress={() => router.push({ pathname: "/course/[id]", params: { id: course.id } })}
                />
              ))}
            </Animated.View>
          ) : null}

          {past.length > 0 ? <SectionLabel>Past semesters</SectionLabel> : null}
          {past.map((semester, index) => (
            <Row
              key={semester.name}
              index={index + 3}
              title={semester.name}
              subtitle={`${semester.courses.length} ${semester.courses.length === 1 ? "course" : "courses"} · ${[...new Set(semester.courses.map((c) => c.code))].join(", ")}`}
              chevron={false}
            />
          ))}
        </>
      )}

      <Button size="lg" className="mt-8 rounded-full" onPress={() => router.push("/course/new")}>
        <Button.Label>New course</Button.Label>
      </Button>
    </Screen>
  );
}
