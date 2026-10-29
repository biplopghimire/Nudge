/** Pieces shared by the student and teacher profile screens. */
import { Switch } from "heroui-native";
import { type ReactNode } from "react";
import { Text, View } from "react-native";
import Animated from "react-native-reanimated";

import { initials } from "@/lib/format";
import { haptics } from "@/lib/haptics";
import { enterRow } from "@/lib/motion";

import { Icon } from "./icon";
import { Tappable } from "./tappable";

export function ProfileHeader({ name, detail }: { name: string; detail: string }) {
  return (
    <Animated.View entering={enterRow(0)} className="mb-6 flex-row items-center gap-4">
      <View className="h-16 w-16 items-center justify-center rounded-full bg-mint-soft">
        <Text className="text-[26px] font-bold text-mint-foreground">{initials(name)}</Text>
      </View>
      <View className="flex-1">
        <Text className="text-[24px] font-bold tracking-tight text-foreground">{name}</Text>
        <Text className="text-[14px] text-muted">{detail}</Text>
      </View>
    </Animated.View>
  );
}

export function StatTiles({ stats }: { stats: { value: number; label: string }[] }) {
  return (
    <Animated.View entering={enterRow(1)} className="flex-row gap-3">
      {stats.map((stat) => (
        <View key={stat.label} className="flex-1 rounded-2xl bg-surface-secondary p-4" style={{ borderCurve: "continuous" }}>
          <Text className="text-[24px] font-bold text-foreground">{stat.value}</Text>
          <Text className="mt-1 text-[12px] leading-4 text-muted">{stat.label}</Text>
        </View>
      ))}
    </Animated.View>
  );
}

export function SwitchRow({
  title,
  description,
  value,
  onChange,
  index = 0,
}: {
  title: string;
  description: string;
  value: boolean;
  onChange: (value: boolean) => void;
  index?: number;
}) {
  return (
    <Animated.View entering={enterRow(index)} className="flex-row items-center gap-4 border-b border-separator py-4">
      <View className="flex-1">
        <Text className="text-[16px] font-semibold text-foreground">{title}</Text>
        <Text className="mt-0.5 text-[13px] leading-4 text-muted">{description}</Text>
      </View>
      <Switch
        isSelected={value}
        onSelectedChange={(next: boolean) => {
          haptics.tap();
          onChange(next);
        }}
        accessibilityLabel={title}
      />
    </Animated.View>
  );
}

export function SignOutRow({ onPress, children }: { onPress: () => void; children?: ReactNode }) {
  return (
    <Tappable onPress={onPress} className="mt-8 flex-row items-center gap-2 py-3" accessibilityRole="button" haptic="press">
      <Icon name="signOut" size={16} color="danger" />
      <Text className="text-[16px] font-semibold text-danger">{children ?? "Sign out"}</Text>
    </Tappable>
  );
}
