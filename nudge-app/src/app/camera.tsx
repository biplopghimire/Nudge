import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import { router, useLocalSearchParams } from "expo-router";
import { Button } from "heroui-native";
import { useRef, useState } from "react";
import { Text, View } from "react-native";
import Animated, { FadeIn, useAnimatedStyle, useSharedValue, withSequence, withSpring, withTiming } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Icon } from "@/components/ui/icon";
import { Tappable } from "@/components/ui/tappable";
import { haptics } from "@/lib/haptics";
import { springs } from "@/lib/motion";
import { pendingPhoto } from "@/lib/pending-photo";

export default function Camera() {
  const { threadId, title } = useLocalSearchParams<{ threadId: string; title?: string }>();
  const insets = useSafeAreaInsets();
  const [permission, requestPermission] = useCameraPermissions();
  const [ready, setReady] = useState(false);
  const camera = useRef<CameraView>(null);
  const flash = useSharedValue(0);
  const shutter = useSharedValue(1);

  const flashStyle = useAnimatedStyle(() => ({ opacity: flash.value }));
  const shutterStyle = useAnimatedStyle(() => ({ transform: [{ scale: shutter.value }] }));

  function done(uri: string, width: number, height: number) {
    pendingPhoto.set(threadId, { uri, width, height });
    router.back();
  }

  async function capture() {
    if (!camera.current || !ready) return;
    haptics.press();
    shutter.set(withSequence(withSpring(0.86, springs.snappy), withSpring(1, springs.bouncy)));
    flash.set(withSequence(withTiming(0.85, { duration: 60 }), withTiming(0, { duration: 260 })));
    const photo = await camera.current.takePictureAsync({ quality: 0.8 });
    if (photo) done(photo.uri, photo.width, photo.height);
  }

  async function pickFromLibrary() {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8 });
    const asset = result.canceled ? null : result.assets[0];
    if (asset) done(asset.uri, asset.width, asset.height);
  }

  const granted = permission?.granted;

  return (
    <View className="flex-1 bg-black" style={{ paddingTop: insets.top, paddingBottom: insets.bottom + 12 }}>
      <View className="flex-row items-center justify-between px-5 py-2">
        <Tappable onPress={() => router.back()} className="h-10 w-10 items-center justify-center rounded-full bg-white/15" accessibilityLabel="Close camera">
          <Icon name="close" size={16} color="#ffffff" />
        </Tappable>
        {title ? (
          <View className="rounded-full bg-white/15 px-3 py-1.5">
            <Text className="text-[13px] font-semibold text-white">{title}</Text>
          </View>
        ) : null}
        <View className="w-10" />
      </View>

      <View className="mx-4 my-4 flex-1 overflow-hidden rounded-[28px] bg-[#111]" style={{ borderCurve: "continuous" }}>
        {granted ? (
          <CameraView ref={camera} style={{ flex: 1 }} facing="back" onCameraReady={() => setReady(true)} />
        ) : (
          <View className="flex-1 items-center justify-center px-8">
            <Icon name="camera" size={34} color="#9fdcc8" />
            <Text className="mt-4 text-center text-[17px] font-semibold text-white">
              {permission?.canAskAgain === false ? "Camera access is off" : "Snap your work"}
            </Text>
            <Text className="mt-2 text-center text-[14px] leading-5 text-white/60">
              {permission?.canAskAgain === false
                ? "Turn on camera access for Nudge in Settings, or pick a photo instead."
                : "Nudge needs the camera to see what you're working on."}
            </Text>
            {permission?.canAskAgain !== false ? (
              <Button className="mt-6 rounded-full" onPress={requestPermission}>
                <Button.Label>Allow camera</Button.Label>
              </Button>
            ) : null}
          </View>
        )}

        {granted ? (
          <View pointerEvents="none" className="absolute inset-6">
            {(["top-0 left-0 border-l-4 border-t-4 rounded-tl-2xl", "top-0 right-0 border-r-4 border-t-4 rounded-tr-2xl", "bottom-0 left-0 border-b-4 border-l-4 rounded-bl-2xl", "bottom-0 right-0 border-b-4 border-r-4 rounded-br-2xl"] as const).map((corner) => (
              <View key={corner} className={`absolute h-10 w-10 border-white ${corner}`} />
            ))}
          </View>
        ) : null}
        {granted && ready ? (
          <Animated.View entering={FadeIn.delay(400)} pointerEvents="none" className="absolute bottom-6 self-center rounded-full bg-black/55 px-4 py-2">
            <Text className="text-[13px] font-medium text-white">Fit the whole problem in the frame</Text>
          </Animated.View>
        ) : null}
        <Animated.View pointerEvents="none" className="absolute inset-0 bg-white" style={flashStyle} />
      </View>

      <View className="flex-row items-center justify-between px-10">
        <Tappable onPress={pickFromLibrary} className="h-12 w-12 items-center justify-center rounded-2xl bg-white/15" accessibilityLabel="Choose from photo library">
          <Icon name="photo" size={20} color="#ffffff" />
        </Tappable>
        <Animated.View style={shutterStyle}>
          <Tappable
            onPress={capture}
            disabled={!granted || !ready}
            haptic="none"
            className="h-[78px] w-[78px] items-center justify-center rounded-full border-4 border-white"
            accessibilityLabel="Take photo"
          >
            <View className="h-[62px] w-[62px] rounded-full bg-mint" />
          </Tappable>
        </Animated.View>
        <View className="h-12 w-12" />
      </View>
    </View>
  );
}
