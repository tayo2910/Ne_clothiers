import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="NE Clothiers",
    page_icon="✂️",
    layout="wide"
)
# ---------------- THEME ----------------
PRIMARY_COLOR = "#2563EB"
BG_COLOR = "#010C26"
CARD_COLOR = "#1E293B"
TEXT_COLOR = "#FFFFFF"

# ---------------- FILE ----------------
FILE_NAME = "NE_Clothiers_measurements.csv"

FIELDS = [
    "Name", "Outfit Type", "Unit", "Date",
    "Chest", "Stomach", "Shoulder",
    "Sleeve Length", "Neck", "Round Sleeve", "Top Length",
    "Trouser Length", "Trouser-waist", "Hips",
    "Laps", "Knee", "Ankle"
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
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {BG_COLOR};
        color: white;
    }}

    .main-title {{
        font-size: 40px;
        font-weight: bold;
        color: white;
        text-align: center;
        margin-bottom: 0;
    }}
     .sub-title {{
        text-align: center;
        color: #CBD5E1;
        margin-top: 0;
        margin-bottom: 30px;
    }}

    div[data-testid="stForm"] {{
        background-color: {CARD_COLOR};
        padding: 20px;
        border-radius: 15px;
    }}

    </style>
    """,
    unsafe_allow_html=True
)

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

# ---------------- NEW MEASUREMENT ----------------
if page == "New Measurement":

    st.subheader("Add New Customer Measurement")

    with st.form("measurement_form"):

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Customer Name")
            outfit = st.selectbox(
                "Outfit Type",
                ["Agbada", "Senator", "Suit", "Native", "Kaftan"]
            )

            chest = st.text_input("Chest")
            stomach = st.text_input("Stomach")
            shoulder = st.text_input("Shoulder")
            sleeve = st.text_input("Sleeve Length")
            neck = st.text_input("Neck")
            round_sleeve = st.text_input("Round Sleeve")

            with col2:
                top_length = st.text_input("Top Length")
                trouser_length = st.text_input("Trouser Length")
                trouser_waist = st.text_input("Trouser Waist")
                hips = st.text_input("Hips")
                laps = st.text_input("Laps")
                knee = st.text_input("Knee")
                ankle = st.text_input("Ankle")
                unit = st.radio(
                "Measurement Unit",
                ["cm", "inches"],
                horizontal=True
            )

        submitted = st.form_submit_button("Save Measurement")
        if submitted:

            if not name:
                st.error("Customer name is required")
            else:
                data = {
                    "Name": name,
                    "Outfit Type": outfit,
                    "Unit": unit,
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
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
                st.success("Measurement saved successfully")
    # ---------------- CUSTOMER RECORDS ----------------
if page == "Customer Records":

    st.subheader("Customer Records")

    df = load_data()

    search = st.text_input("Search customer")

    if search:
        filtered_df = df[
            df["Name"].astype(str).str.lower().str.contains(search.lower())
        ]
    else:
        filtered_df = df

    st.dataframe(filtered_df, use_container_width=True)

    st.download_button(
        label="Download CSV",
        data=filtered_df.to_csv(index=False),
        file_name="NE_Clothiers_measurements.csv",
        mime="text/csv"
    )
    excel_file = "NE_Clothiers_measurements.xlsx"
    filtered_df.to_excel(excel_file, index=False)

    with open(excel_file, "rb") as file:
        st.download_button(
            label="Download Excel",
            data=file,
            file_name=excel_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )