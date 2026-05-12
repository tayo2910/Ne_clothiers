# ============================================================
# NE CLOTHIERS — Tkinter Desktop App
# ============================================================

import csv
import io
import os
import sys
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

# ── THEME ────────────────────────────────────────────────────
BG_COLOR    = "#010C26"
CARD_COLOR  = "#1E293B"
BTN_COLOR   = "#2563EB"
BTN_DANGER  = "#DC2626"
TEXT_COLOR  = "#FFFFFF"
ENTRY_BG    = "#334155"
ACCENT      = "#93C5FD"
ROW_ODD     = "#1E293B"
ROW_EVEN    = "#263548"

# ── FILE SETUP ───────────────────────────────────────────────
def get_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

BASE_DIR  = get_base_path()
FILE_NAME = os.path.join(BASE_DIR, "NE_Clothiers_measurements.csv")

FIELDS = [
    "Name", "Phone", "Outfit Type", "Unit", "Date",
    "Delivery Status", "Payment Status", "Amount Paid",
    "Chest", "Stomach", "Shoulder", "Sleeve Length",
    "Neck", "Round Sleeve", "Top Length",
    "Trouser Length", "Trouser-waist", "Hips",
    "Laps", "Knee", "Ankle"
]

INFO_FIELDS  = ["Name", "Phone", "Outfit Type", "Unit", "Date",
                "Delivery Status", "Payment Status", "Amount Paid"]
UPPER_FIELDS = ["Chest", "Stomach", "Shoulder", "Sleeve Length",
                "Neck", "Round Sleeve", "Top Length"]
LOWER_FIELDS = ["Trouser Length", "Trouser-waist", "Hips",
                "Laps", "Knee", "Ankle"]

entries        = {}
selected_index = None

# ── FILE HELPERS ─────────────────────────────────────────────
def ensure_file():
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()


