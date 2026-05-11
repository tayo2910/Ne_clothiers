import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
from datetime import datetime
import sys

# ---------------- THEME ----------------
BG_COLOR = "#010C26"
CARD_COLOR = "#1E293B"
BTN_COLOR = "#2563EB"
TEXT_COLOR = "#FFFFFF"
ENTRY_BG = "#334155"

# ---------------- FILE SETUP ----------------
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

BASE_DIR = get_base_path()
FILE_NAME = os.path.join(BASE_DIR, "NE_Clothiers_measurements.csv")

FIELDS = [
    "Name", "Outfit Type", "Unit", "Date",
    "Chest", "Stomach", "Shoulder",
    "Sleeve Length", "Neck", "Round Sleeve", "Top Length",
    "Trouser Length", "Trouser-waist", "Hips",
    "Laps", "Knee", "Ankle"
]

entries = {}
selected_index = None

# ---------------- FILE HELPERS ----------------
def ensure_file():
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()

# ---------------- FORM DATA ----------------
def get_form_data():
    data = {}

    for field in FIELDS:
        if field in ["Unit", "Date"]:
            continue

        widget = entries.get(field)
        value = widget.get().strip() if widget else ""

        if field == "Name" and value == "":
            messagebox.showerror("Error", "Name is required")
            return None

        data[field] = value

    data["Unit"] = unit_var.get()
    data["Date"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    return data

# ---------------- CORE FUNCTIONS ----------------
def save_data():
    data = get_form_data()
    if not data:
        return

    ensure_file()

    with open(FILE_NAME, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writerow(data)

    messagebox.showinfo("Success", "Saved successfully")
    clear_form()
    load_table()

def load_table():
    ensure_file()
    table.delete(*table.get_children())

    with open(FILE_NAME, newline="") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            table.insert("", "end", iid=i, values=[row[f] for f in FIELDS])

# def search_customer():
#     query = search_entry.get().lower()
#     table.delete(*table.get_children())

#     with open(FILE_NAME, newline="") as f:
#         reader = csv.DictReader(f)

#         for i, row in enumerate(reader):
#             if query in row["Name"].lower():
#                 table.insert("", "end", iid=i, values=[row[f] for f in FIELDS])

def on_row_select(event):
    global selected_index

    selected = table.focus()
    if not selected:
        return

    selected_index = int(selected)
    values = table.item(selected, "values")

    for i, field in enumerate(FIELDS):
        if field in entries:
            entries[field].delete(0, tk.END)
            entries[field].insert(0, values[i])

    unit_var.set(values[FIELDS.index("Unit")])

def update_data():
    global selected_index

    if selected_index is None:
        messagebox.showerror("Error", "Select a record first")
        return

    new_data = get_form_data()
    if not new_data:
        return

    rows = []

    with open(FILE_NAME, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if selected_index < len(rows):
        rows[selected_index] = new_data

    with open(FILE_NAME, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    messagebox.showinfo("Updated", "Record updated")
    load_table()

def export_excel():
    try:
        import pandas as pd
    except ImportError:
        messagebox.showerror("Error", "Install pandas first")
        return

    df = pd.read_csv(FILE_NAME)
    df.to_excel("NE_Clothiers_measurements.xlsx", index=False)

    messagebox.showinfo("Exported", "Excel file created")

def clear_form():
    for widget in entries.values():
        widget.delete(0, tk.END)

# ---------------- UI ----------------
root = tk.Tk()
root.title("NE Clothiers Measurement System")
root.geometry("1100x750")
root.configure(bg=BG_COLOR)

# Title
tk.Label(
    root,
    text="NE CLOTHIERS",
    font=("Segoe UI", 24, "bold"),
    bg=BG_COLOR,
    fg="white"
).pack(pady=(20, 5))

tk.Label(
    root,
    text="Premium Tailoring Measurement System",
    font=("Segoe UI", 11),
    bg=BG_COLOR,
    fg="#CBD5E1"
).pack(pady=(0, 15))

# Unit
# ---------------- UNIT SELECTION ----------------
unit_var = tk.StringVar(value="cm")

unit_frame = tk.Frame(root, bg=BG_COLOR)
unit_frame.pack(pady=5)

tk.Label(
    unit_frame,
    text="Unit:",
    bg=BG_COLOR,
    fg="white",
    font=("Segoe UI", 10, "bold")
).pack(side="left", padx=5)

cm_radio = tk.Radiobutton(
    unit_frame,
    text="CM",
    variable=unit_var,
    value="cm",
    bg=BG_COLOR,
    fg="white",
    activebackground=BG_COLOR,
    activeforeground="white",
    selectcolor=BTN_COLOR,
    font=("Segoe UI", 10)
)

cm_radio.pack(side="left", padx=5)

inch_radio = tk.Radiobutton(
    unit_frame,
    text="Inches",
    variable=unit_var,
    value="inches",
    bg=BG_COLOR,
    fg="white",
    activebackground=BG_COLOR,
    activeforeground="white",
    selectcolor=BTN_COLOR,
    font=("Segoe UI", 10)
)

inch_radio.pack(side="left", padx=5)
# Form
form_frame = tk.Frame(root, bg=CARD_COLOR, padx=20, pady=20)
form_frame.pack(pady=15, padx=15, fill="x")

for field in FIELDS:
    if field in ["Unit", "Date"]:
        continue

    frame = tk.Frame(form_frame, bg=CARD_COLOR)
    frame.pack(fill="x", pady=2)

    tk.Label(
        frame,
        text=field,
        width=18,
        anchor="w",
        font=("Segoe UI", 10, "bold"),
        bg=CARD_COLOR,
        fg=TEXT_COLOR
    ).pack(side="left")

    entry = tk.Entry(
        frame,
        font=("Segoe UI", 10),
        bg=ENTRY_BG,
        fg="white",
        insertbackground="white",
        relief="flat"
    )
    entry.pack(fill="x", expand=True, ipady=5)

    entries[field] = entry

# Buttons
# ---------------- BUTTONS ----------------
btn_frame = tk.Frame(root, bg=BG_COLOR)
btn_frame.pack(pady=10)

tk.Button(
    btn_frame,
    text="Save",
    command=save_data,
    bg=BTN_COLOR,
    fg="white",
    padx=10,
    pady=5
).pack(side="left", padx=5)

tk.Button(
    btn_frame,
    text="Update",
    command=update_data,
    bg=BTN_COLOR,
    fg="white",
    padx=10,
    pady=5
).pack(side="left", padx=5)

tk.Button(
    btn_frame,
    text="Export",
    command=export_excel,
    bg=BTN_COLOR,
    fg="white",
    padx=10,
    pady=5
).pack(side="left", padx=5)

tk.Button(
    btn_frame,
    text="Clear",
    command=clear_form,
    bg=BTN_COLOR,
    fg="white",
    padx=10,
    pady=5
).pack(side="left", padx=5)

# Table
style = ttk.Style()
style.theme_use("clam")

style.configure("Treeview",
                background="#1E293B",
                foreground="white",
                fieldbackground="#1E293B",
                rowheight=28)

style.configure("Treeview.Heading",
                background="#2563EB",
                foreground="white")

table = ttk.Treeview(root, columns=FIELDS, show="headings")

for col in FIELDS:
    table.heading(col, text=col)
    table.column(col, width=90)

table.pack(expand=True, fill="both")
table.bind("<<TreeviewSelect>>", on_row_select)

# Init
ensure_file()
load_table()

root.mainloop()