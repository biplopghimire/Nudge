import { BottomSheet } from "heroui-native";
import { Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Icon, type IconName } from "@/components/ui/icon";
import { Tappable } from "@/components/ui/tappable";

export type AttachChoice = "camera" | "library" | "files";

const OPTIONS: { choice: AttachChoice; icon: IconName; title: string; detail: string }[] = [
  { choice: "camera", icon: "camera", title: "Camera", detail: "Snap your work" },
  { choice: "library", icon: "photo", title: "Photo library", detail: "Pick an existing photo" },
  { choice: "files", icon: "file", title: "Files", detail: "PDF or document" },
];

/** The + menu: camera, photo library or a file. */
export function AttachSheet({
  isOpen,
  onOpenChange,
  onChoose,
}: {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onChoose: (choice: AttachChoice) => void;
}) {
  const insets = useSafeAreaInsets();
  return (
    <BottomSheet isOpen={isOpen} onOpenChange={onOpenChange}>
      <BottomSheet.Portal>
        <BottomSheet.Overlay />
        <BottomSheet.Content detached bottomInset={insets.bottom + 10} className="mx-3" backgroundClassName="rounded-[30px]">
          <View className="gap-1 pb-2">
            {OPTIONS.map((option) => (
              <Tappable
                key={option.choice}
                onPress={() => {
                  onOpenChange(false);
                  onChoose(option.choice);
                }}
                className="flex-row items-center gap-4 rounded-2xl px-2 py-3"
                accessibilityRole="button"
                accessibilityLabel={option.title}
                scale={0.98}
              >
                <View className="h-11 w-11 items-center justify-center rounded-2xl bg-mint-soft">
                  <Icon name={option.icon} size={19} color="mint-foreground" />
                </View>
                <View>
                  <Text className="text-[17px] font-semibold text-foreground">{option.title}</Text>
                  <Text className="text-[13px] text-muted">{option.detail}</Text>
                </View>
              </Tappable>
            ))}
          </View>
        </BottomSheet.Content>
      </BottomSheet.Portal>
    </BottomSheet>
  );
}
