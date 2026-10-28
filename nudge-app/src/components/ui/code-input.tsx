/**
 * Six-box code entry (join codes). One hidden TextInput holds the text; the
 * boxes just draw it, with a springy focus ring and a blinking caret.
 */
import { type ComponentRef, forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withSpring,
  withTiming,
} from "react-native-reanimated";

import { springs } from "@/lib/motion";

export type CodeInputHandle = { focus: () => void; blur: () => void };

type Props = {
  value: string;
  onChange: (value: string) => void;
  onComplete?: (value: string) => void;
  length?: number;
  invalid?: boolean;
};

export const CodeInput = forwardRef<CodeInputHandle, Props>(function CodeInput(
  { value, onChange, onComplete, length = 6, invalid = false },
  ref,
) {
  const input = useRef<ComponentRef<typeof TextInput>>(null);
  const [focused, setFocused] = useState(false);
  useImperativeHandle(ref, () => ({ focus: () => input.current?.focus(), blur: () => input.current?.blur() }));

  return (
    <Pressable onPress={() => input.current?.focus()} accessibilityRole="none">
      <View className="flex-row justify-between" pointerEvents="none">
        {Array.from({ length }, (_, index) => (
          <Box
            key={index}
            char={value[index]}
            active={focused && index === Math.min(value.length, length - 1)}
            invalid={invalid}
          />
        ))}
      </View>
      <TextInput
        ref={input}
        value={value}
        onChangeText={(text) => {
          const clean = text.replace(/[^a-z0-9]/gi, "").slice(0, length);
          onChange(clean);
          if (clean.length === length) onComplete?.(clean);
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        maxLength={length}
        autoCapitalize="characters"
        autoCorrect={false}
        autoComplete="off"
        spellCheck={false}
        caretHidden
        accessibilityLabel={`Course code, ${value.length} of ${length} characters entered`}
        style={{ position: "absolute", inset: 0, opacity: 0.011, color: "transparent" }}
      />
    </Pressable>
  );
});

function Box({ char, active, invalid }: { char?: string; active: boolean; invalid: boolean }) {
  const ring = useSharedValue(0);
  const caret = useSharedValue(0);
  const pop = useSharedValue(1);

  useEffect(() => {
    ring.set(withSpring(active ? 1 : 0, springs.snappy));
    caret.set(active && !char ? withRepeat(withSequence(withTiming(1, { duration: 450 }), withTiming(0, { duration: 450 })), -1) : 0);
  }, [active, char, ring, caret]);

  useEffect(() => {
    if (char) pop.set(withSequence(withTiming(1.12, { duration: 70 }), withSpring(1, springs.bouncy)));
  }, [char, pop]);

  const boxStyle = useAnimatedStyle(() => ({ borderWidth: 2 * ring.value, transform: [{ scale: pop.value }] }));
  const caretStyle = useAnimatedStyle(() => ({ opacity: caret.value }));

  return (
    <Animated.View
      className={`h-14 w-12 items-center justify-center rounded-2xl bg-surface-secondary ${invalid ? "border-danger" : "border-accent"}`}
      style={[{ borderCurve: "continuous" }, boxStyle]}
    >
      {char ? (
        <Text className="text-[24px] font-semibold uppercase text-foreground">{char}</Text>
      ) : (
        <Animated.View className="h-6 w-0.5 rounded-full bg-accent" style={caretStyle} />
      )}
    </Animated.View>
  );
}
