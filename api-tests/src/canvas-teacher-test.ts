// Canvas API test from the teacher/TA side (Sprint 3, Part 6).
// Run: npm run canvas:teacher
//
// This is what the version 2 "Import from Canvas" button does for a teacher:
// 1. Find the courses I teach or TA       GET /api/v1/courses?include[]=term
// 2. Read the course's folders            GET /api/v1/courses/:id/folders
// 3. List every file, turn into Materials GET /api/v1/courses/:id/files
// 4. Download one PDF (proves we can get the bytes Gemini will read)
// 5. List assignments with due dates      GET /api/v1/courses/:id/assignments
//
// Only course content is read. No student, roster or grade endpoints are called.

import { canvasDownload, canvasGetAll } from "./canvas/client.ts";
import {
  IMPORTABLE_TYPES,
  semesterFor,
  toCreateCourseRequest,
  toNudgeAssignment,
  toNudgeMaterial,
  type MaterialType,
} from "./canvas/toNudge.ts";
import type { CanvasAssignment, CanvasCourseWithEnrollments, CanvasFile, CanvasFolder } from "./canvas/types.ts";
import { env } from "./env.ts";

const wantedCourseId = env("CANVAS_TEACHER_COURSE_ID", "");
const wantedCode = env("CANVAS_TEACHER_COURSE_CODE", "67272");
const timeZone = "America/New_York";

function heading(text: string) {
  console.log(`\n=== ${text} ===`);
}

function kb(bytes: number): string {
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
}

function formatDue(iso: string | null): string {
  if (!iso) return "no due date";
  return new Date(iso).toLocaleString("en-US", {
    timeZone,
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

async function main() {
  heading("1. Courses I teach or TA");
  const { items: courses } = await canvasGetAll<CanvasCourseWithEnrollments>("/courses", {
    "include[]": "term",
  });
  const teaching = courses.filter((c) => c.enrollments?.some((e) => e.type === "teacher" || e.type === "ta"));
  for (const c of teaching) {
    const roles = [...new Set(c.enrollments?.map((e) => e.type))].join(", ");
    console.log(`  ${c.id}  ${c.course_code}  ${semesterFor(c).padEnd(12)} ${c.name}  (${roles})`);
  }
  const course = wantedCourseId
    ? teaching.find((c) => String(c.id) === wantedCourseId)
    : teaching.find((c) => c.course_code.replace("-", "") === wantedCode.replace("-", ""));
  if (!course) throw new Error("No course found where you are a teacher or TA. Set CANVAS_TEACHER_COURSE_ID.");
  const nudgeCourse = toCreateCourseRequest(course);
  console.log(`\nImporting ${course.id} as ${JSON.stringify(nudgeCourse)}`);

  heading("2. Folders");
  const { items: folders } = await canvasGetAll<CanvasFolder>(`/courses/${course.id}/folders`);
  const folderById = new Map(folders.map((f) => [f.id, f]));
  for (const f of folders.filter((f) => f.files_count > 0).slice(0, 12)) {
    const hidden = f.hidden || f.locked ? "  (hidden from students)" : "";
    console.log(`  ${f.full_name.replace(/^course files\/?/, "/").padEnd(40)} ${String(f.files_count).padStart(3)} files${hidden}`);
  }
  if (folders.length > 12) console.log(`  ... ${folders.length} folders in all`);

  heading("3. Files as Nudge materials");
  const { items: files, pages } = await canvasGetAll<CanvasFile>(`/courses/${course.id}/files`, {
    per_page: "100",
    sort: "updated_at",
    order: "desc",
  });
  const importable = files.filter((f) => IMPORTABLE_TYPES.has(f["content-type"]));
  const materials = importable.map((f) => toNudgeMaterial(f, "<nudge course id>", folderById.get(f.folder_id)));
  console.log(`${files.length} files over ${pages} pages. ${importable.length} can be imported (PDFs and photos).`);
  console.log(`Skipped types: ${[...new Set(files.filter((f) => !IMPORTABLE_TYPES.has(f["content-type"])).map((f) => f["content-type"]))].join(", ") || "none"}`);

  const byType = new Map<MaterialType, number>();
  for (const m of materials) byType.set(m.type, (byType.get(m.type) ?? 0) + 1);
  console.log(`By type: ${[...byType].map(([t, n]) => `${t} ${n}`).join(", ")}`);
  console.log(`Restricted (solution keys or hidden in Canvas): ${materials.filter((m) => m.restricted).length}`);
  console.log("\nMost recent 8:");
  for (const m of materials.slice(0, 8)) {
    console.log(`  ${m.type.padEnd(13)} ${m.restricted ? "restricted " : "           "}${kb(m.sizeBytes).padStart(7)}  ${m.title}`);
  }
  console.log("\nAs JSON (first one):");
  console.log(JSON.stringify(materials[0], null, 2));

  heading("4. Download one PDF");
  // Only lecture slides students can already see. Never anything restricted or grade-related.
  const pdf = importable
    .filter((f, i) => f["content-type"] === "application/pdf" && materials[i].type === "slides" && !materials[i].restricted)
    .filter((f) => !/grade|score|roster/i.test(f.display_name))
    .sort((a, b) => a.size - b.size)[0];
  if (pdf) {
    const bytes = await canvasDownload(pdf.url);
    const header = new TextDecoder().decode(bytes.slice(0, 5));
    console.log(`${pdf.display_name}: downloaded ${kb(bytes.length)}, starts with "${header}" ${header === "%PDF-" ? "(valid PDF)" : "(not a PDF?)"}`);
    console.log("The backend would save this to Cloud Storage and send each page to Gemini.");
  } else {
    console.log("No PDFs to download.");
  }

  heading("5. Assignments and due dates");
  const { items: assignments } = await canvasGetAll<CanvasAssignment>(`/courses/${course.id}/assignments`, {
    order_by: "due_at",
    per_page: "100",
  });
  const dated = assignments.filter((a) => a.due_at);
  console.log(`${assignments.length} assignments, ${dated.length} with due dates. Last 8 by due date:`);
  for (const a of dated.slice(-8)) console.log(`  ${formatDue(a.due_at).padEnd(22)} ${a.name}`);
  console.log("\nAs Nudge assignments (first 2):");
  console.log(JSON.stringify(dated.slice(0, 2).map((a) => toNudgeAssignment(a, "<nudge course id>")), null, 2));
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
