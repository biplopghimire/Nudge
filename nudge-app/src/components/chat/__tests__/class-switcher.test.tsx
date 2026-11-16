import type { StudentCourseSummary } from "@api";
import { fireEvent, render, screen } from "@testing-library/react-native";
import { router } from "expo-router";

import { ClassSwitcher } from "../class-switcher";

const course = (id: string, code: string, assignment: string | null): StudentCourseSummary => ({
  id,
  code,
  section: "Sec 1",
  teacherName: "Dr. Kim",
  nextDue: null,
  currentAssignmentTitle: assignment,
});
const COURSES = [course("c272", "67-272", "Problem Set 4"), course("c213", "15-213", "Lab 3")];

const mockUseStudentCourses = jest.fn();
jest.mock("@/lib/queries", () => ({ useStudentCourses: () => mockUseStudentCourses() }));
jest.mock("@/lib/haptics", () => ({ haptics: { tap: jest.fn() } }));
jest.mock("@/components/ui/icon", () => ({ Icon: () => null }));
jest.mock("expo-router", () => ({ router: { push: jest.fn() } }));

// A plain stand-in for the design-system menu: always open, and pressing an item
// in a group reports that item's id the way the real single-select group does.
jest.mock("heroui-native", () => {
  /* eslint-disable @typescript-eslint/no-require-imports */
  const { createContext, useContext } = require("react");
  const { Pressable, Text, View } = require("react-native");
  /* eslint-enable @typescript-eslint/no-require-imports */
  const GroupContext = createContext(null);
  function Pass({ children }: any) {
    return <>{children}</>;
  }
  function Trigger({ children, ...props }: any) {
    return <Pressable {...props}>{children}</Pressable>;
  }
  function Overlay() {
    return null;
  }
  function Group({ children, onSelectionChange }: any) {
    return <GroupContext.Provider value={onSelectionChange}>{children}</GroupContext.Provider>;
  }
  function Item({ id, onPress, children }: any) {
    const select = useContext(GroupContext);
    return (
      <Pressable accessibilityRole="menuitem" onPress={(event: unknown) => (id && select ? select(new Set([id])) : onPress?.(event))}>
        {children}
      </Pressable>
    );
  }
  const Menu = Object.assign(Pass, {
    Trigger,
    Portal: Pass,
    Overlay,
    Content: Pass,
    Label: Text,
    Group,
    Item,
    ItemTitle: Text,
    ItemDescription: Text,
    ItemIndicator: Overlay,
  });
  return { Menu, Separator: View };
});

beforeEach(() => {
  jest.clearAllMocks();
  mockUseStudentCourses.mockReturnValue({ data: { upNext: null, courses: COURSES } });
});

describe("ClassSwitcher", () => {
  it("lists the student's courses with their current assignment on a new chat", async () => {
    await render(<ClassSwitcher courseId="c272" courseCode="67-272" locked={false} onSwitch={jest.fn()} />);
    expect(screen.getByText("Switch class")).toBeTruthy();
    expect(screen.getByText("15-213")).toBeTruthy();
    expect(screen.getByText("Problem Set 4")).toBeTruthy();
    expect(screen.getByText("Lab 3")).toBeTruthy();
  });

  it("switches to the course that is picked", async () => {
    const onSwitch = jest.fn();
    await render(<ClassSwitcher courseId="c272" courseCode="67-272" locked={false} onSwitch={onSwitch} />);
    await fireEvent.press(screen.getByText("15-213"));
    expect(onSwitch).toHaveBeenCalledWith(COURSES[1]);
  });

  it("does nothing when the current course is picked again", async () => {
    const onSwitch = jest.fn();
    await render(<ClassSwitcher courseId="c272" courseCode="67-272" locked={false} onSwitch={onSwitch} />);
    await fireEvent.press(screen.getByText("Problem Set 4"));
    expect(onSwitch).not.toHaveBeenCalled();
  });

  it("opens the Join screen from the menu", async () => {
    await render(<ClassSwitcher courseId="c272" courseCode="67-272" locked={false} onSwitch={jest.fn()} />);
    await fireEvent.press(screen.getByText("Join a course"));
    expect(router.push).toHaveBeenCalledWith("/join");
  });

  it("is greyed out with no menu once the chat has started", async () => {
    await render(<ClassSwitcher courseId="c272" courseCode="67-272" locked onSwitch={jest.fn()} />);
    expect(screen.getByText("67-272")).toBeTruthy();
    expect(screen.queryByText("Switch class")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
    // A locked pill must not even ask for the course list.
    expect(mockUseStudentCourses).not.toHaveBeenCalled();
  });
});
