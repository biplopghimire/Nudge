// The backend the app talks to. Defaults to the live Cloud Run deploy; set
// EXPO_PUBLIC_API_URL (for example http://localhost:8000) to use a local server.
export const API_URL = (
  process.env.EXPO_PUBLIC_API_URL ?? "https://nudge-api-214919077406.us-east1.run.app"
).replace(/\/$/, "");