def read_rows() -> list:
    ensure_file()
    with open(FILE_NAME, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_rows(rows: list):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

# ── FORM HELPERS ─────────────────────────────────────────────
def get_form_data() -> dict | None:
    data = {}
    for field in FIELDS:
        if field in ("Unit", "Date", "Delivery Status", "Payment Status"):
            continue
        widget = entries.get(field)
        value  = widget.get().strip() if widget else ""
        if field == "Name" and not value:
            messagebox.showerror("Error", "Customer name is required.")
            return None
        data[field] = value

    data["Unit"]            = unit_var.get()
    data["Delivery Status"] = delivery_var.get()
    data["Payment Status"]  = payment_var.get()
    data["Date"]            = datetime.now().strftime("%Y-%m-%d %H:%M")
    return data


def clear_form():
    global selected_index
    selected_index = None
    for widget in entries.values():
        widget.delete(0, tk.END)
    unit_var.set("cm")
    delivery_var.set("Pending")
    payment_var.set("Not Paid")
    set_status("Form cleared.")


def populate_form(values: list):
    """Fill form fields from a table row's values list."""
    for i, field in enumerate(FIELDS):
        if field == "Unit":
            unit_var.set(values[i])
        elif field == "Delivery Status":
            delivery_var.set(values[i])
        elif field == "Payment Status":
            payment_var.set(values[i])
        elif field == "Date":
            pass
        elif field in entries:
            entries[field].delete(0, tk.END)
            entries[field].insert(0, values[i])

# ── CORE FUNCTIONS ───────────────────────────────────────────
def save_data():
    data = get_form_data()
    if not data:
        return
    ensure_file()
    with open(FILE_NAME, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=FIELDS).writerow(data)
    messagebox.showinfo("Saved", f"Record for {data['Name']} saved successfully.")
    clear_form()
    load_table()


def update_data():
    global selected_index
    if selected_index is None:
        messagebox.showerror("Error", "Select a record from the table first.")
        return
    new_data = get_form_data()
    if not new_data:
        return
    rows = read_rows()
    if selected_index < len(rows):
        rows[selected_index] = new_data
        write_rows(rows)
        messagebox.showinfo("Updated", "Record updated successfully.")
        load_table()
        set_status(f"Updated record #{selected_index + 1}.")
    else:
        messagebox.showerror("Error", "Selected record no longer exists.")


def delete_data():
    global selected_index
    if selected_index is None:
        messagebox.showerror("Error", "Select a record from the table first.")
        return
    rows = read_rows()
    name = rows[selected_index].get("Name", "this record") if selected_index < len(rows) else "this record"
    confirm = messagebox.askyesno("Confirm Delete", f"Delete record for '{name}'? This cannot be undone.")
    if confirm:
        rows.pop(selected_index)
        write_rows(rows)
        clear_form()
        load_table()
        set_status(f"Deleted record for '{name}'.")


def export_excel():
    try:
        import pandas as pd
    except ImportError:
        messagebox.showerror("Error", "pandas is not installed. Run: pip install pandas openpyxl")
        return
    out = os.path.join(BASE_DIR, "NE_Clothiers_measurements.xlsx")
    pd.read_csv(FILE_NAME).to_excel(out, index=False)
    messagebox.showinfo("Exported", f"Excel file saved to:\n{out}")
    set_status("Exported to Excel.")


def search_customer(*_):
    query = search_var.get().lower().strip()
    table.delete(*table.get_children())
    rows = read_rows()
    count = 0
    for i, row in enumerate(rows):
        if (query in row.get("Name", "").lower() or
                query in row.get("Phone", "").lower()):
            tag = "even" if count % 2 == 0 else "odd"
            table.insert("", "end", iid=i, values=[row.get(f, "") for f in FIELDS], tags=(tag,))
            count += 1
    set_status(f"{count} record(s) found for '{query}'." if query else f"{count} records loaded.")


def load_table():
    table.delete(*table.get_children())
    rows = read_rows()
    for i, row in enumerate(rows):
        tag = "even" if i % 2 == 0 else "odd"
        table.insert("", "end", iid=i, values=[row.get(f, "") for f in FIELDS], tags=(tag,))
    set_status(f"{len(rows)} record(s) loaded.")


def on_row_select(event):
    global selected_index
    selected = table.focus()
    if not selected:
        return
    selected_index = int(selected)
    values = table.item(selected, "values")
    populate_form(list(values))
    set_status(f"Editing record #{selected_index + 1}: {values[0]}")


def set_status(msg: str):
    status_var.set(f"  {msg}  |  {datetime.now().strftime('%H:%M:%S')}")

# ── KEYBOARD SHORTCUTS ───────────────────────────────────────
def bind_shortcuts(root):
    root.bind("<Control-s>", lambda e: save_data())
    root.bind("<Control-u>", lambda e: update_data())
    root.bind("<Control-e>", lambda e: export_excel())
    root.bind("<Escape>",    lambda e: clear_form())
    root.bind("<Delete>",    lambda e: delete_data())

# ════════════════════════════════════════════════════════════
# UI BUILD
# ════════════════════════════════════════════════════════════
root = tk.Tk()
root.title("NE Clothiers — Measurement System")
root.geometry("1280x820")
root.minsize(1100, 700)
root.configure(bg=BG_COLOR)

bind_shortcuts(root)

# ── TITLE ────────────────────────────────────────────────────
tk.Label(root, text="NE CLOTHIERS", font=("Segoe UI", 26, "bold"),
         bg=BG_COLOR, fg="white").pack(pady=(18, 2))
tk.Label(root, text="Premium Tailoring Measurement System",
         font=("Segoe UI", 11), bg=BG_COLOR, fg=ACCENT).pack(pady=(0, 10))

# ── SEARCH BAR ───────────────────────────────────────────────
search_frame = tk.Frame(root, bg=BG_COLOR)
search_frame.pack(fill="x", padx=20, pady=(0, 6))

tk.Label(search_frame, text="🔍 Search:", bg=BG_COLOR, fg="white",
         font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 6))

search_var = tk.StringVar()
search_var.trace_add("write", search_customer)

search_entry = tk.Entry(search_frame, textvariable=search_var,
                        font=("Segoe UI", 10), bg=ENTRY_BG, fg="white",
                        insertbackground="white", relief="flat", width=35)
search_entry.pack(side="left", ipady=5, padx=(0, 8))

tk.Button(search_frame, text="Clear", command=lambda: search_var.set(""),
          bg=CARD_COLOR, fg="white", relief="flat", padx=8).pack(side="left")

# ── MAIN CONTENT AREA ────────────────────────────────────────
content_frame = tk.Frame(root, bg=BG_COLOR)
content_frame.pack(fill="both", expand=True, padx=15, pady=5)

