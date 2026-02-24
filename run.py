"""
TaskFlow — One-Click Entry Point
================================
Start the entire application with:  python run.py

This script:
  1. Ensures the uploads directory exists
  2. Initialises the database tables (safe if they already exist)
  3. Launches the Flask development server on port 8000
"""

import os
import sys


def main():
    # ─── Ensure uploads directory ────────────────────────────
    from app import app, db

    uploads_dir = app.config["UPLOAD_FOLDER"]
    os.makedirs(uploads_dir, exist_ok=True)

    # ─── Ensure database tables ──────────────────────────────
    with app.app_context():
        db.create_all()
        print("✔  Database tables verified.")

    print(f"✔  Uploads directory: {uploads_dir}")
    print("─" * 48)
    print("🚀  Starting TaskFlow on http://127.0.0.1:8000")
    print("─" * 48)

    # ─── Start Flask dev server ──────────────────────────────
    app.run(debug=True, port=8000, use_reloader=False)


if __name__ == "__main__":
    main()
