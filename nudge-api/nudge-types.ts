// Nudge API types.
//
// These are the "structs" the app fills from the backend's JSON. Every example
// response in this folder is one populated instance of the type named in its
// "types" field. Dates are ISO 8601 strings; ids are UUID strings.

// ---------------------------------------------------------------------------
// Shared building blocks
// ---------------------------------------------------------------------------

export type Role = 'student' | 'teacher';

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  department?: string; // teachers only
}

export interface ApiError {
  error: string; // machine-readable code, e.g. "invalid_code"
  message: string; // shown to the user
}

// A file picked on the phone and sent in a multipart/form-data body
// (React Native's FormData file shape).
export interface UploadFile {
  uri: string;
  name: string;
  type: string; // MIME type, e.g. "image/jpeg" or "application/pdf"
}

// ---------------------------------------------------------------------------
// Courses, assignments and materials
// ---------------------------------------------------------------------------

export interface Assignment {
  id: string;
  courseId: string;
  courseCode: string;
  title: string; // "Problem Set 4"
  shortTitle: string; // "PS 4", used on badges and cards
  dueAt: string;
}

// A course in the student's list (Home, Switch class).
export interface StudentCourseSummary {
  id: string;
  code: string; // "67-272"
  section: string; // "Sec 1"
  teacherName: string;
  nextDue: string | null; // preformatted badge, e.g. "PS 4 · Thu"
  currentAssignmentTitle: string | null;
}

// A course with counts. joinCode is only sent to the course's teacher.
export interface Course {
  id: string;
  code: string;
  section: string;
  semester: string; // "Fall 2026"
  teacherName: string;
  materialCount: number;
  studentCount: number;
  joinCode?: string;
}

export interface Semester {
  name: string;
  isCurrent: boolean;
  courses: Course[];
}

export interface CourseSettings {
  hintsOnly: boolean;
  useSolutionKeys: boolean;
  citeMaterials: boolean;
  deadlineReminders: boolean; // turns reminders on for every student in the course
}

export type MaterialKind = 'slides' | 'notes' | 'homework' | 'syllabus' | 'photo' | 'other';

export type MaterialStatus = 'processing' | 'ready' | 'failed';

export interface Material {
  id: string;
  courseId: string;
  title: string;
  kind: MaterialKind;
  sizeBytes: number;
  restricted: boolean; // solution keys and rubrics; never sent to students
  status: MaterialStatus;
}

export interface MaterialLink {
  url: string; // signed Cloud Storage URL, valid for 15 minutes
  page: number | null; // page to open, when the link comes from a citation
  expiresAt: string;
}

// ---------------------------------------------------------------------------
// Chats
// ---------------------------------------------------------------------------

export interface ThreadSummary {
  id: string;
  courseId: string;
  courseCode: string;
  assignmentId: string | null;
  ownerRole: Role; // teacher threads skip "hints only" and dashboard counts
  title: string;
  updatedAt: string;
}

export interface Citation {
  materialId: string;
  title: string; // "Lecture 6"
  page: number;
}

export type AttachmentType = 'image' | 'pdf';

export type AttachmentSource = 'camera' | 'library' | 'files';

// One-off context for a single question. Not added to course materials.
export interface Attachment {
  url: string; // signed Cloud Storage URL, valid for 15 minutes
  type: AttachmentType;
  source: AttachmentSource;
}

export interface Message {
  id: string;
  threadId: string;
  role: Role | 'nudge'; // who wrote it
  content: string;
  attachment: Attachment | null;
  citations: Citation[];
  createdAt: string;
}

// ---------------------------------------------------------------------------
// Flags and the teacher dashboard
// ---------------------------------------------------------------------------

export type FlagStatus = 'open' | 'resolved';

export interface Flag {
  id: string;
  messageId: string;
  courseId: string;
  assignmentTitle: string | null;
  flagCount: number;
  status: FlagStatus;
  correction: string | null; // the teacher's fix, once resolved
  createdAt: string;
}

export interface DashboardStats {
  questionCount: number; // student questions only
  activeStudents: number;
  flaggedCount: number;
}

export interface TrendingTopic {
  id: string;
  title: string;
  studentCount: number;
}

// ---------------------------------------------------------------------------
// Profiles
// ---------------------------------------------------------------------------

export interface StudentStats {
  questionsAsked: number;
  problemsSolved: number;
  photosChecked: number;
}

export interface StudentNotifications {
  deadlineReminders: boolean; // mutes reminders for this student only
  studyNudges: boolean;
}

export interface TeacherStats {
  sectionsNow: number;
  students: number;
  semesters: number;
}

