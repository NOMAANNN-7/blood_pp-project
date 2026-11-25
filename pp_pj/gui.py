#!/usr/bin/env python3
"""
gui.py - LIFEPOINT: Modern Healthcare Desktop Application
Built with CustomTkinter for a premium CSS-like modern SaaS interface:
- Deep Crimson #B91C1C healthcare design system
- Modern left sidebar navigation (no truncated tabs)
- Rounded cards, smooth inputs, and hover states
- Light / Dark theme switching
- 8 Complete Modules: Dashboard, Registration, Donors, Analytics, Camps, CSV Import, Reports, Audit Logs
- 100% Offline Local Engine (SQLite)
"""

import os
import sys
import webbrowser
from datetime import datetime, date
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import customtkinter as ctk

# Ensure root directory is on Python path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.database import SessionLocal, engine, Base
from backend.app.models.donor import Donor
from backend.app.models.camp import DonationCamp
from backend.app.schemas.donor import DonorCreate, DonorUpdate, DonationRecordCreate
from backend.app.schemas.camp import CampCreate
from backend.app.services.donor_service import (
    register_donor,
    get_donors,
    get_donor_by_id,
    update_donor,
    soft_delete_donor,
    record_donation
)
from backend.app.services.camp_service import (
    create_camp,
    get_camps,
    delete_camp
)
from backend.app.services.analytics_service import (
    compute_blood_group_analytics,
    compute_dashboard_summary
)
from backend.app.services.import_export_service import (
    export_donors_csv,
    generate_pdf_report,
    parse_and_validate_csv,
    execute_csv_import
)
from backend.app.services.backup_service import create_json_backup
from backend.app.services.audit_service import get_audit_logs
from backend.app.config import ALLOWED_BLOOD_GROUPS, EXPORTS_DIR

# Ensure tables exist
Base.metadata.create_all(bind=engine)

