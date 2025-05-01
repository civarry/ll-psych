import os
import secrets
import smtplib
import json
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import requests
import base64
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile
from datetime import datetime
import tempfile
from flask_migrate import Migrate

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///exams.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@app.template_filter('fromjson')
def fromjson_filter(json_string):
    """Filter to convert a JSON string back to a Python object"""
    if not json_string:
        return {}
    try:
        return json.loads(json_string)
    except:
        return {}

# PayMongo API configuration
PAYMONGO_PUBLIC_KEY = os.getenv('PAYMONGO_PUBLIC_KEY')
PAYMONGO_SECRET_KEY = os.getenv('PAYMONGO_SECRET_KEY') 
PAYMONGO_API_URL = "https://api.paymongo.com/v1"

# Email configuration
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
# Flag to check if email is properly configured
EMAIL_ENABLED = all([EMAIL_ADDRESS, EMAIL_PASSWORD])

# Admin credentials - in production store these securely or in database
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH', 
                              generate_password_hash('admin123'))  # Default password for dev only

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database Models
class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(20))  # 'content' or 'likert'
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    content = db.Column(db.Text, nullable=False)
    questions = db.Column(db.Text, nullable=True)  # Stored as JSON
    exam_type = db.Column(db.String(20), default='content')  # 'content' or 'likert'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scoring_rules = db.Column(db.Text, nullable=True)
    
    def get_questions(self):
        """Parse the JSON questions with scale support"""
        if not self.questions:
            return []
        try:
            questions = json.loads(self.questions)
            for q in questions:
                if 'scale' not in q:
                    q['scale'] = []  # fallback to empty if missing
            return questions
        except Exception:
            return []
class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    access_token = db.Column(db.String(100), unique=True, nullable=False)
    payment_id = db.Column(db.String(100), nullable=True)
    payment_status = db.Column(db.String(20), default='pending')
    answers = db.Column(db.Text, nullable=True)  # Store user answers as JSON
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    exam = db.relationship('Exam', backref=db.backref('purchases', lazy=True))

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Authentication decorator for admin routes
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in to access the admin area.', 'warning')
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    """Landing page with introduction and CTA"""
    return render_template('index.html')

@app.route('/shop')
def shop():
    """Shop page listing all available exams"""
    exams = Exam.query.all()
    return render_template('shop.html', exams=exams)

@app.route('/admin/blog')
@admin_required
def admin_blog():
    """Admin blog posts list"""
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog.html', posts=posts)

@app.route('/admin/blog/create', methods=['GET', 'POST'])
@admin_required
def admin_create_blog():
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
        return redirect(url_for('admin_blog'))
    
    return render_template('admin/create_blog.html')

@app.route('/admin/blog/edit/<int:post_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_blog(post_id):
    """Edit an existing blog post"""
    post = BlogPost.query.get_or_404(post_id)
    
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        
        db.session.commit()
        flash('Blog post updated successfully!', 'success')
        return redirect(url_for('admin_blog'))
    
    return render_template('admin/edit_blog.html', post=post)

@app.route('/admin/blog/delete/<int:post_id>', methods=['POST'])
@admin_required
def admin_delete_blog(post_id):
    """Delete a blog post"""
    post = BlogPost.query.get_or_404(post_id)
    
    db.session.delete(post)
    db.session.commit()
    flash('Blog post deleted successfully!', 'success')
    return redirect(url_for('admin_blog'))

@app.route('/about')
def about():
    """About page with psychologist information and blog posts"""
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('about.html', posts=posts)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            next_page = request.args.get('next')
            flash('You have been logged in successfully!', 'success')
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin_dashboard():
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

@app.route('/admin/exams')
@admin_required
def admin_exams():
    """Admin exams list"""
    exams = Exam.query.order_by(Exam.created_at.desc()).all()
    return render_template('admin/exams.html', exams=exams)

@app.route('/admin/exams/create', methods=['GET', 'POST'])
@admin_required
def admin_create_exam():
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
            return redirect(url_for('admin_create_exam'))

        # 🔹 Build questions list for likert type
        questions = []
        questions = []
        if exam_type == 'likert':
            try:
                questions_json = request.form.get('likert_questions_json')
                questions = json.loads(questions_json) if questions_json else []
            except Exception as e:
                flash('Failed to parse Likert questions.', 'danger')
                return redirect(url_for('admin_create_exam'))

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
            scoring_rules=json.dumps(scoring_rules) if scoring_rules else None,
            likert_scale=None  # Deprecated: now unused
        )

        db.session.add(new_exam)
        db.session.commit()

        flash('Exam created successfully!', 'success')
        return redirect(url_for('admin_exams'))

    return render_template('admin/create_exam.html')

