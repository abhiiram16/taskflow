import os
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'taskflow-dev-key-change-in-production')
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
app.config['REMEMBER_COOKIE_SECURE'] = False  # Set True in production with HTTPS
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
BASEDIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///' + os.path.join(BASEDIR, 'taskflow.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'doc', 'docx', 'txt', 'csv', 'xlsx', 'pptx', 'zip', 'mp3', 'wav', 'ogg'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'

# ─── Models ───────────────────────────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_pic_url = db.Column(db.String(300), nullable=True)
    preferred_sound = db.Column(db.String(300), default='chime')
    gmail = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('Task', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), default='medium')
    reminder_date = db.Column(db.String(50), nullable=True)
    reminder_time = db.Column(db.String(50), nullable=True)
    custom_sound = db.Column(db.String(300), nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    attachments = db.relationship('Attachment', backref='task', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'reminder_date': self.reminder_date,
            'reminder_time': self.reminder_time,
            'custom_sound': self.custom_sound,
            'is_completed': self.is_completed,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'attachments': [a.to_dict() for a in self.attachments]
        }

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    stored_name = db.Column(db.String(300), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'stored_name': self.stored_name,
            'file_type': self.file_type,
            'url': f'/uploads/{self.stored_name}'
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Create tables
with app.app_context():
    db.create_all()

# ─── Page Routes ──────────────────────────────────────────

@app.route("/sw.js")
def service_worker():
    response = send_from_directory(app.static_folder, 'sw.js')
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    return response


@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template("login.html")

# ─── Auth API ─────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'All fields are required'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({'message': 'Registration successful', 'username': user.username}), 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    login_user(user, remember=True)
    return jsonify({'message': 'Login successful', 'username': user.username})

@app.route("/api/auth/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))

@app.route("/api/auth/me")
@login_required
def me():
    return jsonify({
        'username': current_user.username,
        'email': current_user.email,
        'gmail': current_user.gmail,
        'profile_pic_url': current_user.profile_pic_url,
        'preferred_sound': current_user.preferred_sound
    })

# ─── Task API ─────────────────────────────────────────────

@app.route("/api/tasks", methods=["GET"])
@login_required
def get_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tasks])

@app.route("/api/tasks", methods=["POST"])
@login_required
def add_task():
    data = request.json
    if not data or not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400

    # Smart date/time defaults (server-side safety net)
    now = datetime.now()
    r_date = data.get('reminder_date') or now.strftime('%Y-%m-%d')
    r_time = data.get('reminder_time')
    if not r_time:
        # If date was explicitly set but no time → midnight; otherwise → now
        r_time = now.strftime('%H:%M') if not data.get('reminder_date') else '00:00'

    # Past-date validation
    try:
        reminder_dt = datetime.strptime(f"{r_date} {r_time}", '%Y-%m-%d %H:%M')
        if reminder_dt < now:
            return jsonify({'error': 'Cannot schedule a reminder in the past'}), 400
    except ValueError:
        pass  # Let it through if date parsing fails

    task = Task(
        title=data['title'],
        description=data.get('description', ''),
        priority=data.get('priority', 'medium'),
        reminder_date=r_date,
        reminder_time=r_time,
        custom_sound=data.get('custom_sound'),
        user_id=current_user.id
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201

@app.route("/api/tasks/<int:id>", methods=["PUT"])
@login_required
def update_task(id):
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    data = request.json
    for field in ['title', 'description', 'priority', 'is_completed', 'reminder_date', 'reminder_time', 'custom_sound']:
        if field in data:
            setattr(task, field, data[field])

    # Past-date validation for reminder changes (skip if just toggling completion)
    if ('reminder_date' in data or 'reminder_time' in data) and not data.get('is_completed'):
        r_date = task.reminder_date
        r_time = task.reminder_time
        if r_date and r_time:
            try:
                reminder_dt = datetime.strptime(f"{r_date} {r_time}", '%Y-%m-%d %H:%M')
                if reminder_dt < datetime.now():
                    return jsonify({'error': 'Cannot schedule a reminder in the past'}), 400
            except ValueError:
                pass

    db.session.commit()
    return jsonify(task.to_dict())

@app.route("/api/tasks/<int:id>", methods=["DELETE"])
@login_required
def delete_task(id):
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted'})

# ─── Snooze API ──────────────────────────────────────────

@app.route("/api/tasks/<int:id>/snooze", methods=["POST"])
@login_required
def snooze_task(id):
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if not task.reminder_time:
        return jsonify({'error': 'No reminder time set'}), 400

    # Parse current time, add 10 minutes
    parts = task.reminder_time.split(':')
    hour, minute = int(parts[0]), int(parts[1])
    minute += 10
    if minute >= 60:
        minute -= 60
        hour = (hour + 1) % 24
    task.reminder_time = f"{hour:02d}:{minute:02d}"
    db.session.commit()
    return jsonify({'message': 'Snoozed by 10 minutes', 'new_time': task.reminder_time, 'task': task.to_dict()})

# ─── Attachment API ───────────────────────────────────────

@app.route("/api/tasks/<int:id>/attachments", methods=["POST"])
@login_required
def upload_attachment(id):
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    original_name = secure_filename(file.filename)
    ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else ''
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], stored_name))

    # Determine file type category
    image_exts = {'png', 'jpg', 'jpeg', 'gif'}
    video_exts = {'mp4', 'webm'}
    file_type = 'image' if ext in image_exts else 'video' if ext in video_exts else 'document'

    attachment = Attachment(
        task_id=task.id,
        filename=original_name,
        stored_name=stored_name,
        file_type=file_type
    )
    db.session.add(attachment)
    db.session.commit()
    return jsonify(attachment.to_dict()), 201

