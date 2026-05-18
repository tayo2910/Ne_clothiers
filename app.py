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
    layout="wide"
)

# ── THEME ────────────────────────────────────────────────────
PRIMARY_COLOR = "#2563EB"
BG_COLOR      = "#061C49"
CARD_COLOR    = "#1E3A6E"
TEXT_COLOR    = "#FFFFFF"

# ── CONFIG ───────────────────────────────────────────────────
FILE_NAME      = "NE_Clothiers_measurements.csv"
IMAGE_FOLDER   = "customer_images"
RECEIPT_FOLDER = "receipts"
OUTFIT_FOLDER  = "outfit_images"

# Base directory — resolves correctly on both localhost and Streamlit Cloud
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Map outfit types to their preview images
OUTFIT_IMAGES = {
    "Agbada":  os.path.join(BASE_DIR, OUTFIT_FOLDER, "agbada.jpg"),
    "Senator": os.path.join(BASE_DIR, OUTFIT_FOLDER, "senator.jpg"),
    "Suit":    os.path.join(BASE_DIR, OUTFIT_FOLDER, "suit.jpg"),
    "Kaftan":  os.path.join(BASE_DIR, OUTFIT_FOLDER, "kaftan.jpg"),
}

def _secret(key: str, default: str = "") -> str:
    """Read from env first, then Streamlit secrets, then default."""
    val = (os.getenv(key) or "").strip()
    if not val:
        try:
            val = str(st.secrets.get(key, default) or "").strip()
        except Exception:
            val = default
    return val or default

ADMIN_USERNAME = _secret("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = _secret("ADMIN_PASSWORD", "nedee123")

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(RECEIPT_FOLDER, exist_ok=True)

# ── FIELDS ───────────────────────────────────────────────────
FIELDS = [
    "Order ID", "Name", "Phone", "Email", "Outfit Type", "Unit",
    "Date Created", "Expected Delivery Date",
    "Amount Paid",
    "Receipt File", "Design Photo", "Customer Notes",
    "Chest", "Stomach", "Shoulder", "Sleeve Length",
    "Neck", "Round Sleeve", "Top Length",
    "Trouser Length", "Trouser-waist", "Hips",
    "Laps", "Knee", "Ankle"
]

UPPER_BODY = ["Chest", "Stomach", "Shoulder", "Sleeve Length",
              "Neck", "Round Sleeve", "Top Length"]
LOWER_BODY = ["Trouser Length", "Trouser-waist", "Hips", "Laps", "Knee", "Ankle"]

# ── HELPERS ──────────────────────────────────────────────────
def ensure_file():
    if not os.path.exists(FILE_NAME):
        pd.DataFrame(columns=FIELDS).to_csv(FILE_NAME, index=False)


@st.cache_data
def load_data() -> pd.DataFrame:
    ensure_file()
    df = pd.read_csv(FILE_NAME, dtype=str)
    for col in FIELDS:
        if col not in df.columns:
            df[col] = ""
    df = df.fillna("")
    return df


def save_data(data: dict):
    df = load_data()
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_csv(FILE_NAME, index=False)
    st.cache_data.clear()


def update_record(index: int, data: dict):
    df = load_data()
    for key, value in data.items():
        df[key] = df[key].astype(str)   # ensure column is string before assignment
        df.at[index, key] = str(value)
    df.to_csv(FILE_NAME, index=False)
    st.cache_data.clear()


def delete_record(index: int):
    df = load_data()
    df = df.drop(index=index).reset_index(drop=True)
    df.to_csv(FILE_NAME, index=False)
    st.cache_data.clear()


def validate_phone(phone: str) -> bool:
    return bool(re.match(r'^[0-9+\-\s]{7,15}$', phone)) if phone else True


def generate_order_id() -> str:
    """Generate a unique order tracking ID like NEC-2026-A3F7."""
    suffix = uuid.uuid4().hex[:4].upper()
    year   = datetime.now().year
    return f"NEC-{year}-{suffix}"


def is_overdue(row) -> bool:
    try:
        delivery = pd.to_datetime(row["Expected Delivery Date"])
        return delivery < pd.Timestamp(date.today())
    except Exception:
        return False


def generate_pdf_receipt(record: dict) -> bytes:
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "NE CLOTHIERS", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, "Premium Tailoring Measurement System", ln=True, align="C")
    pdf.ln(6)
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    def row(label, value):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(60, 8, label + ":", border=0)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, str(value), ln=True)

    for label, key in [
        ("Order ID",        "Order ID"),
        ("Customer Name",   "Name"),
        ("Phone",           "Phone"),
        ("Outfit Type",     "Outfit Type"),
        ("Unit",            "Unit"),
        ("Date Created",    "Date Created"),
        ("Delivery Date",   "Expected Delivery Date"),
        ("Amount Paid",     "Amount Paid"),
        ("Notes",           "Customer Notes"),
    ]:
        val = record.get(key, "")
        if key == "Amount Paid":
            try:
                val = f"NGN {float(val):,.0f}"
            except (ValueError, TypeError):
                val = str(val)
        row(label, val)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Measurements", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    meas_fields = UPPER_BODY + LOWER_BODY
    for i in range(0, len(meas_fields), 2):
        f1 = meas_fields[i]
        f2 = meas_fields[i + 1] if i + 1 < len(meas_fields) else ""
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(60, 8, f1 + ":")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(40, 8, str(record.get(f1, "-")))
        if f2:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(50, 8, f2 + ":")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 8, str(record.get(f2, "-")), ln=True)
        else:
            pdf.ln()

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 8, "Thank you for choosing NE Clothiers.", ln=True, align="C")

    return bytes(pdf.output())


def validate_email(email: str) -> bool:
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email)) if email else False


