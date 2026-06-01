# ============================================================
# NE CLOTHIERS — Streamlit Web App
# ============================================================

import os
import io
import re
import uuid
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime, date

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── PAGE CONFIG ──────────────────────────────────────────────
st.set_page_config(
    page_title="NE Clothiers",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── THEME ────────────────────────────────────────────────────
PRIMARY   = "#2563EB"
PRIMARY_D = "#1D4ED8"
BG        = "#050E24"
SURFACE   = "#0D1F3C"
CARD      = "#112240"
CARD2     = "#162B4D"
ACCENT    = "#93C5FD"
GOLD      = "#F59E0B"
GREEN     = "#10B981"
RED       = "#EF4444"
TEXT      = "#E2E8F0"
MUTED     = "#64748B"

# ── CONFIG ───────────────────────────────────────────────────
IMAGE_FOLDER   = "customer_images"
RECEIPT_FOLDER = "receipts"
OUTFIT_FOLDER  = "outfit_images"

_WRITABLE           = "/tmp" if not os.access(os.path.dirname(os.path.abspath(__file__)), os.W_OK) else os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER_PATH   = os.path.join(_WRITABLE, IMAGE_FOLDER)
RECEIPT_FOLDER_PATH = os.path.join(_WRITABLE, RECEIPT_FOLDER)
os.makedirs(IMAGE_FOLDER_PATH,   exist_ok=True)
os.makedirs(RECEIPT_FOLDER_PATH, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OUTFIT_IMAGES = {
    "Agbada":  os.path.join(BASE_DIR, OUTFIT_FOLDER, "agbada.jpg"),
    "Senator": os.path.join(BASE_DIR, OUTFIT_FOLDER, "senator.jpg"),
    "Suit":    os.path.join(BASE_DIR, OUTFIT_FOLDER, "suit.jpg"),
    "Kaftan":  os.path.join(BASE_DIR, OUTFIT_FOLDER, "kaftan.jpg"),
}

def _secret(key: str, default: str = "") -> str:
    val = (os.getenv(key) or "").strip()
    if not val:
        try:
            val = str(st.secrets.get(key, default) or "").strip()
        except Exception:
            val = default
    return val or default

ADMIN_USERNAME = _secret("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = _secret("ADMIN_PASSWORD", "nedee123")

# ── SUPABASE ──────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    from supabase import create_client
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in secrets.")
    return create_client(url, key)

TABLE = "customers"

FIELDS = [
    "Order ID", "Name", "Phone", "Email", "Outfit Type", "Unit",
    "Date Created", "Expected Delivery Date", "Amount Paid",
    "Receipt File", "Design Photo", "Customer Notes",
    "Chest", "Stomach", "Shoulder", "Sleeve Length",
    "Neck", "Round Sleeve", "Top Length",
    "Trouser Length", "Trouser-waist", "Hips", "Laps", "Knee", "Ankle"
]
UPPER_BODY = ["Chest", "Stomach", "Shoulder", "Sleeve Length", "Neck", "Round Sleeve", "Top Length"]
LOWER_BODY = ["Trouser Length", "Trouser-waist", "Hips", "Laps", "Knee", "Ankle"]

# ── DATA HELPERS ──────────────────────────────────────────────
def _col(n): return n.lower().replace(" ", "_").replace("-", "_")

def _cast_row(row: dict) -> dict:
    num = {_col(f) for f in (UPPER_BODY + LOWER_BODY)} | {"amount_paid"}
    out = {}
    for k, v in row.items():
        if k in num:
            try:    out[k] = float(v) if v not in ("", None) else None
            except: out[k] = None
        else:
            out[k] = v
    return out

@st.cache_data(ttl=30)
def load_data() -> pd.DataFrame:
    try:
        sb   = get_supabase()
        rows = sb.table(TABLE).select("*").order("created_at", desc=False).execute().data
        if not rows:
            return pd.DataFrame(columns=FIELDS)
        df  = pd.DataFrame(rows)
        rev = {_col(f): f for f in FIELDS}
        df  = df.rename(columns=rev)
        for c in FIELDS:
            if c not in df.columns: df[c] = ""
        df = df[FIELDS]
        for c in UPPER_BODY + LOWER_BODY + ["Amount Paid"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        txt = [f for f in FIELDS if f not in UPPER_BODY + LOWER_BODY + ["Amount Paid"]]
        df[txt] = df[txt].fillna("").astype(str)
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame(columns=FIELDS)

def save_data(data: dict):
    sb = get_supabase()
    sb.table(TABLE).insert(_cast_row({_col(k): v for k, v in data.items()})).execute()
    st.cache_data.clear()

def update_record(order_id: str, data: dict):
    sb = get_supabase()
    sb.table(TABLE).update(_cast_row({_col(k): v for k, v in data.items()})).eq("order_id", order_id).execute()
    st.cache_data.clear()

def delete_record(order_id: str):
    get_supabase().table(TABLE).delete().eq("order_id", order_id).execute()
    st.cache_data.clear()

def validate_phone(p): return bool(re.match(r'^[0-9+\-\s]{7,15}$', p)) if p else True
def validate_email(e): return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', e)) if e else False

def generate_order_id():
    return f"NEC-{datetime.now().year}-{uuid.uuid4().hex[:4].upper()}"

def generate_pdf_receipt(record: dict) -> bytes:
    from fpdf import FPDF

    def _safe(text: str) -> str:
        """Replace characters outside Latin-1 range with ASCII equivalents."""
        return (str(text)
                .replace("—", "-").replace("–", "-")
                .replace("\u2019", "'").replace("\u2018", "'")
                .replace("\u201C", '"').replace("\u201D", '"')
                .replace("₦", "NGN ")
                .encode("latin-1", errors="replace").decode("latin-1"))
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 14, "NE CLOTHIERS", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 7, "Premium Tailoring - Measurement Receipt", ln=True, align="C")
    pdf.ln(4)
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_text_color(0, 0, 0)

    def row(label, value):
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(55, 7, _safe(label) + ":", border=0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 7, _safe(value), ln=True)

    for label, key in [
        ("Order ID", "Order ID"), ("Customer", "Name"), ("Phone", "Phone"),
        ("Outfit", "Outfit Type"), ("Unit", "Unit"), ("Date", "Date Created"),
        ("Delivery", "Expected Delivery Date"), ("Amount Paid", "Amount Paid"), ("Notes", "Customer Notes"),
    ]:
        val = record.get(key, "") or ""
        if key == "Amount Paid":
            try: val = f"NGN {float(val):,.0f}"
            except: val = str(val)
        row(label, val)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 9, "Body Measurements", ln=True)
    pdf.set_draw_color(37, 99, 235)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_text_color(0, 0, 0)

    mf = UPPER_BODY + LOWER_BODY
    for i in range(0, len(mf), 2):
        f1, f2 = mf[i], mf[i+1] if i+1 < len(mf) else ""
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(55, 7, _safe(f1) + ":")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(35, 7, _safe(record.get(f1, "-") or "-"))
        if f2:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(50, 7, _safe(f2) + ":")
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 7, _safe(record.get(f2, "-") or "-"), ln=True)
        else:
            pdf.ln()

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 7, "Thank you for choosing NE Clothiers - We tailor for the leading man.", ln=True, align="C")
    return bytes(pdf.output())

