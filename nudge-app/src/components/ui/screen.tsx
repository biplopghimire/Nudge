import { router } from "expo-router";
import { type ReactNode } from "react";
import { ScrollView, type ScrollViewProps, Text, View } from "react-native";
import Animated from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { enterFade } from "@/lib/motion";

import { Icon, type IconName } from "./icon";
import { Tappable } from "./tappable";

/** Full-screen scrollable page with safe-area padding and room for the tab bar. */
export function Screen({
  children,
  scroll = true,
  tabBar = false,
  contentClassName = "",
  ...rest
}: { children: ReactNode; scroll?: boolean; tabBar?: boolean; contentClassName?: string } & ScrollViewProps) {
  const insets = useSafeAreaInsets();
  const bottom = insets.bottom + (tabBar ? 96 : 24);
  if (!scroll) {
    return (
      <View className="flex-1 bg-background" style={{ paddingTop: insets.top, paddingBottom: insets.bottom }}>
        {children}
      </View>
    );
  }
  return (
    <ScrollView
      className="flex-1 bg-background"
      contentContainerClassName={`px-5 ${contentClassName}`}
      contentContainerStyle={{ paddingTop: insets.top + 8, paddingBottom: bottom }}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
      {...rest}
    >
      {children}
    </ScrollView>
  );
}

/** Round icon button used in headers (back, close, compose). */
export function IconButton({
  icon,
  onPress,
  label,
  tone = "default",
}: {
  icon: IconName;
  onPress: () => void;
  label: string;
  tone?: "default" | "accent";
}) {
  return (
    <Tappable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      hitSlop={8}
      className={`h-10 w-10 items-center justify-center rounded-full ${tone === "accent" ? "bg-accent" : "bg-surface-secondary"}`}
    >
      <Icon name={icon} size={16} color={tone === "accent" ? "accent-foreground" : "foreground"} />
    </Tappable>
  );
}

export function BackButton({ label = "Back" }: { label?: string }) {
  return <IconButton icon="chevronLeft" label={label} onPress={() => router.back()} />;
}

/** Big bold page title with an optional small caption above it (wireframe style). */
export function LargeTitle({ title, caption, trailing }: { title: string; caption?: string; trailing?: ReactNode }) {
  return (
    <Animated.View entering={enterFade} className="mb-6 flex-row items-end justify-between">
      <View className="flex-1">
        {caption ? <Text className="mb-1 text-[13px] font-medium text-muted">{caption}</Text> : null}
        <Text className="text-[30px] font-bold tracking-tight text-foreground" accessibilityRole="header">
          {title}
        </Text>
      </View>
      {trailing}
    </Animated.View>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <Text className="mb-2 mt-7 text-[13px] font-medium text-muted">{children}</Text>;
}
