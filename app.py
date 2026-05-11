import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="NE Clothiers",
    page_icon="✂️",
    layout="wide"
)

# ---------------- THEME ----------------

PRIMARY_COLOR = "#2563EB"
BG_COLOR = "#010F32"
CARD_COLOR = "#FFFFFF"
TEXT_COLOR = "#0F172A"

# ---------------- FILES ----------------

FILE_NAME = "NE_Clothiers_measurements.csv"

IMAGE_FOLDER = "customer_images"
RECEIPT_FOLDER = "receipts"

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(RECEIPT_FOLDER, exist_ok=True)

# ---------------- FIELDS ----------------

FIELDS = [
    "Name",
    "Phone",
    "Outfit Type",
    "Unit",
    "Date Created",
    "Expected Delivery Date",
    "Payment Status",
    "Amount Paid",
    "Receipt File",
    "Customer Image",
    "Customer Notes",

    "Chest",
    "Stomach",
    "Shoulder",
    "Sleeve Length",
    "Neck",
    "Round Sleeve",
    "Top Length",
    "Trouser Length",
    "Trouser-waist",
    "Hips",
    "Laps",
    "Knee",
    "Ankle"
]

# ---------------- HELPERS ----------------

def ensure_file():
    if not os.path.exists(FILE_NAME):
        df = pd.DataFrame(columns=FIELDS)
        df.to_csv(FILE_NAME, index=False)


def load_data():
    ensure_file()
    return pd.read_csv(FILE_NAME)


def save_data(data):
    df = load_data()

    new_df = pd.DataFrame([data])

    df = pd.concat([df, new_df], ignore_index=True)

    df.to_csv(FILE_NAME, index=False)

# ---------------- CUSTOM CSS ----------------

