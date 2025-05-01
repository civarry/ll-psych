import os
from flask import request, session, flash, redirect, url_for, render_template
from functools import wraps
from routes import admin_bp
from models import BlogPost, Exam, Purchase, db
from werkzeug.security import check_password_hash, generate_password_hash
import json

# Admin credentials - in production store these securely or in database
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH', 
                              generate_password_hash('admin123'))  # Default password for dev only

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in to access the admin area.', 'warning')
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/blog')
@admin_required
def blog():
    """Admin blog posts list"""
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog.html', posts=posts)

@admin_bp.route('/blog/create', methods=['GET', 'POST'])
@admin_required
def create_blog():
    """Create a new blog post"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        # Check number of posts, limit to 5
        posts_count = BlogPost.query.count()
        if posts_count >= 5:
            # Find the oldest post and delete it
            oldest_post = BlogPost.query.order_by(BlogPost.created_at.asc()).first()
            if oldest_post:
                db.session.delete(oldest_post)
                flash('Oldest blog post was deleted to maintain the 5-post limit.', 'info')
        
        # Create the new blog post
        new_post = BlogPost(
            title=title,
            content=content
        )
        
        db.session.add(new_post)
        db.session.commit()
        
        flash('Blog post created successfully!', 'success')
        return redirect(url_for('admin.blog'))
    
    return render_template('admin/create_blog.html')

@admin_bp.route('/blog/edit/<int:post_id>', methods=['GET', 'POST'])
@admin_required
def edit_blog(post_id):
    """Edit an existing blog post"""
    post = BlogPost.query.get_or_404(post_id)
    
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        
        db.session.commit()
        flash('Blog post updated successfully!', 'success')
        return redirect(url_for('admin.blog'))
    
    return render_template('admin/edit_blog.html', post=post)

@admin_bp.route('/blog/delete/<int:post_id>', methods=['POST'])
@admin_required
def delete_blog(post_id):
    """Delete a blog post"""
    post = BlogPost.query.get_or_404(post_id)
    
    db.session.delete(post)
    db.session.commit()
    flash('Blog post deleted successfully!', 'success')
    return redirect(url_for('admin.blog'))

# Admin routes
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            next_page = request.args.get('next')
            flash('You have been logged in successfully!', 'success')
            return redirect(next_page or url_for('admin.dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard"""
    exams_count = Exam.query.count()
    purchases_count = Purchase.query.count()
    completed_purchases = Purchase.query.filter_by(payment_status='paid').count()
    recent_purchases = Purchase.query.order_by(Purchase.purchased_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                          exams_count=exams_count,
                          purchases_count=purchases_count,
                          completed_purchases=completed_purchases,
                          recent_purchases=recent_purchases)

@admin_bp.route('/exams')
@admin_required
def exams():
    """Admin exams list"""
    exams = Exam.query.order_by(Exam.created_at.desc()).all()
    return render_template('admin/exams.html', exams=exams)

@admin_bp.route('/exams/create', methods=['GET', 'POST'])
@admin_required
def create_exam():
    """Create a new exam"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        exam_type = request.form.get('exam_type')
        content = request.form.get('content', '')

        # 🔹 Get scoring_rules (optional JSON input)
        scoring_rules_raw = request.form.get('scoring_rules')
        try:
            scoring_rules = json.loads(scoring_rules_raw) if scoring_rules_raw else None
        except json.JSONDecodeError:
            flash('Invalid JSON in scoring rules.', 'danger')
            return redirect(url_for('admin.create_exam'))

        # 🔹 Build questions list for likert type
        questions = []
        if exam_type == 'likert':
            try:
                questions_json = request.form.get('likert_questions_json')
                questions = json.loads(questions_json) if questions_json else []
            except Exception as e:
                flash('Failed to parse Likert questions.', 'danger')
                return redirect(url_for('admin.create_exam'))

        # 🔹 Create the new Exam object with scoring_rules
        likert_scale = None
        if exam_type == 'likert':
            likert_values = request.form.getlist("likert_value")
            likert_labels = request.form.getlist("likert_label")
            likert_scale = json.dumps({v: l for v, l in zip(likert_values, likert_labels)})

        new_exam = Exam(
            title=title,
            description=description,
            price=price,
            content=content,
            exam_type=exam_type,
            questions=json.dumps(questions) if questions else None,
            scoring_rules=json.dumps(scoring_rules) if scoring_rules else None
        )

        db.session.add(new_exam)
        db.session.commit()

        flash('Exam created successfully!', 'success')
        return redirect(url_for('admin.exams'))

    return render_template('admin/create_exam.html')

@admin_bp.route('/exams/edit/<int:exam_id>', methods=['GET', 'POST'])
@admin_required
def edit_exam(exam_id):
    """Edit an existing exam"""
    exam = Exam.query.get_or_404(exam_id)

    if request.method == 'POST':
        exam.title = request.form.get('title')
        exam.description = request.form.get('description')
        exam.price = float(request.form.get('price'))
        exam.exam_type = request.form.get('exam_type')
        exam.content = request.form.get('content', '')

        if exam.exam_type == 'likert':
            # Process Likert scale questions
            try:
                questions_json = request.form.get('likert_questions_json')
                questions = json.loads(questions_json) if questions_json else []
                exam.questions = json.dumps(questions)
            except Exception:
                flash("Failed to parse Likert questions JSON.", "danger")
                return redirect(request.url)

            # Process scoring rules
            scoring_rules_raw = request.form.get("scoring_rules", "").strip()
            if scoring_rules_raw:
                try:
                    parsed = json.loads(scoring_rules_raw)
                    exam.scoring_rules = json.dumps(parsed)
                except json.JSONDecodeError:
                    flash("Invalid JSON format in scoring rules.", "danger")
                    return redirect(request.url)
            else:
                exam.scoring_rules = None
        else:
            # Clear Likert-specific fields if not a Likert exam
            exam.questions = None
            exam.scoring_rules = None

        db.session.commit()
        flash('Exam updated successfully!', 'success')
        return redirect(url_for('admin.exams'))

    # For GET request, populate form with existing data
    if exam.exam_type == 'likert':
        try:
            exam.scoring_rules = json.loads(exam.scoring_rules) if exam.scoring_rules else {}
        except json.JSONDecodeError:
            exam.scoring_rules = {}

        try:
            exam.questions = json.loads(exam.questions) if exam.questions else []
        except json.JSONDecodeError:
            exam.questions = []

    return render_template('admin/edit_exam.html', exam=exam)

@admin_bp.route('/exams/delete/<int:exam_id>', methods=['POST'])
@admin_required
def delete_exam(exam_id):
    """Delete an exam"""
    exam = Exam.query.get_or_404(exam_id)
    
    # Check if there are any purchases for this exam
    purchase_count = Purchase.query.filter_by(exam_id=exam_id).count()
    if purchase_count > 0:
        flash(f'Cannot delete exam: {purchase_count} customers have purchased it.', 'danger')
        return redirect(url_for('admin.exams'))
    
    # If no purchases, delete the exam
    db.session.delete(exam)
    db.session.commit()
    flash('Exam deleted successfully!', 'success')
    return redirect(url_for('admin.exams'))

@admin_bp.route('/purchases')
@admin_required
def purchases():
    """Admin purchases list"""
    purchases = Purchase.query.order_by(Purchase.purchased_at.desc()).all()
    return render_template('admin/purchases.html', purchases=purchases)