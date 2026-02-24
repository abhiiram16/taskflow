# 🚀 Deploying TaskFlow on PythonAnywhere (Free Tier)

Step-by-step guide to deploy TaskFlow at **`https://abhiiram16.pythonanywhere.com`** — completely free, no credit card required.

---

## Table of Contents

1. [Create account & open console](#1-create-account--open-console)
2. [Clone & install](#2-clone--install)
3. [Set up the database](#3-set-up-the-database)
4. [Configure the web app](#4-configure-the-web-app)
5. [Edit the WSGI file](#5-edit-the-wsgi-file)
6. [Map static files](#6-map-static-files)
7. [Set environment variables](#7-set-environment-variables)
8. [Create uploads directory](#8-create-uploads-directory)
9. [Reload & verify](#9-reload--verify)
10. [Keeping it alive](#10-keeping-it-alive)

---

## 1. Create Account & Open Console

1. Go to [www.pythonanywhere.com](https://www.pythonanywhere.com/) and click **"Start running Python online"**.
2. Sign up for a **Beginner (free)** account.
   - Your username becomes your URL: `https://YOUR_USERNAME.pythonanywhere.com`
3. After signup, go to **Dashboard → Consoles → New Console → Bash**.

---

## 2. Clone & Install

In the Bash console, run:

```bash
# Clone the repository
cd ~
git clone https://github.com/abhiiram16/taskflow.git

# Create virtual environment (use Python 3.10)
mkvirtualenv --python=/usr/bin/python3.10 taskflow-env

# Install dependencies
cd ~/taskflow
pip install -r requirements.txt
```

> **Note:** PythonAnywhere uses `mkvirtualenv` (virtualenvwrapper) for managing venvs. To re-activate later: `workon taskflow-env`

---

## 3. Set Up the Database

### Option A: SQLite (Simplest — recommended for free tier)

No setup needed! The app defaults to SQLite. A `taskflow.db` file will be created automatically when the app starts. Skip to Step 4.

### Option B: PythonAnywhere MySQL (if you prefer MySQL)

1. Go to **Dashboard → Databases**.
2. Set a MySQL password and click **Initialize MySQL**.
3. Create a database: Enter `taskflow` in the "Create a database" field and click **Create**.
   - Full database name will be: `YOUR_USERNAME$taskflow`
4. Note these details:

| Setting | Value |
|---------|-------|
| **Host** | `YOUR_USERNAME.mysql.pythonanywhere-services.com` |
| **Username** | `YOUR_USERNAME` |
| **Database** | `YOUR_USERNAME$taskflow` |

5. You'll set the `DATABASE_URL` in Step 7.

---

## 4. Configure the Web App

1. Go to **Dashboard → Web** tab.
2. Click **"Add a new web app"**.
3. Click **Next** on the domain name (it will be `YOUR_USERNAME.pythonanywhere.com`).
4. Select **Manual configuration** (NOT "Flask" — we need custom WSGI).
5. Select **Python 3.10**.
6. Click **Next** to create the web app.

### Set the virtualenv path:

On the **Web** tab, scroll to **"Virtualenv"** section:
- Enter: `/home/YOUR_USERNAME/.virtualenvs/taskflow-env`
- Click the checkmark to save.

---

## 5. Edit the WSGI File

On the **Web** tab, click the link to your **WSGI configuration file** (it will be something like `/var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py`).

**Delete all the existing content** and replace with:

```python
import os
import sys

# Add project directory to path
project_home = '/home/YOUR_USERNAME/taskflow'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# Import the Flask app
from app import app as application
```

> ⚠️ Replace `YOUR_USERNAME` with your actual PythonAnywhere username in both lines.

Click **Save**.

---

## 6. Map Static Files

On the **Web** tab, scroll to the **"Static files"** section. Add these mappings:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/YOUR_USERNAME/taskflow/static/` |
| `/uploads/` | `/home/YOUR_USERNAME/taskflow/static/uploads/` |

This lets PythonAnywhere serve static files directly (faster, no Python overhead).

---

## 7. Set Environment Variables

Create a `.env` file in the project directory:

```bash
# In a Bash console
nano ~/taskflow/.env
```

Add:
```bash
SECRET_KEY=paste-a-random-64-char-string-here
```

**Generate a secret key:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### If using MySQL (Option B from Step 3), also add:
```bash
DATABASE_URL=mysql+pymysql://YOUR_USERNAME:YOUR_MYSQL_PASSWORD@YOUR_USERNAME.mysql.pythonanywhere-services.com/YOUR_USERNAME$taskflow
```

### If using SQLite (Option A), no `DATABASE_URL` is needed — the default handles it.

Save the file (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

## 8. Create Uploads Directory

```bash
mkdir -p ~/taskflow/static/uploads
chmod 755 ~/taskflow/static/uploads
```

### Initialize the database tables:

```bash
cd ~/taskflow
workon taskflow-env
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('Tables created!')"
```

---

## 9. Reload & Verify

1. Go back to the **Web** tab.
2. Click the big green **"Reload"** button at the top.
3. Visit: **`https://YOUR_USERNAME.pythonanywhere.com`**

You should see the TaskFlow login page! 🎉

### If something goes wrong:

- Check the **Error log** link on the Web tab.
- Common issues:
  - Wrong username in WSGI file paths → double-check every `/home/YOUR_USERNAME/` path
  - Virtualenv not found → verify the path in the Virtualenv section
  - Module not found → ensure you ran `pip install -r requirements.txt` inside the venv

---

## 10. Keeping It Alive

### Free tier limitations

| Limit | Value |
|-------|-------|
| **CPU** | 100 seconds/day for web apps |
| **Disk** | 512 MB total |
| **Outbound HTTP** | Whitelisted sites only |
| **App expiry** | Must click **"Run until 3 months from today"** button every 3 months |

### Stay alive checklist:

- ✅ **Every 3 months:** Go to Web tab → click the **"Run until 3 months from today"** button
- ✅ **No background loops:** The app already doesn't have any — you're fine
- ✅ **Keep uploads small:** Free tier has 512 MB total disk. Clean old uploads periodically
- ✅ **No infinite tasks:** Avoid AJAX polling shorter than 60 seconds to conserve CPU

### Updating the app:

```bash
cd ~/taskflow
git pull
# Then go to Web tab → click Reload
```

---

## Quick Reference

| Item | Value |
|------|-------|
| **App URL** | `https://YOUR_USERNAME.pythonanywhere.com` |
| **Project path** | `/home/YOUR_USERNAME/taskflow` |
| **Virtualenv** | `/home/YOUR_USERNAME/.virtualenvs/taskflow-env` |
| **WSGI file** | `/var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py` |
| **Env variables** | `/home/YOUR_USERNAME/taskflow/.env` |
| **Error log** | Web tab → "Error log" link |
| **Reload** | Web tab → green "Reload" button |
