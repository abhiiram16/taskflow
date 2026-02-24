# 🚀 TaskFlow — Smart Task Manager PWA

A premium, glassmorphic **Progressive Web App** for managing tasks with priority-based alarms, hero notifications, file attachments, and custom notification sounds.

Built with **Flask** + vanilla **JavaScript** and a fully hand-crafted CSS design system.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Glassmorphic UI** | Dark-mode interface with frosted-glass panels, glow effects, and smooth micro-animations |
| **Progressive Web App** | Installable on mobile/desktop with offline caching via Service Worker |
| **Hero Notifications** | Full-screen, animated notification tiles when a task is due |
| **Smart Scheduling** | Auto-fills T+5 minutes when no time is specified; blocks past-date reminders |
| **Priority Alarms** | Color-coded priorities (critical / high / medium / low) with visual indicators |
| **File Attachments** | Drag-and-drop upload of images, documents, audio, and video per task |
| **Custom Sounds** | Choose built-in alarm tones or upload your own `.mp3` / `.wav` / `.ogg` |
| **Snooze** | One-tap 10-minute snooze from notifications or the task card |
| **User Profiles** | Avatar upload, password changes, and per-user sound preferences |
| **Persistent Auth** | "Remember me" sessions with Flask-Login (30-day cookies) |

---

## 📋 Prerequisites

- **Python 3.10+**
- **MySQL 8.0+** running on `localhost:3306`
- A MySQL database named `tasksmaganerapp`

---

## ⚡ Quick Start

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd Flask

# 2. Create & activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure the database
#    Edit the SQLALCHEMY_DATABASE_URI in app.py if your
#    MySQL credentials differ from root:abhi@localhost:3306

# 5. Launch 🚀
python run.py
```

The app will be live at **http://127.0.0.1:8000**

---

## 📁 Project Structure

```
Flask/
├── app.py              # Flask application — routes, models, API
├── run.py              # One-click entry point
├── requirements.txt    # Pinned Python dependencies
├── .gitignore          # Repository hygiene rules
├── README.md           # You are here
├── static/
│   ├── css/
│   │   └── style.css   # Full design system (glassmorphic theme)
│   ├── icons/          # PWA icons (icon-192.png, icon-512.png)
│   ├── uploads/        # Runtime user uploads (git-ignored)
│   ├── manifest.json   # PWA manifest
│   └── sw.js           # Service Worker (caching, push, sync)
└── templates/
    ├── index.html      # Main dashboard SPA
    └── login.html      # Auth page (login / register)
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Create account |
| `POST` | `/api/auth/login` | Log in |
| `GET`  | `/api/auth/logout` | Log out |
| `GET`  | `/api/auth/me` | Current user profile |
| `GET`  | `/api/tasks` | List all tasks |
| `POST` | `/api/tasks` | Create a task |
| `PUT`  | `/api/tasks/:id` | Update a task |
| `DELETE` | `/api/tasks/:id` | Delete a task |
| `POST` | `/api/tasks/:id/snooze` | Snooze reminder +10 min |
| `POST` | `/api/tasks/:id/attachments` | Upload file attachment |
| `DELETE` | `/api/attachments/:id` | Remove attachment |
| `PUT` | `/api/user/profile` | Update username / email |
| `PUT` | `/api/user/password` | Change password |
| `POST` | `/api/user/avatar` | Upload profile picture |
| `PUT` | `/api/user/sound` | Set sound preference |
| `POST` | `/api/user/sound/upload` | Upload custom sound |

---

## 📄 License

This project is for personal / educational use. Add your preferred license here.
