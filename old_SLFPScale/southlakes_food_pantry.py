import threading
import csv
import os
import json
import tkinter as tk
from tkinter import simpledialog, messagebox
from datetime import datetime
from collections import deque
from queue import Queue, Empty
from pywinusb import hid
import struct
from PIL import Image, ImageTk

# ── Configuration ─────────────────────────────────────────────
CSV_FILE        = "weights.csv"
SOURCE_CACHE    = "sources.json"
VENDOR_ID       = 0x0922
PRODUCT_ID      = 0x8009
TYPE_OPTIONS    = ["Produce", "Dry", "Dairy", "Meat",
                   "Prepared", "Bread", "Non-food"]
N_ROW           = 5    # 4 history + 1 preview
MIN_WEIGHT_LB   = 0.11

# Font sizes
FONT_WEIGHT = ("Helvetica", 48)
FONT_BUTTON = ("Helvetica", 24)
FONT_STATUS = ("Helvetica", 16)
FONT_SHEET  = ("Courier", 16)
FONT_MENU   = ("Helvetica", 16)

# ── Load or initialize food sources ───────────────────────────
if os.path.exists(SOURCE_CACHE):
    try:
        with open(SOURCE_CACHE, "r") as f:
            SOURCE_OPTIONS = json.load(f)
    except Exception:
        SOURCE_OPTIONS = ["Food for Neighbors"]
else:
    SOURCE_OPTIONS = ["Food for Neighbors"]

# ── Globals ───────────────────────────────────────────────────
device         = None
read_queue     = Queue()
stop_flag      = threading.Event()
last_kg        = None
last_lb        = None
history        = deque(maxlen=N_ROW-1)    # store 4 records
prev_row_data  = None
summary_labels = []

# In-memory totals & count
category_totals = {cat: 0.0 for cat in TYPE_OPTIONS}
overall_total   = 0.0
record_count    = 0

# ── HID reading via pywinusb ─────────────────────────────────
def open_scale():
    filt = hid.HidDeviceFilter(vendor_id=VENDOR_ID, product_id=PRODUCT_ID)
    devs = filt.get_devices()
    if not devs:
        raise RuntimeError("DYMO S100 not found")
    dev = devs[0]
    dev.open()
    return dev

def reader_thread():
    global device, last_kg, last_lb
    try:
        device = open_scale()
    except Exception as e:
        read_queue.put(("error", str(e)))
        return

    def handler(raw_report):
        global last_kg, last_lb
        ba = bytes(raw_report[:6])
        _, _, unit, exp, lo, hi = struct.unpack("6B", ba)
        if exp >= 128:
            exp -= 256
        raw = lo + (hi << 8)
        if unit == 0x0C:  # pounds
            lb = raw * (10 ** exp)
            kg = lb / 2.20462
        else:             # kilograms
            kg = raw * (10 ** exp)
            lb = kg * 2.20462
        last_kg, last_lb = kg, lb
        read_queue.put((kg, lb))

    device.set_raw_data_handler(handler)
    stop_flag.wait()
    device.close()

# ── GUI Callbacks ──────────────────────────────────────────────
def copy_csv_path():
    path = os.path.abspath(CSV_FILE)
    root.clipboard_clear()
    root.clipboard_append(path)
    status_var.set("Copied CSV path")
    status_lbl.config(fg="black")

def clear_csv():
    global overall_total, record_count
    if record_count == 0:
        status_var.set("No records to clear")
        status_lbl.config(fg="black")
        return

    if not messagebox.askyesno(
        "Confirm Clear",
        f"Delete {record_count} records totaling {overall_total:.1f} lb?"
    ):
        return

    open(CSV_FILE, "w").close()
    history.clear()
    for lbl in sheet_labels[:-1]:
        lbl.config(text="")
    overall_total = 0.0
    record_count = 0
    for cat in category_totals:
        category_totals[cat] = 0.0

    status_var.set("CSV cleared")
    status_lbl.config(fg="black")
    update_category_totals()
    update_total()

def add_new_source():
    val = simpledialog.askstring("Add Food Source", "Enter new food source:")
    if not val:
        return
    val = val.strip()
    if val not in SOURCE_OPTIONS:
        SOURCE_OPTIONS.append(val)
        with open(SOURCE_CACHE, "w") as f:
            json.dump(SOURCE_OPTIONS, f)
        menu = source_option_menu["menu"]
        menu.add_radiobutton(label=val, variable=selected_source_var, value=val)
    selected_source_var.set(val)
    status_lbl.config(fg="black")

