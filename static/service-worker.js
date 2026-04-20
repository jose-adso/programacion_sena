/**
 * Service Worker para PWA - Sistema de Gestión SENA
 * Cachea recursos estáticos y maneja errores de conexión
 */

const CACHE_NAME = 'sena-gestion-v1';
const STATIC_CACHE = 'static-cache-v1';
const DYNAMIC_CACHE = 'dynamic-cache-v1';

// Recursos estáticos críticos para cached
const STATIC_ASSETS = [
  '/',
  '/offline.html',
  '/static/manifest.json',
  '/static/css/style.css',
  '/static/16%20mar%202026%2C%2009_19_27.png',
  '/static/sena-favicon.svg',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'
];

// Instalación del service worker
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('Cache estático abierto');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activación y limpieza de caches antiguos
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log('Eliminando cache antiguo:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Estrategia de cache: Cache First, luego network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Solo manejar solicitudes GET
  if (request.method !== 'GET') {
    return;
  }

  // Para archivos estáticos: Cache First
  if (STATIC_ASSETS.some(asset => url.pathname.includes(asset.split('/').pop()))) {
    event.respondWith(
      caches.match(request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          return fetch(request)
            .then((networkResponse) => {
              return caches.open(STATIC_CACHE)
                .then((cache) => {
                  cache.put(request, networkResponse.clone());
                  return networkResponse;
                });
            })
            .catch(() => {
              // Si falla la red y no hay cache, retornar página offline
              return caches.match('/offline.html');
            });
        })
    );
    return;
  }

  // Para API calls: Network First, luego cache
  if (url.pathname.startsWith('/api/') || url.pathname.includes('/cambiar_rol/')) {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          // Guardar respuesta en cache dinámico
          return caches.open(DYNAMIC_CACHE)
            .then((cache) => {
              cache.put(request, networkResponse.clone());
              return networkResponse;
            });
        })
        .catch(() => {
          // Si no hay red, intentar desde cache
          return caches.match(request)
            .then((cachedResponse) => {
              if (cachedResponse) {
                return cachedResponse;
              }
              // Retornar respuesta de error
              return new Response(
                JSON.stringify({ error: 'Sin conexión', success: false }),
                {
                  status: 503,
                  headers: { 'Content-Type': 'application/json' }
                }
              );
            });
        })
    );
    return;
  }

  // Para otras solicitudes: Network First con fallback a cache
  event.respondWith(
    fetch(request)
      .then((networkResponse) => {
        return caches.open(DYNAMIC_CACHE)
          .then((cache) => {
            cache.put(request, networkResponse.clone());
            return networkResponse;
          });
      })
      .catch(() => {
        return caches.match(request)
          .then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            // Retornar página offline para rutas HTML
            if (request.headers.get('accept').includes('text/html')) {
              return caches.match('/offline.html');
            }
            return new Response('Sin conexión', { status: 503 });
          });
      })
  );
});

// Mensajes desde la página principal
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
