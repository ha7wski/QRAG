"use client";

import {
  useEffect,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

/**
 * In-memory page cache — "my search is still there when I come back".
 *
 * The App Router unmounts a page on navigation, so every `useState` on it is
 * lost: leaving Verse Study for Lisan Analysis and returning used to reset the
 * word, the verses and the collapsed sections. `useCachedState` is a drop-in
 * replacement for `useState` that keeps the value in a module-level Map, which
 * outlives any single page mount.
 *
 * **Scope: the tab's JS session.** A module lives as long as the client bundle,
 * so the cache survives every in-app navigation and is dropped by a hard reload
 * (F5) or closing the tab. Nothing is written to disk — deliberately: caching a
 * 180-verse lookup in localStorage would mean serialising it on every keystroke-
 * driven search and handling quota failures, for state whose whole value is
 * being *current*.
 *
 * **Why the write lives in an effect, and why that matters.** A module-level Map
 * is shared by every request on the server, so writing to it during render would
 * leak one visitor's search into another's SSR output. `useEffect` never runs on
 * the server, so the cache is only ever *written* in a browser: server-side it
 * stays permanently empty and every SSR render falls back to `initial`. That is
 * a structural guarantee, not a convention — do not move the write into render.
 *
 * **Cache durable state only.** `loading` flags, in-flight request ids and
 * anything transient must stay on plain `useState`: a cached `loading: true`
 * would restore a spinner that never stops.
 */
const cache = new Map<string, unknown>();

/** `useState`, but the value survives unmount for the life of the tab's session.
 *
 * `key` must be unique across the whole app — prefix it with the page and field
 * (`"verse-study.word.query"`), never a bare name. */
export function useCachedState<T>(
  key: string,
  initial: T,
): [T, Dispatch<SetStateAction<T>>] {
  // `has`, not a truthiness test: `null`, `""` and `0` are values a reader left
  // behind, and must win over `initial` just like any other.
  const [value, setValue] = useState<T>(() =>
    cache.has(key) ? (cache.get(key) as T) : initial,
  );

  useEffect(() => {
    cache.set(key, value);
  }, [key, value]);

  return [value, setValue];
}

/** Drop every cached value. Exposed for tests; nothing in the app calls it. */
export function clearPageCache(): void {
  cache.clear();
}
