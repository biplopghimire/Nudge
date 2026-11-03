import type { AttachmentSource } from "@api";
import { BlurView } from "expo-blur";
import { Image } from "expo-image";
import { type ComponentRef, forwardRef } from "react";
import { Text, TextInput, View } from "react-native";
import Animated, { useAnimatedStyle, withSpring, ZoomIn, ZoomOut } from "react-native-reanimated";
import { useCSSVariable } from "uniwind";

import { Icon } from "@/components/ui/icon";
import { Tappable } from "@/components/ui/tappable";
import { springs } from "@/lib/motion";

export type PendingAttachment = { uri: string; name: string; type: string; source: AttachmentSource };

type Props = {
  value: string;
  onChangeText: (text: string) => void;
  onSend: () => void;
  onPlus: () => void;
  attachment: PendingAttachment | null;
  onRemoveAttachment: () => void;
  busy: boolean;
  placeholder?: string;
};

export const Composer = forwardRef<ComponentRef<typeof View>, Props>(function Composer(
  { value, onChangeText, onSend, onPlus, attachment, onRemoveAttachment, busy, placeholder = "Ask Nudge…" },
  ref,
) {
  const canSend = (value.trim().length > 0 || attachment !== null) && !busy;
  const placeholderColor = useCSSVariable("--field-placeholder");
  const foreground = useCSSVariable("--foreground");

  const sendStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(canSend ? 1 : 0.82, springs.bouncy) }],
    opacity: withSpring(canSend ? 1 : 0.35, springs.snappy),
  }));

  return (
    <View ref={ref} className="px-3 pb-2 pt-1">
      <BlurView
        intensity={40}
        tint="systemChromeMaterial"
        className="overflow-hidden rounded-[26px] border border-border"
        style={{ borderCurve: "continuous" }}
      >
        {attachment ? (
          <Animated.View entering={ZoomIn.springify().damping(springs.bouncy.damping)} exiting={ZoomOut.duration(140)} className="flex-row px-3 pt-3">
            <View>
              {attachment.type === "application/pdf" ? (
                <View className="h-16 w-16 items-center justify-center rounded-2xl bg-surface-secondary">
                  <Icon name="doc" size={22} color="accent" />
                  <Text className="mt-1 text-[10px] font-semibold text-muted">PDF</Text>
                </View>
              ) : (
                <Image source={{ uri: attachment.uri }} style={{ width: 64, height: 64, borderRadius: 16 }} contentFit="cover" />
              )}
              <Tappable
                onPress={onRemoveAttachment}
                className="absolute -right-2 -top-2 h-6 w-6 items-center justify-center rounded-full bg-foreground"
                accessibilityLabel="Remove attachment"
              >
                <Icon name="close" size={10} color="background" weight="bold" />
              </Tappable>
            </View>
          </Animated.View>
        ) : null}
        <View className="flex-row items-end gap-2 p-2">
          <Tappable
            onPress={onPlus}
            className="h-9 w-9 items-center justify-center rounded-full bg-surface-secondary"
            accessibilityLabel="Add a photo or file"
          >
            <Icon name="plus" size={16} color="foreground" />
          </Tappable>
          <TextInput
            value={value}
            onChangeText={onChangeText}
            placeholder={placeholder}
            placeholderTextColor={typeof placeholderColor === "string" ? placeholderColor : undefined}
            multiline
            className="max-h-32 flex-1 py-2 text-[16px] text-foreground"
            style={{ color: typeof foreground === "string" ? foreground : undefined }}
            accessibilityLabel="Message"
          />
          <Animated.View style={sendStyle}>
            <Tappable
              onPress={onSend}
              disabled={!canSend}
              haptic="press"
              className="h-9 w-9 items-center justify-center rounded-full bg-accent"
              accessibilityLabel="Send"
            >
              <Icon name="send" size={16} color="accent-foreground" weight="bold" />
            </Tappable>
          </Animated.View>
        </View>
      </BlurView>
    </View>
  );
});
