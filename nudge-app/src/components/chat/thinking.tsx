/**
 * What Nudge shows while it works: the axolotl in its thinking state and a
 * shimmering status line that moves through the steps it's actually doing
 * (search, read, write). Muse-style layered status.
 */
import { Canvas, LinearGradient, matchFont, Text as SkiaText, vec } from "@shopify/react-native-skia";
import { useEffect, useState } from "react";
import { Platform, View } from "react-native";
import Animated, {
  Easing,
  FadeIn,
  FadeOut,
  useDerivedValue,
  useSharedValue,
  withRepeat,
  withTiming,
} from "react-native-reanimated";
import { useCSSVariable } from "uniwind";

import { NudgeAvatar } from "@/components/brand/nudge-avatar";

const STEPS = [
  { after: 0, text: "Searching your course materials" },
  { after: 1600, text: "Reading the most relevant pages" },
  { after: 3600, text: "Writing your answer" },
  { after: 9000, text: "Still working on it" },
];

const font = matchFont({
  fontFamily: Platform.select({ ios: "Helvetica Neue", default: "sans-serif" }),
  fontSize: 15,
  fontWeight: "500",
});

export function Thinking({ withPhoto = false }: { withPhoto?: boolean }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timers = STEPS.slice(1).map((s, i) => setTimeout(() => setStep(i + 1), s.after));
    return () => timers.forEach(clearTimeout);
  }, []);

  const text = step === 0 && withPhoto ? "Looking at your photo" : STEPS[step].text;

  return (
    <Animated.View entering={FadeIn.duration(220)} exiting={FadeOut.duration(150)} className="flex-row items-center gap-3 py-2">
      <NudgeAvatar size={34} state="thinking" />
      <Animated.View key={text} entering={FadeIn.duration(260)} exiting={FadeOut.duration(160)}>
        <Shimmer text={text} />
      </Animated.View>
    </Animated.View>
  );
}

function Shimmer({ text }: { text: string }) {
  const muted = useCSSVariable("--muted");
  const fg = useCSSVariable("--foreground");
  const base = typeof muted === "string" ? muted : "#6b7a7c";
  const shine = typeof fg === "string" ? fg : "#0f1b1d";
  const width = Math.ceil(font.measureText(text).width) + 4;

  const progress = useSharedValue(0);
  useEffect(() => {
    progress.value = withRepeat(withTiming(1, { duration: 1500, easing: Easing.inOut(Easing.quad) }), -1, false);
  }, [progress]);

  const start = useDerivedValue(() => vec(-width + progress.value * width * 2, 0));
  const end = useDerivedValue(() => vec(progress.value * width * 2, 0));

  return (
    <View accessible accessibilityRole="text" accessibilityLabel={text}>
      <Canvas style={{ width, height: 22 }}>
        <SkiaText x={0} y={16} text={text} font={font}>
          <LinearGradient start={start} end={end} colors={[base, base, shine, base, base]} positions={[0, 0.35, 0.5, 0.65, 1]} />
        </SkiaText>
      </Canvas>
    </View>
  );
}
