# ============================================================
# NE CLOTHIERS — Streamlit Web App
# ============================================================

import os
import io
import re
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
    "Name", "Phone", "Outfit Type", "Unit",
    "Date Created", "Expected Delivery Date",
    "Payment Status", "Amount Paid",
    "Receipt File", "Customer Image", "Customer Notes",
    "Delivery Status",
    # Upper body
    "Chest", "Stomach", "Shoulder", "Sleeve Length",
    "Neck", "Round Sleeve", "Top Length",
    # Lower body
    "Trouser Length", "Trouser-waist", "Hips",
    "Laps", "Knee", "Ankle"
]

# Measurements shown per outfit type
OUTFIT_FIELDS = {
    "Agbada":   ["Chest", "Stomach", "Shoulder", "Sleeve Length", "Neck",
                 "Round Sleeve", "Top Length", "Hips"],
    "Senator":  ["Chest", "Stomach", "Shoulder", "Sleeve Length", "Neck",
                 "Round Sleeve", "Top Length",
                 "Trouser Length", "Trouser-waist", "Hips", "Laps", "Knee", "Ankle"],
    "Suit":     ["Chest", "Stomach", "Shoulder", "Sleeve Length", "Neck",
                 "Top Length",
                 "Trouser Length", "Trouser-waist", "Laps", "Knee", "Ankle"],
    "Native":   ["Chest", "Stomach", "Shoulder", "Sleeve Length", "Neck",
                 "Round Sleeve", "Top Length",
                 "Trouser Length", "Trouser-waist", "Hips", "Laps", "Knee", "Ankle"],
    "Kaftan":   ["Chest", "Stomach", "Shoulder", "Sleeve Length", "Neck",
                 "Round Sleeve", "Top Length", "Hips"],
}

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
    # Ensure all expected columns exist (handles older CSV files)
    for col in FIELDS:
        if col not in df.columns:
            df[col] = ""
    return df


def save_data(data: dict):
    df = load_data()
    new_df = pd.DataFrame([data])
    df = pd.concat([df, new_df], ignore_index=True)
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


def validate_measurement(value: str, field: str) -> bool:
    if value and not value.replace('.', '', 1).isdigit():
        st.warning(f"⚠️ {field} should be a number (e.g. 42 or 42.5)")
        return False
    return True


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

    info_fields = [
        ("Customer Name",    record.get("Name", "")),
        ("Phone",            record.get("Phone", "")),
        ("Outfit Type",      record.get("Outfit Type", "")),
        ("Unit",             record.get("Unit", "")),
        ("Date Created",     record.get("Date Created", "")),
        ("Delivery Date",    record.get("Expected Delivery Date", "")),
        ("Delivery Status",  record.get("Delivery Status", "")),
        ("Payment Status",   record.get("Payment Status", "")),
        ("Amount Paid",      f"₦{record.get('Amount Paid', 0):,.0f}"),
        ("Notes",            record.get("Customer Notes", "")),
    ]
    for label, value in info_fields:
        row(label, value)

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
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = None

