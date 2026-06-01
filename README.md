# ✂️ NE Clothiers — Premium Tailoring Measurement System

A professional tailoring management web app built with Streamlit, Supabase, and MediaPipe AI.

## Features

- **AI Body Scan** — Upload a photo and get estimated body measurements using MediaPipe pose detection
- **Measurement Management** — Record and store customer measurements with a clean, guided form
- **Order Tracking** — Customers can track their orders by Order ID, name, or phone number
- **Email Confirmations** — Automatic PDF receipt sent to customers on order creation
- **Admin Dashboard** — View stats, manage records, export CSV/Excel, generate PDF receipts
- **Supabase Backend** — Cloud database for reliable data storage

## Tech Stack

- [Streamlit](https://streamlit.io) — Web framework
- [Supabase](https://supabase.com) — PostgreSQL database + auth
- [MediaPipe](https://mediapipe.dev) — AI pose estimation
- [fpdf2](https://py-fpdf2.readthedocs.io) — PDF generation
- Python 3.11

## Setup

1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.streamlit/secrets.toml` with your credentials (see `.env` for required keys)
4. Run: `streamlit run app.py`

## Deployment

Deployed on [Streamlit Cloud](https://share.streamlit.io). Add secrets via the app's Settings → Secrets panel.

## Required Secrets

```toml
SUPABASE_URL = "..."
SUPABASE_KEY = "..."
ADMIN_USERNAME = "..."
ADMIN_PASSWORD = "..."
EMAIL_SENDER = "..."
EMAIL_PASSWORD = "..."
EMAIL_SMTP_HOST = "smtp.gmail.com"
EMAIL_SMTP_PORT = "465"
```
