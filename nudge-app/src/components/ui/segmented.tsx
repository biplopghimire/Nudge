/** Two-or-more option switch with a sliding thumb (iOS segmented control feel). */
import { useState } from "react";
import { type LayoutChangeEvent, Text, View } from "react-native";
import Animated, { useAnimatedStyle, withSpring } from "react-native-reanimated";

import { springs } from "@/lib/motion";

import { Tappable } from "./tappable";

export function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  const [width, setWidth] = useState(0);
  const index = Math.max(0, options.findIndex((o) => o.value === value));
  const slot = width / options.length;

  const thumb = useAnimatedStyle(() => ({
    width: slot,
    transform: [{ translateX: withSpring(index * slot, springs.snappy) }],
  }));

  return (
    <View
      className="flex-row rounded-full bg-surface-secondary p-1"
      onLayout={(e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width - 8)}
      accessibilityRole="tablist"
    >
      {width > 0 ? (
        <Animated.View
          className="absolute bottom-1 left-1 top-1 rounded-full bg-surface"
          style={[thumb, { shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 6, shadowOffset: { width: 0, height: 2 } }]}
        />
      ) : null}
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <Tappable
            key={option.value}
            className="flex-1 items-center py-2.5"
            onPress={() => onChange(option.value)}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            scale={0.97}
          >
            <Text className={`text-[14px] font-semibold ${selected ? "text-foreground" : "text-muted"}`}>
              {option.label}
            </Text>
          </Tappable>
        );
      })}
    </View>
  );
}