@app.route('/admin/exams/edit/<int:exam_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_exam(exam_id):
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
        return redirect(url_for('admin_exams'))

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

@app.route('/admin/exams/delete/<int:exam_id>', methods=['POST'])
@admin_required
def admin_delete_exam(exam_id):
    """Delete an exam"""
    exam = Exam.query.get_or_404(exam_id)
    
    # Check if there are any purchases for this exam
    purchase_count = Purchase.query.filter_by(exam_id=exam_id).count()
    if purchase_count > 0:
        flash(f'Cannot delete exam: {purchase_count} customers have purchased it.', 'danger')
        return redirect(url_for('admin_exams'))
    
    # If no purchases, delete the exam
    db.session.delete(exam)
    db.session.commit()
    flash('Exam deleted successfully!', 'success')
    return redirect(url_for('admin_exams'))

@app.route('/admin/purchases')
@admin_required
def admin_purchases():
    """Admin purchases list"""
    purchases = Purchase.query.order_by(Purchase.purchased_at.desc()).all()
    return render_template('admin/purchases.html', purchases=purchases)

@app.route('/buy/<int:exam_id>', methods=['GET', 'POST'])
def buy(exam_id):
    """Purchase form for a specific exam"""
    exam = Exam.query.get_or_404(exam_id)
    
    if request.method == 'POST':
        email = request.form.get('email')
            
        # Generate a unique token for this purchase
        access_token = secrets.token_urlsafe(32)
        
        # Save purchase info in the database
        purchase = Purchase(
            exam_id=exam_id,
            email=email,
            access_token=access_token,
            payment_id="dev-test-payment",
            payment_status='pending'
        )
        db.session.add(purchase)
        db.session.commit()
        
        # Redirect to the simple payment form for development/testing
        return render_template('direct_payment.html', 
                              amount=exam.price,
                              purchase_id=purchase.id,
                              exam_title=exam.title,
                              exam=exam)
    if exam.questions:
        questions = json.loads(exam.questions)
        question_count = len(questions)
    else:
        question_count = 0

    test_type = exam.exam_type.title()
    
    return render_template('buy.html', 
                           exam=exam,
                           question_count=question_count,
                           test_type=test_type)

@app.route('/process_payment/<int:purchase_id>', methods=['POST'])
def process_payment(purchase_id):
    """Process payment manually (for development/testing only)"""
    purchase = Purchase.query.get_or_404(purchase_id)
    
    # In a real implementation, this would validate the card data with PayMongo
    # For development purposes, we'll just mark the payment as successful
    purchase.payment_status = 'paid'
    db.session.commit()
    
    # Send email with exam access link
    email_sent = send_exam_email(purchase)
    if not email_sent and EMAIL_ENABLED:
        flash('Payment successful but there was an issue sending the confirmation email. You can still access your exam.', 'warning')
    
    return redirect(url_for('payment_success', purchase_id=purchase_id))

@app.route('/payment/success/<int:purchase_id>')
def payment_success(purchase_id):
    """Handle successful payment"""
    purchase = Purchase.query.get_or_404(purchase_id)
    
    # Only update status if it's not already paid
    if purchase.payment_status != 'paid':
        purchase.payment_status = 'paid'
        db.session.commit()
        
        # Send email with exam access link if not already sent
        email_sent = send_exam_email(purchase)
        if not email_sent and EMAIL_ENABLED:
            flash('There was an issue sending the confirmation email. You can still access your exam.', 'warning')
    
    return render_template('payment_success.html', 
                          access_token=purchase.access_token,
                          exam_title=purchase.exam.title)

@app.route('/exam/<token>', methods=['GET', 'POST'])
def exam(token):
    """Access purchased exam content with token"""
    # Find the purchase record by token
    purchase = Purchase.query.filter_by(access_token=token).first_or_404()
    
    # Check if payment is verified
    if purchase.payment_status != 'paid':
        flash('Payment is required to access this exam.', 'danger')
        abort(403)  # Not authorized

    # Get the associated exam
    exam = purchase.exam
    if not exam:
        flash('The requested exam could not be found.', 'danger')
        abort(404)
    
    # Initialize answers if needed
    answers = {}
    if purchase.answers:
        try:
            answers = json.loads(purchase.answers)
        except json.JSONDecodeError:
            app.logger.error(f"Failed to parse answers JSON for purchase {purchase.id}")
    
    # Handle exam submission for Likert scale
    if request.method == 'POST' and exam.exam_type == 'likert':
        new_answers = {}
        for question in exam.get_questions():
            question_id = str(question['id'])
            if question_id in request.form:
                new_answers[question_id] = request.form.get(question_id)
        
        if new_answers:
            total_score = sum(int(v) for v in new_answers.values())
            purchase.answers = json.dumps(new_answers)

            flash(f'Your responses have been submitted successfully! Total Score: {total_score}', 'success')

            if exam.scoring_rules:
                try:
                    scoring = json.loads(exam.scoring_rules)
                    for zone in scoring.get("zones", []):
                        if zone["min"] <= total_score <= zone["max"]:
                            flash(zone["label"], 'info')
                            break
                except Exception as e:
                    app.logger.error(f"Scoring rules parsing failed: {e}")

            db.session.commit()

            # Determine zone label
            zone_label = "Uncategorized"
            if exam.scoring_rules:
                try:
                    scoring = json.loads(exam.scoring_rules)
                    for zone in scoring.get("zones", []):
                        if zone["min"] <= total_score <= zone["max"]:
                            zone_label = zone["label"]
                            break
                except Exception as e:
                    app.logger.error(f"Scoring rules parsing failed: {e}")

            # Generate PDF and send result email
            pdf_path = generate_result_pdf(purchase, total_score, zone_label)
            send_result_email(purchase.email, exam.title, pdf_path)

            return redirect(url_for('exam', token=token))

    
    # Log exam access for debugging
    app.logger.info(f"Accessing exam {exam.id} ({exam.title}) with token {token[:5]}...")
    app.logger.info(f"Exam type: {exam.exam_type}, Questions: {exam.questions is not None}")
    
    return render_template('exam.html', exam=exam, purchase=purchase, answers=answers)

# Helper Functions
def send_exam_email(purchase):
    """Send email with the exam access link"""
    # Check if email is configured
    if not EMAIL_ENABLED:
        print("Email is not configured. Skipping email send.")
        return False
        
    try:
        msg = EmailMessage()
        msg['Subject'] = f"Your Access to {purchase.exam.title}"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = purchase.email
        
        exam_link = url_for('exam', token=purchase.access_token, _external=True)
        
        # Email content
        content = f"""
        Hello,
        
        Thank you for purchasing {purchase.exam.title}!
        
        You can access your exam using the link below:
        {exam_link}
        
        Please note that this link is unique to you and should not be shared.
        
        Best regards,
        The Exam Portal Team
        """
        
        msg.set_content(content)
        
        # Send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            
        print(f"Email sent successfully to {purchase.email}")
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False
    
def send_result_email(to_email, exam_title, pdf_path):
    """Send the exam result PDF to the user"""
    if not EMAIL_ENABLED:
        print("Email not configured. Skipping result email.")
        return False

    try:
        msg = EmailMessage()
        msg['Subject'] = f"Your Result for {exam_title}"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email

        msg.set_content(
            f"""Hello,

Here is the result of your recent exam: {exam_title}.

Please see the attached PDF for your score and category.

We recommend setting up a follow-up call to discuss your results in more detail.

Best regards,
The Exam Portal Team"""
        )

        # Attach PDF
        with open(pdf_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename='exam_result.pdf')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)

        print(f"Result email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send result email: {e}")
        return False

