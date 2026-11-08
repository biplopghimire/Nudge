/**
 * SF Symbols on iOS (crisp, weight-matched to the system font), Ionicons on
 * Android. Screens use our names, so swapping icon sets is one table.
 */
import Ionicons from "@expo/vector-icons/Ionicons";
import { SymbolView, type SFSymbol } from "expo-symbols";
import { Platform } from "react-native";
import { useCSSVariable } from "uniwind";

const ICONS = {
  home: ["house.fill", "home"],
  chats: ["bubble.left.and.bubble.right.fill", "chatbubbles"],
  profile: ["person.fill", "person"],
  courses: ["books.vertical.fill", "library"],
  plus: ["plus", "add"],
  chevronRight: ["chevron.right", "chevron-forward"],
  chevronLeft: ["chevron.left", "chevron-back"],
  chevronDown: ["chevron.down", "chevron-down"],
  menu: ["line.3.horizontal", "menu"],
  send: ["arrow.up", "arrow-up"],
  camera: ["camera.fill", "camera"],
  photo: ["photo.on.rectangle", "images"],
  file: ["doc.fill", "document"],
  doc: ["doc.text.fill", "document-text"],
  flag: ["flag", "flag-outline"],
  retry: ["arrow.clockwise", "refresh"],
  copy: ["doc.on.doc", "copy"],
  share: ["square.and.arrow.up", "share-outline"],
  check: ["checkmark", "checkmark"],
  checkCircle: ["checkmark.circle.fill", "checkmark-circle"],
  clipboard: ["doc.on.clipboard", "clipboard"],
  close: ["xmark", "close"],
  search: ["magnifyingglass", "search"],
  compose: ["square.and.pencil", "create-outline"],
  sliders: ["slider.horizontal.3", "options"],
  signOut: ["rectangle.portrait.and.arrow.right", "log-out-outline"],
  book: ["book.closed.fill", "book"],
  sparkles: ["sparkles", "sparkles"],
  warning: ["exclamationmark.triangle.fill", "warning"],
  lock: ["lock.fill", "lock-closed"],
  flash: ["bolt.fill", "flash"],
} as const satisfies Record<string, readonly [SFSymbol, keyof typeof Ionicons.glyphMap]>;

export type IconName = keyof typeof ICONS;

type Props = {
  name: IconName;
  size?: number;
  /** A theme token like "accent" or "muted", or any color string. */
  color?: string;
  weight?: "regular" | "medium" | "semibold" | "bold";
};

export function Icon({ name, size = 20, color = "foreground", weight = "semibold" }: Props) {
  const themed = useCSSVariable(`--${color}`);
  const tint = (typeof themed === "string" ? themed : undefined) ?? color;
  const [sf, ion] = ICONS[name];
  if (Platform.OS === "ios") {
    return <SymbolView name={sf} size={size} tintColor={tint} weight={weight} resizeMode="scaleAspectFit" />;
  }
  return <Ionicons name={ion} size={size} color={tint} />;
}
