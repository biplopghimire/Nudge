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

**Student**

| Request | Description |
|---|---|
| `GET /me` | Signed-in user |
| `GET /me/home` | "Up next" assignment and the student's courses |
| `POST /enrollments` | Join a course with a code |
| `GET /me/courses` | Student's courses |
| `GET /courses/{courseId}/materials` | A course's materials |
| `GET /materials/{materialId}/link` | Temporary link to open a file |
| `GET /threads` | List or search past chats |
| `POST /threads` | Start a chat |
| `GET /threads/{threadId}/messages` | Messages in a chat |
| `POST /threads/{threadId}/messages` | Ask a question (optional photo) and get Nudge's reply |
| `POST /messages/{messageId}/flag` | Report an answer as wrong |
| `GET /me/stats` | Questions asked, problems solved, photos checked |
| `PATCH /me/notifications` | Turn reminders on or off |

**Teacher**

| Request | Description |
|---|---|
| `GET /teacher/courses` | Teacher's courses by semester |
| `POST /courses` | Create a course and its join code |
| `POST /courses/{courseId}/copy` | Copy a past course |
| `POST /courses/{courseId}/materials` | Upload a file |
| `DELETE /materials/{materialId}` | Remove a file and its chunks |
| `GET /courses/{courseId}/settings` | Read Nudge's settings for the course |
| `PATCH /courses/{courseId}/settings` | Change Nudge's settings |
| `GET /courses/{courseId}/summary` | Question count, active students, flagged count |
| `GET /courses/{courseId}/trending` | Topics students ask about most |
| `GET /courses/{courseId}/flags` | Answers waiting for review |
| `PATCH /flags/{flagId}` | Correct and close a flagged answer |

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
