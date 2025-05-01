import os
import json
import secrets
import tempfile
import smtplib
import requests
from datetime import datetime
from email.message import EmailMessage
from flask import render_template, request, redirect, url_for, flash, abort, jsonify
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from dotenv import load_dotenv
load_dotenv()

from models import db, Exam, Purchase
from routes import payment_bp

# Email configuration
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
# Check if email credentials are properly configured
EMAIL_ENABLED = bool(EMAIL_ADDRESS and EMAIL_PASSWORD)

# PayMongo API configuration
PAYMONGO_PUBLIC_KEY = os.getenv('PAYMONGO_PUBLIC_KEY')
PAYMONGO_SECRET_KEY = os.getenv('PAYMONGO_SECRET_KEY')
PAYMONGO_API_URL = 'https://api.paymongo.com/v1'

@payment_bp.route('/buy/<int:exam_id>', methods=['GET', 'POST'])
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
            payment_status='pending'
        )
        db.session.add(purchase)
        db.session.commit()
        
        # Redirect to the payment options page
        return redirect(url_for('payment.checkout', purchase_id=purchase.id))
    
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

@payment_bp.route('/checkout/<int:purchase_id>')
def checkout(purchase_id):
    """Show payment options page"""
    purchase = Purchase.query.get_or_404(purchase_id)
    exam = purchase.exam
    
    # Calculate amount in cents (PayMongo requires amounts in cents)
    amount_cents = int(exam.price * 100)
    
    # Pass Flask's debug mode as a template variable
    debug_mode = app.debug if 'app' in globals() else False
    
    return render_template('checkout.html', 
                          purchase=purchase,
                          exam=exam,
                          amount_cents=amount_cents,
                          public_key=PAYMONGO_PUBLIC_KEY,
                          debug=debug_mode)

@payment_bp.route('/create-payment-intent/<int:purchase_id>', methods=['POST'])
def create_payment_intent(purchase_id):
    """Create a payment intent for card payments"""
    purchase = Purchase.query.get_or_404(purchase_id)
    exam = purchase.exam

    # Check and log price
    print("Exam price:", exam.price)

    # Calculate amount in cents
    try:
        amount_cents = int(exam.price * 100)
        print("Amount in cents:", amount_cents)
    except Exception as e:
        print("Error calculating amount:", e)
        return jsonify({'error': 'Invalid exam price'}), 400

    # Ensure PayMongo secret is set
    if not PAYMONGO_SECRET_KEY:
        print("Missing PAYMONGO_SECRET_KEY")
        return jsonify({'error': 'Payment configuration error'}), 500

    # Base64 encode the secret key
    import base64
    encoded_key = base64.b64encode(PAYMONGO_SECRET_KEY.encode()).decode()
    print("Encoded Auth Key:", encoded_key[:10] + "…")  # only show first few chars

    headers = {
        'Authorization': f'Basic {encoded_key}',
        'Content-Type': 'application/json'
    }

    data = {
        'data': {
            'attributes': {
                'amount': amount_cents,
                'payment_method_allowed': ['card', 'gcash', 'grab_pay', 'paymaya'],
                'payment_method_options': {
                    'card': {'request_three_d_secure': 'any'}
                },
                'currency': 'PHP',
                'description': f'Payment for {exam.title}',
                'statement_descriptor': 'EXAM PORTAL',
            }
        }
    }

    print("Sending request to PayMongo with data:")
    print(json.dumps(data, indent=2))

    response = requests.post(
        f'{PAYMONGO_API_URL}/payment_intents',
        headers=headers,
        json=data
    )

    print("PayMongo Response Code:", response.status_code)
    print("PayMongo Response Body:", response.text)

    if response.status_code == 200:
        payment_intent = response.json()['data']

        # Update purchase with payment ID
        purchase.payment_id = payment_intent['id']
        db.session.commit()

        return jsonify(payment_intent)
    else:
        return jsonify({'error': 'Failed to create payment intent'}), 400

