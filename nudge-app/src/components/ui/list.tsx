import { type ReactNode } from "react";
import { Text, View } from "react-native";
import Animated from "react-native-reanimated";

import { enterRow } from "@/lib/motion";

import { Icon, type IconName } from "./icon";
import { Tappable } from "./tappable";

/** A tappable row: title, optional subtitle, trailing content and a chevron. */
export function Row({
  title,
  subtitle,
  trailing,
  icon,
  onPress,
  index = 0,
  chevron = true,
  divider = true,
}: {
  title: string;
  subtitle?: string;
  trailing?: ReactNode;
  icon?: IconName;
  onPress?: () => void;
  index?: number;
  chevron?: boolean;
  divider?: boolean;
}) {
  const body = (
    <View className={`flex-row items-center gap-3 py-4 ${divider ? "border-b border-separator" : ""}`}>
      {icon ? (
        <View className="h-9 w-9 items-center justify-center rounded-xl bg-surface-secondary">
          <Icon name={icon} size={16} color="accent" />
        </View>
      ) : null}
      <View className="flex-1">
        <Text className="text-[17px] font-semibold text-foreground" numberOfLines={1}>
          {title}
        </Text>
        {subtitle ? (
          <Text className="mt-0.5 text-[13px] text-muted" numberOfLines={1}>
            {subtitle}
          </Text>
        ) : null}
      </View>
      {trailing}
      {chevron && onPress ? <Icon name="chevronRight" size={13} color="muted" /> : null}
    </View>
  );
  return (
    <Animated.View entering={enterRow(index)}>
      {onPress ? (
        <Tappable onPress={onPress} scale={0.98} accessibilityRole="button" accessibilityLabel={title}>
          {body}
        </Tappable>
      ) : (
        body
      )}
    </Animated.View>
  );
}

/** Small rounded pill, e.g. the blush "PS 4 · Thu" due badge. */
export function Badge({ children, tone = "blush" }: { children: ReactNode; tone?: "blush" | "mint" | "muted" }) {
  const styles = {
    blush: "bg-blush text-blush-foreground",
    mint: "bg-mint-soft text-mint-foreground",
    muted: "bg-surface-secondary text-muted",
  }[tone];
  const [bg, fg] = styles.split(" ");
  return (
    <View className={`rounded-full px-2.5 py-1 ${bg}`}>
      <Text className={`text-[12px] font-semibold ${fg}`}>{children}</Text>
    </View>
  );
}

/** Friendly empty state with the axolotl or an icon. */
export function EmptyState({
  art,
  title,
  body,
  action,
}: {
  art: ReactNode;
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <Animated.View entering={enterRow(1)} className="items-center px-8 py-12">
      {art}
      <Text className="mt-5 text-center text-[19px] font-semibold text-foreground">{title}</Text>
      <Text className="mt-2 text-center text-[15px] leading-5 text-muted">{body}</Text>
      {action ? <View className="mt-6 w-full">{action}</View> : null}
    </Animated.View>
  );
}
