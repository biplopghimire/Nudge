import type { MaterialKind, UploadFile } from "@api";
import * as DocumentPicker from "expo-document-picker";

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

export async function pickMaterials(): Promise<PickedFile[]> {
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