def format_row(ts, kg, lb, t_str, s_str):
    t = datetime.fromisoformat(ts).strftime("%H:%M:%S")
    return f"{t} | {kg:5.1f}kg | {lb:5.1f}lb | {t_str} | {s_str}"

def preview_row(kg, lb):
    t = datetime.now().strftime("%H:%M:%S")
    return f"{t} | {kg:5.1f}kg | {lb:5.1f}lb | {selected_type_var.get()} | {selected_source_var.get()}"

def record(event=None):
    global prev_row_data, overall_total, record_count
    if last_lb is None or last_lb < MIN_WEIGHT_LB:
        status_var.set(f"Ignored: weight below {MIN_WEIGHT_LB:.2f} lb")
        status_lbl.config(fg="black")
        return

    row_data = (
        f"{last_kg:.2f}", f"{last_lb:.2f}",
        selected_type_var.get(), selected_source_var.get(),
    )
    is_dup = (row_data == prev_row_data)
    prev_row_data = row_data

    ts = datetime.now().isoformat(sep=" ", timespec="seconds")
    full_row = [ts, *row_data]
    new_file = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["Timestamp","KG","LB","Type","Source"])
        w.writerow(full_row)

    history.append((ts, *row_data))
    category_totals[selected_type_var.get()] += last_lb
    overall_total += last_lb
    record_count += 1

    refresh_history_display()
    update_category_totals()
    update_total()

    if is_dup:
        status_var.set("⚠️ Duplicate record")
        status_lbl.config(fg="red")
    else:
        status_var.set(f"Recorded at {ts}")
        status_lbl.config(fg="black")

def undo(event=None):
    global overall_total, record_count
    if not history:
        status_var.set("Nothing to undo")
        status_lbl.config(fg="black")
        return

    ts, kg_s, lb_s, type_s, _ = history.pop()
    lb = float(lb_s)
    category_totals[type_s] -= lb
    overall_total -= lb
    record_count -= 1

    with open(CSV_FILE, "r") as f:
        lines = f.readlines()
    if len(lines) > 1:
        lines.pop()
        with open(CSV_FILE, "w") as f:
            f.writelines(lines)

    refresh_history_display()
    update_category_totals()
    update_total()
    status_var.set("Last record undone")
    status_lbl.config(fg="black")

def refresh_history_display():
    for i, lbl in enumerate(sheet_labels[:-1]):
        if i < len(history):
            ts, kg_s, lb_s, t_s, s_s = history[i]
            lbl.config(text=format_row(ts, float(kg_s), float(lb_s), t_s, s_s))
        else:
            lbl.config(text="")
    if last_kg is not None and last_lb is not None:
        sheet_labels[-1].config(text=preview_row(last_kg, last_lb))
    else:
        sheet_labels[-1].config(text="")

def update_weight():
    try:
        while True:
            item = read_queue.get_nowait()
            if item[0] == "error":
                status_var.set(f"Error: {item[1]}")
                status_lbl.config(fg="black")
            else:
                kg, lb = item
                weight_lb_var.set(f"{lb:.2f} lb")
                sheet_labels[-1].config(text=preview_row(kg, lb))
    except Empty:
        pass
    root.after(200, update_weight)

def update_category_totals():
    for idx, cat in enumerate(TYPE_OPTIONS):
        summary_labels[idx].config(text=f"{cat}: {category_totals[cat]:.1f} lb")

def update_total():
    total_var.set(f"Total: {overall_total:.1f} lb")

# ── Build GUI ──────────────────────────────────────────────────
root = tk.Tk()
root.title("DYMO S100 Logger")
root.geometry("800x650")

# title‐bar icon
icon_path = os.path.join(os.path.dirname(__file__), "scale_icon.ico")
if os.path.exists(icon_path):
    try:
        root.iconbitmap(default=icon_path)
    except tk.TclError:
        pass

# Menubar: Food Source
menubar     = tk.Menu(root, font=FONT_MENU)
source_menu = tk.Menu(menubar, tearoff=0, font=FONT_MENU)
source_menu.add_command(label="Add Food Source…", command=add_new_source)
menubar.add_cascade(label="Food Source", menu=source_menu)
root.config(menu=menubar)

# Load & resize logos
raw = Image.open("scale_icon.png")
orig_w, orig_h = raw.size
h = 180
scale = h / orig_h
w = int(orig_w * scale)
raw = raw.resize((w, h), Image.BICUBIC)
left_logo = ImageTk.PhotoImage(raw)

