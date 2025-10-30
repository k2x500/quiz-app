from flask import Flask, render_template, request, send_file, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json
import random
import csv

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuration
UPLOAD_FOLDER = 'uploads'
CSV_FOLDER = 'csv_files'
TEMP_FOLDER = 'temp_quiz_data'
ALLOWED_EXTENSIONS = {'docx'}

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CSV_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Optional
    password_hash = db.Column(db.String(200), nullable=True)  # Optional
    language = db.Column(db.String(5), default='en')  # 'en' or 'ro'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trial_end_date = db.Column(db.DateTime, nullable=True)
    is_paid = db.Column(db.Boolean, default=False)
    current_quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=True)
    locked_home_page = db.Column(db.Text, nullable=True)  # JSON string for home page navigation state
    quiz_progress = db.relationship('QuizProgress', backref='user', lazy=True)
    
    def set_password(self, password):
        if password:
            self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False
    
    def has_password(self):
        """Check if user has set a password"""
        return self.password_hash is not None
    
    def has_access(self):
        """Check if user has access (trial or paid)"""
        if self.is_paid:
            return True
        if self.trial_end_date and datetime.utcnow() < self.trial_end_date:
            return True
        return False
    
    def get_trial_days_left(self):
        """Get number of trial days remaining"""
        if self.trial_end_date:
            days_left = (self.trial_end_date - datetime.utcnow()).days
            return max(0, days_left)
        return 0

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    difficulty = db.Column(db.String(50), nullable=True)  # Easy, Medium, Hard
    is_beta = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=True)
    option_d = db.Column(db.Text, nullable=True)
    option_e = db.Column(db.Text, nullable=True)
    correct_answers = db.Column(db.String(50), nullable=False)  # e.g., "A" or "A,B,C"
    order_num = db.Column(db.Integer, default=0)

class QuizProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    quiz_ref = db.relationship('Quiz', backref='progress', lazy=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    """Landing page - show landing or redirect to main menu if logged in"""
    if current_user.is_authenticated:
        return redirect(url_for('main_menu'))
    return render_template('index.html')

@app.route('/onboarding')
def onboarding():
    """Onboarding flow - shown before registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main_menu'))
    return render_template('onboarding.html')

@app.route('/check_phone', methods=['POST'])
def check_phone():
    """Check if phone number exists and return account status"""
    phone_number = request.json.get('phone_number')
    
    user = User.query.filter_by(phone_number=phone_number).first()
    
    if not user:
        return jsonify({'exists': False, 'message': 'No account found with this phone number'})
    
    return jsonify({
        'exists': True,
        'has_password': user.has_password(),
        'name': user.name
    })

@app.route('/send_otp', methods=['POST'])
def send_otp():
    """Send OTP to phone number for login (placeholder - always returns success)"""
    phone_number = request.json.get('phone_number')
    
    # Verify phone exists
    user = User.query.filter_by(phone_number=phone_number).first()
    if not user:
        return jsonify({'success': False, 'message': 'Phone number not registered'})
    
    # For now, we just store the phone in session
    # In production, this would send actual SMS
    session['otp_phone'] = phone_number
    session['otp_code'] = '1111'  # Always 1111 for testing
    
    return jsonify({'success': True, 'message': 'OTP sent successfully'})

@app.route('/send_registration_otp', methods=['POST'])
def send_registration_otp():
    """Send OTP for registration (placeholder - always returns success)"""
    phone_number = request.json.get('phone_number')
    
    # For registration, we don't check if user exists
    # In production, this would send actual SMS
    session['otp_phone'] = phone_number
    session['otp_code'] = '1111'  # Always 1111 for testing
    
    return jsonify({'success': True, 'message': 'OTP sent successfully'})

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    """Verify OTP code"""
    otp_code = request.json.get('otp_code')
    phone_number = request.json.get('phone_number')
    
    # Check if OTP matches (always 1111 for now)
    if otp_code == '1111' and phone_number == session.get('otp_phone'):
        session['otp_verified'] = True
        return jsonify({'success': True, 'message': 'OTP verified successfully'})
    else:
        return jsonify({'success': False, 'message': 'Invalid OTP code'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration with phone + OTP + optional password"""
    if current_user.is_authenticated:
        return redirect(url_for('main_menu'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')  # Optional
        password = request.form.get('password')  # Optional
        confirm_password = request.form.get('confirm_password')
        language = request.form.get('language', 'en')
        otp_verified = session.get('otp_verified', False)
        
        # Validation
        if not name or not phone_number:
            flash('Name and phone number are required', 'error')
            return render_template('register.html')
        
        if not otp_verified:
            flash('Please verify your phone number with OTP', 'error')
            return render_template('register.html')
        
        # If password is provided, validate it
        if password:
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('register.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters', 'error')
                return render_template('register.html')
        
        # Check if phone number exists
        if User.query.filter_by(phone_number=phone_number).first():
            flash('Phone number already registered', 'error')
            return render_template('register.html')
        
        # Check if email exists (if provided)
        if email and User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user with 3-day trial
        user = User(
            name=name,
            phone_number=phone_number,
            email=email if email else None,
            language=language,
            trial_end_date=datetime.utcnow() + timedelta(days=3)
        )
        
        # Set password if provided
        if password:
            user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Clear OTP session
        session.pop('otp_verified', None)
        session.pop('otp_phone', None)
        session.pop('otp_code', None)
        
        login_user(user)
        flash('Registration successful! You have a 3-day free trial.', 'success')
        return redirect(url_for('main_menu'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login with phone + OTP or phone + password"""
    if current_user.is_authenticated:
        return redirect(url_for('main_menu'))
    
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        login_method = request.form.get('login_method', 'otp')  # 'otp' or 'password'
        
        user = User.query.filter_by(phone_number=phone_number).first()
        
        if not user:
            flash('Phone number not registered', 'error')
            return render_template('login.html')
        
        if login_method == 'otp':
            # OTP login (OTP should be verified before form submission)
            otp_verified = session.get('otp_verified', False)
            if otp_verified:
                login_user(user)
                session.pop('otp_verified', None)
                session.pop('otp_phone', None)
                session.pop('otp_code', None)
                flash('Login successful!', 'success')
                return redirect(url_for('main_menu'))
            else:
                flash('Please verify OTP first', 'error')
        else:
            # Password login
            password = request.form.get('password')
            if user.has_password() and user.check_password(password):
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('main_menu'))
            else:
                flash('Invalid password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/main_menu')
@login_required
def main_menu():
    """Main menu - display available quizzes"""
    if not current_user.has_access():
        return redirect(url_for('payment'))
    
    quizzes = Quiz.query.filter_by(is_beta=False).all()
    
    # Get user's progress for each quiz
    quiz_data = []
    for quiz in quizzes:
        # Calculate progress percentage
        total_questions = len(quiz.questions)
        completed_progress = QuizProgress.query.filter_by(
            user_id=current_user.id,
            quiz_id=quiz.id
        ).all()
        
        # Calculate percentage based on completed quizzes
        if completed_progress:
            # Get the best score
            best_score = max([p.score for p in completed_progress])
            progress_percentage = int((best_score / total_questions) * 100) if total_questions > 0 else 0
        else:
            progress_percentage = 0
        
        last_progress = QuizProgress.query.filter_by(
            user_id=current_user.id,
            quiz_id=quiz.id
        ).order_by(QuizProgress.completed_at.desc()).first()
        
        quiz_info = {
            'id': quiz.id,
            'title': quiz.title,
            'description': quiz.description,
            'category': quiz.category,
            'difficulty': quiz.difficulty,  # Keep for reference but won't show
            'question_count': total_questions,
            'progress_percentage': progress_percentage,
            'last_score': last_progress.score if last_progress else None,
            'last_total': last_progress.total_questions if last_progress else None
        }
        quiz_data.append(quiz_info)
    
    return render_template('main_menu.html', 
                         quizzes=quiz_data,
                         trial_days_left=current_user.get_trial_days_left(),
                         is_paid=current_user.is_paid,
                         locked_home_page=current_user.locked_home_page)

@app.route('/set_home_page', methods=['POST'])
@login_required
def set_home_page():
    """Save the current page as user's home page"""
    try:
        data = request.get_json()
        # Store the navigation state as JSON string
        current_user.locked_home_page = json.dumps(data)
        db.session.commit()
        return jsonify({'success': True, 'message': 'This page has been set as your Home.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_home_page', methods=['GET'])
@login_required
def get_home_page():
    """Get user's saved home page"""
    if current_user.locked_home_page:
        try:
            home_page_data = json.loads(current_user.locked_home_page)
            return jsonify({'success': True, 'data': home_page_data})
        except:
            return jsonify({'success': False, 'data': None})
    return jsonify({'success': False, 'data': None})

@app.route('/remove_home_page', methods=['POST'])
@login_required
def remove_home_page():
    """Remove user's saved home page"""
    try:
        current_user.locked_home_page = None
        db.session.commit()
        return jsonify({'success': True, 'message': 'Home page removed.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    # Get user's quiz history
    progress_records = QuizProgress.query.filter_by(user_id=current_user.id).order_by(QuizProgress.completed_at.desc()).limit(10).all()
    
    return render_template('profile.html',
                         user=current_user,
                         progress_records=progress_records,
                         trial_days_left=current_user.get_trial_days_left())

@app.route('/progress')
@login_required
def progress():
    """User progress page"""
    # Get current quiz
    current_quiz = None
    if current_user.current_quiz_id:
        current_quiz = Quiz.query.get(current_user.current_quiz_id)
    
    # Get all quizzes (non-beta)
    all_quizzes = Quiz.query.filter_by(is_beta=False).all()
    total_quizzes = len(all_quizzes)
    
    # Get user's progress for each quiz
    completed_quizzes = QuizProgress.query.filter_by(user_id=current_user.id).count()
    
    # Calculate overall progress
    progress_percentage = (completed_quizzes / total_quizzes * 100) if total_quizzes > 0 else 0
    
    # Get all progress records (not just 5)
    recent_progress = QuizProgress.query.filter_by(user_id=current_user.id).order_by(QuizProgress.completed_at.desc()).all()
    
    return render_template('progress.html',
                         current_quiz=current_quiz,
                         completed_quizzes=completed_quizzes,
                         total_quizzes=total_quizzes,
                         progress_percentage=progress_percentage,
                         recent_progress=recent_progress,
                         all_quizzes=all_quizzes)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Settings page"""
    if request.method == 'POST':
        # Update settings
        new_email = request.form.get('email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        new_language = request.form.get('language')
        
        if new_email != current_user.email:
            # Check if email is already taken (if it's not empty)
            if new_email:
                existing_user = User.query.filter_by(email=new_email).first()
                if existing_user and existing_user.id != current_user.id:
                    flash('Email already in use', 'error')
                else:
                    current_user.email = new_email
                    db.session.commit()
                    flash('Email updated successfully', 'success')
            else:
                # Allow removing email
                current_user.email = None
                db.session.commit()
                flash('Email removed', 'success')
        
        if new_language and new_language != current_user.language:
            current_user.language = new_language
            db.session.commit()
            flash('Language updated successfully', 'success')
        
        if new_password:
            if new_password != confirm_password:
                flash('Passwords do not match', 'error')
            elif len(new_password) < 6:
                flash('Password must be at least 6 characters', 'error')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                if current_user.has_password():
                    flash('Password updated successfully', 'success')
                else:
                    flash('Password added successfully', 'success')
        
        return redirect(url_for('settings'))
    
    # Get feedback delay from session
    feedback_delay = session.get('feedback_delay', 2)
    
    return render_template('settings.html', 
                         feedback_delay=feedback_delay,
                         has_password=current_user.has_password())

@app.route('/set_delay', methods=['POST'])
@login_required
def set_delay():
    """Set the feedback delay setting"""
    data = request.json
    delay = data.get('delay', 2)
    
    try:
        delay = int(delay)
        if delay < 1 or delay > 10:
            return jsonify({'error': 'Delay must be between 1 and 10 seconds'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid delay value'}), 400
    
    session['feedback_delay'] = delay
    return jsonify({'success': True, 'delay': delay})

@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    """Payment page (placeholder)"""
    if request.method == 'POST':
        # Placeholder payment processing
        card_number = request.form.get('card_number')
        card_name = request.form.get('card_name')
        card_expiry = request.form.get('card_expiry')
        card_cvv = request.form.get('card_cvv')
        
        # Basic validation (placeholder)
        if card_number and card_name and card_expiry and card_cvv:
            # Mark user as paid
            current_user.is_paid = True
            db.session.commit()
            
            flash('Payment successful! You now have full access.', 'success')
            return redirect(url_for('main_menu'))
    
    return render_template('payment.html',
                         trial_days_left=current_user.get_trial_days_left(),
                         has_access=current_user.has_access())

@app.route('/quiz_details/<int:quiz_id>')
@login_required
def quiz_details(quiz_id):
    """Get quiz details for the settings modal"""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Count question types - check for comma in correct_answers (properly trimmed)
    single_answer_count = 0
    multiple_answer_count = 0
    
    for question in quiz.questions:
        # Clean the correct_answers string and check for multiple answers
        correct_ans = str(question.correct_answers).strip()
        if ',' in correct_ans:
            multiple_answer_count += 1
    else:
            single_answer_count += 1
    
    return jsonify({
        'id': quiz.id,
        'title': quiz.title,
        'description': quiz.description,
        'total_questions': len(quiz.questions),
        'single_answer_count': single_answer_count,
        'multiple_answer_count': multiple_answer_count
    })

@app.route('/quiz/<int:quiz_id>')
@login_required
def quiz_page(quiz_id):
    """Display quiz page"""
    if not current_user.has_access():
        return redirect(url_for('payment'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Get feedback delay from session
    feedback_delay = session.get('feedback_delay', 2)
    
    return render_template('quiz.html',
                         quiz=quiz,
                         feedback_delay=feedback_delay)

@app.route('/get_quiz_data/<int:quiz_id>')
@login_required
def get_quiz_data(quiz_id):
    """Get quiz questions for a specific quiz"""
    if not current_user.has_access():
        return jsonify({'error': 'Access denied'}), 403
    
    # Get question filter type from query parameter
    question_filter = request.args.get('filter', 'all')  # all, single, multiple
    
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order_num).all()
    
    # Filter questions based on type
    if question_filter == 'single':
        questions = [q for q in questions if ',' not in str(q.correct_answers).strip()]
    elif question_filter == 'multiple':
        questions = [q for q in questions if ',' in str(q.correct_answers).strip()]
    # else: 'all' - no filtering
    
    quiz_data = []
    for q in questions:
        options_list = []
        for i, letter in enumerate(['A', 'B', 'C', 'D', 'E']):
            option_text = getattr(q, f'option_{letter.lower()}', None)
            if option_text:
                options_list.append({
                    'letter': letter,
                    'text': option_text
                })
        
        correct_answers = q.correct_answers.split(',') if ',' in q.correct_answers else [q.correct_answers]
        
        quiz_data.append({
            'id': q.id,
            'question': q.question_text,
            'options': options_list,
            'correct_answers': correct_answers
        })
    
    # Shuffle questions
    random.shuffle(quiz_data)
    
    return jsonify(quiz_data)

@app.route('/submit_quiz', methods=['POST'])
@login_required
def submit_quiz():
    """Submit quiz results"""
    data = request.json
    quiz_id = data.get('quiz_id')
    score = data.get('score')
    total = data.get('total')
    
    if not quiz_id or score is None or total is None:
        return jsonify({'error': 'Invalid data'}), 400
    
    # Save progress
    progress = QuizProgress(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=score,
        total_questions=total
    )
    db.session.add(progress)
    db.session.commit()
    
    return jsonify({'success': True})

def import_all_quizzes():
    """
    Comprehensive import of all quiz data from CSV files.
    This function:
    - Finds all CSV files in csv_files folder (including subfolders)
    - Maps each CSV to the appropriate quiz topic
    - Deletes old questions and imports new ones
    - Reports import status
    """
    
    # Mapping of CSV filenames (without extension) to quiz information
    quiz_mapping = {
        # Main subjects
        'Nephrology': {
            'title': 'Nephrology',
            'description': 'Medical nephrology exam questions',
            'category': 'Final Exam - English'
        },
        'Cardiologie': {
            'title': 'Cardiology',
            'description': 'Medical cardiology exam questions',
            'category': 'Final Exam - English'
        },
        'Gastrologie': {
            'title': 'Gastroenterology',
            'description': 'Medical gastroenterology exam questions',
            'category': 'Final Exam - English'
        },
        'Obstetrics': {
            'title': 'Obstetrics',
            'description': 'Medical obstetrics exam questions',
            'category': 'Final Exam - English'
        },
        'Pneumologie Alergologie': {
            'title': 'Pneumology & Allergology',
            'description': 'Medical pneumology and allergology exam questions',
            'category': 'Final Exam - English'
        },
        'Reumatologie': {
            'title': 'Rheumatology',
            'description': 'Medical rheumatology exam questions',
            'category': 'Final Exam - English'
        },
        'Surgery 1': {
            'title': 'Surgery I',
            'description': 'Medical surgery exam questions - Part 1',
            'category': 'Final Exam - English'
        },
        'Surgery 2': {
            'title': 'Surgery II',
            'description': 'Medical surgery exam questions - Part 2',
            'category': 'Final Exam - English'
        },
        
        # Pediatrics subtopics
        'Acute pneumonia': {
            'title': 'Acute Pneumonia',
            'description': 'Pediatric acute pneumonia questions',
            'category': 'Pediatrics'
        },
        'Acute repiratory infections': {
            'title': 'Acute Respiratory Infections',
            'description': 'Pediatric acute respiratory infections questions',
            'category': 'Pediatrics'
        },
        'Acute rheumatic fever': {
            'title': 'Acute Rheumatic Fever',
            'description': 'Pediatric acute rheumatic fever questions',
            'category': 'Pediatrics'
        },
        'Bronchial asthma': {
            'title': 'Bronchial Asthma',
            'description': 'Pediatric bronchial asthma questions',
            'category': 'Pediatrics'
        },
        'Bronchitis': {
            'title': 'Bronchitis',
            'description': 'Pediatric bronchitis questions',
            'category': 'Pediatrics'
        },
        'Cardiomyopathies': {
            'title': 'Cardiomyopathies',
            'description': 'Pediatric cardiomyopathies questions',
            'category': 'Pediatrics'
        },
        'Child growth and development': {
            'title': 'Child Growth and Development',
            'description': 'Child growth and development questions',
            'category': 'Pediatrics'
        },
        'Chronic lung disease': {
            'title': 'Chronic Lung Disease',
            'description': 'Pediatric chronic lung disease questions',
            'category': 'Pediatrics'
        },
        'Coagulation disorders': {
            'title': 'Coagulation Disorders',
            'description': 'Pediatric coagulation disorders questions',
            'category': 'Pediatrics'
        },
        'Colagenosis in child': {
            'title': 'Collagenosis in Children',
            'description': 'Pediatric collagenosis questions',
            'category': 'Pediatrics'
        },
        'Congenetal heart diseases': {
            'title': 'Congenital Heart Diseases',
            'description': 'Pediatric congenital heart diseases questions',
            'category': 'Pediatrics'
        },
        'Iron deficiency anemia': {
            'title': 'Iron Deficiency Anemia',
            'description': 'Pediatric iron deficiency anemia questions',
            'category': 'Pediatrics'
        },
        'Malabsorbtion': {
            'title': 'Malabsorption',
            'description': 'Pediatric malabsorption questions',
            'category': 'Pediatrics'
        },
        'Malnutriia': {
            'title': 'Malnutrition',
            'description': 'Pediatric malnutrition questions',
            'category': 'Pediatrics'
        },
        'Neonatology': {
            'title': 'Neonatology',
            'description': 'Neonatology questions',
            'category': 'Pediatrics'
        },
        'Rickets': {
            'title': 'Rickets',
            'description': 'Pediatric rickets questions',
            'category': 'Pediatrics'
        }
    }
    
    # Find all CSV files recursively
    csv_files = []
    for root, dirs, files in os.walk('csv_files'):
        for file in files:
            if file.endswith('.csv'):
                csv_path = os.path.join(root, file)
                csv_files.append(csv_path)
    
    print(f"\n{'='*60}")
    print(f"Found {len(csv_files)} CSV files to import")
    print(f"{'='*60}\n")
    
    import_stats = {
        'success': 0,
        'failed': 0,
        'total_questions': 0,
        'details': []
    }
    
    # Import each CSV file
    for csv_path in sorted(csv_files):
        # Get filename without extension
        filename = os.path.splitext(os.path.basename(csv_path))[0]
        
        # Skip non-quiz files
        if filename in ['PROCESSING_COMPLETE', 'Nephrology_ENG_Examen_de_Stat']:
            continue
        
        # Get quiz info from mapping
        quiz_info = quiz_mapping.get(filename)
        
        if not quiz_info:
            print(f"WARNING: Skipping {filename} - no mapping found")
            import_stats['failed'] += 1
            continue
        
        try:
            # Find or create quiz
            quiz = Quiz.query.filter_by(title=quiz_info['title']).first()
            
            if quiz:
                # Delete old questions
                Question.query.filter_by(quiz_id=quiz.id).delete()
                print(f"UPDATING: {quiz_info['title']}")
            else:
                # Create new quiz
                quiz = Quiz(
                    title=quiz_info['title'],
                    description=quiz_info['description'],
                    category=quiz_info['category'],
                    difficulty='Advanced'
                )
                db.session.add(quiz)
                db.session.flush()
                print(f"CREATING: {quiz_info['title']}")
            
            # Import questions from CSV
            questions_imported = 0
            with open(csv_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)
                for i, row in enumerate(csv_reader):
                    question = Question(
                        quiz_id=quiz.id,
                        order_num=i,
                        question_text=row['question'].strip(),
                        option_a=row['option_a'].strip(),
                        option_b=row['option_b'].strip(),
                        option_c=row['option_c'].strip() if row.get('option_c') and row['option_c'].strip() else None,
                        option_d=row['option_d'].strip() if row.get('option_d') and row['option_d'].strip() else None,
                        option_e=row['option_e'].strip() if row.get('option_e') and row['option_e'].strip() else None,
                        correct_answers=row['correct_answers'].strip()
                    )
                    db.session.add(question)
                    questions_imported += 1
            
            db.session.commit()
            
            print(f"   SUCCESS: Imported {questions_imported} questions")
            import_stats['success'] += 1
            import_stats['total_questions'] += questions_imported
            import_stats['details'].append({
                'title': quiz_info['title'],
                'questions': questions_imported,
                'category': quiz_info['category']
            })
            
        except Exception as e:
            print(f"   ERROR: {str(e)}")
            import_stats['failed'] += 1
            db.session.rollback()
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"IMPORT SUMMARY")
    print(f"{'='*60}")
    print(f"Successfully imported: {import_stats['success']} quizzes")
    print(f"Failed: {import_stats['failed']} quizzes")
    print(f"Total questions: {import_stats['total_questions']}")
    print(f"\nDetailed breakdown:")
    
    # Group by category
    by_category = {}
    for detail in import_stats['details']:
        cat = detail['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(detail)
    
    for category, quizzes in by_category.items():
        print(f"\n  {category}:")
        for quiz in quizzes:
            print(f"    • {quiz['title']}: {quiz['questions']} questions")
    
    print(f"\n{'='*60}\n")
    
    return import_stats

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        import_all_quizzes()
    
    app.run(debug=True)
