# Nudge API

FastAPI backend for Nudge. All endpoints below are implemented. For now the database, Gemini, Cloud Storage and login are mocked, so it runs with no accounts or keys.

## Run it

```bash
cd nudge-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

- Interactive docs: http://localhost:8000/docs
- From the Expo app on a phone, use your computer's LAN IP, for example `uvicorn app.main:app --reload --host 0.0.0.0`, then call `http://192.168.x.x:8000`.
- Tests: `pytest`. `tests/test_examples.py` checks every endpoint returns the same shape as its example JSON file.

### Mock accounts

Any non-empty password works. The token is `mock-{userId}`.

| Email | Role | Notes |
|---|---|---|
| `samlee@andrew.cmu.edu` | student | In 67-272 Sec 1 and 15-213, has 4 chats |
| `alexchen@andrew.cmu.edu` | student | In 67-272 Sec 1 and Sec 2 |
| `ppatel@andrew.cmu.edu` | student | In 67-272 Sec 1 |
| `profh@cmu.edu` | teacher | Teaches 67-272 (join code `K7M4QX`), has past semesters to reuse |
| `profk@cmu.edu` | teacher | Teaches 15-213 (join code `H2QW9D`) |

Data is kept in memory and resets when the server restarts. Uploads stay "processing" for 5 seconds, then become "ready".

## How the code is organized

```
app/
  main.py            creates the FastAPI app
  config.py          settings from env vars / .env (see .env.example)
  deps.py            picks mock or real implementations, gives services to routers
  errors.py          {"error", "message"} error responses
  domain.py          internal records, one per database table (snake_case)
  routers/           HTTP only: parse the request, call a service
    auth.py  student.py  teacher.py
  services/          the app's logic: permissions, rules, building responses
    student.py  teacher.py  auth.py
    chat.py          RAG: embed, search two ways, merge, ask the AI, cite
    ingestion.py     uploaded file -> page text -> chunks -> embeddings
    views.py         domain records -> API responses
  schemas/           request/response models, camelCase JSON (Part 9 types)
  repositories/      all database access
    base.py          the contract: every query the services need
    memory.py        mock (used now)
    postgres.py      Postgres + pgvector (to fill in)
    seed.py          example data, same IDs as the JSON files
  integrations/      outside services, each an interface + a mock
    ai.py  storage.py  auth.py
db/schema.sql        Postgres tables (Part 3 plus the columns the API needs)
```

A request goes **router → service → repository / integrations**. Services only use the interfaces in `repositories/base.py` and `integrations/`, so replacing a mock never touches the logic.

## Replacing the mocks

| Mock | What to do | Switch |
|---|---|---|
| Database | Run `db/schema.sql` in Supabase. Fill in the `TODO` methods in `repositories/postgres.py` (the two RAG searches are already written). `pip install -r requirements-postgres.txt`. | `NUDGE_REPOSITORY=postgres`, `NUDGE_DATABASE_URL=...` |
| Gemini | Write `GeminiClient(AIClient)` in `integrations/ai.py` and return it from `build_ai` in `deps.py`. | `NUDGE_AI=gemini`, `NUDGE_GEMINI_API_KEY=...` |
| Cloud Storage | Write `GCSStorage(StorageClient)` in `integrations/storage.py` and return it from `build_storage`. | `NUDGE_STORAGE=gcs` |
| Login | Write a real `AuthProvider` (password hashes or Supabase Auth, signed JWTs) in `integrations/auth.py`. | add a value to `auth` in `config.py` |
| PDF pages | `split_pages` in `services/ingestion.py` treats a file as one page. Render each PDF page to an image. | none |

Real credentials go in `nudge-api/.env`, which git ignores.

## Endpoints

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
