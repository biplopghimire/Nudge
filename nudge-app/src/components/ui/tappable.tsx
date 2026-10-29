/**
 * The app's pressable: shrinks with a spring while held and gives a haptic tap.
 * Use it for anything tappable that isn't a HeroUI Button.
 */
import { type ReactNode } from "react";
import { Pressable, type PressableProps, type StyleProp, type ViewStyle } from "react-native";
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from "react-native-reanimated";

import { haptics } from "@/lib/haptics";
import { pressScale, springs } from "@/lib/motion";

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

type Props = Omit<PressableProps, "style" | "children"> & {
  children: ReactNode;
  className?: string;
  style?: StyleProp<ViewStyle>;
  scale?: number;
  haptic?: "tap" | "press" | "none";
};

export function Tappable({ children, className, style, scale = pressScale, haptic = "tap", onPress, ...rest }: Props) {
  const pressed = useSharedValue(0);
  const animated = useAnimatedStyle(() => ({
    transform: [{ scale: 1 - (1 - scale) * pressed.value }],
  }));

  return (
    <AnimatedPressable
      {...rest}
      className={className}
      style={[style, animated]}
      onPressIn={(event) => {
        pressed.value = withSpring(1, springs.snappy);
        rest.onPressIn?.(event);
      }}
      onPressOut={(event) => {
        pressed.value = withSpring(0, springs.snappy);
        rest.onPressOut?.(event);
      }}
      onPress={(event) => {
        if (haptic !== "none") haptics[haptic]();
        onPress?.(event);
      }}
    >
      {children}
    </AnimatedPressable>
  );
}