# ── CUSTOM CSS ───────────────────────────────────────────────
st.markdown(f"""
<style>
.stApp {{
    background-color: {BG_COLOR};
}}
.block-container {{
    padding-top: 2rem;
}}
h1, h2, h3, h4 {{
    color: white;
}}
.main-title {{
    font-size: 64px;
    font-weight: 850;
    color: white;
    margin-top: 10px;
    margin-bottom: 4px;
    letter-spacing: 3px;
    text-align: center;
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
    padding: 25px;
    border-radius: 16px;
    border: 1px solid #2563EB33;
}}
.metric-card {{
    background-color: {CARD_COLOR};
    border-radius: 12px;
    padding: 18px 22px;
    border-left: 4px solid {PRIMARY_COLOR};
    margin-bottom: 10px;
}}
.stTextInput input,
.stNumberInput input,
.stDateInput input {{
    background-color: #1E3A6E;
    color: white;
    border-radius: 8px;
    border: 1px solid #2563EB55;
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
    transition: background-color 0.2s;
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
.overdue-row {{
    color: #FCA5A5 !important;
    font-weight: bold;
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
    page = st.radio("Navigate", ["📊 Dashboard", "📋 New Measurement", "🗂️ Customer Records"])
    st.markdown("---")
    if st.session_state.logged_in:
        st.success("Admin logged in")
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.subheader("📊 Dashboard")

    df = load_data()

    if df.empty:
        st.info("No records yet. Add your first customer measurement to see stats here.")
    else:
        # ── KPI METRICS ──
        total      = len(df)
        fully_paid = len(df[df["Payment Status"] == "Fully Paid"])
        part_paid  = len(df[df["Payment Status"] == "Part Payment"])
        not_paid   = len(df[df["Payment Status"] == "Not Paid"])

        today = pd.Timestamp(date.today())
        try:
            df["_delivery_dt"] = pd.to_datetime(df["Expected Delivery Date"], errors="coerce")
            due_this_week = df[
                (df["_delivery_dt"] >= today) &
                (df["_delivery_dt"] <= today + pd.Timedelta(days=7))
            ]
            overdue = df[
                (df["_delivery_dt"] < today) &
                (df.get("Delivery Status", pd.Series([""] * len(df))).astype(str) != "Delivered")
            ]
        except Exception:
            due_this_week = pd.DataFrame()
            overdue       = pd.DataFrame()

        total_collected = pd.to_numeric(df["Amount Paid"], errors="coerce").sum()

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("👥 Total Customers",   total)
        col2.metric("✅ Fully Paid",         fully_paid)
        col3.metric("🕐 Part Payment",       part_paid)
        col4.metric("📅 Due This Week",      len(due_this_week))
        col5.metric("⚠️ Overdue",            len(overdue))

        st.markdown(f"### 💰 Total Collected: ₦{total_collected:,.0f}")
        st.markdown("---")

        # ── CHARTS ──
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("**Payment Status Breakdown**")
            payment_counts = df["Payment Status"].value_counts()
            st.bar_chart(payment_counts)

        with chart_col2:
            st.markdown("**Outfit Type Breakdown**")
            outfit_counts = df["Outfit Type"].value_counts()
            st.bar_chart(outfit_counts)

        st.markdown("---")

        # ── RECENT RECORDS ──
        st.markdown("**🕐 5 Most Recent Entries**")
        recent = df.tail(5)[["Name", "Phone", "Outfit Type", "Payment Status",
                              "Expected Delivery Date", "Delivery Status"]].iloc[::-1]
        st.dataframe(recent, use_container_width=True)

        # ── OVERDUE ORDERS ──
        if not overdue.empty:
            st.markdown("---")
            st.markdown("**🚨 Overdue Orders**")
            st.dataframe(
                overdue[["Name", "Phone", "Outfit Type",
                          "Expected Delivery Date", "Payment Status"]],
                use_container_width=True
            )

# ════════════════════════════════════════════════════════════
# PAGE: NEW MEASUREMENT
# ════════════════════════════════════════════════════════════
elif page == "📋 New Measurement":
    st.subheader("📋 Add New Customer Measurement")

    with st.form("measurement_form", clear_on_submit=True):

        col1, col2 = st.columns([1, 1])

        # ── LEFT COLUMN ──────────────────────────────────────
        with col1:
            st.markdown("#### Customer Info")

            name  = st.text_input("Customer Name *")
            phone = st.text_input("Phone Number")

            outfit = st.selectbox(
                "Outfit Type",
                ["Agbada", "Senator", "Suit", "Native", "Kaftan"]
            )

            unit = st.radio("Measurement Unit", ["cm", "inches"], horizontal=True)

            delivery_date = st.date_input("Expected Delivery Date")

            delivery_status = st.selectbox(
                "Delivery Status",
                ["Pending", "In Progress", "Ready", "Delivered"]
            )

            payment_status = st.selectbox(
                "Payment Status",
                ["Not Paid", "Part Payment", "Fully Paid"]
            )

            amount_paid = st.number_input("Amount Paid (₦)", min_value=0.0, step=1000.0)

            st.markdown("---")
            st.markdown("**Payment Receipt**")
            receipt = st.file_uploader(
                "Upload receipt (PNG, JPG, PDF)",
                type=["png", "jpg", "jpeg", "pdf"],
                label_visibility="collapsed"
            )

            st.markdown("**Customer Photo** — upload a file or use the camera below")
            customer_image = st.file_uploader(
                "Upload photo",
                type=["png", "jpg", "jpeg"],
                label_visibility="collapsed"
            )
            camera_photo = st.camera_input("📷 Take Photo")

            notes = st.text_area("Customer Notes", placeholder="Any special instructions...")

        # ── RIGHT COLUMN ─────────────────────────────────────
        with col2:
            st.markdown("#### Body Measurements")
            st.caption(f"Active fields shown for selected outfit: **{outfit}**")

            active_fields = OUTFIT_FIELDS.get(outfit, UPPER_BODY + LOWER_BODY)
            meas_values   = {}

            with st.expander("👕 Upper Body", expanded=True):
                for field in UPPER_BODY:
                    disabled = field not in active_fields
                    meas_values[field] = st.text_input(
                        field,
                        placeholder="—" if disabled else f"Enter {field.lower()}",
                        disabled=disabled,
                        key=f"meas_{field}"
                    )

            with st.expander("👖 Lower Body", expanded=True):
                for field in LOWER_BODY:
                    disabled = field not in active_fields
                    meas_values[field] = st.text_input(
                        field,
                        placeholder="—" if disabled else f"Enter {field.lower()}",
                        disabled=disabled,
                        key=f"meas_{field}"
                    )

        submitted = st.form_submit_button("💾 Save Measurement", use_container_width=True)

        # ── SAVE LOGIC ───────────────────────────────────────
        if submitted:
            errors = []

            if not name.strip():
                errors.append("Customer name is required.")
            if phone and not validate_phone(phone):
                errors.append("Phone number format is invalid.")
            for field, val in meas_values.items():
                if val and not val.replace('.', '', 1).isdigit():
                    errors.append(f"{field} must be a number.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                receipt_filename = ""
                image_filename   = ""

                # Save receipt
                if receipt is not None:
                    receipt_filename = receipt.name
                    with open(os.path.join(RECEIPT_FOLDER, receipt_filename), "wb") as f:
                        f.write(receipt.getbuffer())

                # Save image (camera takes priority)
                image_file = camera_photo if camera_photo is not None else customer_image
                if image_file is not None:
                    image_filename = image_file.name
                    with open(os.path.join(IMAGE_FOLDER, image_filename), "wb") as f:
                        f.write(image_file.getbuffer())

                data = {
                    "Name":                   name.strip(),
                    "Phone":                  phone,
                    "Outfit Type":            outfit,
                    "Unit":                   unit,
                    "Date Created":           datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Expected Delivery Date": str(delivery_date),
                    "Delivery Status":        delivery_status,
                    "Payment Status":         payment_status,
                    "Amount Paid":            amount_paid,
                    "Receipt File":           receipt_filename,
                    "Customer Image":         image_filename,
                    "Customer Notes":         notes,
                    **meas_values
                }

                save_data(data)

                st.success("✅ Measurement saved successfully!")
                st.info(
                    f"**{name.strip()}** | {outfit} | "
                    f"Delivery: {delivery_date} | {payment_status}"
                )
                if image_file is not None:
                    st.image(image_file, caption="Customer Photo", width=220)

# ════════════════════════════════════════════════════════════
# PAGE: CUSTOMER RECORDS
# ════════════════════════════════════════════════════════════
elif page == "🗂️ Customer Records":
    st.subheader("🗂️ Customer Records")

    # ── LOGIN ────────────────────────────────────────────────
    if not st.session_state.logged_in:
        st.markdown("#### Admin Access")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("🔐 Login")

        if login_btn:
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

    # ── RECORDS VIEW ─────────────────────────────────────────
    else:
        df = load_data()

        # ── SEARCH & FILTER ──
        filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
        with filter_col1:
            search = st.text_input("🔍 Search by name or phone", placeholder="Type to search...")
        with filter_col2:
            filter_outfit = st.selectbox("Filter by Outfit", ["All"] + list(df["Outfit Type"].dropna().unique()))
        with filter_col3:
            filter_payment = st.selectbox("Filter by Payment", ["All", "Not Paid", "Part Payment", "Fully Paid"])

        filtered_df = df.copy()
        if search:
            mask = (
                filtered_df["Name"].astype(str).str.lower().str.contains(search.lower()) |
                filtered_df["Phone"].astype(str).str.lower().str.contains(search.lower())
            )
            filtered_df = filtered_df[mask]
        if filter_outfit != "All":
            filtered_df = filtered_df[filtered_df["Outfit Type"] == filter_outfit]
        if filter_payment != "All":
            filtered_df = filtered_df[filtered_df["Payment Status"] == filter_payment]

        st.caption(f"Showing {len(filtered_df)} of {len(df)} records")

        # ── TABLE ──
        st.dataframe(filtered_df, use_container_width=True, height=350)

        # ── EDIT / DELETE ──
        st.markdown("---")
        st.markdown("#### Edit or Delete a Record")

        if not filtered_df.empty:
            record_options = {
                f"{row['Name']} — {row.get('Outfit Type','')} ({row.get('Date Created','')})": idx
                for idx, row in filtered_df.iterrows()
            }
            selected_label = st.selectbox("Select a record", list(record_options.keys()))
            selected_idx   = record_options[selected_label]
            selected_row   = df.loc[selected_idx]

            action_col1, action_col2 = st.columns(2)

            # ── EDIT ──
            with action_col1:
                with st.expander("✏️ Edit Selected Record"):
                    with st.form("edit_form"):
                        e_name     = st.text_input("Name",            value=str(selected_row.get("Name", "")))
                        e_phone    = st.text_input("Phone",           value=str(selected_row.get("Phone", "")))
                        e_outfit   = st.selectbox("Outfit Type",      ["Agbada", "Senator", "Suit", "Native", "Kaftan"],
                                                  index=["Agbada", "Senator", "Suit", "Native", "Kaftan"].index(
                                                      selected_row.get("Outfit Type", "Agbada"))
                                                  if selected_row.get("Outfit Type") in ["Agbada", "Senator", "Suit", "Native", "Kaftan"] else 0)
                        e_delivery = st.selectbox("Delivery Status",  ["Pending", "In Progress", "Ready", "Delivered"],
                                                  index=["Pending", "In Progress", "Ready", "Delivered"].index(
                                                      selected_row.get("Delivery Status", "Pending"))
                                                  if selected_row.get("Delivery Status") in ["Pending", "In Progress", "Ready", "Delivered"] else 0)
                        e_payment  = st.selectbox("Payment Status",   ["Not Paid", "Part Payment", "Fully Paid"],
                                                  index=["Not Paid", "Part Payment", "Fully Paid"].index(
                                                      selected_row.get("Payment Status", "Not Paid"))
                                                  if selected_row.get("Payment Status") in ["Not Paid", "Part Payment", "Fully Paid"] else 0)
                        e_amount   = st.number_input("Amount Paid (₦)",
                                                     value=float(selected_row.get("Amount Paid", 0) or 0),
                                                     min_value=0.0, step=1000.0)
                        e_notes    = st.text_area("Notes", value=str(selected_row.get("Customer Notes", "")))

                        save_edit = st.form_submit_button("💾 Save Changes")

                    if save_edit:
                        update_record(selected_idx, {
                            "Name":            e_name,
                            "Phone":           e_phone,
                            "Outfit Type":     e_outfit,
                            "Delivery Status": e_delivery,
                            "Payment Status":  e_payment,
                            "Amount Paid":     e_amount,
                            "Customer Notes":  e_notes,
                        })
                        st.success("Record updated.")
                        st.rerun()

            # ── DELETE ──
            with action_col2:
                with st.expander("🗑️ Delete Selected Record"):
                    st.warning(f"You are about to delete **{selected_row.get('Name', '')}**. This cannot be undone.")
                    confirm_name = st.text_input("Type the customer name to confirm deletion")
                    if st.button("🗑️ Confirm Delete", type="primary"):
                        if confirm_name.strip().lower() == str(selected_row.get("Name", "")).strip().lower():
                            delete_record(selected_idx)
                            st.success("Record deleted.")
                            st.rerun()
                        else:
                            st.error("Name does not match. Deletion cancelled.")

        # ── PDF RECEIPT ──
        st.markdown("---")
        st.markdown("#### 🧾 Generate PDF Receipt")
        if not filtered_df.empty:
            pdf_options = {
                f"{row['Name']} — {row.get('Outfit Type', '')}": idx
                for idx, row in filtered_df.iterrows()
            }
            pdf_label = st.selectbox("Select customer for receipt", list(pdf_options.keys()), key="pdf_select")
            pdf_idx   = pdf_options[pdf_label]
            pdf_row   = df.loc[pdf_idx].to_dict()

            pdf_bytes = generate_pdf_receipt(pdf_row)
            st.download_button(
                label="📄 Download PDF Receipt",
                data=pdf_bytes,
                file_name=f"receipt_{pdf_row.get('Name','customer').replace(' ','_')}.pdf",
                mime="application/pdf"
            )

        # ── DOWNLOADS ──
        st.markdown("---")
        st.markdown("#### 📥 Export Records")
        dl_col1, dl_col2 = st.columns(2)

        with dl_col1:
            st.download_button(
                label="⬇️ Download CSV",
                data=filtered_df.to_csv(index=False),
                file_name="NE_Clothiers_measurements.csv",
                mime="text/csv"
            )

        with dl_col2:
            excel_buffer = io.BytesIO()
            filtered_df.to_excel(excel_buffer, index=False, engine="openpyxl")
            st.download_button(
                label="⬇️ Download Excel",
                data=excel_buffer.getvalue(),
                file_name="NE_Clothiers_measurements.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
