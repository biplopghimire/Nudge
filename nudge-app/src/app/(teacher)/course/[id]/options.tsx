import { useLocalSearchParams } from "expo-router";
import { Skeleton } from "heroui-native";
import { Text, View } from "react-native";

import { Badge } from "@/components/ui/list";
import { SwitchRow } from "@/components/ui/profile";
import { BackButton, Screen, SectionLabel } from "@/components/ui/screen";
import { useTeacherCourse, useUpdateSettings } from "@/lib/queries";

/** How Nudge helps in this course (wireframe: Teacher · Options). */
export default function Options() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data } = useTeacherCourse(id);
  const update = useUpdateSettings(id);
  const settings = data?.settings;

  return (
    <Screen>
      <View className="flex-row items-center justify-between">
        <BackButton />
        {data ? <Badge tone="mint">{`${data.course.code} · ${data.course.section}`}</Badge> : null}
      </View>
      <Text className="mb-2 mt-6 text-[30px] font-bold tracking-tight text-foreground">Options</Text>

      {!settings ? (
        <Skeleton className="mt-6 h-48 rounded-2xl" />
      ) : (
        <>
          <SectionLabel>How Nudge helps</SectionLabel>
          <SwitchRow
            index={0}
            title="Hints only"
            description="Guide students, never hand over answers"
            value={settings.hintsOnly}
            onChange={(hintsOnly) => update.mutate({ hintsOnly })}
          />
          <SwitchRow
            index={1}
            title="Use solution keys"
            description="Check students' work against your keys, never shown to them"
            value={settings.useSolutionKeys}
            onChange={(useSolutionKeys) => update.mutate({ useSolutionKeys })}
          />
          <SwitchRow
            index={2}
            title="Cite course materials"
            description="Link each answer back to your slides"
            value={settings.citeMaterials}
            onChange={(citeMaterials) => update.mutate({ citeMaterials })}
          />

          <SectionLabel>Students</SectionLabel>
          <SwitchRow
            index={3}
            title="Deadline reminders"
            description="Remind students before work is due"
            value={settings.deadlineReminders}
            onChange={(deadlineReminders) => update.mutate({ deadlineReminders })}
          />
        </>
      )}
    </Screen>
  );
}