# Create database tables
def init_db():
    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()
        
        try:
            # Add sample exams if database is empty
            if Exam.query.count() == 0:
                sample_exams = [
                    Exam(
                        title="Emotional Resilience Assessment",
                        description="Evaluate your ability to adapt to stress and bounce back from adversity using a validated psychological scale.",
                        price=499.00,
                        content="This assessment helps you understand your emotional coping mechanisms and adaptability.",
                        exam_type="likert",
                        questions=json.dumps([
                            {"id": 1, "text": "I stay calm under pressure."},
                            {"id": 2, "text": "I recover quickly from setbacks."},
                            {"id": 3, "text": "I find it easy to manage my emotions in challenging situations."}
                        ])
                    ),
                    Exam(
                        title="Cognitive Flexibility Inventory",
                        description="Assess your ability to shift perspectives and adapt to changing environments and situations.",
                        price=549.00,
                        content="This exam explores how you respond to new information, unexpected changes, and mental challenges.",
                        exam_type="likert",
                        questions=json.dumps([
                            {"id": 1, "text": "I can easily consider multiple options before making a decision."},
                            {"id": 2, "text": "I can view situations from different perspectives."},
                            {"id": 3, "text": "When faced with a new problem, I try to think about it in new ways."}
                        ])
                    ),
                    Exam(
                        title="Well-Being Self-Check",
                        description="Gain insights into your current emotional, social, and psychological well-being.",
                        price=399.00,
                        content="A reflective self-assessment to explore how you are doing across different areas of well-being.",
                        exam_type="likert",
                        questions=json.dumps([
                            {"id": 1, "text": "I feel a sense of purpose in my daily activities."},
                            {"id": 2, "text": "I have positive relationships with others."},
                            {"id": 3, "text": "I generally feel satisfied with my life."}
                        ])
                    )
                ]

                for exam in sample_exams:
                    db.session.add(exam)

                db.session.commit()
                print("Added sample exams to the database")
            else:
                print("Sample exams already exist. Skipping exam seeding.")

            # Add a sample blog post if none exist
            if BlogPost.query.count() == 0:
                sample_post = BlogPost(
                    title="Welcome to Our Blog",
                    content="This is our first blog post. Stay tuned for updates on our services and mental health tips."
                )
                db.session.add(sample_post)
                db.session.commit()
                print("Added sample blog post to the database")
            else:
                print("Blog posts already exist. Skipping blog seeding.")
                
        except Exception as e:
            print("Database initialization failed:", e)
            