# Configure CustomTkinter defaults
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class LifePointModernApp(ctk.CTk):
    """Modern Desktop Application Window with CSS-styled Healthcare Theme."""

    def __init__(self):
        super().__init__()
        self.title("LIFEPOINT — Blood Donation Camp Register & Management System")
        self.geometry("1200x780")
        self.minsize(1050, 680)

        # Setup modern ttk styles for tables
        self.setup_table_styles()

        # Main Layout: Left Sidebar + Right Content Area
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_content_area()

        # Initialize to Dashboard view
        self.active_nav_key = "dashboard"
        self.views = {}
        self.init_views()
        self.show_view("dashboard")

    def setup_table_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background="#F1F5F9",
            foreground="#0F172A",
            padding=[8, 8]
        )
        style.configure(
            "Treeview",
            font=("Segoe UI", 9),
            rowheight=28,
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#1E293B"
        )
        style.map(
            "Treeview",
            background=[("selected", "#B91C1C")],
            foreground=[("selected", "#FFFFFF")]
        )

    # --------------------------------------------------------------------------
    # Left Sidebar Navigation (Modern SaaS style)
    # --------------------------------------------------------------------------
    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color="#0F172A")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(9, weight=1)

        # Brand header
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(20, 20))

        lbl_logo = ctk.CTkLabel(
            brand_frame,
            text="🩸 LIFEPOINT",
            font=("Segoe UI", 20, "bold"),
            text_color="#FFFFFF"
        )
        lbl_logo.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            brand_frame,
            text="Blood Donation Manager",
            font=("Segoe UI", 11),
            text_color="#94A3B8"
        )
        lbl_sub.pack(anchor="w")

        # Nav Buttons list
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "📊  Dashboard"),
            ("register", "✍️  Register Volunteer"),
            ("donors", "👥  Donor Directory"),
            ("analytics", "🩸  Blood Analytics"),
            ("camps", "⛺  Donation Camps"),
            ("import", "📥  Bulk CSV Import"),
            ("reports", "📑  Reports & Exports"),
            ("audit", "📜  Audit & Activity Logs"),
        ]

        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                font=("Segoe UI", 12, "bold"),
                height=38,
                corner_radius=8,
                fg_color="transparent",
                text_color="#E2E8F0",
                hover_color="#1E293B",
                command=lambda k=key: self.show_view(k)
            )
            btn.pack(fill="x", padx=12, pady=4)
            self.nav_buttons[key] = btn

        # Spacer to push settings to bottom
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Theme Switcher & Status in sidebar bottom
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="#1E293B", corner_radius=10)
        bottom_frame.pack(fill="x", padx=12, pady=16)

        lbl_theme = ctk.CTkLabel(bottom_frame, text="Theme Mode:", font=("Segoe UI", 10, "bold"), text_color="#94A3B8")
        lbl_theme.pack(anchor="w", padx=12, pady=(8, 2))

        self.theme_menu = ctk.CTkOptionMenu(
            bottom_frame,
            values=["Light", "Dark"],
            height=26,
            corner_radius=6,
            fg_color="#334155",
            button_color="#475569",
            command=self.change_theme
        )
        self.theme_menu.set("Light")
        self.theme_menu.pack(fill="x", padx=12, pady=(0, 8))

        lbl_db = ctk.CTkLabel(
            bottom_frame,
            text="● Local SQLite Connected",
            font=("Segoe UI", 9, "bold"),
            text_color="#22C55E"
        )
        lbl_db.pack(anchor="w", padx=12, pady=(0, 8))

    def change_theme(self, new_mode: str):
        ctk.set_appearance_mode(new_mode)

    # --------------------------------------------------------------------------
    # Main Content Area
    # --------------------------------------------------------------------------
    def create_content_area(self):
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="#F8FAFC")
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Top Header Bar
        self.top_bar = ctk.CTkFrame(self.main_container, height=60, corner_radius=0, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        self.top_bar.grid(row=0, column=0, sticky="ew")

        self.lbl_view_title = ctk.CTkLabel(
            self.top_bar,
            text="Executive Dashboard",
            font=("Segoe UI", 16, "bold"),
            text_color="#0F172A"
        )
        self.lbl_view_title.pack(side="left", padx=20, pady=15)

        self.btn_refresh = ctk.CTkButton(
            self.top_bar,
            text="🔄 Refresh Data",
            font=("Segoe UI", 11, "bold"),
            fg_color="#B91C1C",
            hover_color="#991B1B",
            corner_radius=8,
            height=32,
            command=self.refresh_all
        )
        self.btn_refresh.pack(side="right", padx=20, pady=14)

        # Dynamic Content View Host
        self.view_host = ctk.CTkFrame(self.main_container, corner_radius=0, fg_color="#F8FAFC")
        self.view_host.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        self.view_host.grid_rowconfigure(0, weight=1)
        self.view_host.grid_columnconfigure(0, weight=1)

    def init_views(self):
        # 1. Dashboard
        self.views["dashboard"] = self.build_dashboard_view()
        # 2. Register
        self.views["register"] = self.build_register_view()
        # 3. Donors
        self.views["donors"] = self.build_donors_view()
        # 4. Analytics
        self.views["analytics"] = self.build_analytics_view()
        # 5. Camps
        self.views["camps"] = self.build_camps_view()
        # 6. Import
        self.views["import"] = self.build_import_view()
        # 7. Reports
        self.views["reports"] = self.build_reports_view()
        # 8. Audit
        self.views["audit"] = self.build_audit_view()

    def show_view(self, key: str):
        self.active_nav_key = key

        # Update sidebar styling
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color="#B91C1C", text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color="#E2E8F0")

        # Update Top Bar Title
        titles = {
            "dashboard": "Executive Analytics & Camp Overview",
            "register": "Register New Volunteer Donor",
            "donors": "Donor Records & Clinical Verification",
            "analytics": "Blood Group Inventory & Percentage Distribution",
            "camps": "Donation Camps & Venue Scheduling",
            "import": "Bulk CSV Dataset Import & Validation",
            "reports": "Audited Reports, PDF Generation & JSON Backups",
            "audit": "Chronological System Audit & Activity Logs",
        }
        self.lbl_view_title.configure(text=titles.get(key, "LIFEPOINT"))

        # Hide all views and show the selected one
        for v in self.views.values():
            v.grid_forget()

        self.views[key].grid(row=0, column=0, sticky="nsew")

        # Trigger data refresh for the view
        if key == "dashboard":
            self.refresh_dashboard()
        elif key == "donors":
            self.load_donors()
        elif key == "analytics":
            self.load_analytics()
        elif key == "camps":
            self.load_camps()
        elif key == "audit":
            self.load_audit_logs()

    # --------------------------------------------------------------------------
    # VIEW 1: EXECUTIVE DASHBOARD
    # --------------------------------------------------------------------------
    def build_dashboard_view(self):
        frame = ctk.CTkScrollableFrame(self.view_host, fg_color="transparent")

        # KPI Metric Cards
        kpi_grid = ctk.CTkFrame(frame, fg_color="transparent")
        kpi_grid.pack(fill="x", pady=(0, 14))

        self.kpi_labels = {}
        cards = [
            ("volunteers", "Total Volunteers", "0", "#B91C1C"),
            ("eligible", "Eligible Donors", "0", "#16A34A"),
            ("deferred", "Temp Deferred", "0", "#D97706"),
            ("camps", "Upcoming Camps", "0", "#2563EB"),
            ("donations", "Completed Units", "0", "#9333EA"),
            ("dominant", "Dominant Group", "N/A", "#DC2626"),
        ]

        for idx, (k, title, val, color) in enumerate(cards):
            card = ctk.CTkFrame(kpi_grid, corner_radius=10, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
            card.grid(row=0, column=idx, padx=4, sticky="nsew")
            kpi_grid.grid_columnconfigure(idx, weight=1)

            lbl_t = ctk.CTkLabel(card, text=title, font=("Segoe UI", 10, "bold"), text_color="#64748B")
            lbl_t.pack(anchor="w", padx=12, pady=(10, 0))

            lbl_v = ctk.CTkLabel(card, text=val, font=("Segoe UI", 18, "bold"), text_color=color)
            lbl_v.pack(anchor="w", padx=12, pady=(2, 10))
            self.kpi_labels[k] = lbl_v

        # Blood Group Inventory Cards (8 Standard Groups)
        bg_card_container = ctk.CTkFrame(frame, corner_radius=12, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        bg_card_container.pack(fill="x", pady=8)

        lbl_bg_sec = ctk.CTkLabel(
            bg_card_container,
            text="🩸 Blood Group Distribution (Live Inventory Count)",
            font=("Segoe UI", 13, "bold"),
            text_color="#0F172A"
        )
        lbl_bg_sec.pack(anchor="w", padx=16, pady=(12, 8))

        bg_grid = ctk.CTkFrame(bg_card_container, fg_color="transparent")
        bg_grid.pack(fill="x", padx=12, pady=(0, 14))

        self.bg_label_cards = {}
        for idx, bg in enumerate(ALLOWED_BLOOD_GROUPS):
            c = ctk.CTkFrame(bg_grid, corner_radius=8, fg_color="#FEF2F2", border_width=1, border_color="#FECACA")
            c.grid(row=0, column=idx, padx=4, sticky="nsew")
            bg_grid.grid_columnconfigure(idx, weight=1)

            lbl_g = ctk.CTkLabel(c, text=bg, font=("Segoe UI", 14, "bold"), text_color="#B91C1C")
            lbl_g.pack(pady=(6, 0))

            lbl_cnt = ctk.CTkLabel(c, text="0", font=("Segoe UI", 15, "bold"), text_color="#1E293B")
            lbl_cnt.pack(pady=(0, 6))
            self.bg_label_cards[bg] = lbl_cnt

        # Recent Registrations Table Card
        recent_container = ctk.CTkFrame(frame, corner_radius=12, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        recent_container.pack(fill="both", expand=True, pady=10)

        lbl_rec = ctk.CTkLabel(
            recent_container,
            text="📋 Recent Volunteer Registrations",
            font=("Segoe UI", 13, "bold"),
            text_color="#0F172A"
        )
        lbl_rec.pack(anchor="w", padx=16, pady=(12, 8))

        cols = ("donor_id", "name", "blood_group", "city", "status", "reg_date")
        self.tree_recent = ttk.Treeview(recent_container, columns=cols, show="headings", height=8)
        self.tree_recent.heading("donor_id", text="Donor ID")
        self.tree_recent.heading("name", text="Full Name")
        self.tree_recent.heading("blood_group", text="Group")
        self.tree_recent.heading("city", text="City")
        self.tree_recent.heading("status", text="Verification Status")
        self.tree_recent.heading("reg_date", text="Registered At")

        self.tree_recent.column("donor_id", width=120)
        self.tree_recent.column("name", width=220)
        self.tree_recent.column("blood_group", width=80, anchor="center")
        self.tree_recent.column("city", width=140)
        self.tree_recent.column("status", width=160)
        self.tree_recent.column("reg_date", width=160)
        self.tree_recent.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        return frame

    def refresh_dashboard(self):
        db = SessionLocal()
        try:
            summary = compute_dashboard_summary(db)
            analytics = compute_blood_group_analytics(db)

            self.kpi_labels["volunteers"].configure(text=str(summary.total_volunteers))
            self.kpi_labels["eligible"].configure(text=str(summary.eligible_donors))
            self.kpi_labels["deferred"].configure(text=str(summary.temporarily_deferred))
            self.kpi_labels["camps"].configure(text=str(summary.upcoming_camps))
            self.kpi_labels["donations"].configure(text=str(summary.completed_donations))
            self.kpi_labels["dominant"].configure(text=str(summary.most_common_blood_group or "N/A"))

            for bg_stat in analytics.blood_groups:
                if bg_stat.blood_group in self.bg_label_cards:
                    self.bg_label_cards[bg_stat.blood_group].configure(text=str(bg_stat.total_donors))

            for item in self.tree_recent.get_children():
                self.tree_recent.delete(item)
            for d in summary.recent_donors:
                self.tree_recent.insert("", "end", values=(
                    d["donor_id"], d["full_name"], d["blood_group"], d["city"], d["screening_status"], d["registration_date"]
                ))
        finally:
            db.close()

    # --------------------------------------------------------------------------
    # VIEW 2: VOLUNTEER REGISTRATION FORM (CSS Styled Card)
    # --------------------------------------------------------------------------
    def build_register_view(self):
        frame = ctk.CTkScrollableFrame(self.view_host, fg_color="transparent")

        card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        card.pack(fill="x", padx=10, pady=10)

        lbl_header = ctk.CTkLabel(
            card,
            text="✍️ Volunteer Donor Registration",
            font=("Segoe UI", 16, "bold"),
            text_color="#B91C1C"
        )
        lbl_header.pack(anchor="w", padx=20, pady=(18, 4))

        lbl_desc = ctk.CTkLabel(
            card,
            text="Enter personal details, blood group, contact information, and medical screening responses.",
            font=("Segoe UI", 11),
            text_color="#64748B"
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 16))

        # 2-Column Form Grid
        f_grid = ctk.CTkFrame(card, fg_color="transparent")
        f_grid.pack(fill="x", padx=20, pady=5)
        f_grid.grid_columnconfigure(0, weight=1)
        f_grid.grid_columnconfigure(1, weight=1)

        # Full Name
        ctk.CTkLabel(f_grid, text="Full Name *", font=("Segoe UI", 11, "bold"), text_color="#1E293B").grid(row=0, column=0, sticky="w", pady=(6, 2))
        self.entry_name = ctk.CTkEntry(f_grid, placeholder_text="e.g. John Doe", height=36, corner_radius=8)
        self.entry_name.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))

        # Phone
        ctk.CTkLabel(f_grid, text="Phone (10+ digits) *", font=("Segoe UI", 11, "bold"), text_color="#1E293B").grid(row=0, column=1, sticky="w", pady=(6, 2))
        self.entry_phone = ctk.CTkEntry(f_grid, placeholder_text="+919876543210", height=36, corner_radius=8)
        self.entry_phone.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))

        # DOB
        ctk.CTkLabel(f_grid, text="Date of Birth (YYYY-MM-DD) *", font=("Segoe UI", 11, "bold"), text_color="#1E293B").grid(row=2, column=0, sticky="w", pady=(6, 2))
        self.entry_dob = ctk.CTkEntry(f_grid, placeholder_text="1995-05-15", height=36, corner_radius=8)
        self.entry_dob.insert(0, "1995-05-15")
        self.entry_dob.grid(row=3, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))

        # Blood Group
        ctk.CTkLabel(f_grid, text="Blood Group *", font=("Segoe UI", 11, "bold"), text_color="#1E293B").grid(row=2, column=1, sticky="w", pady=(6, 2))
        self.combo_bg = ctk.CTkOptionMenu(f_grid, values=ALLOWED_BLOOD_GROUPS, height=36, corner_radius=8, fg_color="#B91C1C", button_color="#991B1B")
        self.combo_bg.set("O+")
        self.combo_bg.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))

        # Weight
        ctk.CTkLabel(f_grid, text="Weight in kg (Min 50kg) *", font=("Segoe UI", 11, "bold"), text_color="#1E293B").grid(row=4, column=0, sticky="w", pady=(6, 2))
        self.entry_weight = ctk.CTkEntry(f_grid, placeholder_text="65.0", height=36, corner_radius=8)
        self.entry_weight.insert(0, "65.0")
        self.entry_weight.grid(row=5, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))

        # Gender
        ctk.CTkLabel(f_grid, text="Gender", font=("Segoe UI", 11, "bold"), text_color="#1E293B").grid(row=4, column=1, sticky="w", pady=(6, 2))
        self.combo_gender = ctk.CTkOptionMenu(f_grid, values=["Male", "Female", "Other", "Prefer not to say"], height=36, corner_radius=8)
        self.combo_gender.set("Male")
        self.combo_gender.grid(row=5, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))

        # Street Address
        ctk.CTkLabel(f_grid, text="Street Address *", font=("Segoe UI", 11, "bold"), text_color="#1E293B").grid(row=6, column=0, sticky="w", pady=(6, 2))
        self.entry_addr = ctk.CTkEntry(f_grid, placeholder_text="123 Hospital Road", height=36, corner_radius=8)
        self.entry_addr.grid(row=7, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))

        # City
        ctk.CTkLabel(f_grid, text="City *", font=("Segoe UI", 11, "bold"), text_color="#1E293B").grid(row=6, column=1, sticky="w", pady=(6, 2))
        self.entry_city = ctk.CTkEntry(f_grid, placeholder_text="Bengaluru", height=36, corner_radius=8)
        self.entry_city.insert(0, "Bengaluru")
        self.entry_city.grid(row=7, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))

        # State & PIN
        ctk.CTkLabel(f_grid, text="State *", font=("Segoe UI", 11, "bold"), text_color="#1E293B").grid(row=8, column=0, sticky="w", pady=(6, 2))
        self.entry_state = ctk.CTkEntry(f_grid, placeholder_text="Karnataka", height=36, corner_radius=8)
        self.entry_state.insert(0, "Karnataka")
        self.entry_state.grid(row=9, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))

        ctk.CTkLabel(f_grid, text="PIN Code *", font=("Segoe UI", 11, "bold"), text_color="#1E293B").grid(row=8, column=1, sticky="w", pady=(6, 2))
        self.entry_pin = ctk.CTkEntry(f_grid, placeholder_text="560001", height=36, corner_radius=8)
        self.entry_pin.insert(0, "560001")
        self.entry_pin.grid(row=9, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))

        # Medical Checklist Card
        chk_card = ctk.CTkFrame(card, corner_radius=8, fg_color="#F8FAFC", border_width=1, border_color="#E2E8F0")
        chk_card.pack(fill="x", padx=20, pady=12)

        ctk.CTkLabel(
            chk_card,
            text="🩺 Preliminary Medical Screening Checklist",
            font=("Segoe UI", 12, "bold"),
            text_color="#B91C1C"
        ).pack(anchor="w", padx=14, pady=(10, 6))

        self.chk_chronic = ctk.CTkCheckBox(chk_card, text="Chronic medical condition reported (cardiac, hepatitis, bleeding disorder)", fg_color="#B91C1C")
        self.chk_chronic.pack(anchor="w", padx=14, pady=4)

        self.chk_surgery = ctk.CTkCheckBox(chk_card, text="Recent major surgery or dental extraction in past 6 months", fg_color="#B91C1C")
        self.chk_surgery.pack(anchor="w", padx=14, pady=4)

        self.chk_meds = ctk.CTkCheckBox(chk_card, text="Active prescription medication (antibiotics, blood thinners)", fg_color="#B91C1C")
        self.chk_meds.pack(anchor="w", padx=14, pady=(4, 12))

        # Submit Button
        btn_submit = ctk.CTkButton(
            card,
            text="✓ Submit Volunteer Registration",
            font=("Segoe UI", 13, "bold"),
            fg_color="#B91C1C",
            hover_color="#991B1B",
            corner_radius=8,
            height=42,
            command=self.handle_registration
        )
        btn_submit.pack(anchor="w", padx=20, pady=(10, 20))

        return frame

    def handle_registration(self):
        name = self.entry_name.get().strip()
        phone = self.entry_phone.get().strip()
        dob_str = self.entry_dob.get().strip()
        bg = self.combo_bg.get().strip()
        weight_str = self.entry_weight.get().strip()
        city = self.entry_city.get().strip()
        addr = self.entry_addr.get().strip()
        state = self.entry_state.get().strip()
        pin = self.entry_pin.get().strip()

        if not name or not phone or not dob_str or not city or not addr or not state or not pin:
            messagebox.showerror("Validation Error", "Please fill in all mandatory fields marked with *.")
            return

        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid Date of Birth format. Please use YYYY-MM-DD.")
            return

        try:
            weight = float(weight_str)
        except ValueError:
            messagebox.showerror("Validation Error", "Weight must be a valid number.")
            return

        db = SessionLocal()
        try:
            donor_in = DonorCreate(
                full_name=name,
                date_of_birth=dob,
                gender=self.combo_gender.get(),
                phone=phone,
                address=addr,
                city=city,
                state=state,
                pin_code=pin,
                blood_group=bg,
                weight_kg=weight,
                has_chronic_illness=bool(self.chk_chronic.get()),
                has_recent_surgery=bool(self.chk_surgery.get()),
                has_medication=bool(self.chk_meds.get()),
                consent_data_storage=True,
                consent_contact=True
            )
            donor = register_donor(db, donor_in)
            messagebox.showinfo(
                "Registration Successful",
                f"Volunteer '{donor.full_name}' registered successfully!\n\n"
                f"Assigned Donor ID: {donor.donor_id}\n"
                f"Blood Group: {donor.blood_group}\n"
                f"Calculated Age: {donor.age} years\n"
                f"Screening Status: {donor.screening_status}"
            )
            # Clear form
            self.entry_name.delete(0, "end")
            self.entry_phone.delete(0, "end")
            self.entry_addr.delete(0, "end")
            self.refresh_all()
            self.show_view("donors")
        except Exception as e:
            messagebox.showerror("Registration Failed", str(e))
        finally:
            db.close()

    # --------------------------------------------------------------------------
    # VIEW 3: DONOR DIRECTORY
    # --------------------------------------------------------------------------
    def build_donors_view(self):
        frame = ctk.CTkFrame(self.view_host, fg_color="transparent")

        # Top search & action toolbar card
        bar = ctk.CTkFrame(frame, corner_radius=10, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        bar.pack(fill="x", pady=(0, 10))

        self.entry_search = ctk.CTkEntry(bar, placeholder_text="🔍 Search by name, phone, city, or donor ID...", width=320, height=36, corner_radius=8)
        self.entry_search.pack(side="left", padx=12, pady=10)

        btn_search = ctk.CTkButton(bar, text="Search", width=80, height=36, corner_radius=8, fg_color="#1E293B", command=self.load_donors)
        btn_search.pack(side="left", padx=(0, 10))

        self.filter_bg = ctk.CTkOptionMenu(bar, values=["All Groups"] + ALLOWED_BLOOD_GROUPS, width=130, height=36, corner_radius=8, command=lambda v: self.load_donors())
        self.filter_bg.set("All Groups")
        self.filter_bg.pack(side="left", padx=5)

        btn_del = ctk.CTkButton(bar, text="🗑️ Deactivate", width=110, height=36, corner_radius=8, fg_color="#EF4444", hover_color="#DC2626", command=self.handle_delete_donor_selected)
        btn_del.pack(side="right", padx=12)

        btn_rec_don = ctk.CTkButton(bar, text="🩸 Record Donation", width=140, height=36, corner_radius=8, fg_color="#B91C1C", hover_color="#991B1B", command=self.handle_record_donation_selected)
        btn_rec_don.pack(side="right", padx=5)

        # Table Card
        tbl_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        tbl_card.pack(fill="both", expand=True)

        cols = ("donor_id", "name", "blood_group", "age", "phone", "city", "status", "donations", "reg_date")
        self.tree_donors = ttk.Treeview(tbl_card, columns=cols, show="headings")
        self.tree_donors.heading("donor_id", text="Donor ID")
        self.tree_donors.heading("name", text="Full Name")
        self.tree_donors.heading("blood_group", text="Group")
        self.tree_donors.heading("age", text="Age")
        self.tree_donors.heading("phone", text="Phone")
        self.tree_donors.heading("city", text="City")
        self.tree_donors.heading("status", text="Verification Status")
        self.tree_donors.heading("donations", text="Units")
        self.tree_donors.heading("reg_date", text="Registered")

        self.tree_donors.column("donor_id", width=110)
        self.tree_donors.column("name", width=180)
        self.tree_donors.column("blood_group", width=70, anchor="center")
        self.tree_donors.column("age", width=50, anchor="center")
        self.tree_donors.column("phone", width=120)
        self.tree_donors.column("city", width=120)
        self.tree_donors.column("status", width=160)
        self.tree_donors.column("donations", width=70, anchor="center")
        self.tree_donors.column("reg_date", width=110)

        scrollbar = ttk.Scrollbar(tbl_card, orient="vertical", command=self.tree_donors.yview)
        self.tree_donors.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", pady=10)
        self.tree_donors.pack(fill="both", expand=True, padx=(12, 0), pady=12)

        return frame

    def load_donors(self):
        query = self.entry_search.get().strip()
        bg = self.filter_bg.get()
        bg_filter = None if bg == "All Groups" else bg

        db = SessionLocal()
        try:
            donors, total = get_donors(db, search=query or None, blood_group=bg_filter, page_size=300)
            for item in self.tree_donors.get_children():
                self.tree_donors.delete(item)
            for d in donors:
                self.tree_donors.insert("", "end", values=(
                    d.donor_id, d.full_name, d.blood_group, d.age, d.phone, d.city, d.screening_status, d.total_donations, d.registration_date.strftime("%Y-%m-%d")
                ))
        finally:
            db.close()

    def handle_record_donation_selected(self):
        selected = self.tree_donors.selection()
        if not selected:
            messagebox.showinfo("Select Donor", "Please select a donor record from the table first.")
            return
        vals = self.tree_donors.item(selected[0], "values")
        did, name = vals[0], vals[1]

        if messagebox.askyesno("Confirm Donation", f"Record 1.0 unit blood donation event for {name} ({did})?"):
            db = SessionLocal()
            try:
                record_donation(db, did, DonationRecordCreate(donation_date=date.today(), units_donated=1.0))
                messagebox.showinfo("Recorded", f"✓ Donation successfully recorded for {name}!")
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                db.close()

    def handle_delete_donor_selected(self):
        selected = self.tree_donors.selection()
        if not selected:
            messagebox.showinfo("Select Donor", "Please select a donor record from the table first.")
            return
        vals = self.tree_donors.item(selected[0], "values")
        did, name = vals[0], vals[1]

        if messagebox.askyesno("Confirm Deactivation", f"Are you sure you want to soft-delete donor '{name}' ({did})?"):
            db = SessionLocal()
            try:
                soft_delete_donor(db, did)
                messagebox.showinfo("Deactivated", f"Donor {did} deactivated.")
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                db.close()

    # --------------------------------------------------------------------------
    # VIEW 4: BLOOD GROUP ANALYTICS
    # --------------------------------------------------------------------------
    def build_analytics_view(self):
        frame = ctk.CTkFrame(self.view_host, fg_color="transparent")

        summary_card = ctk.CTkFrame(frame, corner_radius=10, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        summary_card.pack(fill="x", pady=(0, 10))

        self.lbl_anal_summary = ctk.CTkLabel(
            summary_card,
            text="Calculating Python collections.Counter Aggregation...",
            font=("Segoe UI", 12, "bold"),
            text_color="#B91C1C"
        )
        self.lbl_anal_summary.pack(anchor="w", padx=16, pady=14)

        tbl_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        tbl_card.pack(fill="both", expand=True)

        cols = ("bg", "total", "eligible", "temp_def", "perm_def", "donations", "share")
        self.tree_analytics = ttk.Treeview(tbl_card, columns=cols, show="headings")
        self.tree_analytics.heading("bg", text="Blood Group")
        self.tree_analytics.heading("total", text="Total Donors")
        self.tree_analytics.heading("eligible", text="Eligible")
        self.tree_analytics.heading("temp_def", text="Temp Deferred")
        self.tree_analytics.heading("perm_def", text="Perm Deferred")
        self.tree_analytics.heading("donations", text="Completed Units")
        self.tree_analytics.heading("share", text="Inventory Share (%)")

        for col in cols:
            self.tree_analytics.column(col, width=130, anchor="center")

        self.tree_analytics.pack(fill="both", expand=True, padx=12, pady=12)
        return frame

    def load_analytics(self):
        db = SessionLocal()
        try:
            analytics = compute_blood_group_analytics(db)
            self.lbl_anal_summary.configure(
                text=f"Total Registered Donors: {analytics.total_registered}  |  Most Common: {analytics.most_common_blood_group} ({analytics.most_common_count})  |  Rarest: {analytics.least_common_blood_group} ({analytics.least_common_count})"
            )
            for item in self.tree_analytics.get_children():
                self.tree_analytics.delete(item)
            for bg in analytics.blood_groups:
                self.tree_analytics.insert("", "end", values=(
                    bg.blood_group, bg.total_donors, bg.eligible_donors, bg.temporarily_deferred, bg.permanently_deferred, bg.completed_donations, f"{bg.percentage}%"
                ))
        finally:
            db.close()

    # --------------------------------------------------------------------------
    # VIEW 5: DONATION CAMPS
    # --------------------------------------------------------------------------
    def build_camps_view(self):
        frame = ctk.CTkFrame(self.view_host, fg_color="transparent")

        top_c = ctk.CTkFrame(frame, corner_radius=10, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        top_c.pack(fill="x", pady=(0, 10))

        btn_add_camp = ctk.CTkButton(
            top_c,
            text="➕ Schedule New Camp",
            font=("Segoe UI", 11, "bold"),
            fg_color="#B91C1C",
            hover_color="#991B1B",
            corner_radius=8,
            height=36,
            command=self.open_add_camp_dialog
        )
        btn_add_camp.pack(side="left", padx=14, pady=10)

        tbl_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        tbl_card.pack(fill="both", expand=True)

        cols = ("code", "name", "city", "venue", "dates", "capacity", "donations", "status")
        self.tree_camps = ttk.Treeview(tbl_card, columns=cols, show="headings")
        self.tree_camps.heading("code", text="Camp Code")
        self.tree_camps.heading("name", text="Camp Title")
        self.tree_camps.heading("city", text="City")
        self.tree_camps.heading("venue", text="Venue")
        self.tree_camps.heading("dates", text="Dates")
        self.tree_camps.heading("capacity", text="Volunteers / Capacity")
        self.tree_camps.heading("donations", text="Units Donated")
        self.tree_camps.heading("status", text="Status")

        self.tree_camps.column("code", width=110)
        self.tree_camps.column("name", width=220)
        self.tree_camps.column("city", width=120)
        self.tree_camps.column("venue", width=180)
        self.tree_camps.column("dates", width=160)
        self.tree_camps.column("capacity", width=140, anchor="center")
        self.tree_camps.column("donations", width=100, anchor="center")
        self.tree_camps.column("status", width=100, anchor="center")

        self.tree_camps.pack(fill="both", expand=True, padx=12, pady=12)
        return frame

    def load_camps(self):
        db = SessionLocal()
        try:
            camps = get_camps(db)
            for item in self.tree_camps.get_children():
                self.tree_camps.delete(item)
            for c, donor_cnt, don_cnt in camps:
                self.tree_camps.insert("", "end", values=(
                    c.camp_code, c.name, c.city, c.venue, f"{c.start_date} to {c.end_date}", f"{donor_cnt} / {c.capacity}", don_cnt, c.status
                ))
        finally:
            db.close()

    def open_add_camp_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Schedule Donation Camp")
        dialog.geometry("450x420")
        dialog.transient(self)
        dialog.grab_set()

        f = ctk.CTkFrame(dialog, fg_color="#FFFFFF", corner_radius=12)
        f.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(f, text="Schedule New Donation Camp", font=("Segoe UI", 14, "bold"), text_color="#B91C1C").pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(f, text="Camp Title *", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(4, 2))
        e_name = ctk.CTkEntry(f, height=34, corner_radius=6)
        e_name.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(f, text="Venue *", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(4, 2))
        e_venue = ctk.CTkEntry(f, height=34, corner_radius=6)
        e_venue.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(f, text="City *", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(4, 2))
        e_city = ctk.CTkEntry(f, height=34, corner_radius=6)
        e_city.insert(0, "Bengaluru")
        e_city.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(f, text="Volunteer Capacity *", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(4, 2))
        e_cap = ctk.CTkEntry(f, height=34, corner_radius=6)
        e_cap.insert(0, "100")
        e_cap.pack(fill="x", pady=(0, 12))

        def save_camp():
            c_name, c_venue, c_city = e_name.get().strip(), e_venue.get().strip(), e_city.get().strip()
            c_cap = int(e_cap.get().strip() or "100")

            if not c_name or not c_venue or not c_city:
                messagebox.showerror("Error", "Please fill in all mandatory fields.")
                return

            db = SessionLocal()
            try:
                c_in = CampCreate(
                    name=c_name,
                    venue=c_venue,
                    address=c_venue,
                    city=c_city,
                    start_date=date.today(),
                    end_date=date.today(),
                    capacity=c_cap,
                    organizer="Healthcare Department & LifePoint NGO",
                    contact_phone="+919876543210",
                    status="UPCOMING"
                )
                create_camp(db, c_in)
                messagebox.showinfo("Success", f"Camp '{c_name}' created!")
                dialog.destroy()
                self.load_camps()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))
            finally:
                db.close()

        ctk.CTkButton(f, text="Create Camp", fg_color="#B91C1C", hover_color="#991B1B", height=38, corner_radius=8, command=save_camp).pack(anchor="e", pady=(8, 0))

    # --------------------------------------------------------------------------
    # VIEW 6: BULK CSV IMPORT
    # --------------------------------------------------------------------------
    def build_import_view(self):
        frame = ctk.CTkFrame(self.view_host, fg_color="transparent")

        top_f = ctk.CTkFrame(frame, corner_radius=10, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        top_f.pack(fill="x", pady=(0, 10))

        btn_browse = ctk.CTkButton(
            top_f,
            text="📁 Select CSV File to Validate",
            font=("Segoe UI", 11, "bold"),
            fg_color="#B91C1C",
            hover_color="#991B1B",
            corner_radius=8,
            height=36,
            command=self.handle_browse_csv
        )
        btn_browse.pack(side="left", padx=14, pady=10)

        self.btn_execute_import = ctk.CTkButton(
            top_f,
            text="🚀 Execute Import to Database",
            font=("Segoe UI", 11, "bold"),
            fg_color="#059669",
            hover_color="#047857",
            corner_radius=8,
            height=36,
            state="disabled",
            command=self.handle_execute_import
        )
        self.btn_execute_import.pack(side="left", padx=10)

        self.lbl_import_stats = ctk.CTkLabel(
            top_f,
            text="No file selected. Click Browse to load volunteer CSV dataset.",
            font=("Segoe UI", 11),
            text_color="#64748B"
        )
        self.lbl_import_stats.pack(side="left", padx=10)

        tbl_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        tbl_card.pack(fill="both", expand=True)

        cols = ("row", "name", "phone", "blood_group", "dob", "city", "valid", "notes")
        self.tree_import = ttk.Treeview(tbl_card, columns=cols, show="headings")
        self.tree_import.heading("row", text="Row #")
        self.tree_import.heading("name", text="Full Name")
        self.tree_import.heading("phone", text="Phone")
        self.tree_import.heading("blood_group", text="Group")
        self.tree_import.heading("dob", text="DOB")
        self.tree_import.heading("city", text="City")
        self.tree_import.heading("valid", text="Validation")
        self.tree_import.heading("notes", text="Validation Details / Error Message")

        self.tree_import.column("row", width=60, anchor="center")
        self.tree_import.column("name", width=170)
        self.tree_import.column("phone", width=120)
        self.tree_import.column("blood_group", width=65, anchor="center")
        self.tree_import.column("dob", width=100, anchor="center")
        self.tree_import.column("city", width=110)
        self.tree_import.column("valid", width=90, anchor="center")
        self.tree_import.column("notes", width=260)

        self.tree_import.pack(fill="both", expand=True, padx=12, pady=12)
        self.cached_valid_rows = []
        return frame

    def handle_browse_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            val_result = parse_and_validate_csv(content)
            total = val_result.total_rows
            valid = val_result.valid_rows_count
            errs = val_result.error_rows_count

            self.cached_valid_rows = val_result.valid_rows
            self.lbl_import_stats.configure(text=f"Total: {total} | Valid: {valid} | Invalid: {errs} — Ready for database import.")

            for item in self.tree_import.get_children():
                self.tree_import.delete(item)

            for idx, row in enumerate(val_result.valid_rows):
                self.tree_import.insert("", "end", values=(
                    idx + 1, row.get("full_name"), row.get("phone"), row.get("blood_group"), row.get("date_of_birth"), row.get("city"), "VALID ✓", "Validated for insert"
                ))

            for idx, err in enumerate(val_result.errors):
                self.tree_import.insert("", "end", values=(
                    err.row_number, "-", "-", "-", "-", "-", "ERROR ✗", err.message
                ))

            if valid > 0:
                self.btn_execute_import.configure(state="normal")
            else:
                self.btn_execute_import.configure(state="disabled")

        except Exception as ex:
            messagebox.showerror("Failed to Read CSV", str(ex))

    def handle_execute_import(self):
        if not self.cached_valid_rows:
            messagebox.showinfo("No Rows", "No valid rows available to import.")
            return
        db = SessionLocal()
        try:
            res = execute_csv_import(db, self.cached_valid_rows)
            messagebox.showinfo("Import Completed", f"Successfully imported: {res['imported_count']} volunteers\nSkipped duplicates/errors: {res['skipped_count']}")
            self.cached_valid_rows = []
            self.btn_execute_import.configure(state="disabled")
            self.lbl_import_stats.configure(text=f"Import complete! {res['imported_count']} records saved to database.")
            self.refresh_all()
        except Exception as ex:
            messagebox.showerror("Import Error", str(ex))
        finally:
            db.close()

    # --------------------------------------------------------------------------
    # VIEW 7: REPORTS & EXPORTS
    # --------------------------------------------------------------------------
    def build_reports_view(self):
        frame = ctk.CTkFrame(self.view_host, fg_color="transparent")

        card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        card.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(card, text="📑 Official Healthcare Reports & Data Exports", font=("Segoe UI", 16, "bold"), text_color="#B91C1C").pack(anchor="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(card, text="Generate audited reports in PDF format, export complete donor rosters to CSV, or create a full JSON database snapshot.", font=("Segoe UI", 11), text_color="#64748B").pack(anchor="w", padx=20, pady=(0, 20))

        # 3 Action Cards
        actions = [
            ("📄 Generate Official PDF Report (ReportLab)", "Generates a complete clinical executive summary report with blood group tables and timestamps.", "#B91C1C", "#991B1B", self.export_pdf_file),
            ("📊 Export Donor Registry to CSV", "Exports all registered volunteer donors and screening details to a standard CSV file.", "#059669", "#047857", self.export_csv_file),
            ("💾 Full JSON Database Snapshot Backup", "Creates a timestamped JSON backup snapshot of all database tables (donors, camps, audit logs).", "#0F172A", "#1E293B", self.create_json_backup_file),
        ]

        for title, desc, col, hover_col, cmd in actions:
            action_box = ctk.CTkFrame(card, corner_radius=10, fg_color="#F8FAFC", border_width=1, border_color="#E2E8F0")
            action_box.pack(fill="x", padx=20, pady=8)

            info_f = ctk.CTkFrame(action_box, fg_color="transparent")
            info_f.pack(side="left", padx=16, pady=12)

            ctk.CTkLabel(info_f, text=title, font=("Segoe UI", 13, "bold"), text_color="#0F172A").pack(anchor="w")
            ctk.CTkLabel(info_f, text=desc, font=("Segoe UI", 10), text_color="#64748B").pack(anchor="w")

            btn = ctk.CTkButton(action_box, text="Download / Run", font=("Segoe UI", 11, "bold"), fg_color=col, hover_color=hover_col, corner_radius=8, height=36, width=140, command=cmd)
            btn.pack(side="right", padx=16, pady=12)

        return frame

    def export_pdf_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Documents", "*.pdf")], initialfile=f"lifepoint_report_{datetime.now().strftime('%Y%m%d')}.pdf")
        if file_path:
            db = SessionLocal()
            try:
                pdf_bytes = generate_pdf_report(db)
                with open(file_path, "wb") as f:
                    f.write(pdf_bytes)
                messagebox.showinfo("Export Successful", f"PDF report saved successfully to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                db.close()

    def export_csv_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], initialfile=f"lifepoint_donors_{datetime.now().strftime('%Y%m%d')}.csv")
        if file_path:
            db = SessionLocal()
            try:
                csv_data = export_donors_csv(db)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(csv_data)
                messagebox.showinfo("Export Successful", f"CSV file saved successfully to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                db.close()

    def create_json_backup_file(self):
        db = SessionLocal()
        try:
            res = create_json_backup(db)
            messagebox.showinfo("Backup Successful", f"Full database snapshot saved:\n{res['filename']}\nPath: {res['file_path']}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            db.close()

    # --------------------------------------------------------------------------
    # VIEW 8: AUDIT & ACTIVITY LOGS
    # --------------------------------------------------------------------------
    def build_audit_view(self):
        frame = ctk.CTkFrame(self.view_host, fg_color="transparent")

        top_f = ctk.CTkFrame(frame, corner_radius=10, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        top_f.pack(fill="x", pady=(0, 10))

        btn_refresh = ctk.CTkButton(top_f, text="🔄 Refresh Logs", font=("Segoe UI", 11, "bold"), fg_color="#B91C1C", hover_color="#991B1B", corner_radius=8, height=36, command=self.load_audit_logs)
        btn_refresh.pack(side="left", padx=14, pady=10)

        ctk.CTkLabel(top_f, text="Immutable Chronological System Audit Trail (SQLite Persistence)", font=("Segoe UI", 11), text_color="#64748B").pack(side="left", padx=10)

        tbl_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        tbl_card.pack(fill="both", expand=True)

        cols = ("time", "action", "entity", "entity_id", "desc")
        self.tree_audit = ttk.Treeview(tbl_card, columns=cols, show="headings")
        self.tree_audit.heading("time", text="Timestamp (UTC)")
        self.tree_audit.heading("action", text="Action")
        self.tree_audit.heading("entity", text="Entity Type")
        self.tree_audit.heading("entity_id", text="Entity ID")
        self.tree_audit.heading("desc", text="Description")

        self.tree_audit.column("time", width=160)
        self.tree_audit.column("action", width=120, anchor="center")
        self.tree_audit.column("entity", width=110, anchor="center")
        self.tree_audit.column("entity_id", width=120, anchor="center")
        self.tree_audit.column("desc", width=420)

        self.tree_audit.pack(fill="both", expand=True, padx=12, pady=12)
        return frame

    def load_audit_logs(self):
        db = SessionLocal()
        try:
            logs = get_audit_logs(db, limit=200)
            for item in self.tree_audit.get_children():
                self.tree_audit.delete(item)
            for log in logs:
                t_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "N/A"
                self.tree_audit.insert("", "end", values=(
                    t_str, log.action, log.entity_type, log.entity_id or "-", log.description
                ))
        finally:
            db.close()

    def refresh_all(self):
        self.refresh_dashboard()
        self.load_donors()
        self.load_analytics()
        self.load_camps()
        self.load_audit_logs()


LifePointGUI = LifePointModernApp

def main():
    app = LifePointModernApp()
    app.mainloop()

if __name__ == "__main__":
    main()
