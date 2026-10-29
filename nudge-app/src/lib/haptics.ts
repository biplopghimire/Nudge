import * as Haptics from "expo-haptics";
import { Platform } from "react-native";

// One place that decides how each kind of moment feels.
const run = (fn: () => Promise<void>) => {
  if (Platform.OS !== "web") fn().catch(() => {});
};

export const haptics = {
  /** Taps on rows, chips and tabs. */
  tap: () => run(() => Haptics.selectionAsync()),
  /** Primary actions: send, join, create. */
  press: () => run(() => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light)),
  /** Something landed: reply arrived, file ready. */
  soft: () => run(() => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Soft)),
  success: () => run(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success)),
  error: () => run(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error)),
};