def send_order_confirmation_email(record: dict) -> tuple[bool, str]:
    """Send order confirmation with PDF receipt to the customer's email."""
    # Re-load .env each call so credentials are always fresh
    load_dotenv(override=True)

    # Fall back to Streamlit secrets if env vars are missing (Streamlit Cloud)
    def _get(key: str, default: str = "") -> str:
        val = (os.getenv(key) or "").strip()
        if not val:
            try:
                val = str(st.secrets.get(key, default) or "").strip()
            except Exception:
                val = default
        return val or default
    
    sender   = _get("EMAIL_SENDER")
    password = _get("EMAIL_PASSWORD").replace(" ", "")
    host     = _get("EMAIL_SMTP_HOST", "smtp.gmail.com")
    port     = int(_get("EMAIL_SMTP_PORT", "587") or 587)

    if not sender or not password:
        return False, "Email credentials not configured in .env (EMAIL_SENDER / EMAIL_PASSWORD)."

    recipient = record.get("Email", "").strip()
    if not recipient:
        return False, "No customer email address on record."

    try:
        pdf_bytes = generate_pdf_receipt(record)

        msg = MIMEMultipart()
        msg["From"]    = sender
        msg["To"]      = recipient
        msg["Subject"] = f"NE Clothiers — Order Confirmation {record.get('Order ID', '')}"

        body = f"""Dear {record.get('Name', 'Customer')},

Thank you for choosing NE Clothiers! Your measurement has been recorded successfully.

Order Details:
  Order ID        : {record.get('Order ID', '—')}
  Outfit          : {record.get('Outfit Type', '—')}
  Unit            : {record.get('Unit', '—')}
  Date            : {record.get('Date Created', '—')}
  Expected Delivery: {record.get('Expected Delivery Date', '—') or '—'}
  Amount Paid     : ₦{float(record.get('Amount Paid') or 0):,.0f}

Please find your full measurement receipt attached as a PDF.
Keep your Order ID handy — you can use it to track your order status at any time.

Warm regards,
NE Clothiers Team"""

        msg.attach(MIMEText(body, "plain"))

        # Attach PDF receipt
        part = MIMEBase("application", "octet-stream")
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename=receipt_{record.get('Order ID', 'order')}.pdf"
        )
        msg.attach(part)

        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())

        return True, f"Confirmation sent to {recipient}"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Check EMAIL_SENDER and EMAIL_PASSWORD in .env."
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"



if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "pending_order_id" not in st.session_state:
    st.session_state.pending_order_id = None
if "just_saved_order" not in st.session_state:
    st.session_state.just_saved_order = False
if "just_submitted_order" not in st.session_state:
    st.session_state.just_submitted_order = False
if "show_ai_prompt" not in st.session_state:
    st.session_state.show_ai_prompt = False
if "ai_prompt_pending" not in st.session_state:
    st.session_state.ai_prompt_pending = False
if "ai_front_bytes" not in st.session_state:
    st.session_state["ai_front_bytes"] = None
if "ai_back_bytes" not in st.session_state:
    st.session_state["ai_back_bytes"] = None
if "ai_front_type" not in st.session_state:
    st.session_state["ai_front_type"] = "image/jpeg"
if "ai_back_type" not in st.session_state:
    st.session_state["ai_back_type"] = "image/jpeg"

# ── CUSTOM CSS ───────────────────────────────────────────────
st.markdown(f"""
<style>
.stApp {{
    background-color: {BG_COLOR};
}}
h1, h2, h3, h4 {{
    color: white;
    text-align: center;
}}
[data-testid="stForm"] {{
    background-color: {CARD_COLOR};
    padding: 16px 20px;
    border-radius: 16px;
    border: 1px solid #2563EB33;
}}
/* Tighten vertical spacing inside forms */
[data-testid="stForm"] .stTextInput,
[data-testid="stForm"] .stNumberInput,
[data-testid="stForm"] .stSelectbox,
[data-testid="stForm"] .stRadio,
[data-testid="stForm"] .stFileUploader,
[data-testid="stForm"] .stTextArea {{
    margin-bottom: 0px !important;
}}
[data-testid="stForm"] .stTextInput > div,
[data-testid="stForm"] .stNumberInput > div,
[data-testid="stForm"] .stSelectbox > div {{
    margin-bottom: 0px !important;
}}
/* Tighten expander padding */
[data-testid="stExpander"] > div:first-child {{
    padding: 6px 12px !important;
}}
[data-testid="stExpander"] details summary {{
    padding: 6px 0 !important;
}}
.block-container {{
    padding-top: 2rem;
    padding-bottom: 1rem;
}}
.stSelectbox > div,
.stRadio > div {{
    color: white;
}}
.stButton > button {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border-radius: 10px;
    font-weight: bold;
    height: 42px;
    border: none;
}}
.stButton > button:hover {{
    background-color: #1D4ED8;
    color: white;
}}
.stDownloadButton > button {{
    background-color: #059669;
    color: white;
    border-radius: 10px;
    font-weight: bold;
    border: none;
}}
.stDownloadButton > button:hover {{
    background-color: #047857;
}}
div[data-testid="stSidebarContent"] {{
    background-color: #040F2E;
}}
</style>
""", unsafe_allow_html=True)

# ── HEADER ───────────────────────────────────────────────────
st.title("✂️ NE CLOTHIERS")
st.markdown(
    "<p style='color:#93C5FD; text-align:center; font-size:16px; margin-top:-15px; letter-spacing:1px;'>Premium Tailoring Measurement System</p>",
    unsafe_allow_html=True
)

