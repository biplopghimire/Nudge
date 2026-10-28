import { Redirect } from "expo-router";

import { useAuth } from "@/lib/auth";

/** Sends each person to their starting screen. */
export default function Index() {
  const { status, user } = useAuth();
  if (status !== "signedIn" || !user) return <Redirect href="/welcome" />;
  return <Redirect href={user.role === "teacher" ? "/courses" : "/home"} />;
}