raw2 = Image.open("slfp_logo.png")
orig_w2, orig_h2 = raw2.size
scale2 = h / orig_h2
w2 = int(orig_w2 * scale2)
raw2 = raw2.resize((w2, h), Image.BICUBIC)
right_logo = ImageTk.PhotoImage(raw2)

# Controls: logos + LB-only display
ctrl = tk.Frame(root)
ctrl.pack(pady=5, fill="x")

# left logo
tk.Label(ctrl, image=left_logo).pack(side="left", padx=5)
ctrl.left_logo = left_logo

# large LB display
weight_lb_var = tk.StringVar(value="-- lb")
tk.Label(ctrl, textvariable=weight_lb_var, font=FONT_WEIGHT).pack(side="left", expand=True)

# right logo
tk.Label(ctrl, image=right_logo).pack(side="right", padx=5)
ctrl.right_logo = right_logo

# Controls: Type & Source (below the logos row)
subctrl = tk.Frame(root)
subctrl.pack(pady=5)
selected_type_var   = tk.StringVar(value=TYPE_OPTIONS[0])
tk.Label(subctrl, text="Type:", font=FONT_MENU).pack(side="left", padx=5)
tk.OptionMenu(subctrl, selected_type_var, *TYPE_OPTIONS).pack(side="left")
selected_source_var = tk.StringVar(value=SOURCE_OPTIONS[0])
tk.Label(subctrl, text="Source:", font=FONT_MENU).pack(side="left", padx=5)
source_option_menu = tk.OptionMenu(subctrl, selected_source_var, *SOURCE_OPTIONS)
source_option_menu.pack(side="left")

# History + Preview (5 rows)
sheet = tk.Frame(root)
sheet.pack(fill="x", pady=5)
sheet_labels = []
for _ in range(N_ROW):
    lbl = tk.Label(sheet, text="", font=FONT_SHEET, anchor="w")
    lbl.pack(fill="x")
    sheet_labels.append(lbl)

# Buttons: Record & Undo
btns = tk.Frame(root)
btns.pack(pady=10)
tk.Button(btns, text="● RECORD", font=FONT_BUTTON, bg="red", fg="white",
          command=record).pack(side="left", padx=20)
tk.Button(btns, text="↺ UNDO",   font=FONT_BUTTON, command=undo).pack(side="left", padx=20)

# CSV actions: Copy & Clear
csvf = tk.Frame(root)
csvf.pack(pady=5)
tk.Button(csvf, text="📋 COPY CSV PATH", font=FONT_BUTTON,
          command=copy_csv_path).pack(side="left", padx=20)
tk.Button(csvf, text="🗑️ CLEAR CSV",     font=FONT_BUTTON,
          command=clear_csv).pack(side="left", padx=20)

# Category totals (grid, 4 columns)
catf = tk.Frame(root)
catf.pack(fill="x", pady=(0,2))
for idx, cat in enumerate(TYPE_OPTIONS):
    lbl = tk.Label(catf, text="", font=FONT_STATUS, anchor="w")
    lbl.grid(row=idx//4, column=idx%4, sticky="we", padx=10)
    summary_labels.append(lbl)
for col in range(4):
    catf.grid_columnconfigure(col, weight=1)

root.bind('<KeyRelease-space>', lambda e: record())

# Status & Total
btm = tk.Frame(root)
btm.pack(fill="x", side="bottom", pady=(2,5))
status_var = tk.StringVar(value="Ready")
status_lbl = tk.Label(btm, textvariable=status_var, font=FONT_STATUS, fg="black")
status_lbl.pack(side="left", padx=10)
total_var = tk.StringVar(value=f"Total: {overall_total:.1f} lb")
tk.Label(btm, textvariable=total_var, font=FONT_STATUS).pack(side="right", padx=10)

# Load existing history & seed in-memory totals
if os.path.exists(CSV_FILE):
    with open(CSV_FILE, "r") as f:
        reader = csv.reader(f)
        next(reader, None)
        rows = list(reader)
    record_count = len(rows)
    for ts, kg_s, lb_s, type_s, _ in rows[-(N_ROW-1):]:
        history.append((ts, kg_s, lb_s, type_s, _))
    for ts, kg_s, lb_s, type_s, _ in rows:
        lb = float(lb_s)
        category_totals[type_s] += lb
        overall_total += lb

refresh_history_display()
update_category_totals()
update_total()

# Cleanup & start
root.protocol("WM_DELETE_WINDOW", lambda: (stop_flag.set(), root.destroy()))
threading.Thread(target=reader_thread, daemon=True).start()
root.after(200, update_weight)
root.mainloop()
