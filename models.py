from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import json  # Add this missing import

db = SQLAlchemy()

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