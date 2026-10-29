import type { MaterialKind, UploadFile } from "@api";
import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";

import type { AttachChoice, AttachOption } from "@/components/chat/attach-sheet";
import type { IconName } from "@/components/ui/icon";

export type PickedFile = UploadFile & { size: number; kind: MaterialKind; restricted: boolean };

const SOLUTION = /solution|answer[ _-]?key|\bkey\b|rubric/i;

/** Guess what a file is from its name, so teachers don't have to tag each one. */
export function guessKind(name: string, mime: string): { kind: MaterialKind; restricted: boolean } {
  if (SOLUTION.test(name)) return { kind: "other", restricted: true };
  if (/syllabus/i.test(name)) return { kind: "syllabus", restricted: false };
  if (/\b(hw|homework|problem[ _-]?set|ps[ _-]?\d|lab|assignment)/i.test(name)) return { kind: "homework", restricted: false };
  if (/lecture|slides?|deck/i.test(name)) return { kind: "slides", restricted: false };
  if (mime.startsWith("image/")) return { kind: "photo", restricted: false };
  return { kind: "notes", restricted: false };
}

export const KIND_LABEL: Record<MaterialKind, string> = {
  slides: "Slides",
  notes: "Notes",
  homework: "Homework",
  syllabus: "Syllabus",
  photo: "Photo",
  other: "Other",
};

export const KIND_ICON: Record<MaterialKind, IconName> = {
  slides: "doc",
  notes: "doc",
  homework: "doc",
  syllabus: "book",
  photo: "photo",
  other: "file",
};

/** The "Add files" menu for course materials. */
export const MATERIAL_SOURCES: AttachOption[] = [
  { choice: "library", icon: "photo", title: "Photo library", detail: "Handouts, whiteboards, worked examples" },
  { choice: "camera", icon: "camera", title: "Camera", detail: "Snap a page or the board" },
  { choice: "files", icon: "file", title: "Files", detail: "PDFs and images" },
];

/** Course files from the Files app, the photo library or the camera (whiteboards, handouts). */
export async function pickMaterials(source: AttachChoice = "files"): Promise<PickedFile[]> {
  if (source === "files") {
    const result = await DocumentPicker.getDocumentAsync({
      type: ["application/pdf", "image/*"],
      multiple: true,
      copyToCacheDirectory: true,
    });
    if (result.canceled) return [];
    return result.assets.map((asset) => {
      const type = asset.mimeType ?? "application/pdf";
      return { uri: asset.uri, name: asset.name, type, size: asset.size ?? 0, ...guessKind(asset.name, type) };
    });
  }

  if (source === "camera") {
    const { granted } = await ImagePicker.requestCameraPermissionsAsync();
    if (!granted) return [];
  }
  const options: ImagePicker.ImagePickerOptions = { mediaTypes: ["images"], quality: 0.8 };
  const result =
    source === "camera"
      ? await ImagePicker.launchCameraAsync(options)
      : await ImagePicker.launchImageLibraryAsync({ ...options, allowsMultipleSelection: true, selectionLimit: 20 });
  if (result.canceled) return [];
  const stamp = new Date().toLocaleDateString(undefined, { month: "short", day: "numeric" });
  return result.assets.map((asset, index) => {
    const type = asset.mimeType ?? "image/jpeg";
    const name = asset.fileName ?? `Photo ${stamp}${result.assets.length > 1 ? ` (${index + 1})` : ""}.jpg`;
    return { uri: asset.uri, name, type, size: asset.fileSize ?? 0, ...guessKind(name, type) };
  });
}