# ── SIDEBAR ──────────────────────────────────────────────────
with st.sidebar:
    if os.path.exists(os.path.join(BASE_DIR, "ne.png")):
        st.image(os.path.join(BASE_DIR, "ne.png"), width=110)
    st.title("NE Clothiers")
    st.markdown("---")

    # All users see the same nav items — Dashboard is hidden inside Admin
    _nav_options = ["📋 New Measurement", "📐 AI Measurements", "🔍 Order Tracking", "🔐 Admin"]

    # Handle programmatic navigation
    if "_nav_override" in st.session_state:
        st.session_state["_nav_radio"] = st.session_state.pop("_nav_override")
    elif "pending_order_id" in st.session_state and st.session_state.pending_order_id:
        st.session_state["_nav_radio"] = "🔍 Order Tracking"
    elif "_nav_radio" not in st.session_state:
        st.session_state["_nav_radio"] = "📋 New Measurement"

    page = st.radio(
        "Navigate",
        _nav_options,
        key="_nav_radio"
    )
    st.markdown("---")

    if st.session_state.logged_in:
        st.success("Admin logged in")
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE: ADMIN (login-gated — dashboard lives here)
# ════════════════════════════════════════════════════════════
if page == "🔐 Admin":
    if not st.session_state.logged_in:
        # Show a plain login form — no mention of "admin" or "dashboard"
        st.markdown(
            "<div style='max-width:400px; margin:60px auto 0 auto;'>",
            unsafe_allow_html=True
        )
        st.markdown("#### Sign In")
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
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        # ── DASHBOARD ────────────────────────────────────────
        st.subheader("📊 Dashboard")
        df = load_data()

        if df.empty:
            st.info("No records yet. Add your first customer measurement to see stats here.")
        else:
            total      = len(df)

            today = pd.Timestamp(date.today())
            try:
                df["_delivery_dt"] = pd.to_datetime(df["Expected Delivery Date"], errors="coerce")
                due_this_week = df[
                    (df["_delivery_dt"] >= today) &
                    (df["_delivery_dt"] <= today + pd.Timedelta(days=7))
                ]
                overdue = df[df["_delivery_dt"] < today]
            except Exception:
                due_this_week = pd.DataFrame()
                overdue       = pd.DataFrame()

            total_collected = pd.to_numeric(df["Amount Paid"], errors="coerce").sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("👥 Total Customers", total)
            c2.metric("📅 Due This Week",   len(due_this_week))
            c3.metric("⚠️ Overdue",         len(overdue))

            st.markdown(f"### 💰 Total Collected: ₦{total_collected:,.0f}")
            st.markdown("---")

            st.markdown("**Outfit Type Breakdown**")
            st.bar_chart(df["Outfit Type"].value_counts())

            st.markdown("---")
            st.markdown("**🕐 5 Most Recent Entries**")
            recent_cols = ["Order ID", "Name", "Phone", "Outfit Type", "Expected Delivery Date"]
            st.dataframe(df.tail(5)[recent_cols].iloc[::-1], use_container_width=True)

            if not overdue.empty:
                st.markdown("---")
                st.markdown("**🚨 Overdue Orders**")
                overdue_cols = ["Order ID", "Name", "Phone", "Outfit Type", "Expected Delivery Date"]
                st.dataframe(overdue[overdue_cols], use_container_width=True)

        st.markdown("---")

        # ── ALL RECORDS TABLE ─────────────────────────────────
        st.markdown("#### 🗂️ All Records")
        df_all = load_data()

        fa1, fa2 = st.columns([2, 1])
        with fa1:
            a_search = st.text_input("🔍 Search", placeholder="Name, phone, or Order ID...")
        with fa2:
            outfit_opts = ["All"] + sorted(df_all["Outfit Type"].dropna().unique().tolist())
            a_outfit = st.selectbox("Outfit", outfit_opts)

        filtered = df_all.copy()
        if a_search:
            q = a_search.lower()
            filtered = filtered[
                filtered["Name"].astype(str).str.lower().str.contains(q, na=False) |
                filtered["Phone"].astype(str).str.lower().str.contains(q, na=False) |
                filtered["Order ID"].astype(str).str.lower().str.contains(q, na=False)
            ]
        if a_outfit != "All":
            filtered = filtered[filtered["Outfit Type"] == a_outfit]

        st.caption(f"Showing {len(filtered)} of {len(df_all)} records")
        st.dataframe(filtered, use_container_width=True, height=300)

        # ── EDIT / DELETE ─────────────────────────────────────
        st.markdown("---")
        st.markdown("#### ✏️ Edit or Delete a Record")

        if not filtered.empty:
            rec_opts = {
                f"{r['Order ID']} — {r['Name']} ({r.get('Date Created','')})": idx
                for idx, r in filtered.iterrows()
            }
            sel_label = st.selectbox("Select record", list(rec_opts.keys()))
            sel_idx   = rec_opts[sel_label]
            sel_row   = df_all.loc[sel_idx]

            ec1, ec2 = st.columns(2)

            with ec1:
                with st.expander("✏️ Edit"):
                    outfit_list = ["Agbada", "Senator", "Suit", "Kaftan"]

                    def safe_index(lst, val, default=0):
                        return lst.index(val) if val in lst else default

                    with st.form("edit_form"):
                        e_name   = st.text_input("Name",  value=str(sel_row.get("Name", "")))
                        e_phone  = st.text_input("Phone", value=str(sel_row.get("Phone", "")))
                        e_outfit = st.selectbox("Outfit Type", outfit_list,
                                                index=safe_index(outfit_list, sel_row.get("Outfit Type", "")))
                        e_amount = st.number_input("Amount Paid (₦)",
                                                   value=float(sel_row.get("Amount Paid") or 0),
                                                   min_value=0.0, step=1000.0)
                        e_notes  = st.text_area("Notes", value=str(sel_row.get("Customer Notes", "")))
                        save_edit = st.form_submit_button("💾 Save Changes")

                    if save_edit:
                        update_record(sel_idx, {
                            "Name":           e_name,
                            "Phone":          e_phone,
                            "Outfit Type":    e_outfit,
                            "Amount Paid":    e_amount,
                            "Customer Notes": e_notes,
                        })
                        st.success("Record updated.")
                        st.rerun()

            with ec2:
                with st.expander("🗑️ Delete"):
                    st.warning(f"Delete **{sel_row.get('Name', '')}** ({sel_row.get('Order ID', '')})?")
                    confirm = st.text_input("Type the customer name to confirm")
                    if st.button("🗑️ Confirm Delete", type="primary"):
                        if confirm.strip().lower() == str(sel_row.get("Name", "")).strip().lower():
                            delete_record(sel_idx)
                            st.success("Record deleted.")
                            st.rerun()
                        else:
                            st.error("Name does not match.")

        # ── PDF RECEIPT ───────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 🧾 Generate PDF Receipt")
        if not filtered.empty:
            pdf_opts = {
                f"{r['Order ID']} — {r['Name']}": idx
                for idx, r in filtered.iterrows()
            }
            pdf_label = st.selectbox("Select customer", list(pdf_opts.keys()), key="pdf_sel")
            pdf_row   = df_all.loc[pdf_opts[pdf_label]].to_dict()
            pdf_bytes = generate_pdf_receipt(pdf_row)
            st.download_button(
                "📄 Download PDF Receipt",
                data=pdf_bytes,
                file_name=f"receipt_{pdf_row.get('Order ID','order')}.pdf",
                mime="application/pdf"
            )

        # ── EXPORTS ───────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📥 Export Records")
        ex1, ex2 = st.columns(2)
        with ex1:
            st.download_button(
                "⬇️ Download CSV",
                data=filtered.to_csv(index=False),
                file_name="NE_Clothiers_measurements.csv",
                mime="text/csv"
            )
        with ex2:
            xls = io.BytesIO()
            filtered.to_excel(xls, index=False, engine="openpyxl")
            st.download_button(
                "⬇️ Download Excel",
                data=xls.getvalue(),
                file_name="NE_Clothiers_measurements.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ════════════════════════════════════════════════════════════
# PAGE: NEW MEASUREMENT
# ════════════════════════════════════════════════════════════
elif page == "📋 New Measurement":
    st.subheader("Let's Serve You")

    # Columns are defined OUTSIDE both form and selector so everything
    # sits side-by-side in one unified layout.
    col1, col2 = st.columns([1, 1])

    # ── LEFT COLUMN: outfit selector (live) + customer info form ──
    with col1:
        st.markdown("#### 👔 Outfit Type")
        outfit = st.selectbox(
            "Outfit Type",
            ["Agbada", "Senator", "Suit", "Kaftan"],
            key="outfit_select",
            label_visibility="collapsed"
        )
        _img_path = OUTFIT_IMAGES.get(outfit)
        if _img_path and os.path.exists(_img_path):
            st.image(_img_path, caption=f"{outfit} Style", width=220)

        st.markdown("---")

        with st.form("measurement_form", clear_on_submit=True):
            st.markdown("#### Customer Info")
            name  = st.text_input("Customer Name *")
            phone = st.text_input("Phone Number *")
            email = st.text_input("Email Address *", placeholder="customer@example.com")
            unit  = st.radio("Measurement Unit", ["cm", "inches"], horizontal=True)
            st.markdown("---")
            st.markdown("**Design / Style Photo**")
            st.caption("Upload a photo of the design or style the customer wants.")
            design_photo = st.file_uploader(
                "Upload design photo",
                type=["png", "jpg", "jpeg"],
                label_visibility="collapsed",
                key="design_photo"
            )
            if design_photo:
                st.image(design_photo, caption="Design Preview", width=180)

            submitted = st.form_submit_button("💾 Save Measurement", use_container_width=True)

    # ── RIGHT COLUMN: body measurements ──
    with col2:
        st.markdown("#### Body Measurements")
        meas_values = {}

        with st.expander("👕 Upper Body", expanded=True):
            for field in UPPER_BODY:
                meas_values[field] = st.text_input(
                    f"{field} *",
                    placeholder=f"Enter {field.lower()}",
                    key=f"meas_{field}"
                )

        with st.expander("👖 Lower Body", expanded=True):
            for field in LOWER_BODY:
                meas_values[field] = st.text_input(
                    f"{field} *",
                    placeholder=f"Enter {field.lower()}",
                    key=f"meas_{field}"
                )

    if submitted:
        errors = []
        if not name.strip():
            errors.append("Customer name is required.")
        if not phone.strip():
            errors.append("Phone number is required.")
        elif not validate_phone(phone):
            errors.append("Phone number format is invalid.")
        if not email.strip():
            errors.append("Email address is required.")
        elif not validate_email(email.strip()):
            errors.append("Email address format is invalid.")
        for field, val in meas_values.items():
            if not val.strip():
                errors.append(f"{field} is required.")
            elif not val.replace('.', '', 1).isdigit():
                errors.append(f"{field} must be a number (e.g. 42 or 42.5).")

        if errors:
            for e in errors:
                st.error(e)
        else:
            order_id     = generate_order_id()
            outfit_saved = st.session_state.get("outfit_select", "Agbada")

            design_filename = ""
            if design_photo is not None:
                design_filename = design_photo.name
                with open(os.path.join(IMAGE_FOLDER, design_filename), "wb") as f:
                    f.write(design_photo.getbuffer())

            data = {
                "Order ID":               order_id,
                "Name":                   name.strip(),
                "Phone":                  phone.strip(),
                "Email":                  email.strip(),
                "Outfit Type":            outfit_saved,
                "Unit":                   unit,
                "Date Created":           datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Expected Delivery Date": "",
                "Amount Paid":            0,
                "Receipt File":           "",
                "Design Photo":           design_filename,
                "Customer Notes":         "",
                **meas_values
            }

            save_data(data)
            st.session_state.pending_order_id = order_id
            st.session_state.just_saved_order = True
            st.success(f"✅ Measurement saved! Order ID: **{order_id}**")
            st.info(f"**{name.strip()}** | {outfit_saved}")

            # Send confirmation email to customer
            ok, msg = send_order_confirmation_email(data)
            if ok:
                st.success(f"📧 {msg}")
            else:
                st.warning(f"📧 Email not sent: {msg}")

# ── POST-SUBMIT: continue button only ────────────────────────
if st.session_state.just_saved_order:
    st.markdown("---")
    st.markdown("### 📋 Next Step: Submit Order Details")
    st.markdown(
        "Measurements saved. Click below to add delivery date, "
        "amount paid, and any special notes."
    )
    if st.button("➡️ Continue to Order Details", type="primary", use_container_width=True):
        st.session_state.just_saved_order = False
        st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE: AI MEASUREMENTS (MediaPipe pose estimation)
# ════════════════════════════════════════════════════════════
elif page == "📐 AI Measurements":
    st.subheader("📐 AI Body Measurement Assistant")
    st.markdown(
        "<p style='color:#93C5FD; text-align:center;'>Upload a clear front photo of the customer. "
        "MediaPipe will detect body landmarks and estimate measurements from your height.</p>",
        unsafe_allow_html=True
    )

    with st.expander("📸 Photo Guidelines", expanded=True):
        st.markdown("""
**For best results:**
- Stand straight against a plain, well-lit background
- Wear form-fitting clothing (no baggy outfits)
- Arms slightly away from the body
- Full body visible from head to toe
- Face the camera directly
- **Height is required** — it is used as the scale reference for all measurements
        """)

    ai_col1, ai_col2 = st.columns(2)

    with ai_col1:
        st.markdown("#### 🧍 Front View")
        front_photo = st.file_uploader(
            "Upload front photo",
            type=["png", "jpg", "jpeg"],
            key="ai_front",
            label_visibility="collapsed"
        )
        if front_photo:
            st.session_state["ai_front_bytes"] = front_photo.read()
            st.session_state["ai_front_type"]  = front_photo.type
            st.image(io.BytesIO(st.session_state["ai_front_bytes"]), caption="Front View", use_container_width=True)
        elif st.session_state.get("ai_front_bytes"):
            st.image(io.BytesIO(st.session_state["ai_front_bytes"]), caption="Front View", use_container_width=True)

    with ai_col2:
        st.markdown("#### 🧍\u200d♂️ Back View (optional)")
        back_photo = st.file_uploader(
            "Upload back photo",
            type=["png", "jpg", "jpeg"],
            key="ai_back",
            label_visibility="collapsed"
        )
        if back_photo:
            st.session_state["ai_back_bytes"] = back_photo.read()
            st.session_state["ai_back_type"]  = back_photo.type
            st.image(io.BytesIO(st.session_state["ai_back_bytes"]), caption="Back View", use_container_width=True)
        elif st.session_state.get("ai_back_bytes"):
            st.image(io.BytesIO(st.session_state["ai_back_bytes"]), caption="Back View", use_container_width=True)

    st.markdown("---")

    ai_unit   = st.radio("Preferred measurement unit", ["cm", "inches"], horizontal=True, key="ai_unit")
    ai_height = st.text_input(
        "Customer height * (required for accurate measurements)",
        placeholder="e.g. 175  (just the number, matching the unit selected above)",
        key="ai_height"
    )

    btn_col1, btn_col2 = st.columns([3, 1])
    with btn_col1:
        scan_btn = st.button("🤖 Scan & Estimate Measurements", type="primary", use_container_width=True)
    with btn_col2:
        clear_btn = st.button("🗑️ Clear Photos", use_container_width=True)

    if clear_btn:
        st.session_state["ai_front_bytes"] = None
        st.session_state["ai_back_bytes"]  = None
        st.session_state.pop("ai_measurements", None)
        st.session_state.pop("ai_annotated", None)
        st.rerun()

    if scan_btn:
        has_front = bool(st.session_state.get("ai_front_bytes"))
        if not has_front:
            st.error("Please upload a front photo before scanning.")
        elif not ai_height.strip():
            st.error("Height is required — it is used to scale all measurements accurately.")
        else:
            try:
                height_val = float(re.sub(r"[^\d.]", "", ai_height.strip()))
                height_cm  = height_val if ai_unit == "cm" else height_val * 2.54
            except ValueError:
                height_cm = None
                st.error("Could not parse height. Enter a plain number, e.g. 175")

            if height_cm:
                with st.spinner("🤖 Detecting body landmarks… please wait…"):
                    try:
                        import urllib.request
                        import numpy as np
                        from PIL import Image as PILImage
                        import mediapipe as mp
                        from mediapipe.tasks import python as mp_python
                        from mediapipe.tasks.python import vision as mp_vision
                        from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode

                        # ── Download model if not present ──────────────
                        MODEL_PATH = os.path.join(BASE_DIR, "pose_landmarker.task")
                        MODEL_URL  = (
                            "https://storage.googleapis.com/mediapipe-models/"
                            "pose_landmarker/pose_landmarker_heavy/float16/latest/"
                            "pose_landmarker_heavy.task"
                        )
                        if not os.path.exists(MODEL_PATH):
                            with st.spinner("📥 Downloading pose model (one-time, ~25 MB)…"):
                                urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

                        # ── Load image ─────────────────────────────────
                        pil_img    = PILImage.open(io.BytesIO(st.session_state["ai_front_bytes"])).convert("RGB")
                        img_w_px, img_h_px = pil_img.size
                        img_np     = np.array(pil_img)
                        mp_image   = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_np)

                        # ── Run pose landmarker ────────────────────────
                        options = PoseLandmarkerOptions(
                            base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
                            running_mode=RunningMode.IMAGE,
                            num_poses=1,
                            min_pose_detection_confidence=0.5,
                            min_pose_presence_confidence=0.5,
                            min_tracking_confidence=0.5,
                        )
                        with PoseLandmarker.create_from_options(options) as landmarker:
                            result = landmarker.detect(mp_image)

                        if not result.pose_landmarks or len(result.pose_landmarks) == 0:
                            st.error(
                                "Could not detect a person in the photo. "
                                "Make sure the full body is visible against a plain background."
                            )
                        else:
                            lm = result.pose_landmarks[0]  # list of NormalizedLandmark

                            # Landmark indices (same as classic API)
                            # 0=nose 7=L_ear 8=R_ear 11=L_shoulder 12=R_shoulder
                            # 13=L_elbow 14=R_elbow 15=L_wrist 16=R_wrist
                            # 23=L_hip 24=R_hip 25=L_knee 26=R_knee 27=L_ankle 28=R_ankle
                            IDX = {
                                "NOSE":          0,  "LEFT_EAR": 7,  "RIGHT_EAR": 8,
                                "LEFT_SHOULDER": 11, "RIGHT_SHOULDER": 12,
                                "LEFT_ELBOW":    13, "RIGHT_ELBOW":    14,
                                "LEFT_WRIST":    15, "RIGHT_WRIST":    16,
                                "LEFT_HIP":      23, "RIGHT_HIP":      24,
                                "LEFT_KNEE":     25, "RIGHT_KNEE":     26,
                                "LEFT_ANKLE":    27, "RIGHT_ANKLE":    28,
                            }

                            def lx(name): return lm[IDX[name]].x
                            def ly(name): return lm[IDX[name]].y

                            def horiz(a, b): return abs(lx(a) - lx(b)) * img_w_px
                            def vert(a, b):  return abs(ly(a) - ly(b)) * img_h_px
                            def euc(a, b):
                                dx = (lx(a) - lx(b)) * img_w_px
                                dy = (ly(a) - ly(b)) * img_h_px
                                return (dx**2 + dy**2) ** 0.5

                            # Scale factor
                            nose_y_px  = ly("NOSE")   * img_h_px
                            ankle_y_px = ((ly("LEFT_ANKLE") + ly("RIGHT_ANKLE")) / 2) * img_h_px
                            span_px    = abs(ankle_y_px - nose_y_px) / 0.92
                            ppcm       = span_px / height_cm

                            def cm(px):  return px / ppcm
                            def fmt(v):  return f"{v:.1f}" if ai_unit == "cm" else f"{v/2.54:.1f}"

                            shoulder_w = cm(horiz("LEFT_SHOULDER", "RIGHT_SHOULDER"))
                            hip_w      = cm(horiz("LEFT_HIP",      "RIGHT_HIP"))
                            ear_w      = cm(horiz("LEFT_EAR",      "RIGHT_EAR"))

                            chest_cm_val        = shoulder_w * 0.85 * 3.14159 * 0.95
                            stomach_cm_val      = hip_w      * 0.85 * 3.14159 * 0.95
                            hip_circ_cm         = hip_w             * 3.14159 * 0.98
                            neck_cm_val         = ear_w      * 0.85 * 3.14159
                            round_sleeve_cm_val = shoulder_w * 0.30 * 3.14159 * 0.90

                            sleeve_cm_val = cm(
                                euc("LEFT_SHOULDER", "LEFT_ELBOW") +
                                euc("LEFT_ELBOW",    "LEFT_WRIST")
                            )
                            top_len_cm_val   = cm(vert("LEFT_SHOULDER", "LEFT_HIP"))
                            trouser_cm_val   = cm(vert("LEFT_HIP",      "LEFT_ANKLE"))
                            trouser_w_cm_val = stomach_cm_val * 1.02
                            laps_cm_val      = cm(horiz("LEFT_HIP",   "LEFT_KNEE")  * 0.6) * 3.14159 * 0.95
                            knee_cm_val      = cm(euc("LEFT_KNEE",  "RIGHT_KNEE")   * 0.35) * 3.14159 * 0.90
                            ankle_cm_val     = cm(euc("LEFT_ANKLE", "RIGHT_ANKLE")  * 0.30) * 3.14159 * 0.85

                            # ── Draw landmarks on image ────────────────
                            annotated = img_np.copy()
                            CONNECTIONS = [
                                ("LEFT_SHOULDER","RIGHT_SHOULDER"),("LEFT_SHOULDER","LEFT_ELBOW"),
                                ("LEFT_ELBOW","LEFT_WRIST"),("RIGHT_SHOULDER","RIGHT_ELBOW"),
                                ("RIGHT_ELBOW","RIGHT_WRIST"),("LEFT_SHOULDER","LEFT_HIP"),
                                ("RIGHT_SHOULDER","RIGHT_HIP"),("LEFT_HIP","RIGHT_HIP"),
                                ("LEFT_HIP","LEFT_KNEE"),("LEFT_KNEE","LEFT_ANKLE"),
                                ("RIGHT_HIP","RIGHT_KNEE"),("RIGHT_KNEE","RIGHT_ANKLE"),
                            ]
                            import cv2
                            for a, b in CONNECTIONS:
                                pt1 = (int(lx(a)*img_w_px), int(ly(a)*img_h_px))
                                pt2 = (int(lx(b)*img_w_px), int(ly(b)*img_h_px))
                                cv2.line(annotated, pt1, pt2, (147, 197, 253), 2)
                            for name in IDX:
                                pt = (int(lx(name)*img_w_px), int(ly(name)*img_h_px))
                                cv2.circle(annotated, pt, 4, (37, 99, 235), -1)

                            st.session_state["ai_annotated"] = annotated
                            st.session_state["ai_measurements"] = {
                                "Chest":          fmt(chest_cm_val),
                                "Stomach":        fmt(stomach_cm_val),
                                "Shoulder":       fmt(shoulder_w),
                                "Sleeve Length":  fmt(sleeve_cm_val),
                                "Neck":           fmt(neck_cm_val),
                                "Round Sleeve":   fmt(round_sleeve_cm_val),
                                "Top Length":     fmt(top_len_cm_val),
                                "Trouser Length": fmt(trouser_cm_val),
                                "Trouser-waist":  fmt(trouser_w_cm_val),
                                "Hips":           fmt(hip_circ_cm),
                                "Laps":           fmt(laps_cm_val),
                                "Knee":           fmt(knee_cm_val),
                                "Ankle":          fmt(ankle_cm_val),
                                "confidence": "medium",
                                "notes": (
                                    "Estimated from MediaPipe pose landmarks. "
                                    "Circumference values use anatomical ratio approximations. "
                                    "Always verify with a tape measure before cutting."
                                )
                            }
                            st.session_state["ai_unit_result"] = ai_unit
                            st.rerun()

                    except ImportError as e:
                        st.error(f"Missing dependency: {e}. Make sure mediapipe and opencv-python are in requirements.txt.")
                    except Exception as e:
                        st.error(f"Scan failed: {e}")

    # ── DISPLAY RESULTS ───────────────────────────────────────
    if "ai_measurements" in st.session_state and st.session_state["ai_measurements"]:
        ai_result   = st.session_state["ai_measurements"]
        result_unit = st.session_state.get("ai_unit_result", "cm")
        confidence  = ai_result.get("confidence", "medium")
        notes       = ai_result.get("notes", "")

        if "ai_annotated" in st.session_state:
            st.markdown("#### 🦴 Detected Landmarks")
            st.image(st.session_state["ai_annotated"], caption="Pose landmarks detected", use_container_width=True)

        conf_color = {"high": "#10B981", "medium": "#F59E0B", "low": "#EF4444"}.get(confidence, "#F59E0B")
        st.markdown(
            f"<p style='color:{conf_color}; font-weight:bold; text-align:center;'>"
            f"Confidence: {confidence.upper()}</p>",
            unsafe_allow_html=True
        )
        if notes:
            st.info(f"💬 {notes}")

        st.markdown("#### 📏 Estimated Measurements")
        res_col1, res_col2 = st.columns(2)

        with res_col1:
            st.markdown("**Upper Body**")
            for field in UPPER_BODY:
                val = ai_result.get(field, "—")
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"padding:6px 12px;background:#1E3A6E;border-radius:8px;margin-bottom:4px;'>"
                    f"<span style='color:#93C5FD;'>{field}</span>"
                    f"<span style='color:white;font-weight:bold;'>{val} {result_unit}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        with res_col2:
            st.markdown("**Lower Body**")
            for field in LOWER_BODY:
                val = ai_result.get(field, "—")
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"padding:6px 12px;background:#1E3A6E;border-radius:8px;margin-bottom:4px;'>"
                    f"<span style='color:#93C5FD;'>{field}</span>"
                    f"<span style='color:white;font-weight:bold;'>{val} {result_unit}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("---")
        st.markdown(
            "✅ **Happy with these estimates?** Head to **📋 New Measurement** and enter them manually, "
            "or use the form below to save them directly to a new order."
        )

        with st.expander("💾 Save AI Measurements as New Order", expanded=False):
            with st.form("ai_save_form"):
                ais_name   = st.text_input("Customer Name *")
                ais_phone  = st.text_input("Phone Number *")
                ais_email  = st.text_input("Email Address *", placeholder="customer@example.com")
                ais_outfit = st.selectbox("Outfit Type", ["Agbada", "Senator", "Suit", "Kaftan"])
                ais_unit   = st.radio("Unit", ["cm", "inches"], horizontal=True,
                                      index=0 if st.session_state.get("ai_unit_result", "cm") == "cm" else 1)
                ais_submit = st.form_submit_button("💾 Save Order", use_container_width=True)

            if ais_submit:
                ais_errors = []
                if not ais_name.strip():
                    ais_errors.append("Customer name is required.")
                if not ais_phone.strip():
                    ais_errors.append("Phone number is required.")
                elif not validate_phone(ais_phone):
                    ais_errors.append("Phone number format is invalid.")
                if not ais_email.strip():
                    ais_errors.append("Email address is required.")
                elif not validate_email(ais_email.strip()):
                    ais_errors.append("Email address format is invalid.")

                if ais_errors:
                    for e in ais_errors:
                        st.error(e)
                else:
                    order_id = generate_order_id()
                    meas = {f: str(ai_result.get(f, "")) for f in UPPER_BODY + LOWER_BODY}
                    data = {
                        "Order ID":               order_id,
                        "Name":                   ais_name.strip(),
                        "Phone":                  ais_phone.strip(),
                        "Email":                  ais_email.strip(),
                        "Outfit Type":            ais_outfit,
                        "Unit":                   ais_unit,
                        "Date Created":           datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Expected Delivery Date": "",
                        "Amount Paid":            0,
                        "Receipt File":           "",
                        "Design Photo":           "",
                        "Customer Notes":         f"Measurements estimated by MediaPipe AI (confidence: {confidence})",
                        **meas
                    }
                    save_data(data)
                    st.session_state.pending_order_id = order_id
                    st.success(f"✅ Order saved! Order ID: **{order_id}**")

                    ok, msg = send_order_confirmation_email(data)
                    if ok:
                        st.success(f"📧 {msg}")
                    else:
                        st.warning(f"📧 Email not sent: {msg}")

                    del st.session_state["ai_measurements"]
                    st.session_state.pop("ai_annotated", None)
