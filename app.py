import os
import json
from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate

from models import db, Exam, BlogPost
from routes import register_blueprints

# Load environment variables
load_dotenv()

# Email configuration
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
# Check if email credentials are properly configured
EMAIL_ENABLED = bool(EMAIL_ADDRESS and EMAIL_PASSWORD)

app = Flask(__name__)
register_blueprints(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
if os.environ.get('RENDER'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exams.db'
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

db.init_app(app)
migrate = Migrate(app, db)

# Initialize the database before running the app
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

if __name__ == '__main__':
    # Check email configuration
    if not EMAIL_ENABLED:
        print("WARNING: Email functionality is disabled. Check your .env file for EMAIL_ADDRESS and EMAIL_PASSWORD")
    app.run(debug=False, host='0.0.0.0')