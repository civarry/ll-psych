# ll-psych

A Flask-based storefront for selling and delivering psychometric assessments online. Visitors browse a shop of exams, pay for one, and get a unique access link to take it and receive a scored PDF report by email.

## How it works

- **Shop & landing pages** (`routes/main.py`): a home page, a shop listing all available exams (`Exam` records pulled from the database), and an about page with blog posts.
- **Checkout & payments** (`routes/payment.py`): integrates with [PayMongo](https://www.paymongo.com/) to accept cards, GCash, GrabPay, and Maya. A purchase creates a `Purchase` row with a unique `access_token`, and PayMongo webhooks (or a manual test-mode route) mark it as paid.
- **Taking the exam**: once paid, the buyer's access token unlocks the exam at `/exam/<token>`. Currently supported is a Likert-scale format — each answer is summed into a total score, which is mapped against exam-specific `scoring_rules` (JSON-defined min/max zones with labels) to produce an interpreted category.
- **Results delivery**: after submission, a PDF report (generated with `reportlab`) summarizing the score and interpreted zone is emailed to the buyer via Gmail SMTP, alongside the exam access email sent at purchase time.
- **Admin**: a separate blueprint (`routes/admin.py`) for managing exams and content.
- **Data models** (`models.py`): `Exam`, `Purchase`, and `BlogPost`, backed by SQLAlchemy — SQLite locally, Postgres in production (via `DATABASE_URL` on Render).

## Stack

Flask, Flask-SQLAlchemy, Flask-Migrate, PayMongo REST API, reportlab (PDF generation), smtplib (email), and either SQLite or PostgreSQL depending on environment.

## Configuration

Environment variables (loaded via `.env`):

- `SECRET_KEY` — Flask session secret
- `EMAIL_ADDRESS` / `EMAIL_PASSWORD` — Gmail SMTP credentials for sending access links and result PDFs
- `PAYMONGO_PUBLIC_KEY` / `PAYMONGO_SECRET_KEY` — PayMongo API credentials
- `DATABASE_URL` — Postgres connection string (used automatically when running on Render)

## Running locally

```bash
pip install -r requirements.txt
python app.py
```

On first run it seeds the database with a sample "Emotional Resilience Assessment" exam and a welcome blog post if none exist yet.