def send_order_confirmation_email(record: dict) -> tuple[bool, str]:
    load_dotenv(override=True)
    def _get(key, default=""):
        val = (os.getenv(key) or "").strip()
        if not val:
            try: val = str(st.secrets.get(key, default) or "").strip()
            except: val = default
        return val or default

    sender   = _get("EMAIL_SENDER")
    password = _get("EMAIL_PASSWORD").replace(" ", "")
    host     = _get("EMAIL_SMTP_HOST", "smtp.gmail.com")
    port     = int(_get("EMAIL_SMTP_PORT", "465") or 465)

    if not sender or not password:
        return False, "Email credentials not configured."
    recipient = record.get("Email", "").strip()
    if not recipient:
        return False, "No customer email on record."

    try:
        pdf_bytes = generate_pdf_receipt(record)
        msg = MIMEMultipart()
        msg["From"]    = sender
        msg["To"]      = recipient
        msg["Subject"] = f"NE Clothiers — Order {record.get('Order ID', '')}"
        body = f"""Dear {record.get('Name', 'Customer')},

Thank you for choosing NE Clothiers. Your measurement has been recorded.

Order ID       : {record.get('Order ID', '—')}
Outfit         : {record.get('Outfit Type', '—')}
Date           : {record.get('Date Created', '—')}
Delivery       : {record.get('Expected Delivery Date', '—') or '—'}
Amount Paid    : ₦{float(record.get('Amount Paid') or 0):,.0f}

Your full measurement receipt is attached as a PDF.
Keep your Order ID — use it to track your order at any time.

Warm regards,
NE Clothiers Team"""
        msg.attach(MIMEText(body, "plain"))
        part = MIMEBase("application", "octet-stream")
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename=receipt_{record.get('Order ID','order')}.pdf")
        msg.attach(part)
        with smtplib.SMTP_SSL(host, port, timeout=15) as s:
            s.ehlo(); s.login(sender, password)
            s.sendmail(sender, recipient, msg.as_string())
        return True, f"Confirmation sent to {recipient}"
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed."
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"

