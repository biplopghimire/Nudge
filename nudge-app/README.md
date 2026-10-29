# Nudge app

The React Native (Expo) app for students and teachers. Version 1 screens from the v2 wireframes.

## Run it (same setup as Lab 0)

You need Node, Watchman and Xcode (or Android Studio) from Lab 0, and the **Expo Go** app.

```bash
cd nudge-app
npm install
npx expo start
```

Press `i` for the iOS simulator or `a` for Android, or scan the QR code with Expo Go on your phone.

By default the app talks to the live backend on Cloud Run. To use a backend running on your laptop
(`uvicorn app.main:app --host 0.0.0.0` in `nudge-api/`), create `nudge-app/.env.local`:

```
EXPO_PUBLIC_API_URL=http://localhost:8000
```

(On a physical phone use your computer's LAN IP instead of `localhost`.) Restart `npx expo start` after changing it.

Checks: `npm run typecheck` and `npm run lint`.

## What's inside

| Layer | Library | Why |
|---|---|---|
| Routing | Expo Router | File-based screens in `src/app`, each role sees only its own screens |
| Components | HeroUI Native | Buttons, fields, switches, sheets, toasts, skeletons; all animated with Reanimated |
| Styling | Uniwind (Tailwind) | Theme tokens in `src/global.css` (wireframe teal, mint, blush; light and dark) |
| Motion | Reanimated 4, Skia | `src/lib/motion.ts` holds every spring and timing; Skia draws the "thinking" shimmer |
| Chat | Legend List, keyboard-controller, react-native-marked | Keyboard-aware message list, markdown replies |
| Data | TanStack Query, expo-secure-store | Cached screens; the login token stays in the iPhone's secure storage |
| Native | expo-camera, image-picker, document-picker, haptics, symbols, glass-effect | The + menu, haptics, SF Symbols, Liquid Glass on iOS 26 |

Everything runs in Expo Go (no custom native build needed).

```
src/
  app/                  screens (Expo Router)
    (auth)/welcome      sign in / create account
    (student)/(tabs)/   home, chats, profile;  (student)/join
    (teacher)/(tabs)/   courses, account;  (teacher)/course/new, [id], [id]/options, [id]/share
    chat/[id]           the chat (both roles);  camera
  components/
    brand/              the axolotl (<NudgeAvatar state>, swapped for Rive in v2)
    chat/               messages, composer, thinking status, + menu
    ui/                 shared pieces (Tappable, Row, Segmented, CodeInput, tab bar, ...)
  lib/                  api client, auth, queries, motion, haptics, formatting
```

API types come straight from `../nudge-api/nudge-types.ts` (imported as `@api`), so the app and the backend can't drift apart.
