/**
 * The Nudge axolotl. v1 draws it with SVG and animates it with Reanimated:
 * it breathes, sways its gills and blinks, and gets livelier while thinking.
 *
 * v2 swaps the inside for a Rive state machine. Screens only use
 * <NudgeAvatar state=...>, so nothing else changes.
 */
import { useEffect } from "react";
import { View } from "react-native";
import Animated, {
  cancelAnimation,
  Easing,
  useAnimatedProps,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withSpring,
  withTiming,
} from "react-native-reanimated";
import Svg, { Circle, Ellipse, G, Path } from "react-native-svg";

import { springs } from "@/lib/motion";

export type AvatarState = "idle" | "thinking" | "happy";

const AnimatedG = Animated.createAnimatedComponent(G);
const AnimatedEllipse = Animated.createAnimatedComponent(Ellipse);

const SKIN = "#F8C3D1";
const GILL = "#EE8DA8";
const CHEEK = "#F29BB4";
const EYE = "#2A1A22";

type Props = { size?: number; state?: AvatarState };

export function NudgeAvatar({ size = 40, state = "idle" }: Props) {
  const reduceMotion = useReducedMotion();
  const sway = useSharedValue(0);
  const breathe = useSharedValue(0);
  const blink = useSharedValue(1);
  const bounce = useSharedValue(0);

  useEffect(() => {
    if (reduceMotion) return;
    const thinking = state === "thinking";
    const ease = Easing.inOut(Easing.sin);
    sway.value = withRepeat(withTiming(1, { duration: thinking ? 520 : 1600, easing: ease }), -1, true);
    breathe.value = withRepeat(withTiming(1, { duration: thinking ? 700 : 2200, easing: ease }), -1, true);
    blink.value = withRepeat(
      withSequence(
        withDelay(thinking ? 1400 : 3200, withTiming(0.1, { duration: 90 })),
        withTiming(1, { duration: 120 }),
      ),
      -1,
    );
    if (state === "happy") {
      bounce.value = withSequence(withSpring(-0.18, springs.bouncy), withSpring(0, springs.bouncy));
    }
    return () => {
      cancelAnimation(sway);
      cancelAnimation(breathe);
      cancelAnimation(blink);
    };
  }, [state, reduceMotion, sway, breathe, blink, bounce]);

  const body = useAnimatedStyle(() => ({
    transform: [
      { translateY: (bounce.value + (state === "thinking" ? -0.03 * breathe.value : 0)) * size },
      { scale: 1 + 0.025 * breathe.value },
    ],
  }));

  // Rotate each set of gills around where it meets the head.
  const leftGills = useAnimatedProps(() => ({
    transform: [
      { translateX: 26 },
      { translateY: 50 },
      { rotate: `${-7 + 14 * sway.value}deg` },
      { translateX: -26 },
      { translateY: -50 },
    ],
  }));
  const rightGills = useAnimatedProps(() => ({
    transform: [
      { translateX: 94 },
      { translateY: 50 },
      { rotate: `${7 - 14 * sway.value}deg` },
      { translateX: -94 },
      { translateY: -50 },
    ],
  }));
  const eyes = useAnimatedProps(() => ({ ry: 4.6 * blink.value }));

  return (
    <View style={{ width: size, height: size * (100 / 120) }} accessibilityRole="image" accessibilityLabel="Nudge">
      <Animated.View style={[{ flex: 1 }, body]}>
        <Svg width="100%" height="100%" viewBox="0 0 120 100">
          <AnimatedG animatedProps={leftGills}>
            <Path d="M28 46 C 14 38, 8 30, 6 22" stroke={GILL} strokeWidth={7} strokeLinecap="round" fill="none" />
            <Path d="M26 54 C 12 52, 5 48, 2 44" stroke={GILL} strokeWidth={7} strokeLinecap="round" fill="none" />
            <Path d="M28 62 C 16 66, 9 70, 6 76" stroke={GILL} strokeWidth={7} strokeLinecap="round" fill="none" />
          </AnimatedG>
          <AnimatedG animatedProps={rightGills}>
            <Path d="M92 46 C 106 38, 112 30, 114 22" stroke={GILL} strokeWidth={7} strokeLinecap="round" fill="none" />
            <Path d="M94 54 C 108 52, 115 48, 118 44" stroke={GILL} strokeWidth={7} strokeLinecap="round" fill="none" />
            <Path d="M92 62 C 104 66, 111 70, 114 76" stroke={GILL} strokeWidth={7} strokeLinecap="round" fill="none" />
          </AnimatedG>
          <Ellipse cx={60} cy={56} rx={37} ry={32} fill={SKIN} />
          <Ellipse cx={38} cy={66} rx={7} ry={4.5} fill={CHEEK} opacity={0.55} />
          <Ellipse cx={82} cy={66} rx={7} ry={4.5} fill={CHEEK} opacity={0.55} />
          <AnimatedEllipse cx={46} cy={54} rx={4.6} animatedProps={eyes} fill={EYE} />
          <AnimatedEllipse cx={74} cy={54} rx={4.6} animatedProps={eyes} fill={EYE} />
          <Circle cx={47.6} cy={52.4} r={1.4} fill="#fff" />
          <Circle cx={75.6} cy={52.4} r={1.4} fill="#fff" />
          <Path d="M53 67 Q 60 73, 67 67" stroke={EYE} strokeWidth={2.6} strokeLinecap="round" fill="none" />
        </Svg>
      </Animated.View>
    </View>
  );
}

/** The app mark from the wireframes: the axolotl on a soft mint tile. */
export function NudgeMark({ size = 56, state = "idle" }: Props) {
  return (
    <View
      className="items-center justify-center bg-mint-soft"
      style={{ width: size, height: size, borderRadius: size * 0.28, borderCurve: "continuous" }}
    >
      <NudgeAvatar size={size * 0.74} state={state} />
    </View>
  );
}
