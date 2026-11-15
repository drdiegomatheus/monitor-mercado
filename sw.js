// Service worker mínimo: sempre tenta a rede (dados novos); se estiver sem internet, mostra a última versão guardada.
const C = "monitor-v3";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request, {cache: "no-store"}).then(r => { const c = r.clone(); caches.open(C).then(k => k.put(e.request, c)); return r; })
    .catch(() => caches.match(e.request)));
});
