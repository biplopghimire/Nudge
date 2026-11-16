/**
 * The course pill in a chat's header. On a new chat it opens a "Switch class"
 * menu; once the chat has a message it is greyed out and can't be changed.
 */
import type { StudentCourseSummary } from "@api";
import { router } from "expo-router";
import { Menu, Separator } from "heroui-native";
import { Text, View } from "react-native";

import { Icon } from "@/components/ui/icon";
import { haptics } from "@/lib/haptics";
import { useStudentCourses } from "@/lib/queries";

type Props = {
  courseId?: string;
  courseCode: string;
  /** True once the chat has started: the pill is greyed out and does nothing. */
  locked: boolean;
  onSwitch: (course: StudentCourseSummary) => void;
};

export function ClassSwitcher({ locked, ...rest }: Props) {
  if (locked) {
    return (
      <View
        className="flex-row items-center gap-1.5 rounded-full bg-surface-secondary px-3 py-1.5 opacity-60"
        accessibilityLabel={`Class ${rest.courseCode}. Can't be changed after the chat has started.`}
        accessibilityState={{ disabled: true }}
      >
        <Text className="text-[13px] font-semibold text-muted">{rest.courseCode}</Text>
        <Icon name="chevronDown" size={10} color="muted" />
      </View>
    );
  }
  return <SwitchMenu {...rest} />;
}

// Its own component so the course list is only fetched when the menu can open.
function SwitchMenu({ courseId, courseCode, onSwitch }: Omit<Props, "locked">) {
  const { data } = useStudentCourses();
  const courses = data?.courses ?? [];

  return (
    <Menu>
      <Menu.Trigger
        className="flex-row items-center gap-1.5 rounded-full border border-accent bg-mint-soft px-3 py-1.5"
        accessibilityRole="button"
        accessibilityLabel={`Class ${courseCode}. Switch class`}
        onPress={() => haptics.tap()}
      >
        <Text className="text-[13px] font-semibold text-mint-foreground">{courseCode}</Text>
        <Icon name="chevronDown" size={10} color="mint-foreground" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Overlay />
        <Menu.Content presentation="popover" placement="bottom" align="end" width={260}>
          <Menu.Label>Switch class</Menu.Label>
          <Menu.Group
            selectionMode="single"
            disallowEmptySelection
            selectedKeys={courseId ? [courseId] : []}
            onSelectionChange={(keys) => {
              const course = courses.find((c) => keys.has(c.id));
              if (course && course.id !== courseId) {
                haptics.tap();
                onSwitch(course);
              }
            }}
          >
            {courses.map((course) => (
              <Menu.Item key={course.id} id={course.id}>
                <View className="flex-1">
                  <Menu.ItemTitle>{course.code}</Menu.ItemTitle>
                  {course.currentAssignmentTitle ? (
                    <Menu.ItemDescription>{course.currentAssignmentTitle}</Menu.ItemDescription>
                  ) : null}
                </View>
                <Menu.ItemIndicator />
              </Menu.Item>
            ))}
          </Menu.Group>
          <Separator className="my-1" />
          <Menu.Item onPress={() => router.push("/join")}>
            <Icon name="plus" size={14} color="accent" />
            <Menu.ItemTitle className="text-accent">Join a course</Menu.ItemTitle>
          </Menu.Item>
        </Menu.Content>
      </Menu.Portal>
    </Menu>
  );
}
