# ============================================================
# NE CLOTHIERS — Streamlit Web App
# ============================================================

import os
import io
import re
import uuid
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

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "nedee123")

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(RECEIPT_FOLDER, exist_ok=True)

# ── FIELDS ───────────────────────────────────────────────────
FIELDS = [
    "Order ID", "Name", "Phone", "Outfit Type", "Unit",
    "Date Created", "Expected Delivery Date",
    "Payment Status", "Amount Paid",
    "Receipt File", "Design Photo", "Customer Notes",
    "Delivery Status",
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
    df = pd.read_csv(FILE_NAME)
    for col in FIELDS:
        if col not in df.columns:
            df[col] = ""
    return df


def save_data(data: dict):
    df = load_data()
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_csv(FILE_NAME, index=False)
    st.cache_data.clear()


def update_record(index: int, data: dict):
    df = load_data()
    for key, value in data.items():
        df.at[index, key] = value
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
        status   = str(row.get("Delivery Status", "")).strip()
        return delivery < pd.Timestamp(date.today()) and status != "Delivered"
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
        ("Delivery Status", "Delivery Status"),
        ("Payment Status",  "Payment Status"),
        ("Amount Paid",     "Amount Paid"),
        ("Notes",           "Customer Notes"),
    ]:
        val = record.get(key, "")
        if key == "Amount Paid":
            try:
                val = f"\u20a6{float(val):,.0f}"
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


# ── SESSION STATE DEFAULTS ────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "pending_order_id" not in st.session_state:
    st.session_state.pending_order_id = None
if "just_saved_order" not in st.session_state:
    st.session_state.just_saved_order = False

