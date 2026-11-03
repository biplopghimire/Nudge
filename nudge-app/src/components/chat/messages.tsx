import type { Citation, Message, Role } from "@api";
import * as Clipboard from "expo-clipboard";
import { Image } from "expo-image";
import * as WebBrowser from "expo-web-browser";
import { Spinner, useToast } from "heroui-native";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";
import Animated, { FadeIn, FadeInDown, FadeInUp } from "react-native-reanimated";

import { NudgeAvatar } from "@/components/brand/nudge-avatar";
import { Icon } from "@/components/ui/icon";
import { Tappable } from "@/components/ui/tappable";
import { api, ApiError } from "@/lib/api";
import { haptics } from "@/lib/haptics";
import { springs } from "@/lib/motion";

import { ReplyText } from "./reply-text";

const SOURCE_LABEL = { camera: "Photo · sent from camera", library: "Photo · from your library", files: "File" };

/** A question from the student (or teacher), with its photo or PDF. */
export function SentMessage({ message, localUri, pending }: { message: Message; localUri?: string; pending?: boolean }) {
  const attachment = message.attachment;
  const imageUri = localUri ?? (attachment?.type === "image" ? attachment.url : undefined);

  return (
    <Animated.View
      entering={FadeInUp.springify().damping(springs.bouncy.damping).stiffness(springs.bouncy.stiffness)}
      className="items-end gap-1.5 py-1.5"
    >
      {attachment || localUri ? (
        attachment?.type === "pdf" ? (
          <View className="flex-row items-center gap-3 rounded-2xl bg-surface-secondary px-4 py-3">
            <Icon name="doc" size={18} color="accent" />
            <Text className="text-[15px] font-medium text-foreground">PDF attached</Text>
          </View>
        ) : (
          <View className="overflow-hidden rounded-[22px] border border-border" style={{ borderCurve: "continuous" }}>
            <Image
              source={{ uri: imageUri }}
              style={{ width: 176, height: 220, opacity: pending ? 0.6 : 1 }}
              contentFit="cover"
              transition={250}
              accessibilityLabel="Photo of your work"
            />
            {pending ? (
              <View className="absolute inset-0 items-center justify-center">
                <Spinner color="white" />
              </View>
            ) : null}
          </View>
        )
      ) : null}
      {attachment ? (
        <Text className="px-1 text-[12px] text-muted">{SOURCE_LABEL[attachment.source]}</Text>
      ) : null}
      {message.content ? (
        <View className="max-w-[82%] rounded-[20px] bg-bubble px-4 py-2.5" style={{ borderCurve: "continuous", opacity: pending ? 0.75 : 1 }}>
          <Text className="text-[16px] leading-[22px] text-bubble-foreground">{message.content}</Text>
        </View>
      ) : null}
    </Animated.View>
  );
}

/** Nudge's reply: avatar, text that reveals word by word, then citation chips. */
export function NudgeReply({ message, reveal, viewerRole }: { message: Message; reveal: boolean; viewerRole: Role }) {
  const shown = useReveal(message.content, reveal);
  const done = shown.length >= message.content.length;
  const { toast } = useToast();

  return (
    <Animated.View entering={FadeIn.duration(200)} className="flex-row gap-3 py-3">
      <View className="pt-0.5">
        <NudgeAvatar size={28} />
      </View>
      <View className="flex-1">
        <ReplyText text={shown} />
        {done ? (
          <>
            {message.citations.length > 0 ? (
              <View className="mt-3 flex-row flex-wrap gap-2">
                {message.citations.map((citation, index) => (
                  <CitationChip key={`${citation.materialId}-${citation.page}`} citation={citation} index={index} viewerRole={viewerRole} />
                ))}
              </View>
            ) : null}
            <Animated.View entering={FadeIn.delay(180)} className="mt-2.5 flex-row gap-1">
              <Tappable
                onPress={async () => {
                  await Clipboard.setStringAsync(message.content);
                  toast.show({ label: "Copied", variant: "default", duration: 1400 });
                }}
                className="h-8 w-8 items-center justify-center rounded-full"
                accessibilityLabel="Copy reply"
              >
                <Icon name="copy" size={14} color="muted" weight="medium" />
              </Tappable>
            </Animated.View>
          </>
        ) : null}
      </View>
    </Animated.View>
  );
}

function CitationChip({ citation, index, viewerRole }: { citation: Citation; index: number; viewerRole: Role }) {
  const [opening, setOpening] = useState(false);
  const { toast } = useToast();
  const label = citation.page ? `${citation.title} · p.${citation.page}` : citation.title;

  async function open() {
    if (opening) return;
    setOpening(true);
    try {
      const link =
        viewerRole === "teacher"
          ? await api.teacherMaterialLink(citation.materialId, citation.page)
          : await api.materialLink(citation.materialId, citation.page);
      await WebBrowser.openBrowserAsync(link.page ? `${link.url}#page=${link.page}` : link.url, {
        presentationStyle: WebBrowser.WebBrowserPresentationStyle.PAGE_SHEET,
      });
    } catch (error) {
      haptics.error();
      toast.show({ variant: "danger", label: "Couldn't open the file", description: error instanceof ApiError ? error.message : undefined });
    } finally {
      setOpening(false);
    }
  }

  return (
    <Animated.View entering={FadeInDown.delay(index * 70).springify().damping(springs.bouncy.damping)}>
      <Tappable
        onPress={open}
        accessibilityRole="link"
        accessibilityLabel={`Open ${label}`}
        className="flex-row items-center gap-1.5 rounded-full bg-blush px-3 py-1.5"
      >
        {opening ? <Spinner size="sm" color="blush-foreground" /> : <Icon name="doc" size={12} color="blush-foreground" />}
        <Text className="text-[13px] font-semibold text-blush-foreground">{label}</Text>
      </Tappable>
    </Animated.View>
  );
}

/** Reveals text a few words at a time, like it's being written. */
function useReveal(text: string, active: boolean) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!active) return;
    const words = text.split(/(\s+)/);
    const total = words.length;
    const duration = Math.min(1600, Math.max(450, total * 16));
    const started = Date.now();
    let frame = 0;
    const tick = () => {
      const progress = Math.min(1, (Date.now() - started) / duration);
      const eased = 1 - Math.pow(1 - progress, 2);
      setCount(words.slice(0, Math.ceil(eased * total)).join("").length);
      if (progress < 1) frame = requestAnimationFrame(tick);
      else haptics.soft();
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [text, active]);

  return active ? text.slice(0, count) : text;
}
