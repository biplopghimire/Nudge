/** Nudge's reply text: light markdown (bold, lists) styled to match the app. */
import { Fragment, useMemo } from "react";
import { useColorScheme, View } from "react-native";
import { useMarkdown } from "react-native-marked";
import { useCSSVariable } from "uniwind";

import { readableMath } from "@/lib/format";

const color = (value: unknown, fallback: string) => (typeof value === "string" ? value : fallback);

export function ReplyText({ text }: { text: string }) {
  const scheme = useColorScheme();
  const foreground = color(useCSSVariable("--foreground"), "#0f1b1d");
  const muted = color(useCSSVariable("--muted"), "#6b7a7c");
  const accent = color(useCSSVariable("--accent"), "#1f5c60");
  const surface = color(useCSSVariable("--surface-secondary"), "#f3f6f5");

  const styles = useMemo(
    () => ({
      text: { fontSize: 16, lineHeight: 23, color: foreground },
      paragraph: { marginBottom: 8, paddingVertical: 0 },
      strong: { fontWeight: "700" as const, color: foreground },
      em: { fontStyle: "italic" as const },
      li: { fontSize: 16, lineHeight: 23, color: foreground },
      list: { marginBottom: 6 },
      link: { color: accent, textDecorationLine: "underline" as const },
      codespan: { fontFamily: "Menlo", fontSize: 14, backgroundColor: surface, color: foreground },
      code: { backgroundColor: surface, borderRadius: 12, padding: 12, marginBottom: 8 },
      codeText: { fontFamily: "Menlo", fontSize: 13, color: foreground },
      blockquote: { borderLeftColor: muted, borderLeftWidth: 3, paddingLeft: 10, marginBottom: 8 },
      h1: { fontSize: 20, fontWeight: "700" as const, color: foreground, marginBottom: 6 },
      h2: { fontSize: 18, fontWeight: "700" as const, color: foreground, marginBottom: 6 },
      h3: { fontSize: 17, fontWeight: "600" as const, color: foreground, marginBottom: 4 },
    }),
    [foreground, muted, accent, surface],
  );

  const elements = useMarkdown(readableMath(text).trim(), {
    colorScheme: scheme ?? undefined,
    styles,
    theme: { colors: { text: foreground, link: accent, border: muted, code: surface } },
  });

  return (
    <View style={{ marginBottom: -8 }}>
      {elements.map((element, index) => (
        <Fragment key={index}>{element}</Fragment>
      ))}
    </View>
  );
}
