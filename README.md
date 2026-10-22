# Nudge

Nudge is a mobile study assistant that answers students' questions using only their course's own materials. Teachers upload slides, notes, homework and syllabi; students ask questions (or snap a photo of their work) and get replies that cite the exact file and page they came from. Teachers decide how Nudge behaves, for example giving hints only instead of final answers.

Built for 67-443 Mobile App Development, Fall 2026, Carnegie Mellon University.

## How it works

| Piece | Technology | Role |
|---|---|---|
| App | React Native (Expo), TypeScript | What students and teachers use. Talks only to our backend. |
| Backend | Python (FastAPI) on Google Cloud Run | Logins, courses, chats and uploads. Talks to the other services. |
| File storage | Google Cloud Storage | Original files: PDFs, slides, notes and photos. Private; opened through 15-minute signed URLs. |
| Database | Postgres + pgvector (Supabase) | Users, courses, chats and settings, plus the text chunks and embeddings the AI searches. |
| AI | Gemini API | Embeddings, reading photos and page images, and writing Nudge's replies. |

### Answering a question (RAG)

1. **On upload**, each page is converted to clean text by Gemini (math as LaTeX), split into chunks (one per slide, problem or section, up to ~400 words), labeled with the file title and heading, embedded with `gemini-embedding-2` (768 dimensions), and saved to the `chunks` table.
2. **On a question**, the backend embeds the question and runs two searches over the course's unrestricted chunks: by meaning (pgvector cosine distance) and by keyword (Postgres full-text search). The results are merged and the best 6 to 8 chunks are kept.
3. **Gemini** gets the question, any photo, the chunks, the current assignment's text and the course settings, and is told to use only the course material, match its notation, cite file and page, admit when the material doesn't cover something, and give only hints when "hints only" is on.
4. **The app** shows the reply with tappable citations that open the cited file.

Solution keys are stored as restricted chunks. They are only searched when a student sends their own work and the teacher has turned on "Use solution keys", and Gemini uses them to find the mistake without ever showing them.

## Features

### Version 1 (November 9)

- Student and teacher sign in
- Create a course with a join code; join with a 6-character code
- Upload materials (PDFs and photos), processed into searchable chunks
- Chat grounded in course materials, with citations
- "Hints only" teacher setting
- Photos in chat (camera and photo library)
- Open cited files
- Past chats and class switching
- Report a wrong answer; teachers see flags on Home
- Student home with an "Up next" card and course list

### Version 2 (December 4)

- Canvas import (syllabus, files and deadlines)
- Teacher insights: question counts and trending topics
- Fix flagged answers, with an office-hours option for students
- Solution keys for checking student work
- Reuse a past course (files, settings, deadlines)
- Notifications: deadline reminders, study nudges, weekly digest
- Search chats
- Student stats
- "View as student" test mode for teachers
- Offline access to saved files and chats

## API overview

Full details for each endpoint, including the screens that use it and an example request and response, are in [`nudge-api/`](nudge-api/).

Every request except login sends `Authorization: Bearer {token}`. After login, students use `/student/...` and teachers use `/teacher/...`. The backend rejects a student token on a teacher endpoint and the other way around.

**Shared**

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | Sign in as a student or teacher |

**Student**

| Method | Path | Description |
|---|---|---|
| GET | `/student/me` | Signed-in student, their stats and notification switches |
| PATCH | `/student/me` | Turn notification switches on or off |
| GET | `/student/courses` | "Up next" assignment and the student's courses with due badges |
| POST | `/student/courses/join` | Join a course with a 6-character code |
| GET | `/student/courses/{courseId}` | One course and its materials (never restricted files) |
| GET | `/student/materials/{materialId}/link` | Temporary 15-minute link to open a file |
| GET | `/student/threads` | Past chats, newest first (`?q=` to search by title) |
| POST | `/student/threads` | Start a chat in a course, optionally tied to an assignment |
| GET | `/student/threads/{threadId}` | One chat and all its messages, with citations |
| POST | `/student/threads/{threadId}/messages` | Ask a question with an optional photo (multipart) and get Nudge's reply |
| POST | `/student/messages/{messageId}/flag` | Report a Nudge reply |

**Teacher**

| Method | Path | Description |
|---|---|---|
| GET | `/teacher/me` | Signed-in teacher, profile counts and notification switches |
| PATCH | `/teacher/me` | Turn notification switches on or off |
| GET | `/teacher/courses` | Courses grouped by semester, with material and student counts |
| POST | `/teacher/courses` | Create a course and get its join code (send `copyFrom` to reuse a past course) |
| GET | `/teacher/courses/{courseId}` | One course with its join code, Nudge settings and all materials |
| PATCH | `/teacher/courses/{courseId}/settings` | Change how Nudge helps in the course |
| POST | `/teacher/courses/{courseId}/materials` | Upload a PDF or photo (multipart); starts as `processing`, then `ready` |
| GET | `/teacher/courses/{courseId}/dashboard` | Question count, active students, flagged count, trending topics and flagged answers to review |

## Data model

Postgres tables: `users`, `courses`, `enrollments`, `materials`, `assignments`, `chunks`, `threads`, `messages`, `flags`. The `chunks` table holds both a `vector(768)` embedding (HNSW index) for meaning search and a generated `tsvector` (GIN index) for exact-word search.

Course files live in the `nudge-course-files` bucket:

```
courses/{courseId}/materials/{materialId}/{fileName}    teacher materials
courses/{courseId}/restricted/{materialId}/{fileName}   solution keys and rubrics
uploads/{userId}/{attachmentId}.jpg                     photos sent in chat
```

## On the phone

- **TanStack Query** caches backend responses so screens load instantly.
- **expo-sqlite** keeps courses, chats and messages available offline.
- **expo-file-system** saves opened PDFs.
- **expo-secure-store** stores the login token.

## Secrets

API keys, Canvas tokens and service-account keys are never committed. Keep them in a local `.env` file (ignored by git).

## Team

67-443 Mobile App Development, Fall 2026.