def generate_result_pdf(purchase, total_score, zone_label):
    """Generates a professional PDF summary of the exam results and returns the file path."""
    exam = purchase.exam
    email = purchase.email
    exam_date = datetime.utcnow().strftime('%B %d, %Y')

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    c = canvas.Canvas(temp_file.name, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 60, "Assessment Report")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 90, f"Date: {exam_date}")
    c.drawString(50, height - 110, f"Participant Email: {email}")
    c.drawString(50, height - 130, f"Assessment Title: {exam.title}")

    # Divider
    c.line(50, height - 145, width - 50, height - 145)

    # Results section
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 170, "Results Summary")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 190, f"Total Score: {total_score}")
    c.drawString(50, height - 210, f"Interpreted Category: {zone_label}")

    # Recommendation
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 250, "Next Steps")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 270, "We encourage you to schedule a follow-up session to discuss your results in detail.")
    c.drawString(50, height - 285, "Our licensed professionals can help you better understand your scores and support your goals.")

    # Footer
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 40, "This assessment is for educational and self-reflective purposes only and does not constitute a diagnosis.")

    c.save()
    return temp_file.name

if __name__ == '__main__':
    # Check email configuration
    if not EMAIL_ENABLED:
        print("WARNING: Email functionality is disabled. Check your .env file for EMAIL_ADDRESS and EMAIL_PASSWORD")
    
    init_db()
    app.run(debug=False, host='0.0.0.0')