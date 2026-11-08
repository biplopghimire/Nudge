import { useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { Button, Input, Label, Spinner, TextField, useToast } from "heroui-native";
import { useState } from "react";
import { Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import Animated, { FadeInDown, FadeOut, LinearTransition } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { AttachSheet, type AttachChoice } from "@/components/chat/attach-sheet";
import { Icon } from "@/components/ui/icon";
import { Badge } from "@/components/ui/list";
import { BackButton } from "@/components/ui/screen";
import { Segmented } from "@/components/ui/segmented";
import { Tappable } from "@/components/ui/tappable";
import { api, ApiError } from "@/lib/api";
import { fileSize } from "@/lib/format";
import { haptics } from "@/lib/haptics";
import { KIND_ICON, KIND_LABEL, MATERIAL_SOURCES, pickMaterials, type PickedFile } from "@/lib/materials";
import { layoutSpring, springs } from "@/lib/motion";
import { keys } from "@/lib/queries";

const SEMESTERS = ["Fall 2026", "Spring 2027"] as const;
type Step = "idle" | "creating" | "uploading";

export default function NewCourse() {
  const insets = useSafeAreaInsets();
  const client = useQueryClient();
  const { toast } = useToast();
  const [code, setCode] = useState("");
  const [section, setSection] = useState("Sec 1");
  const [semester, setSemester] = useState<(typeof SEMESTERS)[number]>("Fall 2026");
  const [files, setFiles] = useState<PickedFile[]>([]);
  const [step, setStep] = useState<Step>("idle");
  const [uploaded, setUploaded] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);

  const ready = code.trim().length >= 2 && section.trim().length > 0 && step === "idle";

  async function addFiles(source: AttachChoice) {
    const picked = await pickMaterials(source);
    if (picked.length) {
      haptics.tap();
      setFiles((current) => [...current, ...picked.filter((p) => !current.some((c) => c.uri === p.uri))]);
    }
  }

  async function create() {
    if (!ready) return;
    haptics.press();
    setStep("creating");
    try {
      const { course } = await api.createCourse({ code: code.trim(), section: section.trim(), semester });
      setStep("uploading");
      // The course exists now, so never go back to the form (that would create a duplicate).
      const failed: string[] = [];
      for (const [index, file] of files.entries()) {
        try {
          await api.uploadMaterial(course.id, { uri: file.uri, name: file.name, type: file.type }, file.kind, file.restricted);
        } catch {
          failed.push(file.name);
        }
        setUploaded(index + 1);
      }
      client.invalidateQueries({ queryKey: keys.teacherCourses });
      if (failed.length) {
        haptics.error();
        toast.show({
          variant: "warning",
          label: `${failed.length} ${failed.length === 1 ? "file" : "files"} didn't upload`,
          description: "Your course is ready. Add them again from the course page.",
        });
      } else {
        haptics.success();
      }
      router.replace({ pathname: "/course/[id]/share", params: { id: course.id, code: course.joinCode ?? "", name: `${course.code} · ${course.section}` } });
    } catch (error) {
      haptics.error();
      setStep("idle");
      toast.show({ variant: "danger", label: "Couldn't create the course", description: error instanceof ApiError ? error.message : undefined });
    }
  }

  return (
    <View className="flex-1 bg-background">
      <KeyboardAwareScrollView
        contentContainerStyle={{ paddingTop: 16, paddingBottom: 140 }}
        contentContainerClassName="px-5"
        bottomOffset={120}
        keyboardShouldPersistTaps="handled"
      >
        <BackButton label="Close" />
        <Text className="mb-6 mt-6 text-[30px] font-bold tracking-tight text-foreground">New course</Text>

        <View className="gap-4">
          <TextField>
            <Label>Course code</Label>
            <Input value={code} onChangeText={setCode} placeholder="67-272" autoCapitalize="characters" autoFocus />
          </TextField>
          <TextField>
            <Label>Section</Label>
            <Input value={section} onChangeText={setSection} placeholder="Sec 1" />
          </TextField>
          <View>
            <Text className="mb-2 text-[14px] font-medium text-foreground">Semester</Text>
            <Segmented value={semester} onChange={setSemester} options={SEMESTERS.map((s) => ({ value: s, label: s }))} />
          </View>
        </View>

        <Text className="mb-3 mt-8 text-[13px] font-medium text-muted">Course materials</Text>
        <Tappable
          onPress={() => setSheetOpen(true)}
          className="flex-row items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-border py-5"
          accessibilityRole="button"
        >
          <Icon name="plus" size={14} color="accent" />
          <Text className="text-[15px] font-semibold text-accent">Add slides, notes, photos</Text>
        </Tappable>

        <Animated.View layout={layoutSpring} className="mt-2">
          {files.map((file, index) => (
            <Animated.View
              key={file.uri}
              entering={FadeInDown.springify().damping(springs.smooth.damping)}
              exiting={FadeOut.duration(150)}
              layout={LinearTransition}
              className="flex-row items-center gap-3 border-b border-separator py-3.5"
            >
              <View className="h-10 w-10 items-center justify-center rounded-xl bg-surface-secondary">
                <Icon name={KIND_ICON[file.kind]} size={17} color="accent" />
              </View>
              <View className="flex-1">
                <Text className="text-[15px] font-semibold text-foreground" numberOfLines={1}>
                  {file.name}
                </Text>
                <Text className="text-[12px] text-muted">
                  {file.restricted ? "Solution key, hidden from students" : KIND_LABEL[file.kind]} · {fileSize(file.size)}
                </Text>
              </View>
              {step === "uploading" && index < uploaded ? (
                <Icon name="checkCircle" size={18} color="success" />
              ) : step === "uploading" && index === uploaded ? (
                <Spinner size="sm" />
              ) : file.restricted ? (
                <Badge tone="muted">Hidden</Badge>
              ) : step === "idle" ? (
                <Tappable onPress={() => setFiles((f) => f.filter((x) => x.uri !== file.uri))} hitSlop={10} accessibilityLabel={`Remove ${file.name}`}>
                  <Icon name="close" size={13} color="muted" />
                </Tappable>
              ) : null}
            </Animated.View>
          ))}
        </Animated.View>
      </KeyboardAwareScrollView>

      <View className="absolute inset-x-0 bottom-0 bg-background px-5 pt-3" style={{ paddingBottom: insets.bottom + 12 }}>
        <Button size="lg" className="rounded-full" onPress={create} isDisabled={!ready}>
          {step === "idle" ? (
            <Button.Label>Create course</Button.Label>
          ) : (
            <View className="flex-row items-center gap-2">
              <Spinner size="sm" color="accent-foreground" />
              <Button.Label>{step === "creating" ? "Creating…" : `Uploading ${uploaded + 1} of ${files.length}…`}</Button.Label>
            </View>
          )}
        </Button>
      </View>
      <AttachSheet isOpen={sheetOpen} onOpenChange={setSheetOpen} onChoose={addFiles} options={MATERIAL_SOURCES} />
    </View>
  );
}
