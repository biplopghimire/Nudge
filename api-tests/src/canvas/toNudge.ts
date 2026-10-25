// How Canvas data becomes Nudge data in the version 2 import.
// The output types match Part 9 and the backend's /student/courses response.

import type { CanvasAssignment, CanvasCourse, CanvasFile, CanvasFolder } from "./types.ts";

export type Assignment = {
  id: string;
  courseId: string;
  title: string;      // "Problem Set 4"
  dueAt?: string;
};

export type MaterialType = "slides" | "notes" | "homework" | "syllabus" | "photo" | "solution_key";

// What POST /teacher/courses/:id/materials would create for each file.
export type Material = {
  id: string;
  courseId: string;
  title: string;
  type: MaterialType;
  sizeBytes: number;
  restricted: boolean;
  status: "processing" | "ready" | "failed";
};

export type CreateCourseRequest = {
  code: string;       // "67-443"
  section: string;
  semester: string;   // "Fall 2026"
};

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

export function toNudgeAssignment(a: CanvasAssignment, nudgeCourseId: string): Assignment {
  return {
    id: `canvas-${a.id}`,
    courseId: nudgeCourseId,
    title: a.name,
    ...(a.due_at ? { dueAt: a.due_at } : {}),
  };
}

// File types the upload pipeline can read (Part 4).
export const IMPORTABLE_TYPES = new Set(["application/pdf", "image/jpeg", "image/png", "image/heic", "image/webp"]);

const SOLUTION_WORDS = /solution|answer[ _-]?key|\bkey\b|rubric/i;

/** Guess the Nudge material type from the file name, folder and content type. */
export function guessMaterialType(file: CanvasFile, folder?: CanvasFolder): MaterialType {
  const name = `${folder?.full_name ?? ""}/${file.display_name}`;
  if (SOLUTION_WORDS.test(name)) return "solution_key";
  if (/syllabus/i.test(name)) return "syllabus";
  if (/\b(lab|hw|homework|assignment|problem[ _-]?set|ps[ _-]?\d|phase|project)/i.test(name)) return "homework";
  if (/lecture|slides?\b|_s\d\d\b/i.test(name) || /presentation/.test(file["content-type"])) return "slides";
  if (file["content-type"].startsWith("image/")) return "photo";
  return "notes";
}

export function toNudgeMaterial(file: CanvasFile, nudgeCourseId: string, folder?: CanvasFolder): Material {
  const type = guessMaterialType(file, folder);
  return {
    id: `canvas-${file.id}`,
    courseId: nudgeCourseId,
    title: file.display_name,
    type,
    sizeBytes: file.size,
    // Solution keys, and anything hidden from students in Canvas, stay hidden in Nudge.
    restricted: type === "solution_key" || file.hidden || file.locked || Boolean(folder?.hidden || folder?.locked),
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