# ── LEFT PANEL: FORM ─────────────────────────────────────────
form_outer = tk.Frame(content_frame, bg=CARD_COLOR, padx=16, pady=14,
                      relief="flat", bd=0)
form_outer.pack(side="left", fill="y", padx=(0, 10))

tk.Label(form_outer, text="Customer Details", font=("Segoe UI", 12, "bold"),
         bg=CARD_COLOR, fg=ACCENT).grid(row=0, column=0, columnspan=4,
                                         sticky="w", pady=(0, 8))

# Helper to add a labelled entry to the grid
def add_entry(parent, label, row, col, width=18):
    tk.Label(parent, text=label, bg=CARD_COLOR, fg=TEXT_COLOR,
             font=("Segoe UI", 9, "bold"), anchor="w", width=14
             ).grid(row=row, column=col, sticky="w", pady=2, padx=(0, 4))
    e = tk.Entry(parent, font=("Segoe UI", 10), bg=ENTRY_BG, fg="white",
                 insertbackground="white", relief="flat", width=width)
    e.grid(row=row, column=col + 1, sticky="ew", pady=2, ipady=4)
    return e

# ── INFO FIELDS (left column of form) ──
entries["Name"]        = add_entry(form_outer, "Name",         1, 0)
entries["Phone"]       = add_entry(form_outer, "Phone",        2, 0)
entries["Amount Paid"] = add_entry(form_outer, "Amount Paid",  3, 0)

# Unit radio
tk.Label(form_outer, text="Unit:", bg=CARD_COLOR, fg=TEXT_COLOR,
         font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky="w", pady=2)
unit_var   = tk.StringVar(value="cm")
unit_frame = tk.Frame(form_outer, bg=CARD_COLOR)
unit_frame.grid(row=4, column=1, sticky="w")
for val, lbl in [("cm", "CM"), ("inches", "Inches")]:
    tk.Radiobutton(unit_frame, text=lbl, variable=unit_var, value=val,
                   bg=CARD_COLOR, fg="white", activebackground=CARD_COLOR,
                   activeforeground="white", selectcolor=BTN_COLOR,
                   font=("Segoe UI", 9)).pack(side="left", padx=4)

# Outfit type
tk.Label(form_outer, text="Outfit Type:", bg=CARD_COLOR, fg=TEXT_COLOR,
         font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky="w", pady=2)
outfit_var = tk.StringVar(value="Agbada")
outfit_cb  = ttk.Combobox(form_outer, textvariable=outfit_var, width=16,
                           values=["Agbada", "Senator", "Suit", "Kaftan"],
                           state="readonly")
outfit_cb.grid(row=5, column=1, sticky="w", pady=2)

# Delivery status
tk.Label(form_outer, text="Delivery:", bg=CARD_COLOR, fg=TEXT_COLOR,
         font=("Segoe UI", 9, "bold")).grid(row=6, column=0, sticky="w", pady=2)
delivery_var = tk.StringVar(value="Pending")
delivery_cb  = ttk.Combobox(form_outer, textvariable=delivery_var, width=16,
                              values=["Pending", "In Progress", "Ready", "Delivered"],
                              state="readonly")
delivery_cb.grid(row=6, column=1, sticky="w", pady=2)

# Payment status
tk.Label(form_outer, text="Payment:", bg=CARD_COLOR, fg=TEXT_COLOR,
         font=("Segoe UI", 9, "bold")).grid(row=7, column=0, sticky="w", pady=2)
payment_var = tk.StringVar(value="Not Paid")
payment_cb  = ttk.Combobox(form_outer, textvariable=payment_var, width=16,
                             values=["Not Paid", "Part Payment", "Fully Paid"],
                             state="readonly")
payment_cb.grid(row=7, column=1, sticky="w", pady=2)

# ── MEASUREMENTS (right column of form) ──
tk.Label(form_outer, text="Upper Body", font=("Segoe UI", 10, "bold"),
         bg=CARD_COLOR, fg=ACCENT).grid(row=1, column=2, columnspan=2,
                                         sticky="w", padx=(20, 0), pady=(0, 4))
for r, field in enumerate(UPPER_FIELDS, start=2):
    entries[field] = add_entry(form_outer, field, r, 2, width=12)

