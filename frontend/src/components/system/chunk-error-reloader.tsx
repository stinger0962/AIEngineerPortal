"use client";

import { useEffect } from "react";

const RELOAD_FLAG = "chunkReloadAt";
const RELOAD_WINDOW_MS = 10_000;

/** True when an error is a webpack/Next dynamic-chunk load failure. */
function isChunkLoadError(value: unknown): boolean {
  if (!value) return false;
  const err = value as { name?: string; message?: string };
  if (err.name === "ChunkLoadError") return true;
  const msg = typeof err.message === "string" ? err.message : typeof value === "string" ? value : "";
  return /Loading (?:CSS )?chunk [\w-]+ failed/i.test(msg) || /ChunkLoadError/i.test(msg);
}

/** Reload the current page at most once per RELOAD_WINDOW_MS to recover without looping. */
function reloadOnce() {
  try {
    const last = Number(sessionStorage.getItem(RELOAD_FLAG) ?? 0);
    if (Date.now() - last < RELOAD_WINDOW_MS) return; // already tried recently — a real, permanent 404 must not loop
    sessionStorage.setItem(RELOAD_FLAG, String(Date.now()));
  } catch {
    // sessionStorage may be unavailable (private mode / blocked) — fall through and reload anyway
  }
  window.location.reload();
}

/**
 * Self-heals transient chunk-load failures. A ChunkLoadError — from a stale chunk
 * after a deploy (a tab open across the deploy then navigating), a flaky network, or
 * a corrupted browser cache (ERR_CACHE_READ_FAILURE) — otherwise dead-ends the page
 * with Next's blank "Application error". A full reload refetches the current build's
 * chunks and clears the bad cache entry. Renders nothing.
 */
export function ChunkErrorReloader() {
  useEffect(() => {
    const onError = (event: ErrorEvent) => {
      if (isChunkLoadError(event.error) || isChunkLoadError(event.message)) reloadOnce();
    };
    const onRejection = (event: PromiseRejectionEvent) => {
      if (isChunkLoadError(event.reason)) reloadOnce();
    };
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);
  return null;
}
