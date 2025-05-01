from flask import render_template
from models import Exam, BlogPost
from routes import main_bp

@main_bp.route('/')
def index():
    """Landing page with introduction and CTA"""
    return render_template('index.html')

@main_bp.route('/shop')
def shop():
    """Shop page listing all available exams"""
    exams = Exam.query.all()
    return render_template('shop.html', exams=exams)

@main_bp.route('/about')
def about():
    """About page with psychologist information and blog posts"""
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('about.html', posts=posts)

@main_bp.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404