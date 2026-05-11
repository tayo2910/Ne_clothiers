# NE Clothiers — Improvement & Optimization Plan

A full audit of `app.py`, `tailor.py`, `database.py`, and `supabase_client.py` with actionable improvements across UI/UX, performance, security, and code quality.

---

## Table of Contents

1. [Critical Bugs to Fix First](#1-critical-bugs-to-fix-first)
2. [Security](#2-security)
3. [Performance](#3-performance)
4. [app.py — Streamlit UI/UX](#4-apppy--streamlit-uiux)
5. [tailor.py — Tkinter Desktop UI/UX](#5-tailorpy--tkinter-desktop-uiux)
6. [New Features to Add](#6-new-features-to-add)
7. [Code Quality & Structure](#7-code-quality--structure)
8. [Quick Wins Summary](#8-quick-wins-summary)
9. [Suggested File Structure](#9-suggested-file-structure)

---

## 1. Critical Bugs to Fix First

### `supabase_client.py` — `os.getenv` used incorrectly

**Current (broken):**
```python
SUPABASE_URL = os.getenv("https://tjssgwvsmwdcqxbovuhw.supabase.co")
SUPABASE_KEY = os.getenv("sb_publishable_fJKBcEgdvxDUERMrYVlAZg_LOomXX25")
```

`os.getenv()` takes an environment variable **name** as its argument, not the actual value. Both calls will return `None`, causing `create_client(None, None)` to crash immediately.

**Fix:**
```python
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
```

Then create a `.env` file:
```
SUPABASE_URL=https://tjssgwvsmwdcqxbovuhw.supabase.co
SUPABASE_KEY=your_key_here
```

---

### `app.py` — CSS syntax error in input styling

**Current (missing semicolon):**
```css
.stTextInput input {
    background-color: grey   /* ← missing semicolon */
    color: #0F172A;
}
```

This silently breaks the entire CSS block. Add the missing `;` after `grey`.

---

### `app.py` — Duplicate `import os`

`import os` appears twice at the top. Remove the duplicate.

---

### `app.py` — Excel written to disk on every page load

```python
# This runs every time the admin page renders, not just on button click
filtered_df.to_excel(excel_file, index=False)
```

This writes a file to disk unconditionally on every Streamlit rerun. Move it inside a button callback or use `io.BytesIO` to generate it in memory.

**Fix:**
```python
import io

excel_buffer = io.BytesIO()
filtered_df.to_excel(excel_buffer, index=False)
st.download_button(
    label="Download Excel",
    data=excel_buffer.getvalue(),
    file_name="NE_Clothiers_measurements.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
```

---

## 2. Security

### Hardcoded admin credentials

**Current:**
```python
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "nedee123"
```

Credentials in source code are a serious risk — anyone with access to the file has the password.

**Fix:** Move to `.env` and load with `python-dotenv`:
```python
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
```

### Supabase key exposed in source

The Supabase publishable key is currently hardcoded in `supabase_client.py`. Even publishable keys should not be committed to version control. Move to `.env` and add `.env` to `.gitignore`.

### Add `.gitignore`

The project has a `.git` folder but no `.gitignore`. At minimum it should exclude:
```
.env
.venv/
__pycache__/
*.pyc
customer_images/
receipts/
NE_Clothiers_measurements.csv
NE_Clothiers_measurements.xlsx
```

---

## 3. Performance

### Cache `load_data()` in Streamlit

Every Streamlit interaction triggers a full rerun, which calls `load_data()` and re-reads the CSV from disk each time.

**Fix:**
```python
@st.cache_data
def load_data():
    ensure_file()
    return pd.read_csv(FILE_NAME)
```

Then call `st.cache_data.clear()` after saving new data so the cache refreshes.

### Use `st.session_state` for admin login

Currently the admin login resets on every interaction — the user has to log in again after every button click.

**Fix:**
```python
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if login_btn and username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
    st.session_state.logged_in = True

if st.session_state.logged_in:
    # show records
```

### Wire Supabase into `app.py`

`database.py` has `add_customer()` and `get_customers()` already written but they are never called from `app.py`. The app reads/writes CSV only. Connecting Supabase would:
- Enable multi-device access
- Remove the CSV bottleneck (slow past ~500 rows)
- Allow real-time data sync

### `tailor.py` — search function is commented out

The `search_customer()` function is fully written but commented out. Uncomment it and wire up the search entry widget.

---

## 4. `app.py` — Streamlit UI/UX

### Add a Dashboard page

Add a third sidebar option — **Dashboard** — showing:
- Total customers
- Orders due this week
- Payment breakdown (Not Paid / Part Payment / Fully Paid) as a bar or pie chart using `st.metric` and `st.bar_chart`
- Most recent 5 entries

### Group measurements with `st.expander`

The right column has 13 measurement fields stacked vertically with no grouping. Split into two collapsible sections:

```python
with st.expander("Upper Body Measurements", expanded=True):
    chest = st.text_input("Chest")
    stomach = st.text_input("Stomach")
    # ...

with st.expander("Lower Body Measurements", expanded=True):
    trouser_length = st.text_input("Trouser Length")
    # ...
```

### Add input validation for measurements

All measurement fields are free-text `st.text_input`. Users can type anything. Add numeric validation:

```python
def validate_measurement(value, field_name):
    if value and not value.replace('.', '', 1).isdigit():
        st.warning(f"{field_name} should be a number")
        return False
    return True
```

### Clarify photo input options

Both `st.file_uploader` and `st.camera_input` exist with no visual separation. Add a clear label:

```python
st.markdown("**Customer Photo** — upload a file or use the camera below")
```

And show a preview of the uploaded file immediately (not just after form submit).

### Add a success summary card after saving

Instead of just `st.success("Measurement saved successfully!")`, show a summary:

```python
st.success("Measurement saved!")
st.info(f"**{name}** | {outfit} | Delivery: {delivery_date} | {payment_status}")
```

### Add Edit & Delete in Customer Records

Currently records can only be viewed. Add:
- A **Delete** button per row (with confirmation dialog using `st.warning` + confirm button)
- An **Edit** mode that pre-fills the New Measurement form with selected customer data

### Improve sidebar branding

Add the logo/icon to the sidebar:
```python
st.sidebar.image("ne.png", width=120)
st.sidebar.title("NE Clothiers")
```

### Add a logout button

Once logged in, there is no way to log out without refreshing the page:
```python
if st.session_state.logged_in:
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
```

### Phone number validation

```python
import re
if phone and not re.match(r'^[0-9+\-\s]{7,15}$', phone):
    st.warning("Enter a valid phone number")
```

---

## 5. `tailor.py` — Tkinter Desktop UI/UX

### Uncomment and wire up search

The search function is already written — just needs to be activated:

```python
# Add this widget above the table
search_frame = tk.Frame(root, bg=BG_COLOR)
search_frame.pack(fill="x", padx=15, pady=5)

search_entry = tk.Entry(search_frame, font=("Segoe UI", 10), bg=ENTRY_BG, fg="white")
search_entry.pack(side="left", fill="x", expand=True, ipady=5)

tk.Button(search_frame, text="Search", command=search_customer, bg=BTN_COLOR, fg="white").pack(side="left", padx=5)
```

### Split form into two columns

The form is a single vertical stack of 15 fields. Use a two-column grid layout:

```python
left_frame = tk.Frame(form_frame, bg=CARD_COLOR)
left_frame.grid(row=0, column=0, padx=10)

right_frame = tk.Frame(form_frame, bg=CARD_COLOR)
right_frame.grid(row=0, column=1, padx=10)
```

Put Name, Outfit Type, Unit, Date in the left; all measurements in the right.

### Add a Delete button

```python
def delete_record():
    if selected_index is None:
        messagebox.showerror("Error", "Select a record first")
        return
    confirm = messagebox.askyesno("Confirm", "Delete this record?")
    if confirm:
        rows = []
        with open(FILE_NAME, newline="") as f:
            rows = list(csv.DictReader(f))
        rows.pop(selected_index)
        with open(FILE_NAME, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        load_table()
        clear_form()
```

### Fix table column widths

All columns are `width=90` which truncates names. Set variable widths:

```python
col_widths = {"Name": 150, "Outfit Type": 100, "Date": 130, "Unit": 60}
for col in FIELDS:
    table.column(col, width=col_widths.get(col, 90))
```

### Add alternating row colors

```python
table.tag_configure("odd", background="#1E293B")
table.tag_configure("even", background="#263548")

for i, row in enumerate(reader):
    tag = "even" if i % 2 == 0 else "odd"
    table.insert("", "end", iid=i, values=[row[f] for f in FIELDS], tags=(tag,))
```

### Add a status bar

Show record count and last saved time at the bottom of the window:

```python
status_bar = tk.Label(root, text="Ready", bg="#0F172A", fg="#94A3B8", anchor="w")
status_bar.pack(fill="x", side="bottom", padx=10, pady=2)
```

### Add keyboard shortcuts

```python
root.bind("<Control-s>", lambda e: save_data())
root.bind("<Control-e>", lambda e: export_excel())
root.bind("<Escape>", lambda e: clear_form())
```

---

## 6. New Features to Add

### Delivery Status Tracker

Add a `Delivery Status` field with values: `Pending`, `In Progress`, `Ready`, `Delivered`. Show overdue orders (past delivery date and not `Delivered`) highlighted in red in the records table.

### Print / PDF Receipt Generator

Use `reportlab` or `fpdf2` to generate a formatted PDF receipt per customer with their measurements and payment info. Add a "Print Receipt" button in the records view.

```
pip install fpdf2
```

### Customer History

Allow multiple orders per customer (currently each row is independent). Link records by phone number to show a customer's full order history.

### Outfit-Specific Measurement Fields

Different outfits need different measurements. Agbada doesn't need Trouser Length; a Suit doesn't need Hips. Show/hide measurement fields dynamically based on the selected outfit type.

### Backup & Restore

Add a one-click backup button that zips the CSV, images, and receipts into a timestamped archive. Add a restore option that unpacks a backup archive.

---

## 7. Code Quality & Structure

### Separate concerns into modules

Currently `app.py` mixes UI, data logic, and file I/O in one file. Suggested split:

```
app.py              ← Streamlit entry point (UI only)
data/
  storage.py        ← CSV read/write logic
  supabase.py       ← Supabase client + queries
  models.py         ← FIELDS definition, data validation
utils/
  file_helpers.py   ← Image/receipt saving
  validators.py     ← Input validation functions
pages/
  new_measurement.py
  customer_records.py
  dashboard.py
```

### Use a dataclass or TypedDict for customer data

```python
from typing import TypedDict

class CustomerRecord(TypedDict):
    Name: str
    Phone: str
    OutfitType: str
    Unit: str
    # ...
```

This catches field name typos at development time.

### Add `python-dotenv` to requirements.txt

```
streamlit
pandas
openpyxl
python-dotenv
supabase
```

---

## 8. Quick Wins Summary

These can be done in under 30 minutes each:

| # | Fix | File | Impact |
|---|-----|------|--------|
| 1 | Fix `os.getenv` bug | `supabase_client.py` | Correctness |
| 2 | Fix CSS missing semicolon | `app.py` | Visual |
| 3 | Remove duplicate `import os` | `app.py` | Cleanliness |
| 4 | Add `st.session_state` for login | `app.py` | UX |
| 5 | Cache `load_data()` | `app.py` | Performance |
| 6 | Fix Excel in-memory generation | `app.py` | Performance |
| 7 | Move credentials to `.env` | `app.py`, `supabase_client.py` | Security |
| 8 | Add `.gitignore` | root | Security |
| 9 | Uncomment search in tailor.py | `tailor.py` | UX |
| 10 | Fix table column widths | `tailor.py` | Visual |
| 11 | Add keyboard shortcuts | `tailor.py` | UX |
| 12 | Add logout button | `app.py` | UX |

---

## 9. Suggested File Structure

```
NE Clothiersfolder/
├── .env                          ← secrets (never commit)
├── .gitignore
├── app.py                        ← Streamlit web app
├── tailor.py                     ← Tkinter desktop app
├── database.py                   ← Supabase queries
├── supabase_client.py            ← Supabase connection
├── requirements.txt
├── IMPROVEMENTS.md               ← this file
├── ne.ico
├── ne.png
├── NE Clothiers.spec             ← PyInstaller spec
├── customer_images/              ← uploaded/captured photos
├── receipts/                     ← uploaded receipts
├── build/                        ← PyInstaller build output
└── dist/                         ← compiled .exe
```

---

*Last updated: May 2026*
