/**
 * The floating pill tab bar from the wireframes. The active tab is a teal
 * circle that springs between positions; the pill is frosted glass where the
 * OS supports it.
 */
import { BlurView } from "expo-blur";
import { GlassView, isLiquidGlassAvailable } from "expo-glass-effect";
import type { Tabs } from "expo-router";
import type { ComponentProps } from "react";
import { View } from "react-native";
import Animated, { useAnimatedStyle, withSpring } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { springs } from "@/lib/motion";

import { Icon, type IconName } from "./icon";
import { Tappable } from "./tappable";

type BottomTabBarProps = Parameters<NonNullable<ComponentProps<typeof Tabs>["tabBar"]>>[0];

const SLOT = 52;
const GAP = 6;

export function FloatingTabBar({ state, descriptors, emitter, navigateToTab }: BottomTabBarProps) {
  const insets = useSafeAreaInsets();
  const routes = state.routes.filter((route) => descriptors[route.key].options.tabBarIcon !== undefined);
  const activeIndex = Math.max(0, routes.findIndex((route) => route.key === state.routes[state.index].key));

  const indicator = useAnimatedStyle(() => ({
    transform: [{ translateX: withSpring(activeIndex * (SLOT + GAP), springs.snappy) }],
  }));

  const glass = isLiquidGlassAvailable();
  const Container = glass ? GlassView : BlurView;
  const containerProps = glass ? { glassEffectStyle: "regular" as const } : { intensity: 60, tint: "systemChromeMaterial" as const };

  return (
    <View pointerEvents="box-none" className="absolute inset-x-0 bottom-0 items-center" style={{ paddingBottom: insets.bottom + 6 }}>
      <Container
        {...containerProps}
        style={{ borderRadius: 999, overflow: "hidden", padding: 6, borderCurve: "continuous" }}
        className="border border-border"
      >
        <View className="flex-row" style={{ gap: GAP }}>
          <Animated.View
            className="absolute bg-accent"
            style={[{ width: SLOT, height: SLOT - 8, top: 4, borderRadius: 999 }, indicator]}
          />
          {routes.map((route, index) => {
            const focused = index === activeIndex;
            const { options } = descriptors[route.key];
            const icon = (options.tabBarIcon as unknown as () => IconName)();
            return (
              <Tappable
                key={route.key}
                accessibilityRole="tab"
                accessibilityState={{ selected: focused }}
                accessibilityLabel={options.title ?? route.name}
                className="items-center justify-center"
                style={{ width: SLOT, height: SLOT }}
                scale={0.9}
                onPress={() => {
                  const event = emitter.emit({ type: "tabPress", target: route.key, canPreventDefault: true });
                  if (!focused && !event.defaultPrevented) navigateToTab(route.key);
                }}
              >
                <Icon name={icon} size={19} color={focused ? "accent-foreground" : "muted"} />
              </Tappable>
            );
          })}
        </View>
      </Container>
    </View>
  );
}
