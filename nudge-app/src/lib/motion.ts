/**
 * Nudge's motion system. Every animation in the app uses these, so the whole
 * feel can be retuned here. Springs follow iOS conventions: no overshoot for
 * layout, a little bounce for things the user "throws" or celebrates.
 */
import {
  Easing,
  FadeIn,
  FadeInDown,
  FadeOut,
  LinearTransition,
  type WithSpringConfig,
  type WithTimingConfig,
} from "react-native-reanimated";

export const springs = {
  /** Buttons, toggles, press feedback. */
  snappy: { damping: 22, stiffness: 340, mass: 0.7 } satisfies WithSpringConfig,
  /** Sheets, cards, layout shifts. */
  smooth: { damping: 28, stiffness: 200, mass: 1 } satisfies WithSpringConfig,
  /** Celebrations and things that land (sent message, joined course). */
  bouncy: { damping: 13, stiffness: 190, mass: 0.8 } satisfies WithSpringConfig,
};

export const timings = {
  fast: { duration: 160, easing: Easing.out(Easing.cubic) } satisfies WithTimingConfig,
  base: { duration: 260, easing: Easing.out(Easing.cubic) } satisfies WithTimingConfig,
  slow: { duration: 420, easing: Easing.out(Easing.exp) } satisfies WithTimingConfig,
};

/** How much a pressable shrinks while held. */
export const pressScale = 0.965;

/** Staggered entrance for list rows: index 0 first, capped so long lists don't drag. */
export const enterRow = (index: number) =>
  FadeInDown.delay(Math.min(index, 8) * 45)
    .springify()
    .damping(springs.smooth.damping)
    .stiffness(springs.smooth.stiffness);

export const enterFade = FadeIn.duration(timings.base.duration);
export const exitFade = FadeOut.duration(timings.fast.duration);
export const layoutSpring = LinearTransition.springify()
  .damping(springs.smooth.damping)
  .stiffness(springs.smooth.stiffness);
