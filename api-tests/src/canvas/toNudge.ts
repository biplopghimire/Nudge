// How Canvas data becomes Nudge data in the version 2 import.
// Output types come from the team's shared nudge-api/nudge-types.ts.

import type {
  Assignment,
  CreateCourseRequest,
  Material,
  MaterialKind,
} from "../../../nudge-api/nudge-types.ts";
import type { CanvasAssignment, CanvasCourse, CanvasFile, CanvasFolder } from "./types.ts";

export type { Assignment, CreateCourseRequest, Material, MaterialKind };

/** "67443" -> "67-443". Canvas drops the dash CMU uses. */
export function formatCourseCode(canvasCode: string): string {
  const digits = canvasCode.match(/^(\d{2})(\d{3})/);
  return digits ? `${digits[1]}-${digits[2]}` : canvasCode;
}

/** The term name ("Fall 2026"), or a guess from the start date: Jan-May Spring, Jun-Jul Summer, Aug-Dec Fall. */
export function semesterFor(course: CanvasCourse): string {
  if (course.term?.name && /^(Spring|Summer|Fall) \d{4}$/.test(course.term.name)) return course.term.name;
  const startAt = course.start_at ?? course.term?.start_at;
  if (!startAt) return "Unknown";
  const start = new Date(startAt);
  const month = start.getUTCMonth() + 1;
  const term = month <= 5 ? "Spring" : month <= 7 ? "Summer" : "Fall";
  return `${term} ${start.getUTCFullYear()}`;
}

export function toCreateCourseRequest(course: CanvasCourse): CreateCourseRequest {
  const section = course.name.match(/sec(?:tion)?\s+(\w+)/i)?.[1];
  return {
    code: formatCourseCode(course.course_code),
    section: section ? `Sec ${section}` : "Sec 1",
    semester: semesterFor(course),
  };
}

/** "Lab 13 - Docker" -> "Lab 13", "Sprint 3: API & Prototyping" -> "Sprint 3". */
export function shortTitle(name: string): string {
  const head = name.split(/\s+[-–:]\s+|:\s*/)[0].trim();
  return head.length <= 16 ? head : `${head.slice(0, 15).trim()}…`;
}

/** Nudge assignments need a due date, so undated Canvas assignments return null. */
export function toNudgeAssignment(
  a: CanvasAssignment,
  course: { id: string; code: string },
): Assignment | null {
  if (!a.due_at) return null;
  return {
    id: `canvas-${a.id}`,
    courseId: course.id,
    courseCode: course.code,
    title: a.name,
    shortTitle: shortTitle(a.name),
    dueAt: a.due_at,
  };
}

// File types the upload pipeline can read (Part 4).
export const IMPORTABLE_TYPES = new Set(["application/pdf", "image/jpeg", "image/png", "image/heic", "image/webp"]);

const SOLUTION_WORDS = /solution|answer[ _-]?key|\bkey\b|rubric/i;

/** Solution keys and rubrics. Nudge stores them as restricted, never shown to students. */
export function isSolutionFile(file: CanvasFile, folder?: CanvasFolder): boolean {
  return SOLUTION_WORDS.test(`${folder?.full_name ?? ""}/${file.display_name}`);
}

/** Guess the Nudge material kind from the file name, folder and content type. */
export function guessMaterialKind(file: CanvasFile, folder?: CanvasFolder): MaterialKind {
  const name = `${folder?.full_name ?? ""}/${file.display_name}`;
  if (isSolutionFile(file, folder)) return "other";
  if (/syllabus/i.test(name)) return "syllabus";
  if (/\b(lab|hw|homework|assignment|problem[ _-]?set|ps[ _-]?\d|phase|project)/i.test(name)) return "homework";
  if (/lecture|slides?\b|_s\d\d\b/i.test(name) || /presentation/.test(file["content-type"])) return "slides";
  if (file["content-type"].startsWith("image/")) return "photo";
  return "notes";
}

export function toNudgeMaterial(file: CanvasFile, nudgeCourseId: string, folder?: CanvasFolder): Material {
  return {
    id: `canvas-${file.id}`,
    courseId: nudgeCourseId,
    title: file.display_name,
    kind: guessMaterialKind(file, folder),
    sizeBytes: file.size,
    // Solution keys, and anything hidden from students in Canvas, stay hidden in Nudge.
    restricted: isSolutionFile(file, folder) || file.hidden || file.locked || Boolean(folder?.hidden || folder?.locked),
    status: "processing",
  };
}

/** Very small HTML-to-text for previews. The real import would keep the HTML for Gemini. */
export function htmlToText(html: string): string {
  return html
    .replace(/<(br|\/p|\/h\d|\/li)[^>]*>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#39;|&rsquo;/g, "'")
    .replace(/\n\s*\n+/g, "\n")
    .trim();
}
