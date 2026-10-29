import { Tabs } from "expo-router";

import type { IconName } from "@/components/ui/icon";
import { FloatingTabBar } from "@/components/ui/tab-bar";

const icon = (name: IconName) => (() => name) as never;

export default function TeacherTabs() {
  return (
    <Tabs screenOptions={{ headerShown: false, animation: "fade" }} tabBar={(props) => <FloatingTabBar {...props} />}>
      <Tabs.Screen name="courses" options={{ title: "Courses", tabBarIcon: icon("courses") }} />
      <Tabs.Screen name="account" options={{ title: "Profile", tabBarIcon: icon("profile") }} />
    </Tabs>
  );
}
