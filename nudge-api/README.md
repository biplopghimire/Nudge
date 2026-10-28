# Nudge API

FastAPI backend for Nudge. All endpoints below are implemented. The Nudge engine (Postgres + pgvector search and Gemini) is real; by default everything runs on mocks, so it also works with no accounts or keys. Cloud file storage is still mocked.

## Run it

```bash
cd nudge-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

That runs on mocks (in-memory data, canned AI replies). To run the real engine locally:

1. **Postgres with pgvector:** install [Postgres.app](https://postgresapp.com) (pgvector is included) and start it, then `createdb nudge`.
2. **`.env`** (copy `.env.example`):
   ```
   NUDGE_REPOSITORY=postgres
   NUDGE_DATABASE_URL=postgresql:///nudge
   NUDGE_AI=gemini
   NUDGE_GEMINI_API_KEY=your key from https://aistudio.google.com/apikey
   NUDGE_STORAGE=local
   NUDGE_AUTH=jwt
   NUDGE_JWT_SECRET=a long random string (see .env.example)
   NUDGE_SEED_PASSWORD=a password for the example accounts
   ```
3. **Tables and example data:** `python -m scripts.db setup` (embeds the example chunks with Gemini).
4. `uvicorn app.main:app --reload`, then in another terminal `python -m scripts.smoke`. It uploads `samples/lecture-7-integration-by-parts.pdf` as Prof. H, waits for processing, and asks four questions as Sam, printing each reply and its citation chips.

- Interactive docs: http://localhost:8000/docs
- From the Expo app on a phone, use your computer's LAN IP, for example `uvicorn app.main:app --reload --host 0.0.0.0`, then call `http://192.168.x.x:8000`.
- Tests: `pytest`. To also run every API test against Postgres: `createdb nudge_test`, `NUDGE_DATABASE_URL=postgresql:///nudge_test python -m scripts.db reset`, then `NUDGE_TEST_DATABASE_URL=postgresql:///nudge_test pytest`. `tests/test_examples.py` checks every endpoint returns the same shape as its example JSON file (planned endpoints are skipped).

### Example accounts

With `NUDGE_AUTH=mock` (the default) any non-empty password works and the token is `mock-{userId}`.
With `NUDGE_AUTH=jwt` they use `NUDGE_SEED_PASSWORD`, and new accounts come from `POST /auth/signup`.

| Email | Role | Notes |
|---|---|---|
| `samlee@andrew.cmu.edu` | student | In 67-272 Sec 1 and 15-213, has 4 chats |
| `alexchen@andrew.cmu.edu` | student | In 67-272 Sec 1 and Sec 2 |
| `ppatel@andrew.cmu.edu` | student | In 67-272 Sec 1 |
| `profh@cmu.edu` | teacher | Teaches 67-272 (join code `K7M4QX`), has past semesters to reuse and 1 chat |
| `profk@cmu.edu` | teacher | Teaches 15-213 (join code `H2QW9D`) |

With `NUDGE_REPOSITORY=memory`, data resets when the server restarts and uploads stay "processing" for 5 seconds. With Postgres, `python -m scripts.db seed` resets the data.

## How the code is organized

```
app/
  main.py            creates the FastAPI app
  config.py          settings from env vars / .env (see .env.example)
  deps.py            picks mock or real implementations, gives services to routers
  errors.py          {"error", "message"} error responses
  domain.py          internal records, one per database table (snake_case)
  routers/           HTTP only: parse the request, call a service
    auth.py  threads.py  student.py  teacher.py
  services/          the app's logic: permissions, rules, building responses
    threads.py       chats for both roles: access checks, attachments, saving messages
    student.py  teacher.py  auth.py
    chat.py          RAG: embed, search two ways, merge, ask the AI, cite
    ingestion.py     uploaded file -> page text -> chunks -> embeddings
    views.py         domain records -> API responses
  schemas/           request/response models, camelCase JSON (same names as nudge-types.ts)
  repositories/      all database access
    base.py          the contract: every query the services need
    memory.py        in-memory version
    postgres.py      Postgres + pgvector
    seed.py          example data, same IDs as the JSON files
    pg_seed.py       loads the example data into Postgres
  integrations/      outside services, each an interface + a mock
    ai.py            the AI interface, Nudge's instructions, mock AI
    gemini.py        Gemini: embeddings, PDF transcription, replies; timeouts and model fallback
    storage.py       file storage: in-memory mock and local disk
    auth.py
db/schema.sql        Postgres tables (Part 3 plus the columns the API needs)
scripts/db.py        create the tables and load example data
scripts/smoke.py     end-to-end check against a running server
samples/             a 4-page lecture PDF for testing uploads
```

A request goes **router → service → repository / integrations**. Services only use the interfaces in `repositories/base.py` and `integrations/`, so replacing a mock never touches the logic.

## How the engine works

**Upload** (`services/ingestion.py`, runs in the background after `POST /teacher/courses/{id}/materials`):
the file is saved to storage, Gemini transcribes each page to text (PDFs are sent in parts of 8 pages, math as LaTeX),
each page is split into chunks of at most 400 words labeled like "Lecture 7, page 2 (Choosing u)", the chunks are
embedded with `gemini-embedding-2` (768 numbers) and saved. The material goes from `processing` to `ready` (or `failed`).

**Question** (`services/chat.py`): the question is embedded and searched two ways in the course's chunks (pgvector
cosine distance, and Postgres full-text search on any shared word). The two rankings are merged, and the best 8 chunks
go to Gemini as numbered sources with Nudge's rules (`integrations/ai.py`: course material only, hints only when the
setting is on, never reveal solution keys). Gemini returns the reply and which sources it used; those become the
citation chips. Solution keys are only searched when a student sends their own work.

**Accounts** (`NUDGE_AUTH=jwt`): passwords are stored as salted scrypt hashes, and login returns a token signed with
`NUDGE_JWT_SECRET` that lasts 30 days. `POST /auth/signup` creates student or teacher accounts.

**Reliability:** every Gemini call has a timeout. When a model is overloaded (503) or times out, the next model in the
list is tried, then the whole list once more. If all fail, the API answers `503 nudge_busy` and nothing is saved.

## Still mocked

| Mock | What to do | Switch |
|---|---|---|
| Cloud file storage | Write a cloud `StorageClient` in `integrations/storage.py` and return it from `build_storage`. | `NUDGE_STORAGE=...` |

Real credentials go in `nudge-api/.env`, which git ignores.

## Endpoints

Each JSON file has the method, path, the screens that use it, the TypeScript types for its request and response, an example request and an example response.

The types are in [`nudge-types.ts`](nudge-types.ts). Each example response is one filled-in instance of the type named in its `types.response` field, and field names match exactly.

Every request except login and sign-up sends `Authorization: Bearer {token}`. After login, students use `/student/...` and teachers use `/teacher/...`; these reject the other role's token. The chat endpoints under `/threads` accept either role and check the role inside: students can use threads in courses they are enrolled in, teachers in courses they teach. Each thread records its `ownerRole`.

## Shared

| Method | Path | What it does | File |
|---|---|---|---|
| POST | `/auth/login` | Sign in as a student or teacher. | [01](shared/01-post-auth-login.json) |
| POST | `/auth/signup` | Create a student or teacher account and sign in. | [06](shared/06-post-auth-signup.json) |
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
| POST | `/teacher/courses/{courseId}/canvas/import` | *Planned for v2, details TBD.* Import the syllabus, files and deadlines from Canvas. Returns 501 for now. | [09](teacher/09-post-canvas-import.json) |