// Teachers don't get deadline reminders.
export interface TeacherNotifications {
  flaggedAnswers: boolean;
  weeklyDigest: boolean;
}

// ---------------------------------------------------------------------------
// Shared endpoints
// ---------------------------------------------------------------------------

// POST /auth/login
export interface LoginRequest {
  email: string;
  password: string;
}
export interface LoginResponse {
  token: string;
  user: User;
}

// GET /threads?q=
export interface GetThreadsResponse {
  threads: ThreadSummary[];
}

// POST /threads
export interface CreateThreadRequest {
  courseId: string;
  assignmentId?: string;
  title: string;
}
export interface CreateThreadResponse {
  thread: ThreadSummary;
}

// GET /threads/{threadId}
export interface GetThreadResponse {
  thread: ThreadSummary;
  messages: Message[];
}

// POST /threads/{threadId}/messages (multipart/form-data)
export interface SendMessageRequest {
  content: string;
  attachment?: UploadFile; // an image or a PDF
  attachmentSource?: AttachmentSource; // required when attachment is sent
}
export interface SendMessageResponse {
  sentMessage: Message;
  reply: Message;
}

// ---------------------------------------------------------------------------
// Student endpoints
// ---------------------------------------------------------------------------

// GET /student/me
export interface GetStudentMeResponse {
  user: User;
  stats: StudentStats;
  notifications: StudentNotifications;
}

// PATCH /student/me (send only the switches that changed)
export interface UpdateStudentMeRequest {
  notifications: Partial<StudentNotifications>;
}
export interface UpdateStudentMeResponse {
  notifications: StudentNotifications;
}

// GET /student/courses
export interface GetStudentCoursesResponse {
  upNext: Assignment | null;
  courses: StudentCourseSummary[];
}

// POST /student/courses/join
export interface JoinCourseRequest {
  joinCode: string; // 6 characters
}
export interface JoinCourseResponse {
  course: StudentCourseSummary;
}

// GET /student/courses/{courseId}
export interface GetStudentCourseResponse {
  course: Course;
  materials: Material[]; // never includes restricted files
}

// GET /student/materials/{materialId}/link
export type GetMaterialLinkResponse = MaterialLink;

// POST /student/messages/{messageId}/flag
export interface FlagMessageRequest {
  reason: string;
  note?: string;
}
export interface FlagMessageResponse {
  flag: Flag;
  officeHours: string | null;
}

// ---------------------------------------------------------------------------
// Teacher endpoints
// ---------------------------------------------------------------------------

// GET /teacher/me
export interface GetTeacherMeResponse {
  user: User;
  stats: TeacherStats;
  notifications: TeacherNotifications;
}

// PATCH /teacher/me (send only the switches that changed)
export interface UpdateTeacherMeRequest {
  notifications: Partial<TeacherNotifications>;
}
export interface UpdateTeacherMeResponse {
  notifications: TeacherNotifications;
}

// GET /teacher/courses
export interface GetTeacherCoursesResponse {
  semesters: Semester[];
}

// POST /teacher/courses
export interface CreateCourseRequest {
  code: string;
  section: string;
  semester: string;
  copyFrom?: {
    courseId: string;
    materials: boolean;
    settings: boolean;
    shiftDeadlines: boolean;
  };
}
export interface CreateCourseResponse {
  course: Course; // includes joinCode
}

// GET /teacher/courses/{courseId}
export interface GetTeacherCourseResponse {
  course: Course; // includes joinCode
  settings: CourseSettings;
  materials: Material[]; // includes restricted files
}

// PATCH /teacher/courses/{courseId}/settings (send only the switches that changed)
export type UpdateCourseSettingsRequest = Partial<CourseSettings>;
export interface UpdateCourseSettingsResponse {
  settings: CourseSettings;
}

// POST /teacher/courses/{courseId}/materials (multipart/form-data)
export interface UploadMaterialRequest {
  file: UploadFile;
  kind: MaterialKind;
  restricted: boolean;
}
export interface UploadMaterialResponse {
  material: Material; // starts as "processing"
}

// GET /teacher/courses/{courseId}/dashboard
export interface GetDashboardResponse {
  stats: DashboardStats;
  trending: TrendingTopic[];
  needsReview: Flag[];
}

// POST /teacher/courses/{courseId}/canvas/import
// Planned for v2; details TBD.
export interface CanvasImportRequest {
  syllabus: boolean;
  files: boolean;
  deadlines: boolean;
}
export interface CanvasImportResponse {
  materialsImported: number;
  assignmentsImported: number;
}
