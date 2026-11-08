import { dayGroup, dueLabel, fileSize, initials, readableMath, relativeTime } from "../format";

// Wednesday, November 5, 2025, 10:00 local time.
const NOW = new Date(2025, 10, 5, 10, 0);
const at = (days: number, hours = 10, minutes = 0) =>
  new Date(2025, 10, 5 + days, hours, minutes).toISOString();

beforeEach(() => {
  jest.useFakeTimers();
  jest.setSystemTime(NOW);
});

afterEach(() => {
  jest.useRealTimers();
});

describe("dueLabel", () => {
  it("says today and tomorrow", () => {
    expect(dueLabel(at(0, 23, 59))).toBe("Due today");
    expect(dueLabel(at(1, 0, 1))).toBe("Due tomorrow");
  });

  it("names the weekday within the next week", () => {
    expect(dueLabel(at(2))).toBe("Due Friday");
    expect(dueLabel(at(6))).toBe("Due Tuesday");
  });

  it("gives the date a week or more out, and for past due dates", () => {
    expect(dueLabel(at(7))).toBe("Due Nov 12");
    expect(dueLabel(at(-3))).toBe("Due Nov 2");
  });
});

describe("relativeTime", () => {
  it("counts minutes, then hours earlier today", () => {
    expect(relativeTime(new Date(NOW.getTime() - 20_000).toISOString())).toBe("now");
    expect(relativeTime(at(0, 9, 59))).toBe("1m ago");
    expect(relativeTime(at(0, 9, 15))).toBe("45m ago");
    expect(relativeTime(at(0, 7))).toBe("3h ago");
  });

  it("uses the weekday for the past week and the date before that", () => {
    expect(relativeTime(at(-1, 23))).toBe("Tue");
    expect(relativeTime(at(-6))).toBe("Thu");
    expect(relativeTime(at(-7))).toBe("Oct 29");
  });
});

describe("dayGroup", () => {
  it("groups chats by how long ago they were", () => {
    expect(dayGroup(at(0, 0, 5))).toBe("Today");
    expect(dayGroup(at(-1))).toBe("This week");
    expect(dayGroup(at(-6))).toBe("This week");
    expect(dayGroup(at(-7))).toBe("Earlier");
  });
});

describe("fileSize", () => {
  it("picks bytes, KB or MB", () => {
    expect(fileSize(512)).toBe("512 B");
    expect(fileSize(1024)).toBe("1 KB");
    expect(fileSize(250_000)).toBe("244 KB");
    expect(fileSize(5 * 1024 * 1024 + 300_000)).toBe("5.3 MB");
  });
});

describe("initials", () => {
  it("takes the first letter, capitalized", () => {
    expect(initials("  ada lovelace")).toBe("A");
  });

  it("falls back to ? for an empty name", () => {
    expect(initials("   ")).toBe("?");
  });
});

describe("readableMath", () => {
  it("turns common LaTeX into Unicode", () => {
    expect(readableMath("Solve $x^2 + \\frac{a}{b} \\le \\pi$ now")).toBe(
      "Solve x² + (a)/(b) ≤ π now"
    );
    expect(readableMath("$$\\int_0^1 \\sqrt{x} \\, dx$$")).toBe("∫_0¹ √(x)   dx");
  });

  it("keeps exponents it has no superscript for", () => {
    expect(readableMath("$e^{9}$")).toBe("e^9");
  });

  it("leaves text without math alone", () => {
    expect(readableMath("Costs 5 dollars")).toBe("Costs 5 dollars");
  });
});
