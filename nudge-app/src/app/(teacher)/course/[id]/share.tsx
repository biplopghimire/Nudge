import * as Clipboard from "expo-clipboard";
import { router, useLocalSearchParams } from "expo-router";
import { Button } from "heroui-native";
import { useState } from "react";
import { Share, Text, View } from "react-native";
import Animated, { FadeInDown, ZoomIn } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { NudgeMark } from "@/components/brand/nudge-avatar";
import { Icon } from "@/components/ui/icon";
import { Tappable } from "@/components/ui/tappable";
import { haptics } from "@/lib/haptics";
import { springs } from "@/lib/motion";

/** The join code, big, with copy and share. Shown after creating a course. */
export default function ShareCode() {
  const { id, code = "", name = "" } = useLocalSearchParams<{ id: string; code: string; name: string }>();
  const insets = useSafeAreaInsets();
  const [copied, setCopied] = useState(false);

  async function copy() {
    await Clipboard.setStringAsync(code);
    haptics.success();
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  }

  return (
    <View className="flex-1 bg-background px-6" style={{ paddingBottom: insets.bottom + 12 }}>
      <View className="flex-1 items-center justify-center">
        <Animated.View entering={ZoomIn.springify().damping(springs.bouncy.damping)}>
          <NudgeMark size={84} state="happy" />
        </Animated.View>
        <Animated.Text entering={FadeInDown.delay(120)} className="mt-6 text-[26px] font-bold tracking-tight text-foreground">
          Course created
        </Animated.Text>
        <Animated.Text entering={FadeInDown.delay(180)} className="mt-1 text-[16px] text-muted">
          Share this code with {name || "your class"}
        </Animated.Text>

        <View className="mt-10 flex-row gap-2" accessible accessibilityLabel={`Join code ${code.split("").join(" ")}`}>
          {code.split("").map((char, index) => (
            <Animated.View
              key={index}
              entering={ZoomIn.delay(260 + index * 70).springify().damping(springs.bouncy.damping)}
              className="h-16 w-12 items-center justify-center rounded-2xl bg-mint-soft"
            >
              <Text className="text-[30px] font-bold text-mint-foreground">{char}</Text>
            </Animated.View>
          ))}
        </View>

        <Animated.View entering={FadeInDown.delay(760)} className="mt-8 flex-row gap-3">
          <Tappable onPress={copy} className="flex-row items-center gap-2 rounded-full bg-surface-secondary px-5 py-3" accessibilityRole="button">
            <Icon name={copied ? "check" : "copy"} size={15} color="accent" />
            <Text className="text-[15px] font-semibold text-accent">{copied ? "Copied" : "Copy"}</Text>
          </Tappable>
          <Tappable
            onPress={() => Share.share({ message: `Join ${name} on Nudge with code ${code}` })}
            className="flex-row items-center gap-2 rounded-full bg-surface-secondary px-5 py-3"
            accessibilityRole="button"
          >
            <Icon name="share" size={15} color="accent" />
            <Text className="text-[15px] font-semibold text-accent">Share</Text>
          </Tappable>
        </Animated.View>
      </View>

      <Button size="lg" className="rounded-full" onPress={() => router.replace({ pathname: "/course/[id]", params: { id } })}>
        <Button.Label>Done</Button.Label>
      </Button>
    </View>
  );
}
