/** The "Up next" card on student Home: the next assignment due, or a note that nothing is. */
import type { Assignment } from "@api";
import { Button } from "heroui-native";
import { Text, View } from "react-native";
import Animated from "react-native-reanimated";

import { NudgeMark } from "@/components/brand/nudge-avatar";
import { dueLabel } from "@/lib/format";
import { enterRow } from "@/lib/motion";

type Props = {
  /** The assignment due soonest across the student's courses, or null when nothing is due. */
  assignment: Assignment | null;
  onStart: (assignment: Assignment) => void;
};

export function UpNextCard({ assignment, onStart }: Props) {
  return (
    <Animated.View entering={enterRow(0)} className="rounded-3xl bg-surface-secondary p-5" style={{ borderCurve: "continuous" }}>
      {assignment ? (
        <>
          <Text className="text-[13px] font-medium text-muted">Up next</Text>
          <Text className="mt-1 text-[22px] font-bold tracking-tight text-foreground">{assignment.title}</Text>
          <View className="mt-4 flex-row items-center justify-between gap-3">
            <Text className="flex-1 text-[14px] text-muted" numberOfLines={1}>
              {assignment.courseCode} · {dueLabel(assignment.dueAt)}
            </Text>
            <Button
              className="rounded-full px-6"
              onPress={() => onStart(assignment)}
              accessibilityLabel={`Start ${assignment.title}`}
            >
              <Button.Label>Start</Button.Label>
            </Button>
          </View>
        </>
      ) : (
        <View className="flex-row items-center gap-4">
          <NudgeMark size={48} state="happy" />
          <View className="flex-1">
            <Text className="text-[13px] font-medium text-muted">Up next</Text>
            <Text className="mt-1 text-[19px] font-bold tracking-tight text-foreground">{"You're all caught up"}</Text>
            <Text className="mt-0.5 text-[14px] text-muted">Nothing due right now.</Text>
          </View>
        </View>
      )}
    </Animated.View>
  );
}