# ── CUSTOM CSS ───────────────────────────────────────────────
st.markdown(f"""
<style>
.stApp {{
    background-color: {BG_COLOR};
}}
h1, h2, h3, h4 {{
    color: white;
}}
.main-title {{
    font-size: clamp(22px, 4vw, 42px);
    font-weight: 850;
    color: white;
    margin-top: 10px;
    margin-bottom: 4px;
    letter-spacing: 2px;
    text-align: center;
    white-space: normal;
    word-break: break-word;
    line-height: 1.2;
}}
.sub-title {{
    font-size: 18px;
    color: #93C5FD;
    text-align: center;
    margin-bottom: 30px;
    letter-spacing: 1px;
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
st.markdown('<p class="main-title">✂️ NE CLOTHIERS</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Premium Tailoring Measurement System</p>', unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────────
with st.sidebar:
    if os.path.exists("ne.png"):
        st.image("ne.png", width=110)
    st.title("NE Clothiers")
    st.markdown("---")

    # All users see the same 3 nav items — Dashboard is hidden inside Admin
    page = st.radio(
        "Navigate",
        ["📋 New Measurement", "🔍 Order Tracking", "🔐 Admin"],
        index=1 if st.session_state.pending_order_id else 0
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
            fully_paid = len(df[df["Payment Status"] == "Fully Paid"])
            part_paid  = len(df[df["Payment Status"] == "Part Payment"])

            today = pd.Timestamp(date.today())
            try:
                df["_delivery_dt"] = pd.to_datetime(df["Expected Delivery Date"], errors="coerce")
                due_this_week = df[
                    (df["_delivery_dt"] >= today) &
                    (df["_delivery_dt"] <= today + pd.Timedelta(days=7))
                ]
                delivery_col = df.get("Delivery Status", pd.Series([""] * len(df)))
                overdue = df[
                    (df["_delivery_dt"] < today) &
                    (delivery_col.astype(str) != "Delivered")
                ]
            except Exception:
                due_this_week = pd.DataFrame()
                overdue       = pd.DataFrame()

            total_collected = pd.to_numeric(df["Amount Paid"], errors="coerce").sum()

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("👥 Total Customers", total)
            c2.metric("✅ Fully Paid",       fully_paid)
            c3.metric("🕐 Part Payment",     part_paid)
            c4.metric("📅 Due This Week",    len(due_this_week))
            c5.metric("⚠️ Overdue",          len(overdue))

            st.markdown(f"### 💰 Total Collected: ₦{total_collected:,.0f}")
            st.markdown("---")

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.markdown("**Payment Status Breakdown**")
                st.bar_chart(df["Payment Status"].value_counts())
            with chart_col2:
                st.markdown("**Outfit Type Breakdown**")
                st.bar_chart(df["Outfit Type"].value_counts())

            st.markdown("---")
            st.markdown("**🕐 5 Most Recent Entries**")
            recent_cols = ["Order ID", "Name", "Phone", "Outfit Type",
                           "Payment Status", "Expected Delivery Date", "Delivery Status"]
            st.dataframe(df.tail(5)[recent_cols].iloc[::-1], use_container_width=True)

            if not overdue.empty:
                st.markdown("---")
                st.markdown("**🚨 Overdue Orders**")
                overdue_cols = ["Order ID", "Name", "Phone", "Outfit Type",
                                "Expected Delivery Date", "Payment Status"]
                st.dataframe(overdue[overdue_cols], use_container_width=True)

        st.markdown("---")

        # ── ALL RECORDS TABLE ─────────────────────────────────
        st.markdown("#### 🗂️ All Records")
        df_all = load_data()

        fa1, fa2, fa3 = st.columns([2, 1, 1])
        with fa1:
            a_search = st.text_input("🔍 Search", placeholder="Name, phone, or Order ID...")
        with fa2:
            outfit_opts = ["All"] + sorted(df_all["Outfit Type"].dropna().unique().tolist())
            a_outfit = st.selectbox("Outfit", outfit_opts)
        with fa3:
            a_payment = st.selectbox("Payment", ["All", "Not Paid", "Part Payment", "Fully Paid"])

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
        if a_payment != "All":
            filtered = filtered[filtered["Payment Status"] == a_payment]

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
                    outfit_list   = ["Agbada", "Senator", "Suit", "Native", "Kaftan"]
                    delivery_list = ["Pending", "In Progress", "Ready", "Delivered"]
                    payment_list  = ["Not Paid", "Part Payment", "Fully Paid"]

                    def safe_index(lst, val, default=0):
                        return lst.index(val) if val in lst else default

                    with st.form("edit_form"):
                        e_name     = st.text_input("Name",   value=str(sel_row.get("Name", "")))
                        e_phone    = st.text_input("Phone",  value=str(sel_row.get("Phone", "")))
                        e_outfit   = st.selectbox("Outfit Type", outfit_list,
                                                  index=safe_index(outfit_list, sel_row.get("Outfit Type", "")))
                        e_delivery_status = st.selectbox("Delivery Status", delivery_list,
                                                  index=safe_index(delivery_list, sel_row.get("Delivery Status", "")))
                        e_payment  = st.selectbox("Payment Status", payment_list,
                                                  index=safe_index(payment_list, sel_row.get("Payment Status", "")))
                        e_amount   = st.number_input("Amount Paid (₦)",
                                                     value=float(sel_row.get("Amount Paid") or 0),
                                                     min_value=0.0, step=1000.0)
                        e_notes    = st.text_area("Notes", value=str(sel_row.get("Customer Notes", "")))
                        save_edit  = st.form_submit_button("💾 Save Changes")

                    if save_edit:
                        update_record(sel_idx, {
                            "Name":            e_name,
                            "Phone":           e_phone,
                            "Outfit Type":     e_outfit,
                            "Delivery Status": e_delivery_status,
                            "Payment Status":  e_payment,
                            "Amount Paid":     e_amount,
                            "Customer Notes":  e_notes,
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
    st.subheader("📋 Add New Customer Measurement")

    with st.form("measurement_form", clear_on_submit=True):
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("#### Customer Info")
            name  = st.text_input("Customer Name *")
            phone = st.text_input("Phone Number")
            outfit = st.selectbox(
                "Outfit Type",
                ["Agbada", "Senator", "Suit", "Native", "Kaftan"]
            )
            unit = st.radio("Measurement Unit", ["cm", "inches"], horizontal=True)
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
                st.image(design_photo, caption="Design Preview", width=200)

        with col2:
            st.markdown("#### Body Measurements")
            meas_values = {}

            with st.expander("👕 Upper Body", expanded=True):
                for field in UPPER_BODY:
                    meas_values[field] = st.text_input(
                        field,
                        placeholder=f"Enter {field.lower()}",
                        key=f"meas_{field}"
                    )

            with st.expander("👖 Lower Body", expanded=True):
                for field in LOWER_BODY:
                    meas_values[field] = st.text_input(
                        field,
                        placeholder=f"Enter {field.lower()}",
                        key=f"meas_{field}"
                    )

        submitted = st.form_submit_button("💾 Save Measurement", use_container_width=True)

        if submitted:
            errors = []
            if not name.strip():
                errors.append("Customer name is required.")
            if phone and not validate_phone(phone):
                errors.append("Phone number format is invalid.")
            for field, val in meas_values.items():
                if val and not val.replace('.', '', 1).isdigit():
                    errors.append(f"{field} must be a number (e.g. 42 or 42.5).")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                order_id = generate_order_id()

                design_filename = ""
                if design_photo is not None:
                    design_filename = design_photo.name
                    with open(os.path.join(IMAGE_FOLDER, design_filename), "wb") as f:
                        f.write(design_photo.getbuffer())

                data = {
                    "Order ID":               order_id,
                    "Name":                   name.strip(),
                    "Phone":                  phone,
                    "Outfit Type":            outfit,
                    "Unit":                   unit,
                    "Date Created":           datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Expected Delivery Date": "",
                    "Delivery Status":        "Pending",
                    "Payment Status":         "Not Paid",
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
                st.info(f"**{name.strip()}** | {outfit}")

# Show "Continue" button outside the form, after a successful save
if st.session_state.just_saved_order:
    st.markdown("---")
    st.markdown("### 📋 Next Step: Submit Order Details")
    st.markdown(
        "Measurements saved. Click below to add delivery date, "
        "payment info, and any special notes."
    )
    if st.button("➡️ Continue to Order Details", type="primary", use_container_width=True):
        st.session_state.just_saved_order = False
        st.rerun()

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
                delivery_status = str(row.get("Delivery Status", "Pending"))

                status_map = {
                    "Pending":     ("🕐", "#F59E0B", "#1C1400"),
                    "In Progress": ("🔧", "#3B82F6", "#0A1628"),
                    "Ready":       ("✅", "#10B981", "#021A0E"),
                    "Delivered":   ("📦", "#6B7280", "#111827"),
                }
                icon, badge_color, badge_bg = status_map.get(
                    delivery_status, ("🕐", "#F59E0B", "#1C1400")
                )

                order_id      = row.get("Order ID", "—")
                delivery_date = row.get("Expected Delivery Date", "—") or "—"
                amount        = float(row.get("Amount Paid") or 0)

                st.markdown(f"""
                <div style="
                    background-color: #1E3A6E;
                    border-radius: 14px;
                    padding: 22px 26px;
                    margin-bottom: 18px;
                    border-left: 5px solid {badge_color};
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
                        <div style="
                            background-color: {badge_bg};
                            border: 2px solid {badge_color};
                            border-radius: 20px;
                            padding: 8px 20px;
                            font-weight: bold;
                            color: {badge_color};
                            font-size: 16px;
                            white-space: nowrap;
                            align-self: center;
                        ">
                            {icon} {delivery_status}
                        </div>
                    </div>
                    <hr style="border-color:#2563EB44; margin: 16px 0 14px 0;">
                    <div style="display:flex; gap:40px; flex-wrap:wrap;">
                        <div>
                            <p style="color:#94A3B8; margin:0; font-size:11px; letter-spacing:1px;">EXPECTED DELIVERY</p>
                            <p style="color:white; margin:2px 0 0 0; font-size:15px; font-weight:600;">📆 {delivery_date}</p>
                        </div>
                        <div>
                            <p style="color:#94A3B8; margin:0; font-size:11px; letter-spacing:1px;">PAYMENT STATUS</p>
                            <p style="color:white; margin:2px 0 0 0; font-size:15px; font-weight:600;">💳 {row.get("Payment Status", "—")}</p>
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
        "payment info, and notes."
    )

    # Pre-fill values from search result if available
    prefill_row = results.iloc[0] if not results.empty else None
    default_order_id  = found_order_id
    default_payment   = str(prefill_row.get("Payment Status", "Not Paid")) if prefill_row is not None else "Not Paid"
    default_amount    = float(prefill_row.get("Amount Paid") or 0) if prefill_row is not None else 0.0
    default_notes     = str(prefill_row.get("Customer Notes", "") or "") if prefill_row is not None else ""
    payment_list      = ["Not Paid", "Part Payment", "Fully Paid"]
    default_pay_idx   = payment_list.index(default_payment) if default_payment in payment_list else 0

    with st.form("order_details_form", clear_on_submit=True):
        od_col1, od_col2 = st.columns([1, 1])

        with od_col1:
            od_order_id = st.text_input(
                "Order ID *",
                value=default_order_id,
                placeholder="e.g. NEC-2026-A3F7"
            )
            od_delivery = st.date_input("Expected Delivery Date")
            od_payment  = st.selectbox("Payment Status", payment_list, index=default_pay_idx)
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
                        "Payment Status":         od_payment,
                        "Amount Paid":            od_amount,
                        "Customer Notes":         od_notes,
                        "Receipt File":           receipt_filename,
                    })

                    st.success(f"✅ Order details updated for **{od_order_id.strip().upper()}**!")
                    st.info(
                        f"Delivery: {od_delivery} | {od_payment} | ₦{od_amount:,.0f}"
                    )

    # ── EMPTY STATE ──────────────────────────────────────────
    if not search_query.strip():
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

