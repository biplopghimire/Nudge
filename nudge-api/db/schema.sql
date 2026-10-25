-- Nudge database (Postgres + pgvector). Run once in the Supabase SQL editor.
-- This is the Part 3 schema plus the columns the API needs that Part 3 left out,
-- marked "added". app/domain.py mirrors these tables.

create extension if not exists vector;

create table users (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  email       text unique not null,
  role        text not null check (role in ('student', 'teacher')),
  department  text,                                     -- added: teacher profile
  notifications jsonb not null default '{}',            -- {"deadlineReminders": true, ...}
  created_at  timestamptz not null default now()
);

create table courses (
  id          uuid primary key default gen_random_uuid(),
  code        text not null,              -- '67-272'
  section     text not null,              -- 'Sec 1'
  semester    text not null,              -- 'Fall 2026'
  teacher_id  uuid not null references users(id),
  join_code   text unique not null,       -- 'K7M4QX'
  office_hours text,                      -- added: shown on the flag sheet
  hints_only  boolean not null default true,
  use_solution_keys boolean not null default false,
  cite_materials    boolean not null default true,
  deadline_reminders boolean not null default true  -- on for every student; each can mute it in users.notifications
);

create table enrollments (
  user_id     uuid references users(id),
  course_id   uuid references courses(id),
  joined_at   timestamptz not null default now(),
  primary key (user_id, course_id)
);

create table materials (
  id          uuid primary key default gen_random_uuid(),
  course_id   uuid not null references courses(id),
  title       text not null,
  kind        text not null check (kind in ('slides', 'notes', 'homework', 'syllabus', 'photo', 'other')),
  size_bytes  integer not null,
  storage_path text not null,             -- path in Google Cloud Storage
  restricted  boolean not null default false,   -- solution keys and rubrics
  status      text not null default 'processing' check (status in ('processing', 'ready', 'failed')),
  uploaded_at timestamptz not null default now()
);

create table assignments (
  id          uuid primary key default gen_random_uuid(),
  course_id   uuid not null references courses(id),
  material_id uuid references materials(id),   -- the assignment's own file, if uploaded
  title       text not null,              -- 'Problem Set 4'
  short_title text,                       -- added: 'PS 4', used in badges like 'PS 4 · Thu'
  due_at      timestamptz
);

create table chunks (
  id          uuid primary key default gen_random_uuid(),
  course_id   uuid not null references courses(id),
  material_id uuid not null references materials(id) on delete cascade,
  page        integer,
  heading     text,                       -- slide title or problem number
  content     text not null,
  restricted  boolean not null default false,
  embedding   vector(768) not null,
  search      tsvector generated always as (to_tsvector('english', content)) stored
);

create index on chunks (course_id);
create index on chunks using hnsw (embedding vector_cosine_ops);
create index on chunks using gin (search);

create table threads (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references users(id),
  course_id     uuid not null references courses(id),
  assignment_id uuid references assignments(id),
  owner_role    text not null default 'student' check (owner_role in ('student', 'teacher')),  -- added
  title         text not null,            -- 'Problem 3'
  updated_at    timestamptz not null default now()
);

create table messages (
  id          uuid primary key default gen_random_uuid(),
  thread_id   uuid not null references threads(id) on delete cascade,
  role        text not null check (role in ('student', 'teacher', 'nudge')),
  content     text not null,
  attachment_path text,                   -- image or PDF in Google Cloud Storage, if any
  attachment_type text check (attachment_type in ('image', 'pdf')),                     -- added
  attachment_source text check (attachment_source in ('camera', 'library', 'files')),  -- added
  citations   jsonb not null default '[]',  -- [{materialId, title, page}]
  created_at  timestamptz not null default now()
);

create table flags (
  id          uuid primary key default gen_random_uuid(),
  message_id  uuid not null references messages(id),
  course_id   uuid not null references courses(id),
  reason      text not null check (reason in ('wrong answer', 'gave away answer', 'other')),
  note        text,
  status      text not null default 'open' check (status in ('open', 'resolved')),
  correction  text,
  created_at  timestamptz not null default now()
);

-- added: filled by a periodic job that groups recent questions (version 2).
create table trending_topics (
  id            uuid primary key default gen_random_uuid(),
  course_id     uuid not null references courses(id),
  title         text not null,            -- 'Substitution in PS 4'
  student_count integer not null default 0,
  updated_at    timestamptz not null default now()
);
