import type { Role } from "@api";
import { router } from "expo-router";
import { Button, Input, Label, Spinner, TextField, useToast } from "heroui-native";
import { useState } from "react";
import { Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import Animated, { FadeInDown, LinearTransition } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { NudgeMark } from "@/components/brand/nudge-avatar";
import { Icon } from "@/components/ui/icon";
import { Segmented } from "@/components/ui/segmented";
import { Tappable } from "@/components/ui/tappable";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { haptics } from "@/lib/haptics";
import { layoutSpring, springs } from "@/lib/motion";

type Mode = "signIn" | "signUp";

export default function Welcome() {
  const insets = useSafeAreaInsets();
  const { signIn, signUp } = useAuth();
  const { toast } = useToast();
  const [mode, setMode] = useState<Mode>("signIn");
  const [role, setRole] = useState<Role>("student");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const ready = email.includes("@") && password.length >= (mode === "signUp" ? 8 : 1) && (mode === "signIn" || name.trim());

  async function submit() {
    if (!ready || busy) return;
    setBusy(true);
    haptics.press();
    try {
      const user = mode === "signIn" ? await signIn(email, password) : await signUp(name, email, password, role);
      haptics.success();
      router.replace(user.role === "teacher" ? "/courses" : "/home");
    } catch (error) {
      haptics.error();
      toast.show({
        variant: "danger",
        label: mode === "signIn" ? "Couldn't sign in" : "Couldn't create your account",
        description: error instanceof ApiError ? error.message : "Something went wrong. Try again.",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <KeyboardAwareScrollView
      className="flex-1 bg-background"
      contentContainerStyle={{ flexGrow: 1, paddingTop: insets.top + 48, paddingBottom: insets.bottom + 24 }}
      contentContainerClassName="px-6"
      bottomOffset={24}
      keyboardShouldPersistTaps="handled"
    >
      <Animated.View entering={FadeInDown.springify().damping(springs.smooth.damping)} className="items-center">
        <NudgeMark size={88} />
        <Text className="mt-6 text-[34px] font-bold tracking-tight text-foreground">Nudge</Text>
        <Text className="mt-2 text-center text-[16px] leading-6 text-muted">
          Help from your own course materials,{"\n"}not the whole internet.
        </Text>
      </Animated.View>

      <Animated.View entering={FadeInDown.delay(120).springify().damping(springs.smooth.damping)} className="mt-10">
        <Segmented
          value={mode}
          onChange={setMode}
          options={[
            { value: "signIn", label: "Sign in" },
            { value: "signUp", label: "Create account" },
          ]}
        />
      </Animated.View>

      <Animated.View layout={layoutSpring} className="mt-6 gap-4">
        {mode === "signUp" ? (
          <Animated.View entering={FadeInDown.springify().damping(springs.smooth.damping)} layout={LinearTransition} className="gap-4">
            <View className="flex-row gap-3">
              <RoleCard role="student" selected={role === "student"} onPress={() => setRole("student")} />
              <RoleCard role="teacher" selected={role === "teacher"} onPress={() => setRole("teacher")} />
            </View>
            <TextField>
              <Label>Name</Label>
              <Input value={name} onChangeText={setName} placeholder="Sam Lee" autoComplete="name" textContentType="name" />
            </TextField>
          </Animated.View>
        ) : null}

        <Animated.View layout={layoutSpring}>
          <TextField>
            <Label>Email</Label>
            <Input
              value={email}
              onChangeText={setEmail}
              placeholder="you@andrew.cmu.edu"
              autoCapitalize="none"
              autoComplete="email"
              keyboardType="email-address"
              textContentType="emailAddress"
            />
          </TextField>
        </Animated.View>

        <Animated.View layout={layoutSpring}>
          <TextField>
            <Label>Password</Label>
            <Input
              value={password}
              onChangeText={setPassword}
              placeholder={mode === "signUp" ? "At least 8 characters" : "Your password"}
              secureTextEntry
              autoComplete={mode === "signUp" ? "new-password" : "current-password"}
              textContentType={mode === "signUp" ? "newPassword" : "password"}
              returnKeyType="go"
              onSubmitEditing={submit}
            />
          </TextField>
        </Animated.View>

        <Animated.View layout={layoutSpring} className="mt-2">
          <Button size="lg" className="rounded-full" onPress={submit} isDisabled={!ready || busy}>
            {busy ? <Spinner color="accent-foreground" /> : <Button.Label>{mode === "signIn" ? "Sign in" : "Create account"}</Button.Label>}
          </Button>
        </Animated.View>
      </Animated.View>
    </KeyboardAwareScrollView>
  );
}

function RoleCard({ role, selected, onPress }: { role: Role; selected: boolean; onPress: () => void }) {
  return (
    <Tappable
      onPress={onPress}
      accessibilityRole="radio"
      accessibilityState={{ checked: selected }}
      className={`flex-1 rounded-2xl border-2 p-4 ${selected ? "border-accent bg-mint-soft" : "border-transparent bg-surface-secondary"}`}
      style={{ borderCurve: "continuous" }}
    >
      <Icon name={role === "student" ? "book" : "courses"} size={20} color={selected ? "accent" : "muted"} />
      <Text className="mt-3 text-[16px] font-semibold text-foreground">{role === "student" ? "Student" : "Teacher"}</Text>
      <Text className="mt-0.5 text-[12px] text-muted">{role === "student" ? "Ask about your courses" : "Set up your course"}</Text>
    </Tappable>
  );
}
