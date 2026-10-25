// Canvas API test (Sprint 3, Part 6).
// Run: npm run canvas
//
// 1. List my courses              GET /api/v1/courses
// 2. Get the syllabus             GET /api/v1/courses/:id?include[]=syllabus_body
// 3. List assignments + due dates GET /api/v1/courses/:id/assignments
// 4. Turn them into Nudge types   (what the version 2 import will do)
//
// Lists are paged, so canvasGetAll follows the "next" link in the Link header.

import { canvasGet, canvasGetAll } from "./canvas/client.ts";
import { htmlToText, toCreateCourseRequest, toNudgeAssignment } from "./canvas/toNudge.ts";
import type { CanvasAssignment, CanvasCourse, CanvasCourseWithSyllabus } from "./canvas/types.ts";
import { env } from "./env.ts";

const courseCode = env("CANVAS_COURSE_CODE", "67443");
const timeZone = "America/New_York";

function heading(text: string) {
  console.log(`\n=== ${text} ===`);
}

function formatDue(iso: string | null): string {
  if (!iso) return "no due date";
  return new Date(iso).toLocaleString("en-US", {
    timeZone,
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// Check the JSON has the fields and types our CanvasAssignment type promises.
function isCanvasAssignment(value: unknown): value is CanvasAssignment {
  const a = value as CanvasAssignment;
  return (
    typeof a?.id === "number" &&
    typeof a.name === "string" &&
    (a.due_at === null || typeof a.due_at === "string") &&
    Array.isArray(a.submission_types) &&
    typeof a.html_url === "string"
  );
}

async function main() {
  heading("1. My active courses");
  const { items: courses, pages: coursePages } = await canvasGetAll<CanvasCourse>("/courses", {
    enrollment_state: "active",
    "include[]": "term",
  });
  console.log(`${courses.length} courses (${coursePages} page${coursePages === 1 ? "" : "s"})`);
  for (const c of courses) console.log(`  ${String(c.id).padEnd(6)} ${c.course_code.slice(0, 10).padEnd(11)} ${(c.term?.name ?? "").padEnd(12)} ${c.name}`);

  const course = courses.find((c) => c.course_code.replace("-", "") === courseCode.replace("-", ""));
  if (!course) throw new Error(`No active course with code ${courseCode}`);

  heading(`2. Syllabus for ${course.name}`);
  const withSyllabus = await canvasGet<CanvasCourseWithSyllabus>(`/courses/${course.id}`, {
    "include[]": "syllabus_body",
  });
  const syllabus = htmlToText(withSyllabus.syllabus_body ?? "");
  console.log(`${withSyllabus.syllabus_body?.length ?? 0} characters of HTML. Preview:`);
  console.log(
    syllabus
      .split("\n")
      .slice(0, 6)
      .map((line) => `  ${line.slice(0, 110)}`)
      .join("\n"),
  );

  heading(`3. ${course.course_code} assignments and due dates (${timeZone})`);
  // per_page=10 so the course needs several pages, which shows the paging works.
  const { items: raw, pages } = await canvasGetAll<unknown>(`/courses/${course.id}/assignments`, {
    order_by: "due_at",
    per_page: "10",
  });
  const assignments = raw.filter(isCanvasAssignment);
  console.log(`${raw.length} assignments over ${pages} pages, ${assignments.length} parsed into CanvasAssignment`);
  for (const a of assignments) {
    const points = a.points_possible == null ? "" : `${a.points_possible} pts`;
    console.log(`  ${formatDue(a.due_at).padEnd(24)} ${a.name.padEnd(44)} ${points}`);
  }

  const now = Date.now();
  const upNext = assignments.find((a) => a.due_at && Date.parse(a.due_at) > now);
  console.log(`\nUp next: ${upNext ? `${upNext.name}, due ${formatDue(upNext.due_at)}` : "nothing due"}`);

  heading("4. As Nudge types (version 2 Canvas import)");
  const createCourse = toCreateCourseRequest(course);
  console.log("POST /teacher/courses body:");
  console.log(JSON.stringify(createCourse, null, 2));
  console.log("Assignments (first 3):");
  const target = { id: "<nudge course id>", code: createCourse.code };
  const mapped = assignments.map((a) => toNudgeAssignment(a, target)).filter((a) => a !== null);
  console.log(JSON.stringify(mapped.slice(0, 3), null, 2));
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