tk.Label(form_outer, text="Lower Body", font=("Segoe UI", 10, "bold"),
         bg=CARD_COLOR, fg=ACCENT).grid(row=9, column=2, columnspan=2,
                                         sticky="w", padx=(20, 0), pady=(6, 4))
for r, field in enumerate(LOWER_FIELDS, start=10):
    entries[field] = add_entry(form_outer, field, r, 2, width=12)

form_outer.columnconfigure(1, weight=1)
form_outer.columnconfigure(3, weight=1)

# ── BUTTONS ──────────────────────────────────────────────────
btn_frame = tk.Frame(root, bg=BG_COLOR)
btn_frame.pack(pady=8)

btn_cfg = {"font": ("Segoe UI", 10, "bold"), "relief": "flat",
           "padx": 14, "pady": 6, "cursor": "hand2"}

tk.Button(btn_frame, text="💾 Save (Ctrl+S)",   command=save_data,
          bg=BTN_COLOR, fg="white", **btn_cfg).pack(side="left", padx=5)
tk.Button(btn_frame, text="✏️ Update (Ctrl+U)", command=update_data,
          bg="#0891B2", fg="white", **btn_cfg).pack(side="left", padx=5)
tk.Button(btn_frame, text="🗑️ Delete (Del)",    command=delete_data,
          bg=BTN_DANGER, fg="white", **btn_cfg).pack(side="left", padx=5)
tk.Button(btn_frame, text="📊 Export Excel (Ctrl+E)", command=export_excel,
          bg="#059669", fg="white", **btn_cfg).pack(side="left", padx=5)
tk.Button(btn_frame, text="🔄 Clear (Esc)",     command=clear_form,
          bg=CARD_COLOR, fg="white", **btn_cfg).pack(side="left", padx=5)

# ── TABLE ────────────────────────────────────────────────────
table_frame = tk.Frame(root, bg=BG_COLOR)
table_frame.pack(fill="both", expand=True, padx=15, pady=(0, 5))

style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview",
                background=ROW_ODD, foreground="white",
                fieldbackground=ROW_ODD, rowheight=26,
                font=("Segoe UI", 9))
style.configure("Treeview.Heading",
                background=BTN_COLOR, foreground="white",
                font=("Segoe UI", 9, "bold"))
style.map("Treeview", background=[("selected", "#2563EB")])

col_widths = {
    "Name": 140, "Phone": 110, "Outfit Type": 90, "Unit": 55,
    "Date": 130, "Delivery Status": 95, "Payment Status": 95,
    "Amount Paid": 90,
}

scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical")
scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal")

table = ttk.Treeview(table_frame, columns=FIELDS, show="headings",
                     yscrollcommand=scrollbar_y.set,
                     xscrollcommand=scrollbar_x.set)

scrollbar_y.config(command=table.yview)
scrollbar_x.config(command=table.xview)

for col in FIELDS:
    table.heading(col, text=col, anchor="w")
    table.column(col, width=col_widths.get(col, 80), minwidth=60, anchor="w")

table.tag_configure("odd",  background=ROW_ODD)
table.tag_configure("even", background=ROW_EVEN)

scrollbar_y.pack(side="right",  fill="y")
scrollbar_x.pack(side="bottom", fill="x")
table.pack(fill="both", expand=True)
table.bind("<<TreeviewSelect>>", on_row_select)

# ── STATUS BAR ───────────────────────────────────────────────
status_var = tk.StringVar(value="  Ready")
tk.Label(root, textvariable=status_var, bg="#0F172A", fg="#94A3B8",
         font=("Segoe UI", 9), anchor="w", relief="flat"
         ).pack(fill="x", side="bottom", padx=0, pady=0)

# ── KEYBOARD SHORTCUT HINT ───────────────────────────────────
hint = "  Ctrl+S: Save  |  Ctrl+U: Update  |  Del: Delete  |  Ctrl+E: Export  |  Esc: Clear"
tk.Label(root, text=hint, bg=BG_COLOR, fg="#475569",
         font=("Segoe UI", 8)).pack(side="bottom", anchor="w", padx=15)

# ── INIT ─────────────────────────────────────────────────────
ensure_file()
load_table()

root.mainloop()
