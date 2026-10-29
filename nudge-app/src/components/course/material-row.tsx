/**
 * One course file on the teacher's course page. While Nudge reads it: a progress
 * bar, what step it's on and roughly how long is left. If it fails: why, and Retry.
 */
import type { Material } from "@api";
import { Spinner } from "heroui-native";
import { useEffect } from "react";
import { Text, View } from "react-native";
import Animated, {
  Easing,
  FadeIn,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSpring,
  withTiming,
  ZoomIn,
} from "react-native-reanimated";

import { Icon } from "@/components/ui/icon";
import { Tappable } from "@/components/ui/tappable";
import { fileSize } from "@/lib/format";
import { KIND_ICON, KIND_LABEL } from "@/lib/materials";
import { enterRow, springs } from "@/lib/motion";

export function timeLeft(seconds: number | null) {
  if (seconds == null) return null;
  if (seconds < 45) return "Less than a minute left";
  const minutes = Math.round(seconds / 60);
  return `About ${minutes} min left`;
}

export function MaterialRow({
  material,
  index,
  onRetry,
  retrying,
}: {
  material: Material;
  index: number;
  onRetry: () => void;
  retrying: boolean;
}) {
  const failed = material.status === "failed";
  return (
    <Animated.View entering={enterRow(index)} className="border-b border-separator py-4">
      <View className="flex-row items-center gap-3">
        <View className={`h-10 w-10 items-center justify-center rounded-xl ${failed ? "bg-blush" : "bg-surface-secondary"}`}>
          <Icon name={failed ? "warning" : KIND_ICON[material.kind]} size={16} color={failed ? "blush-foreground" : "accent"} />
        </View>
        <View className="flex-1">
          <Text className="text-[16px] font-semibold text-foreground" numberOfLines={1}>
            {material.title}
          </Text>
          <Text className="mt-0.5 text-[13px] text-muted" numberOfLines={1}>
            {material.restricted ? "Hidden from students" : KIND_LABEL[material.kind]} · {fileSize(material.sizeBytes)}
          </Text>
        </View>
        {material.status === "ready" ? (
          <Animated.View entering={ZoomIn.springify().damping(springs.bouncy.damping)}>
            <Icon name="checkCircle" size={20} color="success" />
          </Animated.View>
        ) : failed ? (
          <Tappable
            onPress={onRetry}
            disabled={retrying}
            haptic="press"
            className="flex-row items-center gap-1.5 rounded-full bg-surface-secondary px-3 py-1.5"
            accessibilityRole="button"
            accessibilityLabel={`Retry ${material.title}`}
          >
            {retrying ? <Spinner size="sm" /> : <Icon name="retry" size={12} color="accent" />}
            <Text className="text-[13px] font-semibold text-accent">Retry</Text>
          </Tappable>
        ) : (
          <Text className="text-[13px] font-semibold text-accent">{material.progress}%</Text>
        )}
      </View>

      {material.status === "processing" ? (
        <Animated.View entering={FadeIn} className="mt-3 pl-[52px]">
          <ProgressBar progress={material.progress} />
          <View className="mt-1.5 flex-row justify-between">
            <Text className="text-[12px] text-muted" numberOfLines={1}>
              {material.stage ?? "Reading the file"}
            </Text>
            {timeLeft(material.etaSeconds) ? (
              <Text className="text-[12px] text-muted">{timeLeft(material.etaSeconds)}</Text>
            ) : null}
          </View>
        </Animated.View>
      ) : null}

      {failed && material.error ? (
        <Animated.Text entering={FadeIn} className="mt-2 pl-[52px] text-[13px] leading-[18px] text-danger">
          {material.error}
        </Animated.Text>
      ) : null}
    </Animated.View>
  );
}

/** Springs to the new value; before the first progress report it shows a gentle sweep. */
function ProgressBar({ progress }: { progress: number }) {
  const fill = useSharedValue(0);
  const sweep = useSharedValue(0);
  const waiting = progress <= 1;

  useEffect(() => {
    fill.set(withSpring(Math.max(progress, 3) / 100, springs.smooth));
  }, [progress, fill]);

  useEffect(() => {
    sweep.set(waiting ? withRepeat(withTiming(1, { duration: 1100, easing: Easing.inOut(Easing.quad) }), -1, true) : 0);
  }, [waiting, sweep]);

  const fillStyle = useAnimatedStyle(() => ({
    width: waiting ? "30%" : `${fill.value * 100}%`,
    transform: [{ translateX: waiting ? sweep.value * 180 : 0 }],
  }));

  return (
    <View
      className="h-1.5 overflow-hidden rounded-full bg-surface-tertiary"
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: progress }}
    >
      <Animated.View className="h-full rounded-full bg-accent" style={fillStyle} />
    </View>
  );
}
