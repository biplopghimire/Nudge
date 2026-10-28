import type { GetThreadResponse, Message } from "@api";
import type { LegendListRef } from "@legendapp/list/react-native";
import { KeyboardAwareLegendList, useKeyboardChatComposerInset, useKeyboardScrollToEnd } from "@legendapp/list/keyboard";
import { useQueryClient } from "@tanstack/react-query";
import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { Skeleton, useToast } from "heroui-native";
import { type ComponentRef, useCallback, useMemo, useRef, useState } from "react";
import { Text, View } from "react-native";
import { KeyboardStickyView } from "react-native-keyboard-controller";
import Animated, { FadeIn, FadeInDown } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { NudgeMark } from "@/components/brand/nudge-avatar";
import { AttachSheet, type AttachChoice } from "@/components/chat/attach-sheet";
import { Composer, type PendingAttachment } from "@/components/chat/composer";
import { NudgeReply, SentMessage } from "@/components/chat/messages";
import { Thinking } from "@/components/chat/thinking";
import { Badge } from "@/components/ui/list";
import { BackButton } from "@/components/ui/screen";
import { Tappable } from "@/components/ui/tappable";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { haptics } from "@/lib/haptics";
import { pendingPhoto } from "@/lib/pending-photo";
import { keys, useThread } from "@/lib/queries";

type Item =
  | { kind: "message"; id: string; message: Message; localUri?: string; pending?: boolean }
  | { kind: "thinking"; id: "thinking"; withPhoto: boolean };

/** The message shown right away while the real one is sent. */
function draftMessage(threadId: string, role: Message["role"], content: string): Message {
  const now = new Date();
  return { id: `local-${now.getTime()}`, threadId, role, content, attachment: null, citations: [], createdAt: now.toISOString() };
}

const SUGGESTIONS = [
  "Explain the main idea from the last lecture",
  "Where in the slides is this covered?",
  "I'm stuck. Can you give me a hint?",
];