st.markdown(f"""
<style>

.stApp {{
    background-color: {BG_COLOR};
}}

.block-container {{
    padding-top: 2rem;
}}

h1, h2, h3 {{
    color: white;
}}

.main-title {{
    font-size: 42px;
    font-weight: bold;
    color: white;
    text-align: center;
}}

.sub-title {{
    font-size: 18px;
    color: #CBD5E1;
    text-align: center;
    margin-bottom: 30px;
}}

[data-testid="stForm"] {{
    background-color: {CARD_COLOR};
    padding: 25px;
    border-radius: 18px;
}}

.stTextInput input,
.stNumberInput input,
.stDateInput input {{
    background-color: #F8FAFC;
    color: {TEXT_COLOR};
    border-radius: 8px;
}}

.stSelectbox div {{
    color: {TEXT_COLOR};
}}

.stButton button {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border-radius: 10px;
    font-weight: bold;
    height: 45px;
    border: none;
}}

.stButton button:hover {{
    background-color: #1D4ED8;
}}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------

st.markdown(
    '<p class="main-title">NE CLOTHIERS</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<p class="sub-title">Premium Tailoring Measurement System</p>',
    unsafe_allow_html=True
)

# ---------------- SIDEBAR ----------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Go To",
    ["New Measurement", "Customer Records"]
)

# =========================================================
# NEW MEASUREMENT PAGE
# =========================================================

if page == "New Measurement":

    st.subheader("Add New Customer Measurement")

    with st.form("measurement_form"):

        col1, col2 = st.columns(2)

        # ---------------- LEFT COLUMN ----------------

        with col1:

            name = st.text_input("Customer Name")

            phone = st.text_input("Phone Number")

            outfit = st.selectbox(
                "Outfit Type",
                ["Agbada", "Senator", "Suit", "Native", "Kaftan"]
            )

            unit = st.radio(
                "Measurement Unit",
                ["cm", "inches"],
                horizontal=True
            )

            delivery_date = st.date_input(
                "Expected Delivery Date"
            )

            payment_status = st.selectbox(
                "Payment Status",
                ["Not Paid", "Part Payment", "Fully Paid"]
            )

            amount_paid = st.number_input(
                "Amount Paid",
                min_value=0.0,
                step=1000.0
            )

            receipt = st.file_uploader(
                "Upload Payment Receipt",
                type=["png", "jpg", "jpeg", "pdf"]
            )

            customer_image = st.file_uploader(
                "Upload Customer Picture",
                type=["png", "jpg", "jpeg"]
            )

            camera_photo = st.camera_input(
                "Take Customer Picture"
            )

            notes = st.text_area("Customer Notes")

        # ---------------- RIGHT COLUMN ----------------

        with col2:

            chest = st.text_input("Chest")

            stomach = st.text_input("Stomach")

            shoulder = st.text_input("Shoulder")

            sleeve = st.text_input("Sleeve Length")

            neck = st.text_input("Neck")

            round_sleeve = st.text_input("Round Sleeve")

            top_length = st.text_input("Top Length")

            trouser_length = st.text_input("Trouser Length")

            trouser_waist = st.text_input("Trouser Waist")

            hips = st.text_input("Hips")

            laps = st.text_input("Laps")

            knee = st.text_input("Knee")

            ankle = st.text_input("Ankle")

        submitted = st.form_submit_button(
            "Save Measurement"
        )

        # =========================================================
        # SAVE LOGIC
        # =========================================================

        if submitted:

            if not name:

                st.error("Customer name is required")

            else:

                receipt_filename = ""
                image_filename = ""

                # ---------------- SAVE RECEIPT ----------------

                if receipt is not None:

                    receipt_filename = receipt.name

                    receipt_path = os.path.join(
                        RECEIPT_FOLDER,
                        receipt_filename
                    )

                    with open(receipt_path, "wb") as f:
                        f.write(receipt.getbuffer())

                # ---------------- SAVE IMAGE ----------------

                image_file = customer_image

                # Use camera image if available
                if camera_photo is not None:
                    image_file = camera_photo

                if image_file is not None:

                    image_filename = image_file.name

                    image_path = os.path.join(
                        IMAGE_FOLDER,
                        image_filename
                    )

                    with open(image_path, "wb") as f:
                        f.write(image_file.getbuffer())

                    st.image(
                        image_file,
                        caption="Customer Preview",
                        width=250
                    )

                # ---------------- DATA ----------------

                data = {
                    "Name": name,
                    "Phone": phone,
                    "Outfit Type": outfit,
                    "Unit": unit,
                    "Date Created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Expected Delivery Date": str(delivery_date),
                    "Payment Status": payment_status,
                    "Amount Paid": amount_paid,
                    "Receipt File": receipt_filename,
                    "Customer Image": image_filename,
                    "Customer Notes": notes,

                    "Chest": chest,
                    "Stomach": stomach,
                    "Shoulder": shoulder,
                    "Sleeve Length": sleeve,
                    "Neck": neck,
                    "Round Sleeve": round_sleeve,
                    "Top Length": top_length,
                    "Trouser Length": trouser_length,
                    "Trouser-waist": trouser_waist,
                    "Hips": hips,
                    "Laps": laps,
                    "Knee": knee,
                    "Ankle": ankle
                }

                save_data(data)

                st.success(
                    "Measurement saved successfully!"
                )

# =========================================================
# CUSTOMER RECORDS PAGE
# =========================================================

if page == "Customer Records":

    st.subheader("Customer Records")

    df = load_data()

    search = st.text_input("Search customer")

    if search:

        filtered_df = df[
            df["Name"].astype(str)
            .str.lower()
            .str.contains(search.lower())
        ]

    else:

        filtered_df = df

    st.dataframe(
        filtered_df,
        use_container_width=True
    )

    # ---------------- CSV DOWNLOAD ----------------

    # st.download_button(
    #     label="Download CSV",
    #     data=filtered_df.to_csv(index=False),
    #     file_name="NE_Clothiers_measurements.csv",
    #     mime="text/csv"
    # )

    # # ---------------- EXCEL DOWNLOAD ----------------

    # excel_file = "NE_Clothiers_measurements.xlsx"

    # filtered_df.to_excel(
    #     excel_file,
    #     index=False
    # )

    # with open(excel_file, "rb") as file:

    #     st.download_button(
    #         label="Download Excel",
    #         data=file,
    #         file_name=excel_file,
    #         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    #     )