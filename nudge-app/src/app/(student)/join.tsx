import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Clipboard from "expo-clipboard";
import { router } from "expo-router";
import { Button, Spinner } from "heroui-native";
import { useEffect, useRef, useState } from "react";
import { Text, View } from "react-native";
import { KeyboardStickyView } from "react-native-keyboard-controller";
import Animated, {
  FadeIn,
  FadeInDown,
  FadeOut,
  useAnimatedStyle,
  useSharedValue,
  withSequence,
  withTiming,
  ZoomIn,
} from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { NudgeMark } from "@/components/brand/nudge-avatar";
import { CodeInput, type CodeInputHandle } from "@/components/ui/code-input";
import { Icon } from "@/components/ui/icon";
import { BackButton } from "@/components/ui/screen";
import { Tappable } from "@/components/ui/tappable";
import { api, ApiError } from "@/lib/api";
import { haptics } from "@/lib/haptics";
import { springs } from "@/lib/motion";
import { keys } from "@/lib/queries";

// Pause between the last character and sending the code, so the final box can land,
// the keyboard can close, and the screen doesn't jump straight to "You're in!".
const SUBMIT_PAUSE_MS = 450;

export default function Join() {
  const insets = useSafeAreaInsets();
  const client = useQueryClient();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const shake = useSharedValue(0);
  const input = useRef<CodeInputHandle>(null);
  const pause = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [queued, setQueued] = useState(false);

  function cancelQueued() {
    if (pause.current) clearTimeout(pause.current);
    pause.current = null;
    setQueued(false);
  }

  useEffect(() => cancelQueued, []);

  // autoFocus fires while the sheet is still sliding up, so iOS ignores it. Focus once it has landed.
  useEffect(() => {
    const timer = setTimeout(() => input.current?.focus(), 450);
    return () => clearTimeout(timer);
  }, []);

  const join = useMutation({
    mutationFn: (joinCode: string) => api.joinCourse(joinCode),
    onSuccess: () => {
      haptics.success();
      client.invalidateQueries({ queryKey: keys.studentCourses });
      setTimeout(() => router.back(), 1400);
    },
    onError: (e) => {
      haptics.error();
      setError(e instanceof ApiError ? e.message : "Couldn't join. Try again.");
      shake.set(withSequence(...[-10, 10, -8, 8, -4, 0].map((x) => withTiming(x, { duration: 55 }))));
      input.current?.focus();
    },
  });

  const shakeStyle = useAnimatedStyle(() => ({ transform: [{ translateX: shake.value }] }));

  function submit(value = code) {
    cancelQueued();
    if (value.length === 6 && !join.isPending) {
      haptics.press();
      join.mutate(value.toUpperCase());
    }
  }

  // Typing or pasting the last character sends the code after a short pause instead of instantly.
  function submitAfterPause(value: string) {
    cancelQueued();
    input.current?.blur();
    setQueued(true);
    pause.current = setTimeout(() => submit(value), SUBMIT_PAUSE_MS);
  }

  async function paste() {
    const text = (await Clipboard.getStringAsync()).replace(/[^a-z0-9]/gi, "").slice(0, 6);
    if (!text) return;
    haptics.tap();
    setCode(text);
    setError(null);
    if (text.length === 6) submitAfterPause(text);
  }

  if (join.isSuccess) {
    const course = join.data.course;
    return (
      <Animated.View entering={FadeIn.duration(250)} className="flex-1 items-center justify-center bg-background px-8">
        <Animated.View entering={ZoomIn.springify().damping(springs.bouncy.damping)}>
          <NudgeMark size={104} state="happy" />
        </Animated.View>
        <Animated.Text entering={FadeInDown.delay(150)} className="mt-6 text-[26px] font-bold text-foreground">
          {"You're in!"}
        </Animated.Text>
        <Animated.Text entering={FadeInDown.delay(230)} className="mt-2 text-center text-[16px] text-muted">
          {course.code} · {course.section} with {course.teacherName}
        </Animated.Text>
      </Animated.View>
    );
  }

  const sending = queued || join.isPending;

  return (
    <Animated.View exiting={FadeOut.duration(200)} className="flex-1 bg-background" style={{ paddingTop: 16 }}>
      <View className="px-5">
        <BackButton label="Close" />
      </View>

      <Animated.View entering={FadeIn.duration(250)} className="px-6 pt-8">
        <NudgeMark size={64} />
        <Text className="mt-6 text-[30px] font-bold tracking-tight text-foreground">Join a course</Text>
        <Text className="mt-2 text-[16px] leading-6 text-muted">Enter the 6-character code from your teacher.</Text>

        <Animated.View style={shakeStyle} className="mt-8">
          <CodeInput
            ref={input}
            value={code}
            onChange={(value) => {
              cancelQueued();
              setCode(value);
              setError(null);
            }}
            onComplete={submitAfterPause}
            invalid={!!error}
          />
        </Animated.View>

        {error ? (
          <Animated.Text entering={FadeInDown} className="mt-3 text-[14px] font-medium text-danger">
            {error}
          </Animated.Text>
        ) : null}

        <Tappable onPress={paste} className="mt-5 flex-row items-center gap-2 self-start" accessibilityRole="button">
          <Icon name="clipboard" size={15} color="accent" />
          <Text className="text-[15px] font-semibold text-accent">Paste from clipboard</Text>
        </Tappable>
      </Animated.View>

      <KeyboardStickyView offset={{ opened: 12 }} style={{ marginTop: "auto" }}>
        <View className="px-6" style={{ paddingBottom: insets.bottom + 12 }}>
          <Button size="lg" className="rounded-full" onPress={() => submit()} isDisabled={code.length < 6 || sending}>
            {sending ? <Spinner color="accent-foreground" /> : <Button.Label>Join</Button.Label>}
          </Button>
        </View>
      </KeyboardStickyView>
    </Animated.View>
  );
}
