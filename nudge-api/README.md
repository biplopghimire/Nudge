# Nudge API: MVP endpoints

Each JSON file has the method, path, the screens that use it, an example request and an example response.

Login is shared. After that, students use `/student/...` and teachers use `/teacher/...`. All requests except login send `Authorization: Bearer {token}`, and the backend rejects a student token on a teacher endpoint and the other way around. Field names match the TypeScript types in Part 9.

## Shared

| Method | Path | What it does |
|---|---|---|
| POST | `/auth/login` | Sign in as a student or teacher. |

## Student

| Method | Path | What it does |
|---|---|---|
| GET | `/student/me` | Get the signed-in student, their stats and their notification switches. |
| PATCH | `/student/me` | Turn the student's notification switches on or off. |
| GET | `/student/courses` | Get the student's Up next assignment and their courses with due badges. |
| POST | `/student/courses/join` | Student joins a course with the 6-character code from their teacher. |
| GET | `/student/courses/{courseId}` | Get one course and its materials. |
| GET | `/student/materials/{materialId}/link` | Get a temporary link (15 minutes) to open a file. |
| GET | `/student/threads` | List the student's past chats, newest first. |
| POST | `/student/threads` | Start a new chat in a course, optionally tied to an assignment. |
| GET | `/student/threads/{threadId}` | Get one chat and all its messages, including Nudge's citations. |
| POST | `/student/threads/{threadId}/messages` | Send a question, with an optional photo (multipart/form-data), and get Nudge's reply. |
| POST | `/student/messages/{messageId}/flag` | Student reports a Nudge reply. |

## Teacher

| Method | Path | What it does |
|---|---|---|
| GET | `/teacher/me` | Get the signed-in teacher, their profile counts and their notification switches. |
| PATCH | `/teacher/me` | Turn the teacher's notification switches on or off. |
| GET | `/teacher/courses` | List the teacher's courses grouped by semester, with material and student counts. |
| POST | `/teacher/courses` | Teacher creates a course and gets its join code. |
| GET | `/teacher/courses/{courseId}` | Get one course with its join code, Nudge settings and all materials, including restricted ones. |
| PATCH | `/teacher/courses/{courseId}/settings` | Teacher changes how Nudge helps in this course. |
| POST | `/teacher/courses/{courseId}/materials` | Teacher uploads a PDF or photo (multipart/form-data). |
| GET | `/teacher/courses/{courseId}/dashboard` | Teacher home for one course: question count, active students, flagged count, trending topics and flagged answers waiting for review. |