@app.route("/api/attachments/<int:id>", methods=["DELETE"])
@login_required
def delete_attachment(id):
    attachment = Attachment.query.get_or_404(id)
    task = Task.query.filter_by(id=attachment.task_id, user_id=current_user.id).first_or_404()
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], attachment.stored_name)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(attachment)
    db.session.commit()
    return jsonify({'message': 'Attachment deleted'})

@app.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# ─── User Profile API ─────────────────────────────────────

@app.route("/api/user/profile", methods=["PUT"])
@login_required
def update_profile():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'username' in data and data['username'] != current_user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 409
        current_user.username = data['username']

    if 'email' in data and data['email'] != current_user.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409
        current_user.email = data['email']

    if 'gmail' in data:
        current_user.gmail = data['gmail']

    db.session.commit()
    return jsonify({'message': 'Profile updated', 'username': current_user.username, 'email': current_user.email})

@app.route("/api/user/password", methods=["PUT"])
@login_required
def change_password():
    data = request.json
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'error': 'Current and new passwords are required'}), 400

    if not current_user.check_password(data['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 401

    if len(data['new_password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    current_user.set_password(data['new_password'])
    db.session.commit()
    return jsonify({'message': 'Password changed successfully'})

@app.route("/api/user/avatar", methods=["POST"])
@login_required
def upload_avatar():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    original_name = secure_filename(file.filename)
    ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else ''
    if ext not in {'png', 'jpg', 'jpeg', 'gif'}:
        return jsonify({'error': 'Only image files are allowed'}), 400

    # Remove old avatar if exists
    if current_user.profile_pic_url:
        old_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.profile_pic_url)
        if os.path.exists(old_path):
            os.remove(old_path)

    stored_name = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], stored_name))
    current_user.profile_pic_url = stored_name
    db.session.commit()
    return jsonify({'message': 'Avatar updated', 'profile_pic_url': stored_name})

@app.route("/api/user/sound", methods=["PUT"])
@login_required
def update_sound():
    data = request.json
    if not data or 'sound' not in data:
        return jsonify({'error': 'Sound preference required'}), 400
    current_user.preferred_sound = data['sound']
    db.session.commit()
    return jsonify({'message': 'Sound preference updated', 'preferred_sound': current_user.preferred_sound})

@app.route("/api/user/sound/upload", methods=["POST"])
@login_required
def upload_custom_sound():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    original_name = secure_filename(file.filename)
    ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else ''
    if ext not in {'mp3', 'wav', 'ogg'}:
        return jsonify({'error': 'Only audio files (mp3, wav, ogg) are allowed'}), 400

    stored_name = f"sound_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], stored_name))
    current_user.preferred_sound = f'custom:{stored_name}'
    db.session.commit()
    return jsonify({'message': 'Custom sound uploaded', 'preferred_sound': current_user.preferred_sound, 'url': f'/uploads/{stored_name}'})

if __name__ == "__main__":
    app.run(debug=True, port=8000)