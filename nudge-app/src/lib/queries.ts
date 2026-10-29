/**
 * Server data, cached with TanStack Query. Screens read through these hooks so
 * they render instantly from cache and refresh in the background.
 */
import type { CourseSettings, GetTeacherCourseResponse } from "@api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";

export const keys = {
  studentCourses: ["student", "courses"] as const,
  studentMe: ["student", "me"] as const,
  teacherCourses: ["teacher", "courses"] as const,
  teacherCourse: (id: string) => ["teacher", "course", id] as const,
  teacherMe: ["teacher", "me"] as const,
  threads: ["threads"] as const,
  thread: (id: string) => ["thread", id] as const,
};

export const useStudentCourses = () =>
  useQuery({ queryKey: keys.studentCourses, queryFn: api.studentCourses });

export const useStudentMe = () => useQuery({ queryKey: keys.studentMe, queryFn: api.studentMe });

export const useTeacherCourses = () =>
  useQuery({ queryKey: keys.teacherCourses, queryFn: api.teacherCourses });

export const useTeacherMe = () => useQuery({ queryKey: keys.teacherMe, queryFn: api.teacherMe });

export const useThreads = () => useQuery({ queryKey: keys.threads, queryFn: () => api.threads() });

export const useThread = (id: string) =>
  useQuery({ queryKey: keys.thread(id), queryFn: () => api.thread(id) });

/** A teacher's course. Polls every 2s while any upload is still processing. */
export const useTeacherCourse = (id: string) =>
  useQuery({
    queryKey: keys.teacherCourse(id),
    queryFn: () => api.teacherCourse(id),
    refetchInterval: (query) =>
      query.state.data?.materials.some((m) => m.status === "processing") ? 2000 : false,
  });

/** Flip a course setting instantly, then confirm with the server (rolls back on failure). */
export function useUpdateSettings(courseId: string) {
  const client = useQueryClient();
  const key = keys.teacherCourse(courseId);
  return useMutation({
    mutationFn: (changes: Partial<CourseSettings>) => api.updateSettings(courseId, changes),
    onMutate: async (changes) => {
      await client.cancelQueries({ queryKey: key });
      const previous = client.getQueryData<GetTeacherCourseResponse>(key);
      if (previous) client.setQueryData(key, { ...previous, settings: { ...previous.settings, ...changes } });
      return { previous };
    },
    onError: (_error, _changes, context) => {
      if (context?.previous) client.setQueryData(key, context.previous);
    },
    onSettled: () => client.invalidateQueries({ queryKey: key }),
  });
}
