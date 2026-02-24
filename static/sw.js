// TaskFlow Service Worker v4 — Mobile-Optimized with Background Alarm Engine
const CACHE_NAME = 'taskflow-v4';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap',
    'https://unpkg.com/lucide@latest'
];

// High-intensity vibration pattern for notifications
const VIBRATION_PATTERN = [500, 110, 500, 110, 450, 110, 200, 110, 700];

// Track fired alarms to prevent duplicates
const firedAlarms = new Set();

// ─── Install — cache static assets ───
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// ─── Activate — clean old caches + start alarm loop ───
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
    // Kick off background alarm checking
    startAlarmLoop();
});

// ─── Fetch — network-first with cache fallback ───
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

// ═══════════════════════════════════════════
//  BACKGROUND ALARM ENGINE
//  Polls /api/tasks every 30s and fires
//  notifications for due tasks — works even
//  when tab is frozen or phone is locked.
// ═══════════════════════════════════════════
function startAlarmLoop() {
    checkTaskAlarms();
}

async function checkTaskAlarms() {
    try {
        const res = await fetch('/api/tasks', { credentials: 'include' });
        if (res.ok) {
            const tasks = await res.json();
            const now = new Date();

            tasks.forEach(task => {
                if (task.is_completed || !task.reminder_date || !task.reminder_time) return;
                if (firedAlarms.has(task.id)) return;

                // Parse reminder datetime
                const [y, m, d] = task.reminder_date.split('-').map(Number);
                const [hh, mm] = task.reminder_time.split(':').map(Number);
                const reminderTime = new Date(y, m - 1, d, hh, mm, 0);

                // Fire if reminder time has passed but less than 2 minutes ago
                const diff = now - reminderTime;
                if (diff >= 0 && diff < 120000) {
                    firedAlarms.add(task.id);
                    fireTaskNotification(task);
                }
            });
        }
    } catch (err) {
        // Network error — silently retry next cycle
        console.log('[SW] Alarm check failed:', err.message);
    }

    // Schedule next check in 30 seconds (setTimeout recursion survives better than setInterval)
    setTimeout(checkTaskAlarms, 30000);
}

function fireTaskNotification(task) {
    const priorityEmoji = { high: '🔴', medium: '🟡', low: '🔵' };
    const emoji = priorityEmoji[task.priority] || '⏰';

    self.registration.showNotification(`${emoji} ${task.title}`, {
        body: task.description || `${(task.priority || 'medium').toUpperCase()} priority — due now!`,
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-192.png',
        tag: `task-alarm-${task.id}`,
        requireInteraction: true,
        renotify: true,
        vibrate: VIBRATION_PATTERN,
        data: { taskId: task.id, url: '/', source: 'alarm-engine' },
        actions: [
            { action: 'complete', title: '✓ Complete' },
            { action: 'snooze', title: '⏰ Snooze 10m' }
        ]
    });

    // Notify all open clients so UI can show hero tile
    self.clients.matchAll({ type: 'window' }).then(clients => {
        clients.forEach(client => {
            client.postMessage({
                type: 'ALARM_FIRED',
                task: task
            });
        });
    });
}

// ─── Push notification from server ───
self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || '⏰ TaskFlow Reminder';
    const options = {
        body: data.body || 'You have a task due!',
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-192.png',
        tag: data.tag || 'taskflow-reminder',
        requireInteraction: true,
        vibrate: VIBRATION_PATTERN,
        data: { taskId: data.taskId, url: data.url || '/' },
        actions: [
            { action: 'complete', title: '✓ Complete' },
            { action: 'snooze', title: '⏰ Snooze 10m' }
        ]
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

// ─── Notification action click handlers ───
self.addEventListener('notificationclick', event => {
    event.notification.close();
    const taskId = event.notification.data?.taskId;

    if (event.action === 'complete' && taskId) {
        event.waitUntil(
            fetch(`/api/tasks/${taskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ is_completed: true })
            }).then(() => self.clients.matchAll({ type: 'window' }))
                .then(clients => {
                    clients.forEach(c => c.postMessage({ type: 'TASK_COMPLETED', taskId }));
                    // Remove from fired set so re-snooze works
                    firedAlarms.delete(taskId);
                })
        );
    } else if (event.action === 'snooze' && taskId) {
        event.waitUntil(
            fetch(`/api/tasks/${taskId}/snooze`, { method: 'POST', credentials: 'include' })
                .then(() => self.clients.matchAll({ type: 'window' }))
                .then(clients => {
                    clients.forEach(c => c.postMessage({ type: 'TASK_SNOOZED', taskId }));
                    firedAlarms.delete(taskId);
                })
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

// ─── Message handler from clients ───
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'RESET_ALARM') {
        // Client tells us to allow re-firing (e.g. after snooze)
        firedAlarms.delete(event.data.taskId);
    } else if (event.data && event.data.type === 'RESET_ALL_ALARMS') {
        firedAlarms.clear();
    }
});

// ─── Background sync for offline snooze/complete ───
self.addEventListener('sync', event => {
    if (event.tag === 'sync-tasks') {
        event.waitUntil(
            self.clients.matchAll({ type: 'window' }).then(clients => {
                if (clients[0]) clients[0].postMessage({ type: 'SYNC_TASKS' });
            })
        );
    }
});
