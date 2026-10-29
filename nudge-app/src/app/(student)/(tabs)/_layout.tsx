import { Tabs } from "expo-router";

import { FloatingTabBar } from "@/components/ui/tab-bar";
import type { IconName } from "@/components/ui/icon";

// The tab bar reads each tab's icon name from tabBarIcon.
const icon = (name: IconName) => (() => name) as never;

export default function StudentTabs() {
  return (
    <Tabs screenOptions={{ headerShown: false, animation: "fade" }} tabBar={(props) => <FloatingTabBar {...props} />}>
      <Tabs.Screen name="home" options={{ title: "Home", tabBarIcon: icon("home") }} />
      <Tabs.Screen name="chats" options={{ title: "Chats", tabBarIcon: icon("chats") }} />
      <Tabs.Screen name="profile" options={{ title: "Profile", tabBarIcon: icon("profile") }} />
    </Tabs>
  );
}
