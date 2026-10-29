/** Small text helpers shared by screens. */

export function greetingDate(date = new Date()) {
  return date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
}

export function dueLabel(iso: string) {
  const due = new Date(iso);
  const days = Math.round((startOfDay(due) - startOfDay(new Date())) / 86_400_000);
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  if (days > 1 && days < 7) return `Due ${due.toLocaleDateString("en-US", { weekday: "long" })}`;
  return `Due ${due.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
}

export function relativeTime(iso: string) {
  const then = new Date(iso);
  const minutes = Math.round((Date.now() - then.getTime()) / 60_000);
  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24 && startOfDay(then) === startOfDay(new Date())) return `${hours}h ago`;
  const days = Math.round((startOfDay(new Date()) - startOfDay(then)) / 86_400_000);
  if (days < 7) return then.toLocaleDateString("en-US", { weekday: "short" });
  return then.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** "Today", "This week" or "Earlier", for grouping chats. */
export function dayGroup(iso: string) {
  const days = Math.round((startOfDay(new Date()) - startOfDay(new Date(iso))) / 86_400_000);
  if (days <= 0) return "Today";
  if (days < 7) return "This week";
  return "Earlier";
}

export function fileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function initials(name: string) {
  return name.trim().charAt(0).toUpperCase() || "?";
}

/**
 * Replies use Unicode math, but older messages (or a model that slips) may
 * still contain LaTeX. Turn the common pieces into readable text.
 */
export function readableMath(text: string) {
  const sup: Record<string, string> = { "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", n: "ⁿ", x: "ˣ" };
  return text
    .replace(/\$\$?([^$]+)\$\$?/g, (_, inner: string) =>
      inner
        .replace(/\\int/g, "∫")
        .replace(/\\sum/g, "∑")
        .replace(/\\sqrt\{([^}]*)\}/g, "√($1)")
        .replace(/\\frac\{([^}]*)\}\{([^}]*)\}/g, "($1)/($2)")
        .replace(/\\(cdot|times)/g, "·")
        .replace(/\\(le|leq)/g, "≤")
        .replace(/\\(ge|geq)/g, "≥")
        .replace(/\\theta/g, "θ")
        .replace(/\\pi/g, "π")
        .replace(/\\,|\\;|\\!/g, " ")
        .replace(/\^\{?([0-4nx])\}?/g, (_m, d: string) => sup[d] ?? `^${d}`)
        .replace(/\\([a-zA-Z]+)/g, "$1")
        .replace(/[{}]/g, ""),
    );
}

function startOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}
