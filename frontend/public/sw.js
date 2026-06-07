/* eslint-disable no-restricted-globals */
// Service worker for Web Push notifications.
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (e) {
    payload = { title: "RSI & MA Tracker", body: event.data ? event.data.text() : "Signal triggered" };
  }
  const title = payload.title || "RSI & MA Tracker";
  const options = {
    body: payload.body || "Signal triggered",
    icon: "/favicon.ico",
    badge: "/favicon.ico",
    tag: (payload.data && payload.data.symbol) || "rsi-tracker",
    data: payload.data || {},
    requireInteraction: false,
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ("focus" in client) return client.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow("/");
    })
  );
});
