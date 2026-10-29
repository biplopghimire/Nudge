import type { GetStudentMeResponse, StudentNotifications } from "@api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { Skeleton } from "heroui-native";
import { Text, View } from "react-native";

import { Icon } from "@/components/ui/icon";
import { Row } from "@/components/ui/list";
import { ProfileHeader, SignOutRow, StatTiles, SwitchRow } from "@/components/ui/profile";
import { Screen, SectionLabel } from "@/components/ui/screen";
import { Tappable } from "@/components/ui/tappable";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { keys, useStudentCourses, useStudentMe } from "@/lib/queries";

export default function Profile() {
  const { user, signOut } = useAuth();
  const me = useStudentMe();
  const courses = useStudentCourses();
  const client = useQueryClient();

  const notify = useMutation({
    mutationFn: (changes: Partial<StudentNotifications>) => api.updateStudentNotifications(changes),
    onMutate: (changes) => {
      const previous = client.getQueryData<GetStudentMeResponse>(keys.studentMe);
      if (previous) client.setQueryData(keys.studentMe, { ...previous, notifications: { ...previous.notifications, ...changes } });
      return { previous };
    },
    onError: (_e, _c, context) => context?.previous && client.setQueryData(keys.studentMe, context.previous),
  });

  return (
    <Screen tabBar>
      <View className="h-4" />
      <ProfileHeader name={user?.name ?? ""} detail={user?.email ?? ""} />

      {me.data ? (
        <StatTiles
          stats={[
            { value: me.data.stats.questionsAsked, label: "Questions asked" },
            { value: me.data.stats.problemsSolved, label: "Problems worked on" },
            { value: me.data.stats.photosChecked, label: "Photos checked" },
          ]}
        />
      ) : (
        <Skeleton className="h-[88px] rounded-2xl" />
      )}

      <SectionLabel>My courses</SectionLabel>
      {courses.data?.courses.map((course, index) => (
        <Row key={course.id} index={index + 2} title={course.code} subtitle={`${course.section} · ${course.teacherName}`} />
      ))}
      <Tappable onPress={() => router.push("/join")} className="flex-row items-center gap-2 py-4" accessibilityRole="button">
        <Icon name="plus" size={14} color="accent" />
        <Text className="text-[15px] font-semibold text-accent">Join a course</Text>
      </Tappable>

      <SectionLabel>Notifications</SectionLabel>
      {me.data ? (
        <>
          <SwitchRow
            index={4}
            title="Deadline reminders"
            description="A day before anything is due"
            value={me.data.notifications.deadlineReminders}
            onChange={(deadlineReminders) => notify.mutate({ deadlineReminders })}
          />
          <SwitchRow
            index={5}
            title="Study nudges"
            description="A check-in if you go quiet"
            value={me.data.notifications.studyNudges}
            onChange={(studyNudges) => notify.mutate({ studyNudges })}
          />
        </>
      ) : null}

      <SignOutRow onPress={signOut} />
    </Screen>
  );
}
