// No-op service worker.
// Some browsers/extensions request /sw.js by default; serving a file avoids noisy 404s.
self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", () => {});