# ── SESSION STATE ─────────────────────────────────────────────
for _k, _v in {
    "logged_in": False, "pending_order_id": None,
    "just_saved_order": False, "just_submitted_order": False,
    "show_ai_prompt": False, "ai_prompt_pending": False,
    "ai_front_bytes": None, "ai_back_bytes": None,
    "ai_front_type": "image/jpeg", "ai_back_type": "image/jpeg",
    "prefill_meas": {},
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── CSS ───────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

.stApp {{ background-color: {BG}; }}

/* Sidebar */
[data-testid="stSidebar"] {{ background: {SURFACE} !important; border-right: 1px solid #1E3A6E; }}
[data-testid="stSidebar"] * {{ color: {TEXT} !important; }}

/* Main container */
.block-container {{ padding: 1.5rem 2rem 2rem 2rem; max-width: 1200px; }}

/* Typography */
h1 {{ color: white !important; text-align: center; font-weight: 700; letter-spacing: -0.5px; }}
h2, h3 {{ color: white !important; font-weight: 600; }}
h4 {{ color: {ACCENT} !important; font-weight: 600; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.5px; }}
p, label, .stMarkdown {{ color: {TEXT}; }}

/* Cards */
.ne-card {{
    background: {CARD};
    border: 1px solid #1E3A6E;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
}}
.ne-card-accent {{
    background: linear-gradient(135deg, {CARD} 0%, #0D2247 100%);
    border: 1px solid {PRIMARY}44;
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 16px;
}}

/* Metric cards */
.metric-card {{
    background: {CARD};
    border: 1px solid #1E3A6E;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}}
.metric-value {{ font-size: 2rem; font-weight: 700; color: white; margin: 0; }}
.metric-label {{ font-size: 0.8rem; color: {MUTED}; text-transform: uppercase; letter-spacing: 1px; margin: 4px 0 0 0; }}

/* Measurement display row */
.meas-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 14px;
    background: {CARD2};
    border-radius: 8px;
    margin-bottom: 5px;
    border-left: 3px solid {PRIMARY}66;
}}
.meas-label {{ color: {ACCENT}; font-size: 0.88rem; }}
.meas-value {{ color: white; font-weight: 600; font-size: 0.95rem; }}

/* Order card */
.order-card {{
    background: {CARD};
    border-radius: 14px;
    padding: 22px 26px;
    margin-bottom: 16px;
    border-left: 4px solid {PRIMARY};
}}

/* Step indicator */
.step-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: {PRIMARY}22;
    border: 1px solid {PRIMARY}55;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.8rem;
    color: {ACCENT};
    font-weight: 500;
    margin-bottom: 12px;
}}

/* Confidence badge */
.conf-high  {{ background: {GREEN}22; border: 1px solid {GREEN}55; color: {GREEN}; border-radius: 20px; padding: 3px 12px; font-size: 0.8rem; font-weight: 600; }}
.conf-med   {{ background: {GOLD}22;  border: 1px solid {GOLD}55;  color: {GOLD};  border-radius: 20px; padding: 3px 12px; font-size: 0.8rem; font-weight: 600; }}
.conf-low   {{ background: {RED}22;   border: 1px solid {RED}55;   color: {RED};   border-radius: 20px; padding: 3px 12px; font-size: 0.8rem; font-weight: 600; }}

/* Forms */
[data-testid="stForm"] {{
    background: {CARD};
    border: 1px solid #1E3A6E;
    border-radius: 16px;
    padding: 20px 24px;
}}

/* Buttons */
.stButton > button {{
    background: linear-gradient(135deg, {PRIMARY} 0%, {PRIMARY_D} 100%);
    color: white;
    border-radius: 10px;
    font-weight: 600;
    height: 44px;
    border: none;
    letter-spacing: 0.3px;
    transition: all 0.2s;
}}
.stButton > button:hover {{
    background: linear-gradient(135deg, {PRIMARY_D} 0%, #1E40AF 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px {PRIMARY}44;
}}
.stDownloadButton > button {{
    background: linear-gradient(135deg, #059669 0%, #047857 100%);
    color: white; border-radius: 10px; font-weight: 600; border: none;
}}

/* Inputs */
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox select {{
    background: {SURFACE} !important;
    border: 1px solid #1E3A6E !important;
    border-radius: 8px !important;
    color: white !important;
}}
.stTextInput input:focus, .stNumberInput input:focus {{
    border-color: {PRIMARY} !important;
    box-shadow: 0 0 0 2px {PRIMARY}33 !important;
}}

/* Expander */
[data-testid="stExpander"] {{
    background: {CARD};
    border: 1px solid #1E3A6E;
    border-radius: 12px;
}}
[data-testid="stExpander"] summary {{ color: {ACCENT} !important; font-weight: 600; }}

/* Divider */
hr {{ border-color: #1E3A6E !important; margin: 1.5rem 0; }}

/* Dataframe */
[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}

/* Radio */
.stRadio label {{ color: {TEXT} !important; }}

/* Success / warning / error */
.stSuccess {{ background: {GREEN}15 !important; border: 1px solid {GREEN}44 !important; border-radius: 10px !important; }}
.stWarning {{ background: {GOLD}15  !important; border: 1px solid {GOLD}44  !important; border-radius: 10px !important; }}
.stError   {{ background: {RED}15   !important; border: 1px solid {RED}44   !important; border-radius: 10px !important; }}

/* Sidebar nav */
.stRadio [data-testid="stMarkdownContainer"] p {{
    font-size: 0.95rem !important;
    padding: 4px 0 !important;
}}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 8px 0 20px 0;">
  <h1 style="font-size:2.4rem; font-weight:800; letter-spacing:-1px; margin:0;">
    ✂️ NE CLOTHIERS
  </h1>
  <p style="color:#93C5FD; font-size:0.9rem; letter-spacing:3px; text-transform:uppercase; margin:4px 0 0 0; font-weight:500;">
    Premium Tailoring · Measurement System
  </p>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    logo_path = os.path.join(BASE_DIR, "ne.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=100)
    else:
        st.markdown("<h2 style='text-align:center;'>✂️</h2>", unsafe_allow_html=True)

    st.markdown(f"<p style='text-align:center; color:{ACCENT}; font-weight:600; font-size:1.1rem; margin:0 0 4px 0;'>NE Clothiers</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:{MUTED}; font-size:0.75rem; margin:0 0 20px 0;'>Premium Tailoring</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Nav order: AI Scan first, then New Measurement, then Tracking, then Admin
    _nav_options = ["📐 AI Body Scan", "📋 New Measurement", "🔍 Order Tracking", "🔐 Admin"]

    if "_nav_override" in st.session_state:
        st.session_state["_nav_radio"] = st.session_state.pop("_nav_override")
    elif st.session_state.pending_order_id:
        st.session_state["_nav_radio"] = "🔍 Order Tracking"
    elif "_nav_radio" not in st.session_state:
        st.session_state["_nav_radio"] = "📐 AI Body Scan"

    page = st.radio("Navigation", _nav_options, key="_nav_radio", label_visibility="collapsed")

    st.markdown("---")
    st.markdown(f"<p style='color:{MUTED}; font-size:0.75rem; text-align:center;'>Workflow</p>", unsafe_allow_html=True)
    steps = [
        ("1", "AI Body Scan", "📐"),
        ("2", "New Measurement", "📋"),
        ("3", "Order Tracking", "🔍"),
    ]
    for num, label, icon in steps:
        active = label in page
        bg = f"{PRIMARY}22" if active else "transparent"
        border = f"1px solid {PRIMARY}55" if active else "1px solid transparent"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;padding:6px 10px;"
            f"border-radius:8px;background:{bg};border:{border};margin-bottom:4px;'>"
            f"<span style='background:{PRIMARY if active else MUTED};color:white;border-radius:50%;"
            f"width:20px;height:20px;display:flex;align-items:center;justify-content:center;"
            f"font-size:0.7rem;font-weight:700;flex-shrink:0;'>{num}</span>"
            f"<span style='color:{'white' if active else MUTED};font-size:0.82rem;'>{icon} {label}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("---")
    if st.session_state.logged_in:
        st.markdown(f"<p style='color:{GREEN}; font-size:0.8rem; text-align:center;'>● Admin logged in</p>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE: AI BODY SCAN
# ════════════════════════════════════════════════════════════
if page == "📐 AI Body Scan":
    st.markdown('<div class="step-badge">Step 1 of 3 — AI Body Scan</div>', unsafe_allow_html=True)
    st.markdown("## 📐 AI Body Measurement Scan")
    st.markdown(f"<p style='color:{MUTED}; text-align:center; margin-top:-8px;'>Upload a photo, provide your height, and let AI estimate your measurements. Then carry them into the measurement form.</p>", unsafe_allow_html=True)

    # Photo upload
    st.markdown("---")
    ph_col1, ph_col2 = st.columns(2)
    with ph_col1:
        st.markdown(f"<h4>🧍 Front View *</h4>", unsafe_allow_html=True)
        front_photo = st.file_uploader("Front photo", type=["png","jpg","jpeg"], key="ai_front", label_visibility="collapsed")
        if front_photo:
            st.session_state["ai_front_bytes"] = front_photo.read()
            st.session_state["ai_front_type"]  = front_photo.type
        if st.session_state.get("ai_front_bytes"):
            st.image(io.BytesIO(st.session_state["ai_front_bytes"]), caption="Front View", use_container_width=True)
        else:
            st.markdown(f"""<div style='background:{CARD};border:2px dashed #1E3A6E;border-radius:12px;
                padding:40px;text-align:center;color:{MUTED};'>
                <p style='font-size:2rem;margin:0;'>📷</p>
                <p style='margin:8px 0 0 0;font-size:0.85rem;'>Upload front photo</p></div>""", unsafe_allow_html=True)

    with ph_col2:
        st.markdown(f"<h4>🧍 Back View <span style='color:{MUTED};font-weight:400;font-size:0.8rem;'>(optional)</span></h4>", unsafe_allow_html=True)
        back_photo = st.file_uploader("Back photo", type=["png","jpg","jpeg"], key="ai_back", label_visibility="collapsed")
        if back_photo:
            st.session_state["ai_back_bytes"] = back_photo.read()
            st.session_state["ai_back_type"]  = back_photo.type
        if st.session_state.get("ai_back_bytes"):
            st.image(io.BytesIO(st.session_state["ai_back_bytes"]), caption="Back View", use_container_width=True)
        else:
            st.markdown(f"""<div style='background:{CARD};border:2px dashed #1E3A6E;border-radius:12px;
                padding:40px;text-align:center;color:{MUTED};'>
                <p style='font-size:2rem;margin:0;'>📷</p>
                <p style='margin:8px 0 0 0;font-size:0.85rem;'>Upload back photo (optional)</p></div>""", unsafe_allow_html=True)

    # Reference measurements
    st.markdown("---")
    st.markdown(f"<h4>📏 Reference Measurements</h4>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{MUTED};font-size:0.85rem;margin-top:-8px;'>Height is required. Tape measurements are optional but significantly improve accuracy.</p>", unsafe_allow_html=True)

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        ai_unit           = st.radio("Unit", ["cm", "inches"], horizontal=True, key="ai_unit")
        ai_height         = st.text_input("Height *", placeholder="e.g. 175", key="ai_height")
    with rc2:
        ai_chest_known    = st.text_input("Chest (tape)", placeholder="e.g. 96", key="ai_chest_known")
        ai_shoulder_known = st.text_input("Shoulder (tape)", placeholder="e.g. 44", key="ai_shoulder_known")
    with rc3:
        ai_waist_known    = st.text_input("Waist / Stomach (tape)", placeholder="e.g. 82", key="ai_waist_known")
        ai_hip_known      = st.text_input("Hips (tape)", placeholder="e.g. 98", key="ai_hip_known")

    st.markdown("---")
    bc1, bc2 = st.columns([4, 1])
    with bc1:
        scan_btn  = st.button("🤖 Scan & Estimate Measurements", type="primary", use_container_width=True)
    with bc2:
        clear_btn = st.button("🗑️ Clear", use_container_width=True)

    if clear_btn:
        for k in ["ai_front_bytes","ai_back_bytes","ai_measurements","ai_annotated"]:
            st.session_state[k] = None if k.endswith("bytes") else st.session_state.pop(k, None)
        st.rerun()

    if scan_btn:
        if not st.session_state.get("ai_front_bytes"):
            st.error("Please upload a front photo first.")
        elif not ai_height.strip():
            st.error("Height is required.")
        else:
            try:
                height_val = float(re.sub(r"[^\d.]", "", ai_height.strip()))
                height_cm  = height_val if ai_unit == "cm" else height_val * 2.54
            except ValueError:
                height_cm = None
                st.error("Could not parse height.")

            def _ref(val):
                if not val or not val.strip(): return None
                try:
                    v = float(re.sub(r"[^\d.]", "", val.strip()))
                    return v if ai_unit == "cm" else v * 2.54
                except: return None

            ref_chest = _ref(ai_chest_known); ref_shoulder = _ref(ai_shoulder_known)
            ref_waist = _ref(ai_waist_known); ref_hip      = _ref(ai_hip_known)
            n_refs    = sum(x is not None for x in [ref_chest, ref_shoulder, ref_waist, ref_hip])

            if height_cm:
                with st.spinner("🤖 Detecting body landmarks…"):
                    try:
                        import urllib.request, numpy as np
                        from PIL import Image as PILImage
                        import mediapipe as mp, cv2
                        from mediapipe.tasks import python as mp_python
                        from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode

                        _mdir = "/tmp" if not os.access(BASE_DIR, os.W_OK) else BASE_DIR
                        MODEL_PATH = os.path.join(_mdir, "pose_landmarker.task")
                        if not os.path.exists(MODEL_PATH):
                            with st.spinner("📥 Downloading pose model (~25 MB, one-time)…"):
                                urllib.request.urlretrieve(
                                    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
                                    MODEL_PATH)

                        opts = PoseLandmarkerOptions(
                            base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
                            running_mode=RunningMode.IMAGE, num_poses=1,
                            min_pose_detection_confidence=0.5,
                            min_pose_presence_confidence=0.5,
                            min_tracking_confidence=0.5,
                        )
                        IDX = {"NOSE":0,"LEFT_EAR":7,"RIGHT_EAR":8,"LEFT_SHOULDER":11,"RIGHT_SHOULDER":12,
                               "LEFT_ELBOW":13,"RIGHT_ELBOW":14,"LEFT_WRIST":15,"RIGHT_WRIST":16,
                               "LEFT_HIP":23,"RIGHT_HIP":24,"LEFT_KNEE":25,"RIGHT_KNEE":26,
                               "LEFT_ANKLE":27,"RIGHT_ANKLE":28}

                        def _pose(img_bytes):
                            pil = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
                            arr = np.array(pil)
                            mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
                            with PoseLandmarker.create_from_options(opts) as lmk:
                                res = lmk.detect(mpi)
                            return res, arr, pil.size

                        fr, fnp, (fw, fh) = _pose(st.session_state["ai_front_bytes"])
                        if not fr.pose_landmarks:
                            st.error("No person detected. Ensure full body is visible against a plain background.")
                        else:
                            lm = fr.pose_landmarks[0]
                            def lx(n): return lm[IDX[n]].x
                            def ly(n): return lm[IDX[n]].y
                            def lv(n): return getattr(lm[IDX[n]], "visibility", 1.0) or 1.0
                            def H(a,b): return abs(lx(a)-lx(b))*fw
                            def V(a,b): return abs(ly(a)-ly(b))*fh
                            def E(a,b): return ((lx(a)-lx(b))**2*fw**2+(ly(a)-ly(b))**2*fh**2)**0.5

                            uv = min(lv("LEFT_SHOULDER"),lv("RIGHT_SHOULDER"),lv("LEFT_HIP"),lv("RIGHT_HIP"))
                            lv2= min(lv("LEFT_HIP"),lv("RIGHT_HIP"),lv("LEFT_KNEE"),lv("RIGHT_KNEE"),lv("LEFT_ANKLE"),lv("RIGHT_ANKLE"))

                            span = abs(((ly("LEFT_ANKLE")+ly("RIGHT_ANKLE"))/2 - ly("NOSE"))*fh)/0.915
                            ppcm = span / height_cm
                            def cm(px): return px/ppcm
                            def fmt(v): return f"{v:.1f}" if ai_unit=="cm" else f"{v/2.54:.1f}"

                            sw = cm(H("LEFT_SHOULDER","RIGHT_SHOULDER"))
                            hw = cm(H("LEFT_HIP","RIGHT_HIP"))
                            ew = cm(H("LEFT_EAR","RIGHT_EAR"))

                            if st.session_state.get("ai_back_bytes"):
                                try:
                                    br,_,(bw,bh) = _pose(st.session_state["ai_back_bytes"])
                                    if br.pose_landmarks:
                                        blm=br.pose_landmarks[0]
                                        bsp=abs(((blm[IDX["LEFT_ANKLE"]].y+blm[IDX["RIGHT_ANKLE"]].y)/2-blm[IDX["NOSE"]].y)*bh)/0.915
                                        bpc=bsp/height_cm
                                        sw=(sw+abs(blm[IDX["LEFT_SHOULDER"]].x-blm[IDX["RIGHT_SHOULDER"]].x)*bw/bpc)/2
                                        hw=(hw+abs(blm[IDX["LEFT_HIP"]].x-blm[IDX["RIGHT_HIP"]].x)*bw/bpc)/2
                                except: pass

                            ce=sw*2.05; se=hw*1.80; he=hw*2.10; ne=ew*2.20; re=sw*0.65
                            cf=ref_chest    if ref_chest    else ce
                            sf=ref_shoulder if ref_shoulder else sw
                            wf=ref_waist    if ref_waist    else se
                            hf=ref_hip      if ref_hip      else he
                            ck=cf/ce if ce>0 else 1; sk=sf/sw if sw>0 else 1
                            wk=wf/se if se>0 else 1; hk=hf/he if he>0 else 1
                            nf=ne*((ck+sk)/2); rf=re*sk
                            slv=cm(E("LEFT_SHOULDER","LEFT_ELBOW")+E("LEFT_ELBOW","LEFT_WRIST"))
                            tl=cm(V("LEFT_SHOULDER","LEFT_HIP"))
                            tr=cm(V("LEFT_HIP","LEFT_ANKLE"))
                            tw=wf*1.05; lp=hf*0.58; kn=hf*0.40; an=hf*0.22

                            if n_refs>=3:   conf,cnote="high",  f"Calibrated with {n_refs} tape measurements."
                            elif n_refs>=1: conf,cnote="medium",f"Partially calibrated ({n_refs} reference). Add more for higher accuracy."
                            elif uv>0.75 and lv2>0.75: conf,cnote="low","No tape references — circumferences are estimates. Verify before cutting."
                            else:           conf,cnote="low","Poor landmark visibility. Retake with better lighting."

                            ann=fnp.copy()
                            for a,b in [("LEFT_SHOULDER","RIGHT_SHOULDER"),("LEFT_SHOULDER","LEFT_ELBOW"),
                                        ("LEFT_ELBOW","LEFT_WRIST"),("RIGHT_SHOULDER","RIGHT_ELBOW"),
                                        ("RIGHT_ELBOW","RIGHT_WRIST"),("LEFT_SHOULDER","LEFT_HIP"),
                                        ("RIGHT_SHOULDER","RIGHT_HIP"),("LEFT_HIP","RIGHT_HIP"),
                                        ("LEFT_HIP","LEFT_KNEE"),("LEFT_KNEE","LEFT_ANKLE"),
                                        ("RIGHT_HIP","RIGHT_KNEE"),("RIGHT_KNEE","RIGHT_ANKLE")]:
                                cv2.line(ann,(int(lx(a)*fw),int(ly(a)*fh)),(int(lx(b)*fw),int(ly(b)*fh)),(147,197,253),2)
                            for n in IDX:
                                vis=lv(n); col=(37,235,99) if vis>0.8 else (235,180,37) if vis>0.5 else (235,37,37)
                                cv2.circle(ann,(int(lx(n)*fw),int(ly(n)*fh)),5,col,-1)

                            st.session_state["ai_annotated"]   = ann
                            st.session_state["ai_unit_result"] = ai_unit
                            st.session_state["ai_measurements"] = {
                                "Chest":fmt(cf),"Stomach":fmt(wf),"Shoulder":fmt(sf),
                                "Sleeve Length":fmt(slv),"Neck":fmt(nf),"Round Sleeve":fmt(rf),
                                "Top Length":fmt(tl),"Trouser Length":fmt(tr),"Trouser-waist":fmt(tw),
                                "Hips":fmt(hf),"Laps":fmt(lp),"Knee":fmt(kn),"Ankle":fmt(an),
                                "confidence":conf,"notes":cnote,
                            }
                            st.rerun()
                    except ImportError as e:
                        st.error(f"Missing dependency: {e}")
                    except Exception as e:
                        st.error(f"Scan failed: {e}")

    # ── RESULTS ───────────────────────────────────────────────
    if st.session_state.get("ai_measurements"):
        ai_res  = st.session_state["ai_measurements"]
        ru      = st.session_state.get("ai_unit_result", "cm")
        conf    = ai_res.get("confidence", "low")
        cnote   = ai_res.get("notes", "")
        conf_cls= {"high":"conf-high","medium":"conf-med","low":"conf-low"}.get(conf,"conf-low")

        st.markdown("---")
        st.markdown("## ✅ Scan Results")

        # Confidence badge + note
        st.markdown(f"<span class='{conf_cls}'>Confidence: {conf.upper()}</span>", unsafe_allow_html=True)
        if cnote:
            st.markdown(f"<p style='color:{MUTED};font-size:0.85rem;margin-top:6px;'>{cnote}</p>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Annotated image + measurements side by side
        if st.session_state.get("ai_annotated") is not None:
            rc1, rc2 = st.columns([1, 1])
            with rc1:
                st.image(st.session_state["ai_annotated"], caption="Detected landmarks", use_container_width=True)
            with rc2:
                st.markdown(f"<h4>Upper Body</h4>", unsafe_allow_html=True)
                for f in UPPER_BODY:
                    v = ai_res.get(f, "—")
                    st.markdown(f"<div class='meas-row'><span class='meas-label'>{f}</span><span class='meas-value'>{v} {ru}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<h4 style='margin-top:12px;'>Lower Body</h4>", unsafe_allow_html=True)
                for f in LOWER_BODY:
                    v = ai_res.get(f, "—")
                    st.markdown(f"<div class='meas-row'><span class='meas-label'>{f}</span><span class='meas-value'>{v} {ru}</span></div>", unsafe_allow_html=True)
        else:
            # No annotated image — show measurements in two columns
            mr1, mr2 = st.columns(2)
            with mr1:
                st.markdown(f"<h4>Upper Body</h4>", unsafe_allow_html=True)
                for f in UPPER_BODY:
                    v = ai_res.get(f, "—")
                    st.markdown(f"<div class='meas-row'><span class='meas-label'>{f}</span><span class='meas-value'>{v} {ru}</span></div>", unsafe_allow_html=True)
            with mr2:
                st.markdown(f"<h4>Lower Body</h4>", unsafe_allow_html=True)
                for f in LOWER_BODY:
                    v = ai_res.get(f, "—")
                    st.markdown(f"<div class='meas-row'><span class='meas-label'>{f}</span><span class='meas-value'>{v} {ru}</span></div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"""
        <div class='ne-card-accent' style='text-align:center;'>
            <p style='color:{ACCENT};font-size:1rem;font-weight:600;margin:0 0 8px 0;'>Ready to proceed?</p>
            <p style='color:{MUTED};font-size:0.85rem;margin:0;'>These measurements will be pre-filled in the New Measurement form. Click below to continue.</p>
        </div>""", unsafe_allow_html=True)

        nc1, nc2 = st.columns(2)
        with nc1:
            if st.button("➡️ Continue to New Measurement", type="primary", use_container_width=True):
                # Pre-fill measurements into session state for the next page
                st.session_state["prefill_meas"] = {f: ai_res.get(f, "") for f in UPPER_BODY + LOWER_BODY}
                st.session_state["prefill_unit"]  = st.session_state.get("ai_unit_result", "cm")
                st.session_state["_nav_override"] = "📋 New Measurement"
                st.rerun()
        with nc2:
            if st.button("🗑️ Clear & Rescan", use_container_width=True):
                for k in ["ai_front_bytes","ai_back_bytes","ai_measurements","ai_annotated"]:
                    st.session_state[k] = None if k.endswith("bytes") else st.session_state.pop(k, None)
                st.rerun()
    else:
        # Tips when no scan yet
        st.markdown("---")
        st.markdown(f"""
        <div class='ne-card'>
            <h4 style='margin:0 0 12px 0;'>📸 Photo Tips for Best Results</h4>
            <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;'>
                <div style='color:{TEXT};font-size:0.85rem;'>✅ Full body visible head to toe</div>
                <div style='color:{TEXT};font-size:0.85rem;'>✅ Plain, well-lit background</div>
                <div style='color:{TEXT};font-size:0.85rem;'>✅ Form-fitting clothing</div>
                <div style='color:{TEXT};font-size:0.85rem;'>✅ Arms slightly away from body</div>
                <div style='color:{RED};font-size:0.85rem;'>❌ No baggy outfits</div>
                <div style='color:{RED};font-size:0.85rem;'>❌ No busy backgrounds</div>
            </div>
        </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: NEW MEASUREMENT
# ════════════════════════════════════════════════════════════
elif page == "📋 New Measurement":
    st.markdown('<div class="step-badge">Step 2 of 3 — New Measurement</div>', unsafe_allow_html=True)
    st.markdown("## 📋 New Measurement")

    # Check for pre-filled measurements from AI scan
    prefill = st.session_state.get("prefill_meas", {})
    prefill_unit = st.session_state.get("prefill_unit", "cm")
    if prefill:
        st.markdown(f"""
        <div style='background:{GREEN}15;border:1px solid {GREEN}44;border-radius:10px;
        padding:12px 16px;margin-bottom:16px;display:flex;align-items:center;gap:10px;'>
            <span style='font-size:1.2rem;'>🤖</span>
            <span style='color:{GREEN};font-size:0.9rem;font-weight:500;'>
                AI measurements pre-filled from your body scan. Review and adjust as needed.
            </span>
        </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(f"<h4>👔 Outfit Type</h4>", unsafe_allow_html=True)
        outfit = st.selectbox("Outfit", ["Agbada", "Senator", "Suit", "Kaftan"],
                               key="outfit_select", label_visibility="collapsed")
        img_path = OUTFIT_IMAGES.get(outfit)
        if img_path and os.path.exists(img_path):
            st.image(img_path, caption=f"{outfit} Style", use_container_width=True)

        st.markdown("---")
        with st.form("measurement_form", clear_on_submit=True):
            st.markdown(f"<h4>👤 Customer Info</h4>", unsafe_allow_html=True)
            name  = st.text_input("Customer Name *")
            phone = st.text_input("Phone Number *")
            email = st.text_input("Email Address *", placeholder="customer@example.com")
            unit  = st.radio("Measurement Unit", ["cm", "inches"], horizontal=True,
                              index=0 if prefill_unit == "cm" else 1)
            st.markdown("---")
            st.markdown(f"<p style='color:{ACCENT};font-weight:600;font-size:0.85rem;'>DESIGN / STYLE PHOTO</p>", unsafe_allow_html=True)
            design_photo = st.file_uploader("Upload design photo", type=["png","jpg","jpeg"],
                                             label_visibility="collapsed", key="design_photo")
            if design_photo:
                st.image(design_photo, caption="Design Preview", use_container_width=True)
            submitted = st.form_submit_button("💾 Save Measurement", use_container_width=True)

    with col2:
        st.markdown(f"<h4>📏 Body Measurements</h4>", unsafe_allow_html=True)
        meas_values = {}

        with st.expander("👕 Upper Body", expanded=True):
            ub_cols = st.columns(2)
            for i, field in enumerate(UPPER_BODY):
                with ub_cols[i % 2]:
                    default_val = str(prefill.get(field, ""))
                    meas_values[field] = st.text_input(
                        field, value=default_val,
                        placeholder=f"e.g. 42",
                        key=f"meas_{field}"
                    )

        with st.expander("👖 Lower Body", expanded=True):
            lb_cols = st.columns(2)
            for i, field in enumerate(LOWER_BODY):
                with lb_cols[i % 2]:
                    default_val = str(prefill.get(field, ""))
                    meas_values[field] = st.text_input(
                        field, value=default_val,
                        placeholder=f"e.g. 42",
                        key=f"meas_{field}"
                    )

    if submitted:
        errors = []
        if not name.strip():  errors.append("Customer name is required.")
        if not phone.strip(): errors.append("Phone number is required.")
        elif not validate_phone(phone): errors.append("Phone number format is invalid.")
        if not email.strip(): errors.append("Email address is required.")
        elif not validate_email(email.strip()): errors.append("Email address format is invalid.")
        for field, val in meas_values.items():
            if not str(val).strip(): errors.append(f"{field} is required.")
            elif not str(val).replace('.','',1).isdigit(): errors.append(f"{field} must be a number.")

        if errors:
            for e in errors: st.error(e)
        else:
            order_id     = generate_order_id()
            outfit_saved = st.session_state.get("outfit_select", "Agbada")
            design_filename = ""
            if design_photo:
                design_filename = design_photo.name
                with open(os.path.join(IMAGE_FOLDER_PATH, design_filename), "wb") as f:
                    f.write(design_photo.getbuffer())

            data = {
                "Order ID": order_id, "Name": name.strip(), "Phone": phone.strip(),
                "Email": email.strip(), "Outfit Type": outfit_saved, "Unit": unit,
                "Date Created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Expected Delivery Date": "", "Amount Paid": 0,
                "Receipt File": "", "Design Photo": design_filename, "Customer Notes": "",
                **meas_values
            }
            save_data(data)
            st.session_state.pending_order_id = order_id
            st.session_state.just_saved_order = True
            st.session_state["prefill_meas"]  = {}  # clear prefill after save

            st.markdown(f"""
            <div style='background:{GREEN}15;border:1px solid {GREEN}44;border-radius:12px;padding:16px 20px;'>
                <p style='color:{GREEN};font-weight:600;margin:0;'>✅ Measurement saved!</p>
                <p style='color:{TEXT};margin:4px 0 0 0;font-size:0.9rem;'>Order ID: <strong>{order_id}</strong> · {name.strip()} · {outfit_saved}</p>
            </div>""", unsafe_allow_html=True)

            ok, msg = send_order_confirmation_email(data)
            if ok:   st.success(f"📧 {msg}")
            else:    st.warning(f"📧 Email not sent: {msg}")

# ── POST-SUBMIT BANNER ────────────────────────────────────────
if st.session_state.just_saved_order:
    st.markdown("---")
    st.markdown(f"""
    <div class='ne-card-accent' style='text-align:center;'>
        <p style='color:{ACCENT};font-size:1rem;font-weight:600;margin:0 0 6px 0;'>📋 Measurement Saved</p>
        <p style='color:{MUTED};font-size:0.85rem;margin:0;'>Click below to add delivery date, amount paid, and notes.</p>
    </div>""", unsafe_allow_html=True)
    if st.button("➡️ Continue to Order Details", type="primary", use_container_width=True):
        st.session_state.just_saved_order = False
        st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE: ORDER TRACKING
# ════════════════════════════════════════════════════════════
elif page == "🔍 Order Tracking":
    st.markdown('<div class="step-badge">Step 3 of 3 — Order Tracking</div>', unsafe_allow_html=True)
    st.markdown("## 🔍 Order Tracking")

    df = load_data()
    found_order_id = ""
    if st.session_state.pending_order_id:
        found_order_id = st.session_state.pending_order_id
        st.session_state.pending_order_id = None

    # Search bar
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        search_query = st.text_input("Search", value=found_order_id,
                                      placeholder="Order ID, name, or phone number…",
                                      label_visibility="collapsed")
    with sc2:
        st.button("🔍 Search", use_container_width=True)

    results = pd.DataFrame()
    if search_query.strip():
        q = search_query.strip().lower()
        mask = (df["Order ID"].astype(str).str.lower().str.contains(q, na=False) |
                df["Name"].astype(str).str.lower().str.contains(q, na=False) |
                df["Phone"].astype(str).str.lower().str.contains(q, na=False))
        results = df[mask]

        if results.empty:
            st.markdown(f"""<div style='background:{CARD};border-radius:12px;padding:24px;text-align:center;'>
                <p style='font-size:1.5rem;margin:0;'>🔍</p>
                <p style='color:{MUTED};margin:8px 0 0 0;'>No orders found for "{search_query}"</p>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"<p style='color:{GREEN};font-size:0.85rem;'>Found {len(results)} order(s)</p>", unsafe_allow_html=True)
            found_order_id = str(results.iloc[0].get("Order ID", ""))

            for _, row in results.iterrows():
                oid   = row.get("Order ID", "—")
                ddate = row.get("Expected Delivery Date", "—") or "—"
                amt   = float(row.get("Amount Paid") or 0)
                st.markdown(f"""
                <div class='order-card'>
                    <div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;'>
                        <div>
                            <p style='color:{MUTED};margin:0;font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;'>Order ID</p>
                            <p style='color:white;margin:2px 0 6px 0;font-size:1.3rem;font-weight:700;letter-spacing:2px;'>{oid}</p>
                            <p style='color:white;margin:0 0 4px 0;font-size:1rem;font-weight:600;'>{row.get("Name","")}</p>
                            <p style='color:{ACCENT};margin:0;font-size:0.82rem;'>
                                📱 {row.get("Phone","—")} &nbsp;·&nbsp; 👔 {row.get("Outfit Type","—")} &nbsp;·&nbsp; 🗓️ {row.get("Date Created","—")}
                            </p>
                        </div>
                    </div>
                    <hr style='border-color:#1E3A6E;margin:14px 0;'>
                    <div style='display:flex;gap:40px;flex-wrap:wrap;'>
                        <div>
                            <p style='color:{MUTED};margin:0;font-size:0.7rem;letter-spacing:1px;text-transform:uppercase;'>Expected Delivery</p>
                            <p style='color:white;margin:3px 0 0 0;font-weight:600;'>📆 {ddate}</p>
                        </div>
                        <div>
                            <p style='color:{MUTED};margin:0;font-size:0.7rem;letter-spacing:1px;text-transform:uppercase;'>Amount Paid</p>
                            <p style='color:white;margin:3px 0 0 0;font-weight:600;'>₦{amt:,.0f}</p>
                        </div>
                        <div>
                            <p style='color:{MUTED};margin:0;font-size:0.7rem;letter-spacing:1px;text-transform:uppercase;'>Notes</p>
                            <p style='color:white;margin:3px 0 0 0;font-size:0.88rem;'>{row.get("Customer Notes","—") or "—"}</p>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📝 Submit Order Details")
    st.markdown(f"<p style='color:{MUTED};font-size:0.85rem;margin-top:-8px;'>Add delivery date, payment, and notes to an existing order.</p>", unsafe_allow_html=True)

    prefill_row    = results.iloc[0] if not results.empty else None
    default_oid    = found_order_id
    default_amount = float(prefill_row.get("Amount Paid") or 0) if prefill_row is not None else 0.0
    default_notes  = str(prefill_row.get("Customer Notes","") or "") if prefill_row is not None else ""

    with st.form("order_details_form", clear_on_submit=True):
        od1, od2 = st.columns([1, 1])
        with od1:
            od_order_id = st.text_input("Order ID *", value=default_oid, placeholder="e.g. NEC-2026-A3F7")
            od_delivery = st.date_input("Expected Delivery Date")
            od_amount   = st.number_input("Amount Paid (₦)", value=default_amount, min_value=0.0, step=1000.0)
            od_notes    = st.text_area("Customer Notes", value=default_notes, placeholder="Special instructions…")
        with od2:
            st.markdown(f"<p style='color:{ACCENT};font-weight:600;font-size:0.85rem;'>PAYMENT RECEIPT</p>", unsafe_allow_html=True)
            od_receipt = st.file_uploader("Upload receipt", type=["png","jpg","jpeg","pdf"],
                                           label_visibility="collapsed", key="od_receipt")
        od_submit = st.form_submit_button("📤 Submit Order Details", use_container_width=True)

        if od_submit:
            if not od_order_id.strip():
                st.error("Order ID is required.")
            else:
                df_check = load_data()
                match = df_check[df_check["Order ID"].astype(str).str.upper() == od_order_id.strip().upper()]
                if match.empty:
                    st.error(f"No order found with ID **{od_order_id.strip()}**.")
                else:
                    mid = od_order_id.strip().upper()
                    ridx = match.index[0]
                    rfn  = str(df_check.at[ridx, "Receipt File"] or "")
                    if od_receipt:
                        rfn = od_receipt.name
                        with open(os.path.join(RECEIPT_FOLDER_PATH, rfn), "wb") as f:
                            f.write(od_receipt.getbuffer())
                    update_record(mid, {"Expected Delivery Date": str(od_delivery),
                                        "Amount Paid": od_amount, "Customer Notes": od_notes,
                                        "Receipt File": rfn})
                    st.success(f"✅ Order **{mid}** updated!")
                    st.info(f"Delivery: {od_delivery} · ₦{od_amount:,.0f}")
                    upd = load_data()
                    um  = upd[upd["Order ID"].astype(str).str.upper() == mid]
                    ok, msg = send_order_confirmation_email(um.iloc[0].to_dict() if not um.empty else {})
                    if ok:   st.success(f"📧 {msg}")
                    else:    st.warning(f"📧 Email not sent: {msg}")
                    st.session_state.just_submitted_order = True

    if st.session_state.just_submitted_order:
        st.session_state.just_submitted_order = False
        st.markdown(f"""
        <div class='ne-card-accent' style='text-align:center;padding:48px 36px;'>
            <p style='font-size:3rem;margin:0 0 12px 0;'>✂️</p>
            <h2 style='color:white;margin:0 0 12px 0;font-size:1.6rem;'>We are happy to serve you.</h2>
            <p style='color:{ACCENT};font-size:0.95rem;line-height:1.8;max-width:480px;margin:0 auto;'>
                At <strong style='color:white;'>NE Clothiers</strong>, we are a one customer brand,
                and we tailor for the leading man.
            </p>
        </div>""", unsafe_allow_html=True)

    if not search_query.strip() and not st.session_state.just_submitted_order:
        st.markdown(f"""
        <div style='background:{CARD};border-radius:14px;padding:40px;text-align:center;margin-top:16px;'>
            <p style='font-size:2.5rem;margin:0;'>✂️</p>
            <h3 style='color:white;margin:12px 0 6px 0;'>NE Clothiers Order Tracker</h3>
            <p style='color:{MUTED};margin:0;font-size:0.9rem;'>Search by Order ID, name, or phone number to view your order status.</p>
        </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: ADMIN
# ════════════════════════════════════════════════════════════
elif page == "🔐 Admin":
    if not st.session_state.logged_in:
        st.markdown(f"""
        <div style='max-width:420px;margin:60px auto 0 auto;'>
            <div class='ne-card-accent' style='text-align:center;padding:32px;'>
                <p style='font-size:2rem;margin:0 0 8px 0;'>🔐</p>
                <h3 style='color:white;margin:0 0 4px 0;'>Admin Sign In</h3>
                <p style='color:{MUTED};font-size:0.85rem;margin:0;'>NE Clothiers Management</p>
            </div>
        </div>""", unsafe_allow_html=True)
        _, lc, _ = st.columns([1, 2, 1])
        with lc:
            with st.form("admin_login_form"):
                a_user = st.text_input("Username")
                a_pass = st.text_input("Password", type="password")
                a_btn  = st.form_submit_button("Sign In", use_container_width=True)
            if a_btn:
                if a_user == ADMIN_USERNAME and a_pass == ADMIN_PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")
    else:
        st.markdown("## 📊 Dashboard")
        df = load_data()

        if df.empty:
            st.info("No records yet.")
        else:
            today = pd.Timestamp(date.today())
            try:
                df["_dt"] = pd.to_datetime(df["Expected Delivery Date"], errors="coerce")
                due_week  = df[(df["_dt"] >= today) & (df["_dt"] <= today + pd.Timedelta(days=7))]
                overdue   = df[df["_dt"] < today]
            except:
                due_week = overdue = pd.DataFrame()

            total_col = pd.to_numeric(df["Amount Paid"], errors="coerce").sum()

            mc1, mc2, mc3, mc4 = st.columns(4)
            for col, val, label in [
                (mc1, len(df),        "Total Customers"),
                (mc2, len(due_week),  "Due This Week"),
                (mc3, len(overdue),   "Overdue"),
                (mc4, f"₦{total_col:,.0f}", "Total Collected"),
            ]:
                col.markdown(f"""<div class='metric-card'>
                    <p class='metric-value'>{val}</p>
                    <p class='metric-label'>{label}</p>
                </div>""", unsafe_allow_html=True)

            st.markdown("---")
            dc1, dc2 = st.columns([1, 1])
            with dc1:
                st.markdown(f"<h4>Outfit Breakdown</h4>", unsafe_allow_html=True)
                st.bar_chart(df["Outfit Type"].value_counts())
            with dc2:
                st.markdown(f"<h4>🕐 5 Most Recent</h4>", unsafe_allow_html=True)
                rc = ["Order ID","Name","Phone","Outfit Type","Expected Delivery Date"]
                st.dataframe(df.tail(5)[rc].iloc[::-1], use_container_width=True, height=220)

            if not overdue.empty:
                st.markdown("---")
                st.markdown(f"<h4 style='color:{RED};'>🚨 Overdue Orders</h4>", unsafe_allow_html=True)
                st.dataframe(overdue[["Order ID","Name","Phone","Outfit Type","Expected Delivery Date"]], use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🗂️ All Records")
        df_all = load_data()
        fa1, fa2 = st.columns([2, 1])
        with fa1:
            a_search = st.text_input("🔍 Search", placeholder="Name, phone, or Order ID…")
        with fa2:
            outfit_opts = ["All"] + sorted(df_all["Outfit Type"].dropna().unique().tolist())
            a_outfit = st.selectbox("Outfit", outfit_opts)

        filtered = df_all.copy()
        if a_search:
            q = a_search.lower()
            filtered = filtered[
                filtered["Name"].astype(str).str.lower().str.contains(q, na=False) |
                filtered["Phone"].astype(str).str.lower().str.contains(q, na=False) |
                filtered["Order ID"].astype(str).str.lower().str.contains(q, na=False)]
        if a_outfit != "All":
            filtered = filtered[filtered["Outfit Type"] == a_outfit]

        st.caption(f"Showing {len(filtered)} of {len(df_all)} records")
        st.dataframe(filtered, use_container_width=True, height=280)

        st.markdown("---")
        st.markdown("#### ✏️ Edit or Delete")
        if not filtered.empty:
            rec_opts = {f"{r['Order ID']} — {r['Name']} ({r.get('Date Created','')})": idx
                        for idx, r in filtered.iterrows()}
            sel_label = st.selectbox("Select record", list(rec_opts.keys()))
            sel_idx   = rec_opts[sel_label]
            sel_row   = df_all.loc[sel_idx]

            ec1, ec2 = st.columns(2)
            with ec1:
                with st.expander("✏️ Edit"):
                    outfit_list = ["Agbada","Senator","Suit","Kaftan"]
                    def safe_idx(lst, val, d=0): return lst.index(val) if val in lst else d
                    with st.form("edit_form"):
                        e_name   = st.text_input("Name",  value=str(sel_row.get("Name","")))
                        e_phone  = st.text_input("Phone", value=str(sel_row.get("Phone","")))
                        e_outfit = st.selectbox("Outfit Type", outfit_list,
                                                 index=safe_idx(outfit_list, sel_row.get("Outfit Type","")))
                        e_amount = st.number_input("Amount Paid (₦)", value=float(sel_row.get("Amount Paid") or 0),
                                                    min_value=0.0, step=1000.0)
                        e_notes  = st.text_area("Notes", value=str(sel_row.get("Customer Notes","")))
                        if st.form_submit_button("💾 Save Changes"):
                            update_record(str(sel_row.get("Order ID","")),
                                          {"Name":e_name,"Phone":e_phone,"Outfit Type":e_outfit,
                                           "Amount Paid":e_amount,"Customer Notes":e_notes})
                            st.success("Record updated.")
                            st.rerun()
            with ec2:
                with st.expander("🗑️ Delete"):
                    st.warning(f"Delete **{sel_row.get('Name','')}** ({sel_row.get('Order ID','')})?")
                    confirm = st.text_input("Type customer name to confirm")
                    if st.button("🗑️ Confirm Delete", type="primary"):
                        if confirm.strip().lower() == str(sel_row.get("Name","")).strip().lower():
                            delete_record(str(sel_row.get("Order ID","")))
                            st.success("Deleted.")
                            st.rerun()
                        else:
                            st.error("Name does not match.")

        st.markdown("---")
        st.markdown("#### 🧾 PDF Receipt")
        if not filtered.empty:
            pdf_opts = {f"{r['Order ID']} — {r['Name']}": idx for idx, r in filtered.iterrows()}
            pdf_label = st.selectbox("Select customer", list(pdf_opts.keys()), key="pdf_sel")
            pdf_row   = df_all.loc[pdf_opts[pdf_label]].to_dict()
            pdf_bytes = generate_pdf_receipt(pdf_row)
            st.download_button("📄 Download PDF Receipt", data=pdf_bytes,
                                file_name=f"receipt_{pdf_row.get('Order ID','order')}.pdf",
                                mime="application/pdf")

        st.markdown("---")
        st.markdown("#### 📥 Export")
        ex1, ex2 = st.columns(2)
        with ex1:
            st.download_button("⬇️ Download CSV", data=filtered.to_csv(index=False),
                                file_name="NE_Clothiers_measurements.csv", mime="text/csv")
        with ex2:
            xls = io.BytesIO()
            filtered.to_excel(xls, index=False, engine="openpyxl")
            st.download_button("⬇️ Download Excel", data=xls.getvalue(),
                                file_name="NE_Clothiers_measurements.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
