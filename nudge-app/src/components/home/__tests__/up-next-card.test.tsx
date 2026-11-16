import type { Assignment } from "@api";
import { fireEvent, render, screen } from "@testing-library/react-native";

import { UpNextCard } from "../up-next-card";

// The card only needs somewhere to draw: stub the animation wrapper, the axolotl
// artwork and the design-system button so the test runs without native modules.
jest.mock("react-native-reanimated", () => {
  // jest.mock factories run before imports, so they have to require what they use.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { View } = require("react-native");
  return { __esModule: true, default: { View } };
});
jest.mock("@/lib/motion", () => ({ enterRow: () => undefined }));
jest.mock("@/components/brand/nudge-avatar", () => ({ NudgeMark: () => null }));
jest.mock("heroui-native", () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { Pressable, Text } = require("react-native");
  const Button = ({ children, onPress, accessibilityLabel }: any) => (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={accessibilityLabel}>
      {children}
    </Pressable>
  );
  Button.Label = Text;
  return { Button };
});

// Wednesday, November 5, 2025, 10:00 local time.
const NOW = new Date(2025, 10, 5, 10, 0);

const assignment: Assignment = {
  id: "ps4",
  courseId: "c272",
  courseCode: "67-272",
  title: "Problem Set 4",
  shortTitle: "PS 4",
  dueAt: new Date(2025, 10, 6, 23, 59).toISOString(),
};

beforeEach(() => {
  jest.useFakeTimers();
  jest.setSystemTime(NOW);
});

afterEach(() => {
  jest.useRealTimers();
});

describe("UpNextCard", () => {
  it("shows the assignment's title, course and due date", async () => {
    await render(<UpNextCard assignment={assignment} onStart={jest.fn()} />);
    expect(screen.getByText("Up next")).toBeTruthy();
    expect(screen.getByText("Problem Set 4")).toBeTruthy();
    expect(screen.getByText("67-272 · Due tomorrow")).toBeTruthy();
  });

  it("hands the assignment to onStart when Start is pressed", async () => {
    const onStart = jest.fn();
    await render(<UpNextCard assignment={assignment} onStart={onStart} />);
    await fireEvent.press(screen.getByLabelText("Start Problem Set 4"));
    expect(onStart).toHaveBeenCalledTimes(1);
    expect(onStart).toHaveBeenCalledWith(assignment);
  });

  it("says you're caught up, with no Start button, when nothing is due", async () => {
    await render(<UpNextCard assignment={null} onStart={jest.fn()} />);
    expect(screen.getByText("You're all caught up")).toBeTruthy();
    expect(screen.getByText("Nothing due right now.")).toBeTruthy();
    expect(screen.queryByText("Start")).toBeNull();
  });
});
