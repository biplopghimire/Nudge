import type { Material } from "@api";
import { useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { Skeleton, Spinner, useToast } from "heroui-native";
import { useState } from "react";
import { RefreshControl, Text, View } from "react-native";
import Animated, { FadeIn, ZoomIn } from "react-native-reanimated";

import { Icon } from "@/components/ui/icon";
import { Badge, Row } from "@/components/ui/list";
import { BackButton, Screen, SectionLabel } from "@/components/ui/screen";
import { Tappable } from "@/components/ui/tappable";
import { api, ApiError } from "@/lib/api";
import { fileSize } from "@/lib/format";
import { haptics } from "@/lib/haptics";
import { KIND_ICON, KIND_LABEL, pickMaterials } from "@/lib/materials";
import { enterRow, springs } from "@/lib/motion";
import { keys, useTeacherCourse } from "@/lib/queries";
import { useStartChat } from "@/lib/start-chat";

export default function TeacherCourse() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data, isLoading, refetch, isRefetching } = useTeacherCourse(id);
  const client = useQueryClient();
  const { toast } = useToast();
  const startChat = useStartChat();
  const [uploading, setUploading] = useState(0);

  async function upload() {
    const files = await pickMaterials();
    if (!files.length) return;
    setUploading(files.length);
    try {
      for (const file of files) {
        await api.uploadMaterial(id, { uri: file.uri, name: file.name, type: file.type }, file.kind, file.restricted);
        setUploading((n) => n - 1);
        client.invalidateQueries({ queryKey: keys.teacherCourse(id) });
      }
      haptics.success();
    } catch (error) {
      haptics.error();
      toast.show({ variant: "danger", label: "Upload failed", description: error instanceof ApiError ? error.message : undefined });
    } finally {
      setUploading(0);
      client.invalidateQueries({ queryKey: keys.teacherCourses });
    }
  }

  const course = data?.course;
  return (
    <Screen refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={() => void refetch()} />}>
      <BackButton />
      {course ? (
        <Animated.View entering={FadeIn} className="mb-2 mt-5">
          <Text className="text-[13px] font-medium text-muted">{course.semester}</Text>
          <Text className="text-[30px] font-bold tracking-tight text-foreground">
            {course.code} · {course.section}
          </Text>
          <Text className="mt-1 text-[14px] text-muted">
            {course.studentCount} students · {course.materialCount} materials
          </Text>
        </Animated.View>
      ) : (
        <Skeleton className="mt-5 h-20 rounded-2xl" />
      )}

      {course?.joinCode ? (
        <Animated.View entering={enterRow(0)}>
          <Tappable
            onPress={() => router.push({ pathname: "/course/[id]/share", params: { id, code: course.joinCode!, name: `${course.code} · ${course.section}` } })}
            className="mt-5 flex-row items-center justify-between rounded-3xl bg-mint-soft px-5 py-4"
            accessibilityRole="button"
            accessibilityLabel={`Join code ${course.joinCode}. Share it`}
          >
            <View>
              <Text className="text-[13px] font-medium text-mint-foreground">Join code</Text>
              <Text className="mt-0.5 text-[26px] font-bold tracking-[4px] text-mint-foreground">{course.joinCode}</Text>
            </View>
            <View className="h-10 w-10 items-center justify-center rounded-full bg-background/60">
              <Icon name="share" size={16} color="mint-foreground" />
            </View>
          </Tappable>
        </Animated.View>
      ) : null}

      <View className="mt-3 flex-row gap-3">
        <QuickAction icon="sliders" label="Options" onPress={() => router.push({ pathname: "/course/[id]/options", params: { id } })} />
        <QuickAction
          icon="sparkles"
          label="Ask Nudge"
          busy={startChat.isPending}
          onPress={() => course && startChat.mutate({ courseId: course.id, title: "Teacher chat" })}
        />
      </View>

      <View className="flex-row items-end justify-between">
        <SectionLabel>Materials</SectionLabel>
        <Tappable onPress={upload} disabled={uploading > 0} className="mb-2 flex-row items-center gap-1.5" accessibilityRole="button">
          {uploading > 0 ? <Spinner size="sm" /> : <Icon name="plus" size={13} color="accent" />}
          <Text className="text-[15px] font-semibold text-accent">{uploading > 0 ? `Uploading ${uploading}…` : "Add files"}</Text>
        </Tappable>
      </View>

      {isLoading ? (
        <Skeleton className="h-14 rounded-xl" />
      ) : data && data.materials.length > 0 ? (
        data.materials.map((material, index) => (
          <Row
            key={material.id}
            index={index + 1}
            icon={KIND_ICON[material.kind]}
            title={material.title}
            subtitle={`${material.restricted ? "Hidden from students" : KIND_LABEL[material.kind]} · ${fileSize(material.sizeBytes)}`}
            trailing={<StatusChip material={material} />}
          />
        ))
      ) : (
        <Text className="py-6 text-center text-[15px] text-muted">Add slides, notes or homework so Nudge can answer from them.</Text>
      )}
    </Screen>
  );
}

function QuickAction({ icon, label, onPress, busy }: { icon: "sliders" | "sparkles"; label: string; onPress: () => void; busy?: boolean }) {
  return (
    <Tappable onPress={onPress} className="flex-1 flex-row items-center gap-3 rounded-2xl bg-surface-secondary px-4 py-3.5" accessibilityRole="button">
      {busy ? <Spinner size="sm" /> : <Icon name={icon} size={16} color="accent" />}
      <Text className="text-[15px] font-semibold text-foreground">{label}</Text>
    </Tappable>
  );
}

function StatusChip({ material }: { material: Material }) {
  if (material.status === "processing") {
    return (
      <View className="flex-row items-center gap-1.5">
        <Spinner size="sm" />
        <Text className="text-[12px] font-medium text-muted">Reading</Text>
      </View>
    );
  }
  if (material.status === "failed") return <Badge tone="blush">Failed</Badge>;
  return (
    <Animated.View entering={ZoomIn.springify().damping(springs.bouncy.damping)}>
      <Icon name="checkCircle" size={18} color="success" />
    </Animated.View>
  );
}