export default function Chat() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const { user } = useAuth();
  const client = useQueryClient();
  const { toast } = useToast();
  const { data, isLoading } = useThread(id);

  const [text, setText] = useState("");
  const [attachment, setAttachment] = useState<PendingAttachment | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sending, setSending] = useState<{ message: Message; localUri?: string } | null>(null);
  const [revealId, setRevealId] = useState<string | null>(null);
  const [anchorIndex, setAnchorIndex] = useState<number | undefined>(undefined);

  const listRef = useRef<LegendListRef>(null);
  const composerRef = useRef<ComponentRef<typeof View>>(null);
  const { contentInsetEndAdjustment, onComposerLayout } = useKeyboardChatComposerInset(
    listRef,
    composerRef as unknown as Parameters<typeof useKeyboardChatComposerInset>[1],
    64,
  );
  const { freeze, scrollMessageToEnd } = useKeyboardScrollToEnd({ listRef });

  // Pick up a photo taken on the camera screen.
  useFocusEffect(
    useCallback(() => {
      const photo = pendingPhoto.take(id);
      if (photo) setAttachment({ uri: photo.uri, name: "work.jpg", type: "image/jpeg", source: "camera" });
    }, [id]),
  );

  const items = useMemo<Item[]>(() => {
    const list: Item[] = (data?.messages ?? []).map((message) => ({ kind: "message", id: message.id, message }));
    if (sending) {
      list.push({ kind: "message", id: sending.message.id, message: sending.message, localUri: sending.localUri, pending: true });
      list.push({ kind: "thinking", id: "thinking", withPhoto: !!sending.localUri });
    }
    return list;
  }, [data, sending]);

  async function send(content = text) {
    const question = content.trim();
    if ((!question && !attachment) || sending || !user) return;
    const outgoing = attachment;
    const optimistic = draftMessage(id, user.role, question);
    setText("");
    setAttachment(null);
    setAnchorIndex(items.length);
    setSending({ message: optimistic, localUri: outgoing?.uri });
    requestAnimationFrame(() => scrollMessageToEnd({ animated: true, closeKeyboard: false }));

    try {
      const response = await api.sendMessage(
        id,
        question,
        outgoing ? { file: { uri: outgoing.uri, name: outgoing.name, type: outgoing.type }, source: outgoing.source } : undefined,
      );
      client.setQueryData<GetThreadResponse>(keys.thread(id), (old) =>
        old ? { ...old, messages: [...old.messages, response.sentMessage, response.reply] } : old,
      );
      setRevealId(response.reply.id);
      client.invalidateQueries({ queryKey: keys.threads });
    } catch (error) {
      haptics.error();
      setText(question);
      setAttachment(outgoing);
      toast.show({
        variant: "danger",
        label: error instanceof ApiError && error.code === "nudge_busy" ? "Nudge is busy" : "Message not sent",
        description: error instanceof ApiError ? error.message : "Try again in a moment.",
      });
    } finally {
      setSending(null);
    }
  }

  async function choose(choice: AttachChoice) {
    if (choice === "camera") {
      router.push({ pathname: "/camera", params: { threadId: id, title: data?.thread.title ?? "" } });
      return;
    }
    if (choice === "library") {
      const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8 });
      const asset = result.canceled ? null : result.assets[0];
      if (asset) setAttachment({ uri: asset.uri, name: asset.fileName ?? "photo.jpg", type: asset.mimeType ?? "image/jpeg", source: "library" });
      return;
    }
    const result = await DocumentPicker.getDocumentAsync({ type: ["application/pdf", "image/*"], copyToCacheDirectory: true });
    const asset = result.canceled ? null : result.assets[0];
    if (asset) setAttachment({ uri: asset.uri, name: asset.name, type: asset.mimeType ?? "application/pdf", source: "files" });
  }

  const thread = data?.thread;
  const empty = !isLoading && items.length === 0;

  return (
    <View className="flex-1 bg-background" style={{ paddingTop: insets.top }}>
      <View className="flex-row items-center gap-3 border-b border-separator px-4 pb-3 pt-1">
        <BackButton />
        <View className="flex-1">
          {thread ? (
            <Animated.View entering={FadeIn} className="flex-row items-center gap-2">
              <Text className="shrink text-[17px] font-semibold text-foreground" numberOfLines={1}>
                {thread.title}
              </Text>
              <Badge tone="mint">{thread.courseCode}</Badge>
            </Animated.View>
          ) : (
            <Skeleton className="h-5 w-40 rounded-md" />
          )}
        </View>
      </View>

      {empty ? (
        <Animated.View entering={FadeIn.duration(300)} className="flex-1 items-center justify-center px-8">
          <NudgeMark size={80} />
          <Text className="mt-5 text-center text-[22px] font-bold tracking-tight text-foreground">What are you working on?</Text>
          <Text className="mt-2 text-center text-[15px] leading-5 text-muted">
            Ask about {thread?.courseCode ?? "your course"}, or send a photo of your work.
          </Text>
          <View className="mt-6 w-full gap-2">
            {SUGGESTIONS.map((suggestion, index) => (
              <Animated.View key={suggestion} entering={FadeInDown.delay(120 + index * 70).springify()}>
                <Tappable onPress={() => send(suggestion)} className="rounded-2xl bg-surface-secondary px-4 py-3.5" accessibilityRole="button">
                  <Text className="text-[15px] text-foreground">{suggestion}</Text>
                </Tappable>
              </Animated.View>
            ))}
          </View>
        </Animated.View>
      ) : (
        <KeyboardAwareLegendList
          ref={listRef}
          data={items}
          keyExtractor={(item) => item.id}
          estimatedItemSize={120}
          renderItem={({ item }) =>
            item.kind === "thinking" ? (
              <Thinking withPhoto={item.withPhoto} />
            ) : item.message.role === "nudge" ? (
              <NudgeReply message={item.message} reveal={item.message.id === revealId} viewerRole={user?.role ?? "student"} />
            ) : (
              <SentMessage message={item.message} localUri={item.localUri} pending={item.pending} />
            )
          }
          contentContainerStyle={{ paddingHorizontal: 18, paddingTop: 12 }}
          alignItemsAtEnd
          initialScrollAtEnd
          maintainScrollAtEnd
          maintainVisibleContentPosition
          anchoredEndSpace={anchorIndex !== undefined ? { anchorIndex } : undefined}
          contentInsetEndAdjustment={contentInsetEndAdjustment}
          freeze={freeze}
          keyboardDismissMode="interactive"
          keyboardOffset={insets.bottom}
          style={{ flex: 1 }}
        />
      )}

      <KeyboardStickyView offset={{ closed: 0, opened: insets.bottom }} style={empty ? undefined : { position: "absolute", left: 0, right: 0, bottom: 0 }}>
        <View style={{ paddingBottom: insets.bottom }} onLayout={onComposerLayout}>
          <Composer
            ref={composerRef}
            value={text}
            onChangeText={setText}
            onSend={() => send()}
            onPlus={() => setSheetOpen(true)}
            attachment={attachment}
            onRemoveAttachment={() => setAttachment(null)}
            busy={!!sending}
          />
        </View>
      </KeyboardStickyView>

      <AttachSheet isOpen={sheetOpen} onOpenChange={setSheetOpen} onChoose={choose} />
    </View>
  );
}
