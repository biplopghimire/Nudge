// The parts of Canvas's JSON that Nudge uses. Canvas sends many more fields;
// these are the ones the version 2 Canvas import needs.
// Docs: https://canvas.instructure.com/doc/api/

export type CanvasCourse = {
  id: number;
  name: string;
  course_code: string;       // "67443"
  enrollment_term_id: number;
  start_at: string | null;
  end_at: string | null;
  time_zone?: string;        // "America/New_York"
  workflow_state: "unpublished" | "available" | "completed" | "deleted";
  term?: CanvasTerm;         // only with include[]=term
};

export type CanvasTerm = {
  id: number;
  name: string;              // "Fall 2026"
  start_at: string | null;
  end_at: string | null;
};

// GET /api/v1/courses/:id?include[]=syllabus_body
export type CanvasCourseWithSyllabus = CanvasCourse & {
  syllabus_body: string | null;  // HTML
};

// GET /api/v1/courses/:id/assignments
export type CanvasAssignment = {
  id: number;
  course_id: number;
  name: string;              // "Sprint 3: API & Prototyping"
  description: string | null;  // HTML
  due_at: string | null;     // ISO 8601, UTC
  unlock_at: string | null;
  lock_at: string | null;
  points_possible: number | null;
  submission_types: string[];  // ["online_upload"]
  html_url: string;
  published: boolean;
};

// Each course enrollment of the token's owner (included in GET /courses).
export type CanvasEnrollment = {
  type: "student" | "teacher" | "ta" | "designer" | "observer";
  role: string;              // "TaEnrollment"
};

export type CanvasCourseWithEnrollments = CanvasCourse & {
  enrollments?: CanvasEnrollment[];
};

// GET /api/v1/courses/:id/folders
export type CanvasFolder = {
  id: number;
  name: string;
  full_name: string;         // "course files/Lectures_2026"
  parent_folder_id: number | null;
  files_count: number;
  hidden: boolean | null;
  locked: boolean;
};

// GET /api/v1/courses/:id/files
export type CanvasFile = {
  id: number;
  folder_id: number;
  display_name: string;      // "Refactoring.pdf"
  filename: string;
  "content-type": string;    // note the dash: "application/pdf"
  size: number;              // bytes
  url: string;               // temporary download link
  hidden: boolean;
  locked: boolean;
  created_at: string;
  updated_at: string;
};

// Error body Canvas returns for 401/403/404.
export type CanvasError = {
  errors: { message: string }[];
};
