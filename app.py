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

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "nedee123")

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

    sender   = os.getenv("EMAIL_SENDER", "").strip()
    # Strip spaces from app password — Gmail displays them grouped but SMTP needs them removed
    password = os.getenv("EMAIL_PASSWORD", "").replace(" ", "")
    host     = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com").strip()
    port     = int(os.getenv("EMAIL_SMTP_PORT", 587))

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
# PAGE: AI MEASUREMENTS (silhouette scan)
# ════════════════════════════════════════════════════════════
elif page == "📐 AI Measurements":
    st.subheader("📐 AI Body Measurement Assistant")
    st.markdown(
        "<p style='color:#93C5FD; text-align:center;'>Upload clear front and back photos of the customer. "
        "Our AI will analyse the silhouette and suggest body measurements.</p>",
        unsafe_allow_html=True
    )

    # ── INSTRUCTIONS ─────────────────────────────────────────
    with st.expander("📸 Photo Guidelines", expanded=True):
        st.markdown("""
**For best results:**
- Stand straight against a plain, well-lit background
- Wear form-fitting clothing (no baggy outfits)
- Arms slightly away from the body
- Full body visible from head to toe in both shots
- Front photo: face the camera directly
- Back photo: turn completely around, same pose
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
            st.image(front_photo, caption="Front View", use_container_width=True)

    with ai_col2:
        st.markdown("#### 🧍‍♂️ Back View")
        back_photo = st.file_uploader(
            "Upload back photo",
            type=["png", "jpg", "jpeg"],
            key="ai_back",
            label_visibility="collapsed"
        )
        if back_photo:
            st.image(back_photo, caption="Back View", use_container_width=True)

    st.markdown("---")

    ai_unit = st.radio("Preferred measurement unit", ["cm", "inches"], horizontal=True, key="ai_unit")
    ai_height = st.text_input(
        "Customer height (optional — improves accuracy)",
        placeholder="e.g. 175 cm  or  5ft 9in",
        key="ai_height"
    )

    scan_btn = st.button("🤖 Scan & Estimate Measurements", type="primary", use_container_width=True)

    if scan_btn:
        if not front_photo or not back_photo:
            st.error("Please upload both the front and back photos before scanning.")
        else:
            openai_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not openai_key:
                st.error(
                    "OpenAI API key not found. Add `OPENAI_API_KEY=sk-...` to your `.env` file "
                    "to enable AI measurement scanning."
                )
            else:
                with st.spinner("🤖 Analysing silhouette… this may take a few seconds…"):
                    try:
                        import httpx

                        def _encode(file_obj) -> str:
                            file_obj.seek(0)
                            return base64.b64encode(file_obj.read()).decode("utf-8")

                        front_b64 = _encode(front_photo)
                        back_b64  = _encode(back_photo)

                        height_hint = (
                            f"The customer's height is {ai_height.strip()}. Use this as a scale reference."
                            if ai_height.strip() else
                            "No height reference was provided; give your best estimate."
                        )

                        prompt = f"""You are an expert tailor's assistant. Analyse the two photos of the same person — one front view and one back view — and estimate their body measurements in {ai_unit}.

{height_hint}

Return ONLY a JSON object with these exact keys (no extra text, no markdown fences):
{{
  "Chest": "",
  "Stomach": "",
  "Shoulder": "",
  "Sleeve Length": "",
  "Neck": "",
  "Round Sleeve": "",
  "Top Length": "",
  "Trouser Length": "",
  "Trouser-waist": "",
  "Hips": "",
  "Laps": "",
  "Knee": "",
  "Ankle": "",
  "confidence": "low | medium | high",
  "notes": "any caveats or assumptions"
}}

Fill every measurement field with a numeric value (e.g. "42"). Use your best professional estimate based on body proportions visible in the photos."""

                        payload = {
                            "model": "gpt-4o",
                            "max_tokens": 600,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": prompt},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:{front_photo.type};base64,{front_b64}",
                                                "detail": "high"
                                            }
                                        },
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:{back_photo.type};base64,{back_b64}",
                                                "detail": "high"
                                            }
                                        },
                                    ]
                                }
                            ]
                        }

                        resp = httpx.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {openai_key}",
                                "Content-Type": "application/json"
                            },
                            json=payload,
                            timeout=60
                        )
                        resp.raise_for_status()
                        raw = resp.json()["choices"][0]["message"]["content"].strip()

                        # Strip markdown fences if model adds them anyway
                        if raw.startswith("```"):
                            raw = re.sub(r"^```[a-z]*\n?", "", raw)
                            raw = re.sub(r"\n?```$", "", raw)

                        import json
                        ai_result = json.loads(raw)
                        st.session_state["ai_measurements"] = ai_result
                        st.session_state["ai_unit"] = ai_unit

                    except httpx.HTTPStatusError as e:
                        st.error(f"OpenAI API error {e.response.status_code}: {e.response.text[:300]}")
                        ai_result = None
                    except Exception as e:
                        st.error(f"Scan failed: {e}")
                        ai_result = None

    # ── DISPLAY RESULTS ───────────────────────────────────────
    if "ai_measurements" in st.session_state and st.session_state["ai_measurements"]:
        ai_result = st.session_state["ai_measurements"]
        confidence = ai_result.get("confidence", "medium")
        notes      = ai_result.get("notes", "")

        conf_color = {"high": "#10B981", "medium": "#F59E0B", "low": "#EF4444"}.get(confidence, "#F59E0B")
        st.markdown(
            f"<p style='color:{conf_color}; font-weight:bold; text-align:center;'>"
            f"AI Confidence: {confidence.upper()}</p>",
            unsafe_allow_html=True
        )
        if notes:
            st.info(f"💬 AI notes: {notes}")

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
                    f"<span style='color:white;font-weight:bold;'>{val} {st.session_state.get('ai_unit','cm')}</span>"
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
                    f"<span style='color:white;font-weight:bold;'>{val} {st.session_state.get('ai_unit','cm')}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("---")
        st.markdown(
            "✅ **Happy with these estimates?** Head to **📋 New Measurement** and enter them manually, "
            "or use the form below to save them directly to a new order."
        )

        # ── QUICK-SAVE TO NEW ORDER ───────────────────────────
        with st.expander("💾 Save AI Measurements as New Order", expanded=False):
            with st.form("ai_save_form"):
                ais_name  = st.text_input("Customer Name *")
                ais_phone = st.text_input("Phone Number *")
                ais_email = st.text_input("Email Address *", placeholder="customer@example.com")
                ais_outfit = st.selectbox("Outfit Type", ["Agbada", "Senator", "Suit", "Kaftan"])
                ais_unit   = st.radio("Unit", ["cm", "inches"], horizontal=True,
                                      index=0 if st.session_state.get("ai_unit", "cm") == "cm" else 1)
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
                        "Customer Notes":         f"Measurements estimated by AI (confidence: {confidence})",
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

                    # Clear cached AI result
                    del st.session_state["ai_measurements"]

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

