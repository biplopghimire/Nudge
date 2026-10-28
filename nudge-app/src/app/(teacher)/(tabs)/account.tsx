import type { GetTeacherMeResponse, TeacherNotifications } from "@api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "heroui-native";
import { View } from "react-native";

import { ProfileHeader, SignOutRow, StatTiles, SwitchRow } from "@/components/ui/profile";
import { Screen, SectionLabel } from "@/components/ui/screen";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { keys, useTeacherMe } from "@/lib/queries";

export default function Account() {
  const { user, signOut } = useAuth();
  const me = useTeacherMe();
  const client = useQueryClient();

  const notify = useMutation({
    mutationFn: (changes: Partial<TeacherNotifications>) => api.updateTeacherNotifications(changes),
    onMutate: (changes) => {
      const previous = client.getQueryData<GetTeacherMeResponse>(keys.teacherMe);
      if (previous) client.setQueryData(keys.teacherMe, { ...previous, notifications: { ...previous.notifications, ...changes } });
      return { previous };
    },
    onError: (_e, _c, context) => context?.previous && client.setQueryData(keys.teacherMe, context.previous),
  });

  return (
    <Screen tabBar>
      <View className="h-4" />
      <ProfileHeader name={user?.name ?? ""} detail={me.data?.user.department ?? user?.email ?? ""} />
      {me.data ? (
        <StatTiles
          stats={[
            { value: me.data.stats.sectionsNow, label: "Sections now" },
            { value: me.data.stats.students, label: "Students" },
            { value: me.data.stats.semesters, label: "Semesters" },
          ]}
        />
      ) : (
        <Skeleton className="h-[88px] rounded-2xl" />
      )}

      <SectionLabel>Notifications</SectionLabel>
      {me.data ? (
        <>
          <SwitchRow
            index={2}
            title="Flagged answers"
            description="When students flag a Nudge reply"
            value={me.data.notifications.flaggedAnswers}
            onChange={(flaggedAnswers) => notify.mutate({ flaggedAnswers })}
          />
          <SwitchRow
            index={3}
            title="Weekly digest"
            description="Trending questions every Monday"
            value={me.data.notifications.weeklyDigest}
            onChange={(weeklyDigest) => notify.mutate({ weeklyDigest })}
          />
        </>
      ) : null}

      <SignOutRow onPress={signOut} />
    </Screen>
  );
}
