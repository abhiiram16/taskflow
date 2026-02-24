# 🚀 Deploying TaskFlow on Oracle Cloud Free Tier

Complete step-by-step guide to deploy TaskFlow on an **Always Free** Oracle Cloud Ubuntu VM.

> **Cost: $0** — Everything uses Always Free resources only.

---

## Table of Contents

1. [Create the VM](#1-create-the-vm)
2. [SSH into the VM](#2-ssh-into-the-vm)
3. [Install system dependencies](#3-install-system-dependencies)
4. [Install & configure MySQL](#4-install--configure-mysql)
5. [Clone & set up the project](#5-clone--set-up-the-project)
6. [Configure environment variables](#6-configure-environment-variables)
7. [Test with Gunicorn](#7-test-with-gunicorn)
8. [Set up Nginx reverse proxy](#8-set-up-nginx-reverse-proxy)
9. [Create systemd service](#9-create-systemd-service-auto-restart)
10. [Open ports (VCN + firewall)](#10-open-ports-vcn--firewall)
11. [Verify deployment](#11-verify-deployment)
12. [Memory optimization](#12-memory-optimization-tips)

---

## 1. Create the VM

1. Go to [Oracle Cloud Console](https://cloud.oracle.com/) → **Create a Free Account** (if you haven't already).
2. Navigate to **Compute → Instances → Create Instance**.
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `taskflow-server` |
| **Image** | **Canonical Ubuntu 22.04** (Always Free eligible) |
| **Shape** | **VM.Standard.A1.Flex** (ARM) — 1 OCPU, 6 GB RAM |
| **OCPU count** | `1` |
| **Memory** | `6` GB |
| **Boot volume** | 50 GB (default, Always Free) |
| **SSH key** | Upload your public key or generate a new pair |

> [!IMPORTANT]
> The **VM.Standard.A1.Flex** shape gives you up to **4 OCPUs + 24 GB RAM free**. Using 1 OCPU / 6 GB is more than enough and stays within free limits.

4. Under **Networking** → ensure a **public subnet** is selected and **Assign a public IPv4 address** is checked.
5. Click **Create** and wait for the instance to become **Running**.
6. Note the **Public IP Address** from the instance details page.

---

## 2. SSH into the VM

```bash
# Replace with your key path and public IP
ssh -i ~/.ssh/your_private_key ubuntu@YOUR_PUBLIC_IP
```

> On Windows, use PowerShell or PuTTY:
> ```powershell
> ssh -i C:\Users\abhir\.ssh\id_rsa ubuntu@YOUR_PUBLIC_IP
> ```

---

## 3. Install System Dependencies

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Python 3, pip, venv, and build tools
sudo apt install -y python3 python3-pip python3-venv git nginx curl

# Verify
python3 --version   # Should be 3.10+
pip3 --version
```

---

## 4. Install & Configure MySQL

```bash
# Install MySQL server
sudo apt install -y mysql-server

# Secure the installation
sudo mysql_secure_installation
# → Set a root password (remember it!)
# → Remove anonymous users: Y
# → Disallow root login remotely: Y
# → Remove test database: Y
# → Reload privilege tables: Y

# Create the database and app user
sudo mysql -u root -p
```

Inside the MySQL shell:
```sql
CREATE DATABASE tasksmaganerapp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'taskflow'@'localhost' IDENTIFIED BY 'YourStrongPassword123!';
GRANT ALL PRIVILEGES ON tasksmaganerapp.* TO 'taskflow'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

> [!TIP]
> Replace `YourStrongPassword123!` with your own strong password. You'll use this in Step 6.

---

## 5. Clone & Set Up the Project

```bash
# Clone your repo
cd /home/ubuntu
git clone https://github.com/abhiiram16/taskflow.git
cd taskflow

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create uploads directory with correct permissions
mkdir -p static/uploads
chmod 755 static/uploads
```

---

## 6. Configure Environment Variables

Create a `.env` file (this file is git-ignored):

```bash
nano /home/ubuntu/taskflow/.env
```

Paste the following (edit the values):
```bash
SECRET_KEY=generate-a-random-64-char-string-here
DATABASE_URL=mysql+pymysql://taskflow:YourStrongPassword123!@localhost:3306/tasksmaganerapp
```

**Generate a random secret key:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as the `SECRET_KEY` value.

---

## 7. Test with Gunicorn

```bash
cd /home/ubuntu/taskflow
source venv/bin/activate

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Test Gunicorn (2 workers, optimized for low memory)
gunicorn --workers 2 --bind 127.0.0.1:8000 wsgi:app
```

You should see:
```
[INFO] Listening at: http://127.0.0.1:8000
[INFO] Using worker: sync
```

Press `Ctrl+C` to stop. If it works, proceed to the next step.

---

## 8. Set Up Nginx Reverse Proxy

```bash
# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Create TaskFlow config
sudo nano /etc/nginx/sites-available/taskflow
```

Paste this config:
```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/ubuntu/taskflow/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads/ {
        alias /home/ubuntu/taskflow/static/uploads/;
        expires 7d;
    }
}
```

Enable the site and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/taskflow /etc/nginx/sites-enabled/
sudo nginx -t          # Test config — should say "syntax is ok"
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 9. Create systemd Service (Auto-Restart)

```bash
sudo nano /etc/systemd/system/taskflow.service
```

Paste:
```ini
[Unit]
Description=TaskFlow Gunicorn WSGI Server
After=network.target mysql.service

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/taskflow
EnvironmentFile=/home/ubuntu/taskflow/.env
ExecStart=/home/ubuntu/taskflow/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl start taskflow
sudo systemctl enable taskflow    # Auto-start on reboot

# Check status
sudo systemctl status taskflow
```

You should see **`active (running)`** in green.

---

## 10. Open Ports (VCN + Firewall)

### A. Oracle VCN Security List (required!)

1. Go to **Oracle Cloud Console → Networking → Virtual Cloud Networks**.
2. Click your VCN → **Security Lists** → **Default Security List**.
3. Click **Add Ingress Rules** and add:

| Source CIDR | Protocol | Dest Port | Description |
|-------------|----------|-----------|-------------|
| `0.0.0.0/0` | TCP | `80` | HTTP |
| `0.0.0.0/0` | TCP | `443` | HTTPS (for future SSL) |

### B. Ubuntu Firewall (UFW)

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

> [!NOTE]
> Oracle Ubuntu images use `iptables` directly, not `ufw`. The commands above are the correct approach for Oracle Cloud.

---

## 11. Verify Deployment

Open your browser and navigate to:

```
http://YOUR_PUBLIC_IP
```

You should see the TaskFlow login page! 🎉

### Useful commands:

```bash
# View app logs
sudo journalctl -u taskflow -f

# Restart after code changes
cd /home/ubuntu/taskflow
git pull
sudo systemctl restart taskflow

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

---

## 12. Memory Optimization Tips

Your Always Free VM has **6 GB RAM**. Here's how to keep usage low:

| Optimization | Command / Setting |
|--------------|-------------------|
| **Gunicorn workers** | Keep at `2` (not more) |
| **MySQL buffer pool** | Add `innodb_buffer_pool_size=128M` to `/etc/mysql/mysql.conf.d/mysqld.cnf` |
| **Swap file** (safety net) | See commands below |
| **Max upload size** | Already set to 50MB in app + Nginx |

**Add a 2GB swap file (prevents OOM crashes):**
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

---

## Quick Reference

| Item | Value |
|------|-------|
| **App URL** | `http://YOUR_PUBLIC_IP` |
| **App directory** | `/home/ubuntu/taskflow` |
| **Service name** | `taskflow` |
| **Restart command** | `sudo systemctl restart taskflow` |
| **Logs** | `sudo journalctl -u taskflow -f` |
| **Nginx config** | `/etc/nginx/sites-available/taskflow` |
| **Env variables** | `/home/ubuntu/taskflow/.env` |
