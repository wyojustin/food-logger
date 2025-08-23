import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from tkinter import filedialog
from PIL import Image, ImageTk
from datetime import datetime
import os
import csv
import scale_logger.db as db

LOGO1_PATH = "assets/slfp_logo.png"
LOGO2_PATH = "assets/scale_icon.png"

class ScaleLoggerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Scale Logger")
        self.geometry("800x500")
        self.resizable(False, False)

        self.create_widgets()
        self.update_totals()

    def create_widgets(self):
        # === Top logos and input frame ===
        top_frame = ttk.Frame(self)
        top_frame.pack(pady=10)

        self.logo1 = self.load_logo(LOGO1_PATH, (100, 150))
        self.logo2 = self.load_logo(LOGO2_PATH, (100, 150))

        if self.logo1:
            logo1_label = ttk.Label(top_frame, image=self.logo1)
            logo1_label.grid(row=0, column=0, padx=10)
        else:
            ttk.Label(top_frame, text="Missing Logo 1").grid(row=0, column=0)

        input_frame = ttk.Frame(top_frame)
        input_frame.grid(row=0, column=1, padx=10)

        ttk.Label(input_frame, text="Weight (lb):").pack(anchor='w')
        self.weight_var = tk.DoubleVar()
        ttk.Entry(input_frame, textvariable=self.weight_var, width=10).pack()

        ttk.Label(input_frame, text="Source:").pack(anchor='w', pady=(10, 0))
        self.source_var = tk.StringVar()
        source_list = db.get_sources()
        self.source_dropdown = ttk.Combobox(input_frame, 
                                            textvariable=self.source_var, 
                                            values=source_list, 
                                            state='readonly')
        self.source_dropdown.current(0)
        self.source_dropdown.pack()

        if self.logo2:
            logo2_label = ttk.Label(top_frame, image=self.logo2)
            logo2_label.grid(row=0, column=2, padx=10)
        else:
            ttk.Label(top_frame, text="Missing Logo 2").grid(row=0, column=2)

        # === Type buttons ===
        self.type_frame = ttk.Frame(self)
        self.type_frame.pack(pady=10)

        ttk.Label(self.type_frame, text="Category:", font=("Segoe UI", 12, "bold")).pack()

        button_row = ttk.Frame(self.type_frame)
        button_row.pack(pady=5)

        self.category_buttons = []
        for i, cat in enumerate(db.get_types()):
            btn = tk.Button(button_row, text=cat, width=12, height=2,
                            command=lambda c=cat: self.log_entry(c))
            btn.grid(row=i//4, column=i % 4, padx=5, pady=5)
            self.category_buttons.append(btn)

        # === Totals Display ===

        self.current_source_label = tk.Label(
            self, 
            text=f"Current Source: {self.source_var.get()}", 
            font=("Arial", 10, "italic"))
        self.current_source_label.pack(side="top", pady=2)
        self.total_label = ttk.Label(self, text="Totals will appear here.", font=("Segoe UI", 10))
        self.total_label.pack(pady=10)
        ttk.Button(self, 
                   text="Generate Report", 
                   command=self.open_report_popup).pack(pady=5)
        self.source_var.trace_add("write", 
                                  lambda *args: self.update_totals())


    def load_logo(self, path, size):
        try:
            if not os.path.exists(path):
                print(f"⚠️ Logo not found: {path}")
                return None
            img = Image.open(path).resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error loading logo {path}: {e}")
            return None

    def log_entry(self, category):
        try:
            weight = self.weight_var.get()
            source = self.source_var.get()
            if weight <= 0:
                messagebox.showerror("Invalid Input", "Please enter a valid weight.")
                return
            db.log_entry(weight=weight, dtype=category, source=source)
            self.weight_var.set(0.0)
            self.update_totals()
        except Exception as e:
            messagebox.showerror("Logging Error", str(e))

    def update_totals(self):
        try:
            source = self.source_var.get()
            self.current_source_label.config(
                text=f"Current Source: {source}")

            today = datetime.now().date().isoformat()
            cat_totals, total_weight, _ = db.create_report(source, start_date=today)

            if not cat_totals:
                self.total_label.config(text="No logs yet for today.")
                return

            lines = [f"{k}: {v:.1f} lb" for k, v in cat_totals.items()]
            lines.append(f"Total: {total_weight:.1f} lb")
            self.total_label.config(text="\n".join(lines))
        except Exception as e:
            self.total_label.config(text=f"Error: {e}")
    def open_report_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Generate Report")
        popup.geometry("300x200")
    
        today = datetime.now().date()
    
        ttk.Label(popup, text="Start Date:").pack(pady=(10, 0))
        start_cal = DateEntry(popup, width=12, background='darkblue',
                              foreground='white', borderwidth=2, year=today.year,
                              month=today.month, day=today.day)
        start_cal.pack(pady=5)
    
        ttk.Label(popup, text="End Date:").pack(pady=(10, 0))
        end_cal = DateEntry(popup, width=12, background='darkblue',
                            foreground='white', borderwidth=2, year=today.year,
                            month=today.month, day=today.day)
        end_cal.pack(pady=5)
    
        def save_report():
            start = start_cal.get_date().isoformat()
            end = end_cal.get_date().isoformat()
            source = self.source_var.get()
            cat_totals, total_weight, rows = db.create_report(source, start_date=start, end_date=end)
    
            file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                     filetypes=[("CSV files", "*.csv")],
                                                     title="Save Report As")
            if not file_path:
                return
    
            try:
                with open(file_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Source", source])
                    writer.writerow(["Start Date", start])
                    writer.writerow(["End Date", end])
                    writer.writerow([])
                    writer.writerow(["Summary by Category"])
                    for k, v in cat_totals.items():
                        writer.writerow([k, f"{v:.1f}"])
                    writer.writerow(["Total", f"{total_weight:.1f}"])
                    writer.writerow([])
                    writer.writerow(["Timestamp", "Weight", "Source", "Type", "Action"])
                    for row in rows:
                        writer.writerow(row)
                messagebox.showinfo("Success", f"Report saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error Saving", str(e))
    
        ttk.Button(popup, text="Save Report", command=save_report).pack(pady=15)
    
if __name__ == "__main__":
    db.initialize_db()
    app = ScaleLoggerApp()
    app.mainloop()
