# Nudge external API tests (Sprint 3, Part 6)

TypeScript scripts that call the two outside APIs Nudge depends on and parse the JSON they return. The types in `src/canvas/types.ts` and `src/gemini/types.ts` describe that JSON, and `src/canvas/toNudge.ts` turns Canvas data into Nudge's own types (Part 9).

| Script | API | What it shows |
|---|---|---|
| `npm run canvas` | Canvas, student side | My courses, the 67-443 syllabus, every 67-443 assignment with its due date (following Canvas's paged `Link` headers), and the "Up next" assignment |
| `npm run canvas:teacher` | Canvas, teacher/TA side | The version 2 "Import from Canvas" flow: courses I teach or TA, folders, every file mapped to a Nudge `Material` (solution keys and hidden files marked restricted), one PDF downloaded, and assignments mapped to Nudge `Assignment`s |
| `npm run gemini` | Gemini | A question with "hints only", a photo of handwritten work (`samples/handwritten-work.jpg`), and a 768-number embedding |

## Setup

Requires Node 22.6 or newer (it runs TypeScript directly).

```bash
cd api-tests
npm install
cp .env.example .env    # then fill in the tokens
npm run canvas
```

- **Canvas token:** Canvas → Account → Settings → Approved Integrations → New Access Token. This is a personal token for testing only. A real launch would need CMU's Canvas admins to approve Nudge.
- **Gemini key:** https://aistudio.google.com/apikey. Change `GEMINI_MODEL` or `GEMINI_EMBEDDING_MODEL` in `.env` if a model name is retired.
- `npm run typecheck` checks the types.

`.env` is ignored by git. Never commit tokens: this repo is public.

## Canvas endpoints used

All requests send `Authorization: Bearer {token}`. Lists are paged, so `canvasGetAll` follows the `rel="next"` URL in the `Link` header until there is none.

| Request | Used for |
|---|---|
| `GET /api/v1/courses?enrollment_state=active&include[]=term` | Courses, semester and my role in each (`enrollments[].type`) |
| `GET /api/v1/courses/:id?include[]=syllabus_body` | Syllabus HTML |
| `GET /api/v1/courses/:id/assignments?order_by=due_at` | Assignments and due dates |
| `GET /api/v1/courses/:id/folders` | Folder names, which help guess material types and hidden folders |
| `GET /api/v1/courses/:id/files` | Files: name, content type, size, download link |
| `GET {file.url}` | The file's bytes, for the upload pipeline |

The teacher script reads only course content. It does not call roster, submission or grade endpoints.