# ════════════════════════════════════════════════════════════
# PAGE: ORDER TRACKING (public)
# ════════════════════════════════════════════════════════════
elif page == "🔍 Order Tracking":
    st.subheader("🔍 Track Your Order")

    df = load_data()

    # ── SEARCH ───────────────────────────────────────────────
    st.markdown("Search by your **Order ID**, **name**, or **phone number**.")

    # Pick up Order ID passed from New Measurement form (must happen before search box renders)
    found_order_id = ""
    if st.session_state.pending_order_id:
        found_order_id = st.session_state.pending_order_id
        st.session_state.pending_order_id = None  # consume it

    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_query = st.text_input(
            "Search",
            value=found_order_id,
            placeholder="e.g. NEC-2026-A3F7  or  John Doe  or  08012345678",
            label_visibility="collapsed"
        )
    with search_col2:
        search_btn = st.button("🔍 Search", use_container_width=True)

    results = pd.DataFrame()

    if search_query.strip():
        q = search_query.strip().lower()
        mask = (
            df["Order ID"].astype(str).str.lower().str.contains(q, na=False) |
            df["Name"].astype(str).str.lower().str.contains(q, na=False) |
            df["Phone"].astype(str).str.lower().str.contains(q, na=False)
        )
        results = df[mask]

        if results.empty:
            st.warning("No orders found. Check your Order ID, name, or phone number and try again.")
        else:
            st.success(f"Found {len(results)} order(s)")
            # Use the first match's Order ID to pre-fill the details form
            found_order_id = str(results.iloc[0].get("Order ID", ""))

            for row_idx, row in results.iterrows():
                order_id      = row.get("Order ID", "—")
                delivery_date = row.get("Expected Delivery Date", "—") or "—"
                amount        = float(row.get("Amount Paid") or 0)

                st.markdown(f"""
                <div style="
                    background-color: #1E3A6E;
                    border-radius: 14px;
                    padding: 22px 26px;
                    margin-bottom: 18px;
                    border-left: 5px solid #2563EB;
                ">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px;">
                        <div>
                            <p style="color:#93C5FD; margin:0 0 2px 0; font-size:12px; letter-spacing:1px;">ORDER ID</p>
                            <h2 style="color:white; margin:0 0 6px 0; font-size:22px; letter-spacing:2px;">{order_id}</h2>
                            <h3 style="color:white; margin:0 0 4px 0; font-size:17px;">{row.get("Name", "")}</h3>
                            <p style="color:#93C5FD; margin:0; font-size:13px;">
                                📱 {row.get("Phone", "—")} &nbsp;|&nbsp;
                                👔 {row.get("Outfit Type", "—")} &nbsp;|&nbsp;
                                🗓️ Placed: {row.get("Date Created", "—")}
                            </p>
                        </div>
                    </div>
                    <hr style="border-color:#2563EB44; margin: 16px 0 14px 0;">
                    <div style="display:flex; gap:40px; flex-wrap:wrap;">
                        <div>
                            <p style="color:#94A3B8; margin:0; font-size:11px; letter-spacing:1px;">EXPECTED DELIVERY</p>
                            <p style="color:white; margin:2px 0 0 0; font-size:15px; font-weight:600;">📆 {delivery_date}</p>
                        </div>
                        <div>
                            <p style="color:#94A3B8; margin:0; font-size:11px; letter-spacing:1px;">AMOUNT PAID</p>
                            <p style="color:white; margin:2px 0 0 0; font-size:15px; font-weight:600;">₦{amount:,.0f}</p>
                        </div>
                        <div>
                            <p style="color:#94A3B8; margin:0; font-size:11px; letter-spacing:1px;">NOTES</p>
                            <p style="color:white; margin:2px 0 0 0; font-size:14px;">{row.get("Customer Notes", "—") or "—"}</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # ── ORDER DETAILS FORM ───────────────────────────────────
    st.markdown("### 📝 Submit Order Details")
    st.markdown(
        "Already have an Order ID? Use this form to add your delivery date, "
        "amount paid, and notes."
    )

    # Pre-fill values from search result if available
    prefill_row      = results.iloc[0] if not results.empty else None
    default_order_id = found_order_id
    default_amount   = float(prefill_row.get("Amount Paid") or 0) if prefill_row is not None else 0.0
    default_notes    = str(prefill_row.get("Customer Notes", "") or "") if prefill_row is not None else ""

    with st.form("order_details_form", clear_on_submit=True):
        od_col1, od_col2 = st.columns([1, 1])

        with od_col1:
            od_order_id = st.text_input(
                "Order ID *",
                value=default_order_id,
                placeholder="e.g. NEC-2026-A3F7"
            )
            od_delivery = st.date_input("Expected Delivery Date")
            od_amount   = st.number_input("Amount Paid (₦)",
                                          value=default_amount,
                                          min_value=0.0, step=1000.0)
            od_notes    = st.text_area("Customer Notes",
                                       value=default_notes,
                                       placeholder="Special instructions, style preferences...")

        with od_col2:
            st.markdown("**Payment Receipt**")
            od_receipt = st.file_uploader("Upload receipt",
                                          type=["png", "jpg", "jpeg", "pdf"],
                                          label_visibility="collapsed",
                                          key="od_receipt")

        od_submit = st.form_submit_button("📤 Submit Order Details", use_container_width=True)

        if od_submit:
            if not od_order_id.strip():
                st.error("Order ID is required.")
            else:
                df_check = load_data()
                match = df_check[
                    df_check["Order ID"].astype(str).str.upper() == od_order_id.strip().upper()
                ]

                if match.empty:
                    st.error(f"No order found with ID **{od_order_id.strip()}**. Please check and try again.")
                else:
                    record_idx = match.index[0]

                    receipt_filename = str(df_check.at[record_idx, "Receipt File"] or "")

                    if od_receipt is not None:
                        receipt_filename = od_receipt.name
                        with open(os.path.join(RECEIPT_FOLDER, receipt_filename), "wb") as f:
                            f.write(od_receipt.getbuffer())

                    update_record(record_idx, {
                        "Expected Delivery Date": str(od_delivery),
                        "Amount Paid":            od_amount,
                        "Customer Notes":         od_notes,
                        "Receipt File":           receipt_filename,
                    })

                    st.success(f"✅ Order details updated for **{od_order_id.strip().upper()}**!")
                    st.info(f"Delivery: {od_delivery} | ₦{od_amount:,.0f}")

                    # Send updated order confirmation email to customer
                    updated_df = load_data()
                    updated_record = updated_df.loc[record_idx].to_dict()
                    ok, msg = send_order_confirmation_email(updated_record)
                    if ok:
                        st.success(f"📧 {msg}")
                    else:
                        st.warning(f"📧 Email not sent: {msg}")

                    st.session_state.just_submitted_order = True
                    st.session_state.ai_prompt_pending = True

    # ── THANK-YOU CARD (shown after order details are submitted) ──
    if st.session_state.just_submitted_order or st.session_state.show_ai_prompt:
        st.session_state.just_submitted_order = False
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #1E3A6E 0%, #0D2247 100%);
            border-radius: 18px;
            padding: 48px 36px;
            text-align: center;
            border: 1px solid #2563EB55;
            margin: 24px 0 10px 0;
        ">
            <p style="font-size: 56px; margin: 0 0 14px 0;">✂️</p>
            <h2 style="color: white; margin: 0 0 16px 0; font-size: 28px; letter-spacing: 1px;">
                We are happy to serve you.
            </h2>
            <p style="color: #93C5FD; font-size: 17px; line-height: 1.8; margin: 0 auto; max-width: 540px;">
                At <strong style="color: white;">NE Clothiers</strong>, we are a one customer brand,
                and we tailor for the leading man.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ── EMPTY STATE (only when no submission is pending) ─────
    if not search_query.strip() and not st.session_state.show_ai_prompt and not st.session_state.just_submitted_order:
        st.markdown("""
        <div style="
            background-color: #1E3A6E;
            border-radius: 14px;
            padding: 30px;
            text-align: center;
            margin-top: 10px;
        ">
            <p style="font-size: 48px; margin: 0;">✂️</p>
            <h3 style="color: white; margin: 10px 0 6px 0;">NE Clothiers Order Tracker</h3>
            <p style="color: #93C5FD; margin: 0;">
                Search by Order ID, name, or phone number to view your order status.
            </p>
        </div>
        """, unsafe_allow_html=True)

# ── AI PROMPT: promote pending flag, then show button ────────────────────────
if st.session_state.ai_prompt_pending:
    st.session_state.ai_prompt_pending = False
    st.session_state.show_ai_prompt = True

if st.session_state.show_ai_prompt:
    st.markdown("---")
    st.markdown(
        "<p style='color:#93C5FD; text-align:center; font-size:15px;'>"
        "Would you like to capture measurements using AI?</p>",
        unsafe_allow_html=True
    )
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button("📐 Try AI Body Measurement", use_container_width=True, key="ai_prompt_btn"):
            st.session_state.show_ai_prompt = False
            st.session_state["_nav_override"] = "📐 AI Measurements"
            st.rerun()

