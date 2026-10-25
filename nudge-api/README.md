# Nudge API: MVP endpoints

Each JSON file has the method, path, the screens that use it, the TypeScript types for its request and response, an example request and an example response.

The types are in [`nudge-types.ts`](nudge-types.ts). Each example response is one filled-in instance of the type named in its `types.response` field, and field names match exactly.

Every request except login sends `Authorization: Bearer {token}`. After login, students use `/student/...` and teachers use `/teacher/...`; these reject the other role's token. The chat endpoints under `/threads` accept either role and check the role inside: students can use threads in courses they are enrolled in, teachers in courses they teach. Each thread records its `ownerRole`.

## Shared

| Method | Path | What it does | File |
|---|---|---|---|
| POST | `/auth/login` | Sign in as a student or teacher. | [01](shared/01-post-auth-login.json) |
| GET | `/threads` | List your past chats, newest first (`?q=` to search by title). | [02](shared/02-get-threads.json) |
| POST | `/threads` | Start a new chat in a course, optionally tied to an assignment. | [03](shared/03-post-threads.json) |
| GET | `/threads/{threadId}` | Get one chat and all its messages, including Nudge's citations. | [04](shared/04-get-thread.json) |
| POST | `/threads/{threadId}/messages` | Send a question, with an optional `attachment` (image or PDF, multipart/form-data), and get Nudge's reply. | [05](shared/05-post-thread-message.json) |

## Student

| Method | Path | What it does | File |
|---|---|---|---|
| GET | `/student/me` | Get the signed-in student, their stats and their notification switches. | [01](student/01-get-me.json) |
| PATCH | `/student/me` | Turn the student's notification switches on or off, including muting deadline reminders. | [02](student/02-patch-me.json) |
| GET | `/student/courses` | Get the student's Up next assignment and their courses with due badges. | [03](student/03-get-courses.json) |
| POST | `/student/courses/join` | Join a course with the 6-character code from the teacher. | [04](student/04-post-courses-join.json) |
| GET | `/student/courses/{courseId}` | Get one course and its materials (never restricted files). | [05](student/05-get-course.json) |
| GET | `/student/materials/{materialId}/link` | Get a temporary link (15 minutes) to open a file. | [06](student/06-get-material-link.json) |
| POST | `/student/messages/{messageId}/flag` | Report a Nudge reply. | [07](student/07-post-message-flag.json) |

## Teacher

| Method | Path | What it does | File |
|---|---|---|---|
| GET | `/teacher/me` | Get the signed-in teacher, their profile counts and their notification switches. | [01](teacher/01-get-me.json) |
| PATCH | `/teacher/me` | Turn the teacher's notification switches on or off. | [02](teacher/02-patch-me.json) |
| GET | `/teacher/courses` | List the teacher's courses grouped by semester, with material and student counts. | [03](teacher/03-get-courses.json) |
| POST | `/teacher/courses` | Create a course and get its join code (send `copyFrom` to reuse a past course). | [04](teacher/04-post-courses.json) |
| GET | `/teacher/courses/{courseId}` | Get one course with its join code, Nudge settings and all materials, including restricted ones. | [05](teacher/05-get-course.json) |
| PATCH | `/teacher/courses/{courseId}/settings` | Change how Nudge helps in this course, and turn deadline reminders on for every student. | [06](teacher/06-patch-course-settings.json) |
| POST | `/teacher/courses/{courseId}/materials` | Upload a PDF or photo (multipart/form-data). | [07](teacher/07-post-course-materials.json) |
| GET | `/teacher/courses/{courseId}/dashboard` | Question count, active students, flagged count, trending topics and flagged answers waiting for review (student questions only). | [08](teacher/08-get-course-dashboard.json) |
| POST | `/teacher/courses/{courseId}/canvas/import` | *Planned for v2, details TBD.* Import the syllabus, files and deadlines from Canvas. | [09](teacher/09-post-canvas-import.json) |
