// TaskFlow Service Worker v2
const CACHE_NAME = 'taskflow-v2';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap',
    'https://unpkg.com/lucide@latest'
];

// Install — cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// Fetch — network-first with cache fallback
self.addEventListener('fetch', event => {
    // Skip non-GET and API requests
    if (event.request.method !== 'GET' || event.request.url.includes('/api/')) return;

    event.respondWith(
        fetch(event.request)
            .then(res => {
                const clone = res.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                return res;
            })
            .catch(() => caches.match(event.request))
    );
});

// Push notification from server
self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || '⏰ TaskFlow Reminder';
    const options = {
        body: data.body || 'You have a task due!',
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-192.png',
        tag: data.tag || 'taskflow-reminder',
        requireInteraction: true,
        vibrate: [200, 100, 200, 100, 400],
        data: { taskId: data.taskId, url: data.url || '/' },
        actions: [
            { action: 'complete', title: '✓ Complete' },
            { action: 'snooze', title: '⏰ Snooze 10m' }
        ]
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

// Notification action click handlers
self.addEventListener('notificationclick', event => {
    event.notification.close();
    const taskId = event.notification.data?.taskId;

    if (event.action === 'complete' && taskId) {
        event.waitUntil(
            fetch(`/api/tasks/${taskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_completed: true })
            }).then(() => self.clients.matchAll({ type: 'window' }))
                .then(clients => { if (clients[0]) clients[0].postMessage({ type: 'TASK_COMPLETED', taskId }); })
        );
    } else if (event.action === 'snooze' && taskId) {
        event.waitUntil(
            fetch(`/api/tasks/${taskId}/snooze`, { method: 'POST' })
                .then(() => self.clients.matchAll({ type: 'window' }))
                .then(clients => { if (clients[0]) clients[0].postMessage({ type: 'TASK_SNOOZED', taskId }); })
        );
    } else {
        // Default: open/focus the app
        event.waitUntil(
            self.clients.matchAll({ type: 'window' }).then(clients => {
                if (clients.length) { clients[0].focus(); }
                else { self.clients.openWindow(event.notification.data?.url || '/'); }
            })
        );
    }
});

// Background sync for offline snooze/complete
self.addEventListener('sync', event => {
    if (event.tag === 'sync-tasks') {
        event.waitUntil(
            self.clients.matchAll({ type: 'window' }).then(clients => {
                if (clients[0]) clients[0].postMessage({ type: 'SYNC_TASKS' });
            })
        );
    }
});
