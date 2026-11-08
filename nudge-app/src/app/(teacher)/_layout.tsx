import { Stack } from "expo-router";

export default function TeacherLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="course/new" options={{ presentation: "modal" }} />
      <Stack.Screen name="course/[id]/share" options={{ presentation: "modal" }} />
    </Stack>
  );
}
