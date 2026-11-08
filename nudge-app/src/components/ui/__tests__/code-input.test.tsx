import { fireEvent, render, screen } from "@testing-library/react-native";

import { CodeInput } from "../code-input";

// Reanimated needs the native UI thread, and its own Jest mock doesn't load in
// this version. The boxes only need its animation helpers to be callable.
jest.mock("react-native-reanimated", () => {
  // jest.mock factories run before imports, so they have to require what they use.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { View } = require("react-native");
  const now = (value: unknown) => value;
  return {
    __esModule: true,
    default: { View },
    useSharedValue: (value: unknown) => ({ value, set: jest.fn() }),
    useAnimatedStyle: () => ({}),
    withRepeat: now,
    withSequence: now,
    withSpring: now,
    withTiming: now,
  };
});
jest.mock("@/lib/motion", () => ({ springs: {} }));

async function setup(value = "") {
  const onChange = jest.fn();
  const onComplete = jest.fn();
  await render(<CodeInput value={value} onChange={onChange} onComplete={onComplete} />);
  const input = screen.getByLabelText(`Course code, ${value.length} of 6 characters entered`);
  return { input, onChange, onComplete };
}

describe("CodeInput", () => {
  it("drops anything that isn't a letter or digit", async () => {
    const { input, onChange, onComplete } = await setup();
    await fireEvent.changeText(input, "ab-1 2");
    expect(onChange).toHaveBeenCalledWith("ab12");
    expect(onComplete).not.toHaveBeenCalled();
  });

  it("stops at six characters and reports the finished code", async () => {
    const { input, onChange, onComplete } = await setup();
    await fireEvent.changeText(input, "MATH-101X");
    expect(onChange).toHaveBeenCalledWith("MATH10");
    expect(onComplete).toHaveBeenCalledWith("MATH10");
  });

  it("draws each character in its own box", async () => {
    await setup("AB3");
    expect(screen.getByText("A")).toBeTruthy();
    expect(screen.getByText("B")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
  });
});