@payment_bp.route('/create-source/<int:purchase_id>', methods=['POST'])
def create_source(purchase_id):
    """Create a payment source for e-wallets (GCash, Maya)"""
    purchase = Purchase.query.get_or_404(purchase_id)
    exam = purchase.exam
    
    # Calculate amount in cents
    amount_cents = int(exam.price * 100)
    
    # Get payment type from form
    payment_type = request.form.get('type', 'gcash')  # Default to GCash
    redirect_url = url_for('payment.success', purchase_id=purchase.id, _external=True)
    
    # Create source via PayMongo API
    headers = {
        'Authorization': f'Basic {PAYMONGO_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'data': {
            'attributes': {
                'amount': amount_cents,
                'currency': 'PHP',
                'redirect': {
                    'success': redirect_url,
                    'failed': url_for('payment.failed', purchase_id=purchase.id, _external=True)
                },
                'type': payment_type,  # 'gcash' or 'grab_pay' or 'paymaya'
                'billing': {
                    'email': purchase.email,
                    'name': f'Customer {purchase.id}'
                }
            }
        }
    }
    
    response = requests.post(
        f'{PAYMONGO_API_URL}/sources',
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        source = response.json()['data']
        
        # Update purchase with source ID
        purchase.payment_id = source['id']
        db.session.commit()
        
        # Redirect to checkout URL
        checkout_url = source['attributes']['redirect']['checkout_url']
        return redirect(checkout_url)
    else:
        flash('Failed to create payment source. Please try again.', 'danger')
        return redirect(url_for('payment.checkout', purchase_id=purchase.id))

@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle PayMongo webhook events"""
    # Verify webhook signature (in production)
    # payload = request.data
    # signature = request.headers.get('Signature')
    
    data = request.get_json()
    event_type = data.get('type')
    
    if event_type == 'source.chargeable':
        # Process the source payment
        source_id = data['data']['id']
        
        # Find the purchase by payment_id
        purchase = Purchase.query.filter_by(payment_id=source_id).first()
        
        if purchase:
            # Create a payment using the source
            headers = {
                'Authorization': f'Basic {PAYMONGO_SECRET_KEY}',
                'Content-Type': 'application/json'
            }
            
            payment_data = {
                'data': {
                    'attributes': {
                        'amount': int(purchase.exam.price * 100),
                        'currency': 'PHP',
                        'description': f'Payment for {purchase.exam.title}',
                        'statement_descriptor': 'EXAM PORTAL',
                        'source': {
                            'id': source_id,
                            'type': 'source'
                        }
                    }
                }
            }
            
            response = requests.post(
                f'{PAYMONGO_API_URL}/payments',
                headers=headers,
                json=payment_data
            )
            
            if response.status_code == 200:
                payment = response.json()['data']
                status = payment['attributes']['status']
                
                if status == 'paid':
                    purchase.payment_status = 'paid'
                    db.session.commit()
                    
                    # Send email with exam access link
                    send_exam_email(purchase)
    
    elif event_type == 'payment_intent.payment_method_attached':
        # Handle credit card payment success
        payment_intent_id = data['data']['id']
        purchase = Purchase.query.filter_by(payment_id=payment_intent_id).first()
        
        if purchase:
            purchase.payment_status = 'paid'
            db.session.commit()
            
            # Send email with exam access link
            send_exam_email(purchase)
    
    return jsonify({'status': 'success'}), 200

@payment_bp.route('/process/<int:purchase_id>', methods=['POST'])
def process_payment(purchase_id):
    """Process manual payment (for development/testing only)"""
    purchase = Purchase.query.get_or_404(purchase_id)
    
    # In a real implementation, this would validate the card data with PayMongo
    # For development purposes, we'll just mark the payment as successful
    purchase.payment_status = 'paid'
    db.session.commit()
    
    # Send email with exam access link
    email_sent = send_exam_email(purchase)
    if not email_sent and EMAIL_ENABLED:
        flash('Payment successful but there was an issue sending the confirmation email. You can still access your exam.', 'warning')
    
    return redirect(url_for('payment.success', purchase_id=purchase_id))

@payment_bp.route('/success/<int:purchase_id>')
def success(purchase_id):
    """Handle successful payment"""
    purchase = Purchase.query.get_or_404(purchase_id)
    # Simulate successful payment (FOR TESTING ONLY)
    if purchase.payment_status != 'paid':
        purchase.payment_status = 'paid'
        db.session.commit()
        print(f"Purchase {purchase.id} marked as PAID (test mode)")

    # Send email with exam access link if not already sent
    email_sent = send_exam_email(purchase)
    if not email_sent and EMAIL_ENABLED:
        flash('There was an issue sending the confirmation email. You can still access your exam.', 'warning')
    
    # Only update status if it's not already paid
    # if purchase.payment_status != 'paid':
    #     # For e-wallets, verify the payment status via API
    #     if purchase.payment_id and (purchase.payment_id.startswith('src_') or purchase.payment_id.startswith('pi_')):
    #         verify_payment_status(purchase)
    #     else:
    #         # Manual success page (for testing)
    #         purchase.payment_status = 'paid'
    #         db.session.commit()
        
    #     # Send email with exam access link if not already sent
    #     if purchase.payment_status == 'paid':
    #         email_sent = send_exam_email(purchase)
    #         if not email_sent and EMAIL_ENABLED:
    #             flash('There was an issue sending the confirmation email. You can still access your exam.', 'warning')
    
    return render_template('payment_success.html', 
                          access_token=purchase.access_token,
                          exam_title=purchase.exam.title)

@payment_bp.route('/failed/<int:purchase_id>')
def failed(purchase_id):
    """Handle failed payment"""
    purchase = Purchase.query.get_or_404(purchase_id)
    
    return render_template('payment_failed.html', 
                          purchase=purchase,
                          exam_title=purchase.exam.title)

@payment_bp.route('/exam/<token>', methods=['GET', 'POST'])
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
            print(f"Failed to parse answers JSON for purchase {purchase.id}")
    
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
                    print(f"Scoring rules parsing failed: {e}")

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
                    print(f"Scoring rules parsing failed: {e}")

            # Generate PDF and send result email
            pdf_path = generate_result_pdf(purchase, total_score, zone_label)
            send_result_email(purchase.email, exam.title, pdf_path)

            return redirect(url_for('payment.exam', token=token))
    
    # Log exam access for debugging
    print(f"Accessing exam {exam.id} ({exam.title}) with token {token[:5]}...")
    print(f"Exam type: {exam.exam_type}, Questions: {exam.questions is not None}")
    
    return render_template('exam.html', exam=exam, purchase=purchase, answers=answers)

# Helper Functions
def verify_payment_status(purchase):
    """Verify payment status via PayMongo API"""
    if not purchase.payment_id:
        return False
    
    headers = {
        'Authorization': f'Basic {PAYMONGO_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    
    # Check if it's a source or payment intent
    if purchase.payment_id.startswith('src_'):
        # For sources (GCash, Grab Pay, etc)
        response = requests.get(
            f'{PAYMONGO_API_URL}/sources/{purchase.payment_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            source = response.json()['data']
            status = source['attributes']['status']
            
            if status == 'chargeable' or status == 'paid':
                purchase.payment_status = 'paid'
                db.session.commit()
                return True
                
    elif purchase.payment_id.startswith('pi_'):
        # For payment intents (credit cards)
        response = requests.get(
            f'{PAYMONGO_API_URL}/payment_intents/{purchase.payment_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            payment_intent = response.json()['data']
            status = payment_intent['attributes']['status']
            
            if status == 'succeeded':
                purchase.payment_status = 'paid'
                db.session.commit()
                return True
    
    return False

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
        
        exam_link = url_for('payment.exam', token=purchase.access_token, _external=True)
        
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