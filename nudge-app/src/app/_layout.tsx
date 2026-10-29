import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { HeroUINativeProvider } from "heroui-native";
import { type ReactNode, useEffect, useState } from "react";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { KeyboardProvider } from "react-native-keyboard-controller";

import { AuthProvider, useAuth } from "@/lib/auth";

import "../global.css";

SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
      }),
  );

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <KeyboardProvider>
          <HeroUINativeProvider config={{ toast: { defaultProps: { placement: "top" } } }}>
            <AuthProvider>
              <Routes />
            </AuthProvider>
          </HeroUINativeProvider>
        </KeyboardProvider>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}

/** Each role only sees its own screens; signing in or out swaps them. */
function Routes(): ReactNode {
  const { status, user } = useAuth();

  useEffect(() => {
    if (status !== "loading") SplashScreen.hideAsync().catch(() => {});
  }, [status]);

  if (status === "loading") return null;
  const signedIn = status === "signedIn";

  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: "transparent" } }}>
      <Stack.Screen name="index" />
      <Stack.Protected guard={!signedIn}>
        <Stack.Screen name="(auth)" options={{ animation: "fade" }} />
      </Stack.Protected>
      <Stack.Protected guard={signedIn && user?.role === "student"}>
        <Stack.Screen name="(student)" options={{ animation: "fade" }} />
      </Stack.Protected>
      <Stack.Protected guard={signedIn && user?.role === "teacher"}>
        <Stack.Screen name="(teacher)" options={{ animation: "fade" }} />
      </Stack.Protected>
      <Stack.Protected guard={signedIn}>
        <Stack.Screen name="chat/[id]" />
        <Stack.Screen name="camera" options={{ presentation: "fullScreenModal", animation: "slide_from_bottom" }} />
      </Stack.Protected>
    </Stack>
  );
}
